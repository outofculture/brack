"""CLI integration tests — invoke ``python -m brack`` in a subprocess.

These tests run the binary end-to-end in an isolated git repo with a mock
``gh`` on PATH. They cover the behavioural gaps identified in the original
shell test suite: stdout/exit-code shape under --quiet, --dry-run zero-
mutation, --black-path, `-- <black args>` pass-through, path handling, etc.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

UGLY = "def f(a,b):\n    return a+b\n"
FORMATTED = "def f(a, b):\n    return a + b\n"


def _seed_feature(tmp_repo, *, extra_new: dict | None = None):
    tmp_repo.commit_file("existing.py", UGLY, "seed existing")
    tmp_repo.checkout("feature", new=True)
    for name, body in (extra_new or {}).items():
        tmp_repo.commit_file(name, body, f"add {name}")


def _no_bg_args() -> list[str]:
    return ["--no-push", "--no-pr", "--no-background"]


# --- exit codes -------------------------------------------------------------


def test_exit_code_2_when_outside_git_repo(brack_cli, tmp_path):
    (tmp_path / "lonely.py").write_text(UGLY)
    result = brack_cli("lonely.py", cwd=tmp_path)
    assert result.returncode == 2


def test_exit_code_1_for_non_py_file(brack_cli, tmp_repo):
    (tmp_repo.path / "a.txt").write_text("hi\n")
    result = brack_cli("a.txt", cwd=tmp_repo.path)
    assert result.returncode == 1
    assert "not a Python file" in (result.stderr + result.stdout)


def test_exit_code_3_when_error_state_file_present(brack_cli, tmp_repo):
    _seed_feature(tmp_repo)
    (tmp_repo.path / "AUTO-BLACK-FORMATTING-ERROR").write_text("prior\n")
    result = brack_cli("existing.py", cwd=tmp_repo.path)
    assert result.returncode == 3


def test_unknown_flag_exits_2(brack_cli, tmp_repo):
    result = brack_cli("--not-a-flag", cwd=tmp_repo.path)
    assert result.returncode == 2


# --- --quiet output shape ---------------------------------------------------


def test_quiet_mode_emits_only_summary_line(brack_cli, tmp_repo, mock_gh):
    _seed_feature(tmp_repo)
    result = brack_cli("--quiet", *_no_bg_args(), "existing.py", cwd=tmp_repo.path)
    assert result.returncode == 0
    # stdout has a single summary line, stderr is silent (no [INFO] noise)
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("brack: formatted")
    assert "[INFO]" not in result.stderr


# --- --dry-run zero mutation ------------------------------------------------


def test_dry_run_makes_no_git_mutations(brack_cli, tmp_repo):
    _seed_feature(tmp_repo, extra_new={"new_one.py": UGLY})
    head_before = tmp_repo.git("rev-parse", "HEAD").stdout.strip()
    branches_before = sorted(tmp_repo.branches())
    result = brack_cli("--dry-run", "--no-push", "--no-pr", "existing.py", "new_one.py", cwd=tmp_repo.path)
    assert result.returncode == 0
    assert tmp_repo.git("rev-parse", "HEAD").stdout.strip() == head_before
    assert sorted(tmp_repo.branches()) == branches_before
    assert tmp_repo.read("existing.py") == UGLY


# --- --black-path -----------------------------------------------------------


def test_black_path_invokes_supplied_binary(brack_cli, tmp_repo, tmp_path):
    """Install a fake black that records args then exits 0 without changes."""
    log = tmp_path / "black.log"
    fake = tmp_path / "fake_black"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import sys, pathlib\n"
        f"pathlib.Path({str(log)!r}).write_text(' '.join(sys.argv[1:]))\n"
        "sys.exit(0)\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    _seed_feature(tmp_repo)
    result = brack_cli(
        "--black-path", str(fake), *_no_bg_args(), "existing.py", cwd=tmp_repo.path
    )
    assert result.returncode == 0
    # The fake was invoked with the file we asked for
    assert "existing.py" in log.read_text()


# --- -- <black args> pass-through ------------------------------------------


def test_black_args_after_double_dash_reach_black(brack_cli, tmp_repo, tmp_path):
    log = tmp_path / "black.log"
    fake = tmp_path / "fake_black"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import sys, pathlib\n"
        f"pathlib.Path({str(log)!r}).write_text(' '.join(sys.argv[1:]))\n"
        "sys.exit(0)\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    _seed_feature(tmp_repo)
    result = brack_cli(
        "--black-path", str(fake), *_no_bg_args(),
        "existing.py", "--", "--line-length", "100",
        cwd=tmp_repo.path,
    )
    assert result.returncode == 0
    captured = log.read_text()
    assert "--line-length 100" in captured


# --- path handling ----------------------------------------------------------


def test_absolute_file_path_accepted(brack_cli, tmp_repo, mock_gh):
    _seed_feature(tmp_repo)
    abs_path = str(tmp_repo.path / "existing.py")
    result = brack_cli(*_no_bg_args(), abs_path, cwd=tmp_repo.path)
    assert result.returncode == 0
    assert tmp_repo.read("existing.py") == FORMATTED


def test_relative_path_from_subdirectory(brack_cli, tmp_repo, mock_gh):
    """Run brack from a sub-directory and use a path relative to that cwd."""
    _seed_feature(tmp_repo)
    sub = tmp_repo.path / "sub"
    sub.mkdir()
    result = brack_cli(*_no_bg_args(), "../existing.py", cwd=sub)
    assert result.returncode == 0, result.stderr
    assert tmp_repo.read("existing.py") == FORMATTED


def test_file_with_spaces_in_name(brack_cli, tmp_repo, mock_gh):
    # Overwrite seed to use a space-filled filename.
    tmp_repo.commit_file("has space.py", UGLY, "seed spaces")
    tmp_repo.checkout("feature", new=True)
    result = brack_cli(*_no_bg_args(), "has space.py", cwd=tmp_repo.path)
    assert result.returncode == 0
    assert tmp_repo.read("has space.py") == FORMATTED


# --- discovery mode ---------------------------------------------------------


def test_discovery_formats_all_py_files_in_repo(brack_cli, tmp_repo, mock_gh):
    tmp_repo.commit_file("a.py", UGLY, "add a")
    tmp_repo.commit_file("b.py", UGLY, "add b")
    tmp_repo.checkout("feature", new=True)
    result = brack_cli(*_no_bg_args(), cwd=tmp_repo.path)
    assert result.returncode == 0, result.stderr
    assert tmp_repo.read("a.py") == FORMATTED
    assert tmp_repo.read("b.py") == FORMATTED


# --- --cleanup --------------------------------------------------------------


def test_cleanup_removes_error_state(brack_cli, tmp_repo):
    _seed_feature(tmp_repo)
    (tmp_repo.path / "AUTO-BLACK-FORMATTING-ERROR").write_text("prior\n")
    result = brack_cli("--cleanup", cwd=tmp_repo.path)
    assert result.returncode == 0
    assert not (tmp_repo.path / "AUTO-BLACK-FORMATTING-ERROR").exists()


# --- formatting-branch reuse across runs -----------------------------------


def test_formatting_branch_reused_on_second_run(brack_cli, tmp_repo, mock_gh):
    _seed_feature(tmp_repo)
    # First run creates formatting branch.
    brack_cli(*_no_bg_args(), "existing.py", cwd=tmp_repo.path)
    assert tmp_repo.has_branch("feature-auto-black-formatting")
    first_sha = tmp_repo.git("rev-parse", "feature-auto-black-formatting").stdout.strip()

    # Re-uglify the file and run again. Branch must still exist afterwards.
    tmp_repo.write("existing.py", UGLY)
    tmp_repo.git("commit", "-am", "re-uglify")
    result = brack_cli(*_no_bg_args(), "existing.py", cwd=tmp_repo.path)
    assert result.returncode == 0
    assert tmp_repo.has_branch("feature-auto-black-formatting")
    assert tmp_repo.git("rev-parse", "feature-auto-black-formatting").stdout.strip()
    # Branch is the SAME branch (same name); may have advanced or not, but not deleted.
    _ = first_sha  # retained for debug


# --- background ops path: gh invocation --------------------------------------


def test_gh_pr_create_invoked_when_no_existing_pr(brack_cli, tmp_repo, mock_gh):
    _seed_feature(tmp_repo)
    # Configure bare remote so `git push` succeeds.
    _setup_bare_remote(tmp_repo)
    result = brack_cli("--no-background", "existing.py", cwd=tmp_repo.path)
    assert result.returncode == 0, result.stderr
    subs = mock_gh.subcommands()
    flat = [s[0:2] for s in subs if len(s) >= 2]
    assert ["pr", "list"] in flat
    assert ["pr", "create"] in flat


def test_gh_pr_edit_used_when_pr_already_exists(brack_cli, tmp_repo, mock_gh):
    _seed_feature(tmp_repo)
    _setup_bare_remote(tmp_repo)
    mock_gh.set_config({"pr_list": {"exit": 0, "stdout": "https://github.com/x/y/pull/5"}})
    result = brack_cli("--no-background", "existing.py", cwd=tmp_repo.path)
    assert result.returncode == 0, result.stderr
    subs = mock_gh.subcommands()
    flat = [s[0:2] for s in subs if len(s) >= 2]
    assert ["pr", "edit"] in flat
    assert ["pr", "create"] not in flat


# --- background error reported into AUTO-BLACK-FORMATTING-ERROR -------------


def test_background_error_logged_to_error_file(brack_cli, tmp_repo, mock_gh):
    _seed_feature(tmp_repo)
    # Make pr create fail so the background path writes an error block.
    mock_gh.set_config(
        {
            "pr_list": {"exit": 0, "stdout": ""},
            "pr_create": {"exit": 1, "stdout": "", "stderr": "boom"},
        }
    )
    _setup_bare_remote(tmp_repo)
    brack_cli("--no-background", "existing.py", cwd=tmp_repo.path)
    err_file = tmp_repo.path / "AUTO-BLACK-FORMATTING-ERROR"
    assert err_file.exists()
    assert "BACKGROUND PROCESS ERROR" in err_file.read_text()


# --- helpers ----------------------------------------------------------------


def _setup_bare_remote(tmp_repo):
    """Create a bare git repo adjacent to the test repo and wire it as origin."""
    bare = tmp_repo.path.parent / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
    tmp_repo.git("remote", "add", "origin", str(bare))
