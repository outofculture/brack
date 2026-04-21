"""Configuration dataclass passed through the workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """All knobs that affect a single `brack.run()` invocation.

    `files` is the positional list from the CLI. Empty means "discover all .py files".
    `black_args` is everything after `--`.
    """

    files: list[str] = field(default_factory=list)
    black_args: list[str] = field(default_factory=list)
    black_path: str | None = None
    quiet: bool = False
    verbose: bool = False
    dry_run: bool = False
    cleanup: bool = False
    main_branch: str | None = None
    formatting_branch_suffix: str = "-auto-black-formatting"
    commit_message_prefix: str = "style: apply black formatting"
    no_push: bool = False
    no_pr: bool = False
    no_background: bool = False
    cwd: Path = field(default_factory=Path.cwd)
