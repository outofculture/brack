"""Wrappers around ``gh`` plus ``git push``, with retry logic for network ops.

The bash version does these as fire-and-forget background processes. The
Python version exposes them as plain functions that can be scheduled onto a
thread (for parity with "local ops return fast") or invoked synchronously
(easier to test, easier to script).
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class PushOutcome:
    success: bool
    attempts: int
    stdout: str
    stderr: str
    returncode: int


def push_with_retry(
    branch: str,
    *,
    cwd: Path,
    attempts: int = 3,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    force_with_lease: bool = True,
) -> PushOutcome:
    """Push ``branch`` to origin, retrying up to ``attempts`` times with
    exponential backoff. Authentication errors abort retry immediately."""
    last_result: subprocess.CompletedProcess | None = None
    delay = base_delay
    args = ["git", "push"]
    if force_with_lease:
        args.append("--force-with-lease")
    args += ["-u", "origin", branch]
    attempt = 0
    for attempt in range(1, attempts + 1):
        last_result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
        if last_result.returncode == 0:
            return PushOutcome(True, attempt, last_result.stdout, last_result.stderr, 0)
        stderr = last_result.stderr or ""
        if "Authentication failed" in stderr or "permission denied" in stderr.lower():
            break
        if attempt < attempts:
            sleep(delay)
            delay *= 2
    assert last_result is not None
    return PushOutcome(
        False, attempt, last_result.stdout, last_result.stderr, last_result.returncode
    )


def gh_available() -> bool:
    return shutil.which("gh") is not None


def gh_authenticated(cwd: Path | None = None) -> bool:
    if not gh_available():
        return False
    return subprocess.run(
        ["gh", "auth", "status"], cwd=cwd, capture_output=True, text=True
    ).returncode == 0


def find_existing_pr(branch: str, base: str, *, cwd: Path) -> str | None:
    """Return the URL of an existing PR for ``branch`` -> ``base``, or None."""
    result = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--base", base, "--json", "url", "--jq", ".[0].url"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    if not url or url == "null":
        return None
    return url


def create_pr(branch: str, base: str, *, title: str, body: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh", "pr", "create", "--head", branch, "--base", base, "--title", title, "--body", body],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def update_pr(url: str, *, title: str, body: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh", "pr", "edit", url, "--title", title, "--body", body],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def render_pr_body(formatting_branch: str, base_branch: str, files: Iterable[str]) -> str:
    original = formatting_branch.replace("-auto-black-formatting", "")
    lines = [
        "## Summary",
        "",
        f"This PR applies black formatting to Python files in the `{original}` branch.",
        "",
        "## Changes",
        "",
        "Formatting-only changes applied by the `black` Python code formatter. No functional changes.",
        "",
    ]
    file_list = list(files)
    if file_list:
        lines += ["### Files Modified", ""]
        lines += [f"- `{f}`" for f in file_list]
        lines.append("")
    lines += [
        "## Review Notes",
        "",
        "- These are formatting-only changes with no functional modifications",
        "- All changes were applied automatically by `black`",
        "- Safe to merge without detailed code review",
        "",
        f"Target base branch: `{base_branch}`.",
    ]
    return "\n".join(lines)


def render_pr_title(formatting_branch: str) -> str:
    original = formatting_branch.replace("-auto-black-formatting", "")
    return f"style: apply black formatting for {original}"


@dataclass
class BackgroundJob:
    """Handle for a thread running a non-blocking GitHub operation."""

    thread: threading.Thread
    errors: list[BaseException] = field(default_factory=list)

    def join(self, timeout: float | None = None) -> None:
        self.thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        return self.thread.is_alive()


def run_in_background(target: Callable[[], None]) -> BackgroundJob:
    job = BackgroundJob(thread=None)  # type: ignore[arg-type]

    def _wrapped() -> None:
        try:
            target()
        except BaseException as exc:
            job.errors.append(exc)

    t = threading.Thread(target=_wrapped, daemon=True)
    job.thread = t
    t.start()
    return job
