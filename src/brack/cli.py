"""Command-line entry point.

The CLI surface is intentionally the same as the original bash ``brack`` script
so drop-in replacement works. Pythonic additions (``--verbose``, ``--no-push``,
``--main-branch``, etc.) are strictly additive.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .config import Config
from .errors import BrackError, ExitCode, InvalidArgsError
from .logging import Logger
from .workflow import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="brack",
        description=(
            "Apply black formatting to Python files while keeping feature-branch "
            "diffs clean. Creates a separate branch/PR for formatting changes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  brack                                # format all Python files\n"
            "  brack file1.py file2.py             # format specific files\n"
            "  brack --dry-run                     # preview without changes\n"
            "  brack --cleanup                     # clear error state\n"
            "  brack file.py -- --line-length 100  # pass --line-length to black"
        ),
    )
    p.add_argument("-v", "--version", action="version", version=f"brack {__version__}")
    p.add_argument("-q", "--quiet", action="store_true", help="minimal output, for IDE integration")
    p.add_argument("-V", "--verbose", action="store_true", help="emit debug-level log lines")
    p.add_argument("--dry-run", action="store_true", help="report what would be done without touching git")
    p.add_argument("--cleanup", action="store_true", help="remove the AUTO-BLACK-FORMATTING-ERROR file and exit")
    p.add_argument("--black-path", metavar="PATH", help="path to the black executable")
    p.add_argument("--main-branch", metavar="BRANCH", help="override main-branch auto-detection")
    p.add_argument(
        "--formatting-branch-suffix",
        metavar="SUFFIX",
        default="-auto-black-formatting",
        help="suffix appended to the current branch to name the formatting branch",
    )
    p.add_argument("--no-push", action="store_true", help="do not push the formatting branch to origin")
    p.add_argument("--no-pr", action="store_true", help="do not create or update a pull request")
    p.add_argument(
        "--no-background",
        action="store_true",
        help="run GitHub operations synchronously (easier to script against)",
    )
    p.add_argument("files", nargs="*", metavar="FILES", help="Python files to format")
    return p


def _split_black_passthrough(argv: Sequence[str]) -> tuple[list[str], list[str]]:
    """Split ``argv`` at the first ``--`` (if any); everything after is for black."""
    args = list(argv)
    if "--" in args:
        i = args.index("--")
        return args[:i], args[i + 1 :]
    return args, []


def parse_args(argv: Sequence[str] | None = None) -> Config:
    argv = list(sys.argv[1:] if argv is None else argv)
    own_args, black_args = _split_black_passthrough(argv)
    parser = build_parser()
    ns = parser.parse_args(own_args)
    for f in ns.files:
        if not f.endswith(".py"):
            raise InvalidArgsError(f"'{f}' is not a Python file (must have .py extension)")
    return Config(
        files=list(ns.files),
        black_args=black_args,
        black_path=ns.black_path,
        quiet=ns.quiet,
        verbose=ns.verbose,
        dry_run=ns.dry_run,
        cleanup=ns.cleanup,
        main_branch=ns.main_branch,
        formatting_branch_suffix=ns.formatting_branch_suffix,
        no_push=ns.no_push,
        no_pr=ns.no_pr,
        no_background=ns.no_background,
        cwd=Path.cwd(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        config = parse_args(argv)
    except InvalidArgsError as exc:
        print(f"[ERROR] {exc.message}", file=sys.stderr)
        return int(ExitCode.INVALID_ARGS)
    except SystemExit as exc:
        # argparse handled --help / --version / usage errors.
        return exc.code if isinstance(exc.code, int) else int(ExitCode.INVALID_ARGS)

    logger = Logger(quiet=config.quiet, verbose=config.verbose)
    try:
        run(config, logger=logger)
    except BrackError as exc:
        logger.error(exc.message)
        if exc.context:
            logger.error(exc.context)
        return int(exc.exit_code)
    except KeyboardInterrupt:
        logger.error("Interrupted")
        return int(ExitCode.INTERRUPTED)
    return int(ExitCode.SUCCESS)
