"""Exceptions and exit codes.

Exit codes match the original bash tool so scripts depending on them keep working.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    INVALID_ARGS = 1
    NOT_GIT_REPO = 2
    ERROR_STATE = 3
    GENERAL_ERROR = 4
    INTERRUPTED = 130


class BrackError(Exception):
    """Base class for brack failures that map to a specific exit code."""

    exit_code: ExitCode = ExitCode.GENERAL_ERROR

    def __init__(self, message: str, *, context: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context


class InvalidArgsError(BrackError):
    exit_code = ExitCode.INVALID_ARGS


class NotAGitRepoError(BrackError):
    exit_code = ExitCode.NOT_GIT_REPO


class ErrorStatePresentError(BrackError):
    exit_code = ExitCode.ERROR_STATE


class BlackFailure(BrackError):
    """Black exited non-zero on supplied files."""

    exit_code = ExitCode.GENERAL_ERROR


class GitFailure(BrackError):
    exit_code = ExitCode.GENERAL_ERROR


class MergeConflictError(GitFailure):
    """A merge conflict was encountered that we could not auto-resolve."""
