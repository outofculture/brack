"""Pytest fixtures for brack tests.

Every integration test uses :func:`tmp_repo` to obtain an isolated git
repository. A mock ``gh`` binary is placed on ``$PATH`` so no real network or
GitHub credentials are required.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import pytest

FIXTURES_DIR = Path(__file__).parent / "_fixtures"
MOCK_GH_SCRIPT = FIXTURES_DIR / "mock_gh.py"

# Make the src/ package importable without installation.
SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@dataclass
class TmpRepo:
    """A throwaway git repo rooted at ``path`` for the duration of a test."""

    path: Path
    default_branch: str = "main"

    def run(self, *args: str, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=self.path,
            check=check,
            capture_output=True,
            text=True,
            env={**os.environ, **(env or {})},
        )

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return self.run("git", *args, check=check)

    def write(self, relpath: str, content: str) -> Path:
        target = self.path / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def read(self, relpath: str) -> str:
        return (self.path / relpath).read_text()

    def commit_file(self, relpath: str, content: str, message: str) -> str:
        self.write(relpath, content)
        self.git("add", relpath)
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def checkout(self, branch: str, *, new: bool = False) -> None:
        if new:
            self.git("checkout", "-b", branch)
        else:
            self.git("checkout", branch)

    def current_branch(self) -> str:
        return self.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    def branches(self) -> list[str]:
        out = self.git("for-each-ref", "--format=%(refname:short)", "refs/heads/").stdout
        return [b for b in out.splitlines() if b]

    def has_branch(self, name: str) -> bool:
        return name in self.branches()

    def log_oneline(self, rev: str = "HEAD") -> list[str]:
        return self.git("log", "--oneline", rev).stdout.splitlines()


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Iterator[TmpRepo]:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    env = {
        "GIT_AUTHOR_NAME": "Brack Tests",
        "GIT_AUTHOR_EMAIL": "tests@brack.local",
        "GIT_COMMITTER_NAME": "Brack Tests",
        "GIT_COMMITTER_EMAIL": "tests@brack.local",
    }
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo_path, check=True)
    for k, v in env.items():
        os.environ.setdefault(k, v)
    subprocess.run(["git", "config", "user.name", "Brack Tests"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "tests@brack.local"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo_path, check=True)

    # Seed with an initial commit so merge-base calculations work.
    (repo_path / "README.md").write_text("# test repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo_path, check=True)

    repo = TmpRepo(repo_path)
    yield repo


@dataclass
class MockGh:
    """Handle to an installed mock ``gh`` binary."""

    bin_dir: Path
    log_path: Path
    config_path: Path
    previous_path: str = ""
    extra_env: dict[str, str] = field(default_factory=dict)

    def invocations(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        records = []
        for line in self.log_path.read_text().splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    def subcommands(self) -> list[list[str]]:
        return [inv["argv"][1:] for inv in self.invocations()]

    def set_config(self, config: dict) -> None:
        self.config_path.write_text(json.dumps(config))

    def reset_log(self) -> None:
        if self.log_path.exists():
            self.log_path.unlink()


@pytest.fixture
def mock_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MockGh:
    bin_dir = tmp_path / "mock_bin"
    bin_dir.mkdir()
    gh_path = bin_dir / "gh"
    # Thin shell shim so the mock runs even when tested binary invokes `gh` directly.
    shim = textwrap.dedent(
        f"""\
        #!{sys.executable}
        import runpy, sys
        sys.argv[0] = "gh"
        runpy.run_path({str(MOCK_GH_SCRIPT)!r}, run_name="__main__")
        """
    )
    gh_path.write_text(shim)
    gh_path.chmod(gh_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    log_path = tmp_path / "gh_log.jsonl"
    config_path = tmp_path / "gh_config.json"
    config_path.write_text("{}")

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("BRACK_MOCK_GH_LOG", str(log_path))
    monkeypatch.setenv("BRACK_MOCK_GH_CONFIG", str(config_path))

    return MockGh(bin_dir=bin_dir, log_path=log_path, config_path=config_path)


@pytest.fixture
def brack_cli(monkeypatch: pytest.MonkeyPatch):
    """Return a callable that runs `python -m brack` in a subprocess."""

    src = str(Path(__file__).parent.parent / "src")

    def _run(*args: str, cwd: Path, env: dict | None = None, check: bool = False) -> subprocess.CompletedProcess:
        invocation_env = {**os.environ, "PYTHONPATH": src + os.pathsep + os.environ.get("PYTHONPATH", "")}
        if env:
            invocation_env.update(env)
        return subprocess.run(
            [sys.executable, "-m", "brack", *args],
            cwd=cwd,
            env=invocation_env,
            capture_output=True,
            text=True,
            check=check,
        )

    return _run
