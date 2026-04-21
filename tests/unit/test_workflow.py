"""Unit tests for the orchestrator. These exercise the full run() on a real
temp git repo using a real black + a mock gh. The tests are fast (<1s each)
because black only touches a handful of small files."""

import pytest

from brack.config import Config
from brack.errors import ErrorStatePresentError, InvalidArgsError, NotAGitRepoError
from brack.error_state import ERROR_FILENAME, error_state_present, write_error_state
from brack.git_ops import GitRunner
from brack.workflow import run


# --- helpers ---------------------------------------------------------------

UGLY_EXISTING = "def f(a,b):\n    return a+b\n"
UGLY_NEW = "def g(c ,d):\n    return c-d\n"


def _feature_branch(tmp_repo, *, committed_uglies: list[str] | None = None):
    """Seed ``tmp_repo`` with the given files on a feature branch."""
    tmp_repo.commit_file("existing.py", UGLY_EXISTING, "seed existing")
    tmp_repo.checkout("feature", new=True)
    for f in committed_uglies or []:
        tmp_repo.commit_file(f, UGLY_NEW, f"add {f}")
    return tmp_repo


def _config(cwd, **overrides) -> Config:
    kwargs = {"cwd": cwd, "no_background": True, "no_push": True, "no_pr": True}
    kwargs.update(overrides)
    return Config(**kwargs)


# --- happy paths -----------------------------------------------------------


def test_run_formats_existing_file_in_separate_branch(tmp_repo):
    _feature_branch(tmp_repo)
    result = run(_config(tmp_repo.path, files=["existing.py"]))
    assert result.formatted_existing == ["existing.py"]
    assert result.formatted_new == []
    # formatting branch must exist
    assert tmp_repo.has_branch("feature-auto-black-formatting")
    # we should be back on the feature branch
    assert tmp_repo.current_branch() == "feature"
    # file in working tree is formatted
    assert tmp_repo.read("existing.py") == "def f(a, b):\n    return a + b\n"


def test_run_formats_new_file_in_current_branch_no_separate_branch(tmp_repo):
    _feature_branch(tmp_repo, committed_uglies=["new_one.py"])
    result = run(_config(tmp_repo.path, files=["new_one.py"]))
    assert result.formatted_new == ["new_one.py"]
    assert result.formatted_existing == []
    # No formatting branch should be created for new-only runs
    assert not tmp_repo.has_branch("feature-auto-black-formatting")
    assert tmp_repo.current_branch() == "feature"


def test_run_handles_mixed_existing_and_new_files(tmp_repo):
    _feature_branch(tmp_repo, committed_uglies=["brand_new.py"])
    result = run(_config(tmp_repo.path, files=["existing.py", "brand_new.py"]))
    assert sorted(result.formatted_existing) == ["existing.py"]
    assert sorted(result.formatted_new) == ["brand_new.py"]


def test_run_reuses_existing_formatting_branch(tmp_repo):
    _feature_branch(tmp_repo)
    run(_config(tmp_repo.path, files=["existing.py"]))
    assert tmp_repo.has_branch("feature-auto-black-formatting")
    sha_after_first = tmp_repo.git("rev-parse", "feature-auto-black-formatting").stdout.strip()

    # Mess the file up again and run a second time — branch should be reused.
    tmp_repo.write("existing.py", UGLY_EXISTING)
    tmp_repo.git("commit", "-am", "re-uglify")
    run(_config(tmp_repo.path, files=["existing.py"]))
    assert tmp_repo.has_branch("feature-auto-black-formatting")
    # Branch ref may have advanced but the branch wasn't deleted.
    assert tmp_repo.git("rev-parse", "feature-auto-black-formatting").stdout.strip()


def test_run_stashes_and_restores_dirty_working_dir(tmp_repo):
    _feature_branch(tmp_repo)
    tmp_repo.write("scratch.txt", "dirty\n")  # untracked
    run(_config(tmp_repo.path, files=["existing.py"]))
    assert (tmp_repo.path / "scratch.txt").read_text() == "dirty\n"
    assert tmp_repo.current_branch() == "feature"


def test_run_returns_to_feature_branch_after_success(tmp_repo):
    _feature_branch(tmp_repo)
    run(_config(tmp_repo.path, files=["existing.py"]))
    assert tmp_repo.current_branch() == "feature"


# --- error paths -----------------------------------------------------------


def test_run_rejects_non_python_file(tmp_repo):
    tmp_repo.commit_file("not_py.txt", "hi\n", "add")
    with pytest.raises(InvalidArgsError):
        run(_config(tmp_repo.path, files=["not_py.txt"]))


def test_run_rejects_outside_repo(tmp_path):
    from pathlib import Path

    (tmp_path / "standalone.py").write_text("x=1\n")
    with pytest.raises(NotAGitRepoError):
        run(_config(tmp_path, files=["standalone.py"]))


def test_run_refuses_when_error_state_present(tmp_repo):
    _feature_branch(tmp_repo)
    write_error_state(tmp_repo.path, "prior failure")
    with pytest.raises(ErrorStatePresentError):
        run(_config(tmp_repo.path, files=["existing.py"]))


def test_cleanup_removes_error_state(tmp_repo):
    _feature_branch(tmp_repo)
    write_error_state(tmp_repo.path, "prior failure")
    result = run(_config(tmp_repo.path, cleanup=True))
    assert result.skipped is True
    assert not error_state_present(tmp_repo.path)


# --- dry run ---------------------------------------------------------------


def test_dry_run_reports_categories_and_makes_no_mutations(tmp_repo):
    _feature_branch(tmp_repo, committed_uglies=["brand_new.py"])
    head_before = tmp_repo.git("rev-parse", "HEAD").stdout.strip()
    branches_before = set(tmp_repo.branches())

    result = run(_config(tmp_repo.path, files=["existing.py", "brand_new.py"], dry_run=True))
    assert result.formatted_existing == ["existing.py"]
    assert result.formatted_new == ["brand_new.py"]
    # No branch created
    assert set(tmp_repo.branches()) == branches_before
    # No new commits
    assert tmp_repo.git("rev-parse", "HEAD").stdout.strip() == head_before
    # Files still have their original ugly content.
    assert tmp_repo.read("existing.py") == UGLY_EXISTING
    assert tmp_repo.read("brand_new.py") == UGLY_NEW


# --- pass-through and pythonic extras --------------------------------------


def test_black_args_are_passed_through(tmp_repo, monkeypatch):
    """``brack file.py -- --line-length=40`` must forward the flag to black."""
    _feature_branch(tmp_repo)
    captured: list[list[str]] = []

    real_run = __import__("brack.black_runner", fromlist=["run_black"]).run_black

    def spy(black_path, files, *, extra_args=(), cwd=None):
        captured.append([*extra_args])
        return real_run(black_path, files, extra_args=extra_args, cwd=cwd)

    monkeypatch.setattr("brack.workflow.black_runner.run_black", spy)
    run(_config(tmp_repo.path, files=["existing.py"], black_args=["--line-length=40"]))
    assert any("--line-length=40" in args for args in captured)


def test_main_branch_override(tmp_repo):
    """--main-branch lets the user skip auto-detection."""
    # Create an alt base branch with an older HEAD than main.
    tmp_repo.commit_file("existing.py", UGLY_EXISTING, "seed existing")
    tmp_repo.git("branch", "release")
    tmp_repo.commit_file("other.py", "z=1\n", "post-release")
    tmp_repo.checkout("feature", new=True)
    run(_config(tmp_repo.path, files=["existing.py"], main_branch="release"))
    assert tmp_repo.has_branch("feature-auto-black-formatting")
