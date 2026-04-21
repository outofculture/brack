"""Unit tests for the git wrapper. These use a real git binary against the
``tmp_repo`` fixture — cheap, deterministic, and catches real git behaviour."""

import pytest

from brack.errors import GitFailure, NotAGitRepoError
from brack.git_ops import GitRunner


def test_find_repo_root_walks_up(tmp_repo):
    nested = tmp_repo.path / "a" / "b"
    nested.mkdir(parents=True)
    assert GitRunner.find_repo_root(nested) == tmp_repo.path


def test_find_repo_root_raises_outside_repo(tmp_path):
    with pytest.raises(NotAGitRepoError):
        GitRunner.find_repo_root(tmp_path)


def test_current_branch_returns_name(tmp_repo):
    runner = GitRunner(tmp_repo.path)
    assert runner.current_branch() == "main"


def test_current_branch_rejects_detached_head(tmp_repo):
    sha = tmp_repo.git("rev-parse", "HEAD").stdout.strip()
    tmp_repo.git("checkout", sha)
    runner = GitRunner(tmp_repo.path)
    with pytest.raises(GitFailure, match="Detached"):
        runner.current_branch()


def test_detect_main_branch_prefers_main(tmp_repo):
    runner = GitRunner(tmp_repo.path)
    assert runner.detect_main_branch() == "main"


def test_detect_main_branch_falls_back_to_master(tmp_repo):
    tmp_repo.git("branch", "-m", "main", "master")
    runner = GitRunner(tmp_repo.path)
    assert runner.detect_main_branch() == "master"


def test_detect_main_branch_raises_if_none(tmp_repo):
    tmp_repo.git("checkout", "-b", "feature")
    tmp_repo.git("branch", "-D", "main")
    runner = GitRunner(tmp_repo.path)
    with pytest.raises(GitFailure, match="No main branch"):
        runner.detect_main_branch()


def test_merge_base_between_feature_and_main(tmp_repo):
    base_sha = tmp_repo.git("rev-parse", "HEAD").stdout.strip()
    tmp_repo.checkout("feature", new=True)
    tmp_repo.commit_file("new.py", "x=1\n", "add new")
    runner = GitRunner(tmp_repo.path)
    assert runner.merge_base("HEAD", "main") == base_sha


def test_file_exists_at_commit(tmp_repo):
    tmp_repo.commit_file("foo.py", "x=1\n", "add foo")
    base_sha = tmp_repo.git("rev-parse", "HEAD").stdout.strip()
    tmp_repo.commit_file("bar.py", "y=2\n", "add bar")
    runner = GitRunner(tmp_repo.path)
    assert runner.file_exists_at(base_sha, "foo.py") is True
    assert runner.file_exists_at(base_sha, "bar.py") is False


def test_stash_push_and_pop_roundtrips_dirty_tree(tmp_repo):
    (tmp_repo.path / "dirty.py").write_text("x=1\n")
    runner = GitRunner(tmp_repo.path)
    assert runner.has_uncommitted_changes() is True
    assert runner.stash_push("brack-test") is True
    assert runner.has_uncommitted_changes() is False
    runner.stash_pop()
    assert runner.has_uncommitted_changes() is True


def test_stash_push_noop_on_clean_tree(tmp_repo):
    runner = GitRunner(tmp_repo.path)
    assert runner.stash_push("unused") is False


def test_checkout_new_creates_branch_at_start_point(tmp_repo):
    sha = tmp_repo.git("rev-parse", "HEAD").stdout.strip()
    runner = GitRunner(tmp_repo.path)
    runner.checkout_new("formatting", sha)
    assert tmp_repo.current_branch() == "formatting"


def test_branch_exists(tmp_repo):
    runner = GitRunner(tmp_repo.path)
    assert runner.branch_exists("main") is True
    assert runner.branch_exists("nope") is False


def test_delete_branch(tmp_repo):
    tmp_repo.checkout("to-delete", new=True)
    tmp_repo.checkout("main")
    runner = GitRunner(tmp_repo.path)
    assert runner.branch_exists("to-delete")
    runner.delete_branch("to-delete")
    assert not runner.branch_exists("to-delete")


def test_commit_round_trip(tmp_repo):
    (tmp_repo.path / "a.py").write_text("x=1\n")
    runner = GitRunner(tmp_repo.path)
    runner.add("a.py")
    assert runner.has_staged_changes()
    runner.commit("add a")
    assert not runner.has_staged_changes()


def test_merge_with_ours_strategy_keeps_current_content(tmp_repo):
    """Simulate the core brack merge pattern: formatting branch was created
    from merge-base and modifies a file; feature branch has diverged and
    modifies the same file. Merging back with ``-X ours`` keeps the feature
    branch's version."""
    tmp_repo.commit_file("t.py", "def f(a,b):\n    return a+b\n", "add t")
    base = tmp_repo.git("rev-parse", "HEAD").stdout.strip()

    tmp_repo.checkout("fmt", new=True)
    (tmp_repo.path / "t.py").write_text("def f(a, b):\n    return a + b\n")
    tmp_repo.git("commit", "-am", "black")

    tmp_repo.checkout("main")
    (tmp_repo.path / "t.py").write_text("def f(a,b):\n    return a - b  # feature change\n")
    tmp_repo.git("commit", "-am", "feature edit")

    runner = GitRunner(tmp_repo.path)
    runner.merge("fmt", message="merge fmt")
    assert "feature change" in tmp_repo.read("t.py")
    assert not runner.in_merge_state()
