from brack.errors import (
    BlackFailure,
    BrackError,
    ErrorStatePresentError,
    ExitCode,
    InvalidArgsError,
    MergeConflictError,
    NotAGitRepoError,
)


def test_exit_codes_match_bash_contract():
    assert int(ExitCode.SUCCESS) == 0
    assert int(ExitCode.INVALID_ARGS) == 1
    assert int(ExitCode.NOT_GIT_REPO) == 2
    assert int(ExitCode.ERROR_STATE) == 3
    assert int(ExitCode.GENERAL_ERROR) == 4
    assert int(ExitCode.INTERRUPTED) == 130


def test_each_subclass_has_correct_exit_code():
    assert InvalidArgsError("x").exit_code is ExitCode.INVALID_ARGS
    assert NotAGitRepoError("x").exit_code is ExitCode.NOT_GIT_REPO
    assert ErrorStatePresentError("x").exit_code is ExitCode.ERROR_STATE
    assert BlackFailure("x").exit_code is ExitCode.GENERAL_ERROR
    assert MergeConflictError("x").exit_code is ExitCode.GENERAL_ERROR


def test_context_is_preserved():
    err = BrackError("boom", context="during stash")
    assert err.message == "boom"
    assert err.context == "during stash"
    assert str(err) == "boom"
