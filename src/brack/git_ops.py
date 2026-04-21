"""Thin, typed wrappers around the ``git`` CLI.

Each method runs a single git command in the given ``repo_root``. Failures are
surfaced as :class:`GitFailure` with the stderr attached as ``context``.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import GitFailure, NotAGitRepoError


@dataclass
class GitRunner:
    repo_root: Path

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            raise GitFailure(
                f"git {' '.join(args)} failed (exit {result.returncode})",
                context=result.stderr.strip() or result.stdout.strip(),
            )
        return result

    # ---- repo + branch inspection -----------------------------------------

    @staticmethod
    def find_repo_root(start: Path) -> Path:
        """Walk upwards from ``start`` looking for a ``.git`` directory."""
        start = start.resolve()
        if start.is_file():
            start = start.parent
        for parent in [start, *start.parents]:
            if (parent / ".git").exists():
                return parent
        raise NotAGitRepoError(f"Not in a git repository: {start}")

    def current_branch(self) -> str:
        out = self._run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if out == "HEAD":
            raise GitFailure("Detached HEAD", context="checkout a branch first")
        return out

    def branch_exists(self, name: str) -> bool:
        return self._run("rev-parse", "--verify", name, check=False).returncode == 0

    def detect_main_branch(self) -> str:
        for candidate in ("main", "master", "origin/main", "origin/master"):
            if self.branch_exists(candidate):
                return candidate
        raise GitFailure("No main branch found", context="tried: main, master, origin/main, origin/master")

    def merge_base(self, a: str, b: str) -> str:
        out = self._run("merge-base", a, b).stdout.strip()
        if not out:
            raise GitFailure(f"Empty merge-base between {a} and {b}")
        return out

    def file_exists_at(self, commit: str, path: str) -> bool:
        return self._run("show", f"{commit}:{path}", check=False).returncode == 0

    # ---- stash ------------------------------------------------------------

    def has_uncommitted_changes(self) -> bool:
        return bool(self._run("status", "--porcelain").stdout.strip())

    def stash_push(self, message: str) -> bool:
        """Stash including untracked files. Returns True if a stash was created."""
        if not self.has_uncommitted_changes():
            return False
        self._run("stash", "push", "-u", "-m", message)
        return True

    def stash_pop(self) -> None:
        self._run("stash", "pop")

    def stash_list(self) -> list[str]:
        return self._run("stash", "list").stdout.splitlines()

    # ---- checkout / branch management ------------------------------------

    def checkout(self, name: str) -> None:
        self._run("checkout", name)

    def checkout_new(self, name: str, start_point: str) -> None:
        self._run("checkout", "-b", name, start_point)

    def delete_branch(self, name: str) -> None:
        self._run("branch", "-D", name)

    # ---- staging / commit / merge ----------------------------------------

    def add(self, *paths: str) -> None:
        self._run("add", "--", *paths)

    def has_staged_changes(self) -> bool:
        return self._run("diff", "--cached", "--quiet", check=False).returncode != 0

    def commit(self, message: str) -> None:
        self._run("commit", "-m", message)

    def merge(self, branch: str, *, message: str, strategy_option: str = "ours") -> None:
        """Merge ``branch`` into current branch. Uses ``-X ours`` by default to
        auto-resolve conflicts by keeping the current branch's content (since
        black will be re-run over the merged tree anyway)."""
        args = ["merge", "--no-ff", f"-X{strategy_option}", "-m", message, branch]
        self._run(*args)

    def in_merge_state(self) -> bool:
        return (self.repo_root / ".git" / "MERGE_HEAD").exists()

    def merge_abort(self) -> None:
        self._run("merge", "--abort", check=False)

    # ---- remote ----------------------------------------------------------

    def has_remote_origin(self) -> bool:
        return self._run("remote", "get-url", "origin", check=False).returncode == 0

    def push(self, branch: str, *, force_with_lease: bool = True) -> subprocess.CompletedProcess:
        args = ["push"]
        if force_with_lease:
            args.append("--force-with-lease")
        args += ["-u", "origin", branch]
        return self._run(*args, check=False)
