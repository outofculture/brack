import json
import subprocess
from pathlib import Path

import pytest

from brack.github_ops import (
    create_pr,
    find_existing_pr,
    gh_authenticated,
    push_with_retry,
    render_pr_body,
    render_pr_title,
    run_in_background,
    update_pr,
)


def test_render_pr_title_strips_suffix():
    assert render_pr_title("feature-x-auto-black-formatting") == "style: apply black formatting for feature-x"


def test_render_pr_body_includes_file_list():
    body = render_pr_body("feat-auto-black-formatting", "main", ["a.py", "dir/b.py"])
    assert "- `a.py`" in body
    assert "- `dir/b.py`" in body
    assert "Target base branch: `main`" in body


def test_render_pr_body_omits_files_section_when_empty():
    body = render_pr_body("feat-auto-black-formatting", "main", [])
    assert "Files Modified" not in body


def test_find_existing_pr_returns_none_when_no_prs(tmp_repo, mock_gh):
    # default mock config: pr list returns empty stdout
    assert find_existing_pr("my-branch", "main", cwd=tmp_repo.path) is None
    assert mock_gh.subcommands()[0][:2] == ["pr", "list"]


def test_find_existing_pr_returns_url_when_one_exists(tmp_repo, mock_gh):
    mock_gh.set_config({"pr_list": {"exit": 0, "stdout": "https://github.com/x/y/pull/7"}})
    assert find_existing_pr("my-branch", "main", cwd=tmp_repo.path) == "https://github.com/x/y/pull/7"


def test_create_pr_invokes_gh_with_right_arguments(tmp_repo, mock_gh):
    create_pr("fmt", "main", title="T", body="B", cwd=tmp_repo.path)
    invocations = mock_gh.subcommands()
    assert invocations[0][:3] == ["pr", "create", "--head"]
    assert "fmt" in invocations[0]
    assert "--title" in invocations[0]


def test_update_pr_invokes_gh_pr_edit(tmp_repo, mock_gh):
    update_pr("https://github.com/x/y/pull/1", title="T", body="B", cwd=tmp_repo.path)
    invocations = mock_gh.subcommands()
    assert invocations[0][:2] == ["pr", "edit"]


def test_gh_authenticated_true_when_mock_auth_succeeds(tmp_repo, mock_gh):
    assert gh_authenticated(cwd=tmp_repo.path) is True


def test_gh_authenticated_false_when_mock_auth_fails(tmp_repo, mock_gh):
    mock_gh.set_config({"auth": {"exit": 1, "stdout": ""}})
    assert gh_authenticated(cwd=tmp_repo.path) is False


def test_push_with_retry_returns_success_on_first_attempt(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kw):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    sleeps: list[float] = []
    outcome = push_with_retry("feat", cwd=tmp_path, sleep=sleeps.append)
    assert outcome.success is True
    assert outcome.attempts == 1
    assert sleeps == []


def test_push_with_retry_backs_off_and_retries(tmp_path, monkeypatch):
    responses = [
        subprocess.CompletedProcess([], 1, "", "network error"),
        subprocess.CompletedProcess([], 1, "", "network error"),
        subprocess.CompletedProcess([], 0, "", ""),
    ]

    def fake_run(args, **kw):
        return responses.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    sleeps: list[float] = []
    outcome = push_with_retry("feat", cwd=tmp_path, base_delay=1.0, sleep=sleeps.append)
    assert outcome.success is True
    assert outcome.attempts == 3
    assert sleeps == [1.0, 2.0]


def test_push_with_retry_aborts_on_auth_error(tmp_path, monkeypatch):
    responses = [subprocess.CompletedProcess([], 128, "", "Authentication failed")]

    def fake_run(args, **kw):
        return responses.pop(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    sleeps: list[float] = []
    outcome = push_with_retry("feat", cwd=tmp_path, sleep=sleeps.append)
    assert outcome.success is False
    assert outcome.attempts == 1  # aborted immediately, no retries
    assert sleeps == []


def test_run_in_background_captures_exceptions():
    def boom():
        raise RuntimeError("nope")

    job = run_in_background(boom)
    job.join(timeout=1)
    assert not job.is_alive()
    assert len(job.errors) == 1
    assert isinstance(job.errors[0], RuntimeError)
