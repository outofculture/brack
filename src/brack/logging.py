"""Structured stderr logging matching the bash tool's output format.

Each line is prefixed with a bracketed level tag (e.g. `[INFO]`). Colour codes
are emitted only when stderr is a TTY, so test assertions can use the plain
prefix. Quiet mode suppresses everything except explicit `out()` calls.
"""

from __future__ import annotations

import sys
from typing import TextIO

_COLORS = {
    "INFO": "\033[0;34m",
    "WARN": "\033[1;33m",
    "ERROR": "\033[0;31m",
    "SUCCESS": "\033[0;32m",
}
_RESET = "\033[0m"


class Logger:
    def __init__(self, *, quiet: bool = False, verbose: bool = False, stream: TextIO | None = None) -> None:
        self.quiet = quiet
        self.verbose = verbose
        self.stream = stream if stream is not None else sys.stderr

    def _emit(self, level: str, message: str) -> None:
        use_color = hasattr(self.stream, "isatty") and self.stream.isatty()
        if use_color:
            prefix = f"{_COLORS[level]}[{level}]{_RESET}"
        else:
            prefix = f"[{level}]"
        print(f"{prefix} {message}", file=self.stream)

    def info(self, message: str) -> None:
        if self.quiet:
            return
        self._emit("INFO", message)

    def debug(self, message: str) -> None:
        if not self.verbose:
            return
        self._emit("INFO", message)

    def warn(self, message: str) -> None:
        self._emit("WARN", message)

    def error(self, message: str) -> None:
        self._emit("ERROR", message)

    def success(self, message: str) -> None:
        if self.quiet:
            return
        self._emit("SUCCESS", message)

    def out(self, message: str) -> None:
        """Unconditional message to stdout (IDE-friendly summary line)."""
        print(message)
