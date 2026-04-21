from pathlib import Path

from brack.config import Config


def test_config_has_sensible_defaults():
    cfg = Config()
    assert cfg.files == []
    assert cfg.black_args == []
    assert cfg.black_path is None
    assert cfg.quiet is False
    assert cfg.verbose is False
    assert cfg.dry_run is False
    assert cfg.cleanup is False
    assert cfg.main_branch is None
    assert cfg.formatting_branch_suffix == "-auto-black-formatting"
    assert cfg.no_push is False
    assert cfg.no_pr is False
    assert cfg.no_background is False
    assert isinstance(cfg.cwd, Path)


def test_config_fields_are_independent():
    a = Config()
    b = Config()
    a.files.append("x.py")
    a.black_args.append("--line-length=100")
    assert b.files == []
    assert b.black_args == []
