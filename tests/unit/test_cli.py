import pytest

from brack.cli import parse_args
from brack.errors import ExitCode, InvalidArgsError


def test_no_args_gives_discovery_mode():
    cfg = parse_args([])
    assert cfg.files == []
    assert cfg.black_args == []


def test_positional_files():
    cfg = parse_args(["a.py", "b.py"])
    assert cfg.files == ["a.py", "b.py"]


def test_quiet_and_verbose_flags():
    cfg = parse_args(["--quiet"])
    assert cfg.quiet is True
    assert cfg.verbose is False
    cfg = parse_args(["-q"])
    assert cfg.quiet is True


def test_dry_run_and_cleanup_flags():
    cfg = parse_args(["--dry-run"])
    assert cfg.dry_run is True
    assert cfg.cleanup is False
    cfg = parse_args(["--cleanup"])
    assert cfg.cleanup is True


def test_black_args_after_double_dash():
    cfg = parse_args(["file.py", "--", "--line-length", "100"])
    assert cfg.files == ["file.py"]
    assert cfg.black_args == ["--line-length", "100"]


def test_black_path():
    cfg = parse_args(["--black-path", "/opt/black/bin/black", "a.py"])
    assert cfg.black_path == "/opt/black/bin/black"


def test_main_branch_override():
    cfg = parse_args(["--main-branch", "develop"])
    assert cfg.main_branch == "develop"


def test_no_push_no_pr_no_background():
    cfg = parse_args(["--no-push", "--no-pr", "--no-background"])
    assert cfg.no_push is True
    assert cfg.no_pr is True
    assert cfg.no_background is True


def test_non_py_file_rejected():
    with pytest.raises(InvalidArgsError):
        parse_args(["thing.txt"])


def test_unknown_flag_exits_2(capsys):
    from brack.cli import main

    rc = main(["--not-a-flag"])
    assert rc == 2  # argparse convention; our CLI forwards it


def test_help_exits_0(capsys):
    from brack.cli import main

    rc = main(["--help"])
    assert rc == 0


def test_version_exits_0(capsys):
    from brack.cli import main

    rc = main(["--version"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "brack" in out
