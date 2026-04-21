"""Wrap invocation of the ``black`` formatter.

We track file checksums before and after running black so we can report which
files actually changed (the existing bash tool does the same so the commit
message reflects reality).
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .errors import BlackFailure


def resolve_black(explicit: str | None) -> str:
    """Return an absolute path to the black executable, or raise."""
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            raise BlackFailure(f"Custom black executable not found: {explicit}")
        if not path.is_file():
            raise BlackFailure(f"Custom black path is not a file: {explicit}")
        return str(path)
    found = shutil.which("black")
    if not found:
        raise BlackFailure("black not found on PATH. Install with: pip install black")
    return found


def _checksum(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


@dataclass
class BlackResult:
    changed: list[str]
    stdout: str
    stderr: str


def run_black(
    black_path: str,
    files: Iterable[str],
    *,
    extra_args: Iterable[str] = (),
    cwd: Path | None = None,
) -> BlackResult:
    file_list = list(files)
    if not file_list:
        return BlackResult(changed=[], stdout="", stderr="")
    before = {}
    for rel in file_list:
        p = (cwd / rel) if cwd else Path(rel)
        if p.exists():
            before[rel] = _checksum(p)
    argv = [black_path, *extra_args, *file_list]
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise BlackFailure(
            f"black exited with code {result.returncode}",
            context=(result.stderr or result.stdout).strip(),
        )
    changed = []
    for rel in file_list:
        p = (cwd / rel) if cwd else Path(rel)
        after = _checksum(p) if p.exists() else None
        if after is not None and before.get(rel) != after:
            changed.append(rel)
    return BlackResult(changed=changed, stdout=result.stdout, stderr=result.stderr)
