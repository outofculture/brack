import os
import stat
import sys
from pathlib import Path

import pytest

from brack.black_runner import BlackResult, resolve_black, run_black
from brack.errors import BlackFailure


def _make_fake_black(
    path: Path,
    *,
    exit_code: int = 0,
    stderr: str = "",
    rewrite_content: str | None = None,
) -> Path:
    lines = [f"#!{sys.executable}", "import sys, pathlib"]
    if stderr:
        lines.append(f"sys.stderr.write({stderr!r})")
    if rewrite_content is not None:
        lines.append(
            f"for a in sys.argv[1:]:\n"
            f"    if a.startswith('-'):\n"
            f"        continue\n"
            f"    pathlib.Path(a).write_text({rewrite_content!r})"
        )
    lines.append(f"sys.exit({exit_code})")
    path.write_text("\n".join(lines))
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def test_resolve_black_finds_real_binary():
    resolved = resolve_black(None)
    assert resolved.endswith("black")


def test_resolve_black_uses_explicit_path(tmp_path):
    fake = _make_fake_black(tmp_path / "my_black")
    assert resolve_black(str(fake)) == str(fake)


def test_resolve_black_rejects_missing_path(tmp_path):
    with pytest.raises(BlackFailure, match="not found"):
        resolve_black(str(tmp_path / "does_not_exist"))


def test_run_black_reports_only_changed_files(tmp_path):
    fake = _make_fake_black(tmp_path / "black", rewrite_content="rewritten\n")
    (tmp_path / "a.py").write_text("rewritten\n")  # already matches -> no change
    (tmp_path / "b.py").write_text("original\n")
    result = run_black(str(fake), ["a.py", "b.py"], cwd=tmp_path)
    assert result.changed == ["b.py"]


def test_run_black_raises_on_failure(tmp_path):
    fake = _make_fake_black(tmp_path / "black", exit_code=123, stderr="syntax error")
    (tmp_path / "broken.py").write_text("x=\n")
    with pytest.raises(BlackFailure) as exc:
        run_black(str(fake), ["broken.py"], cwd=tmp_path)
    assert "syntax error" in (exc.value.context or "")


def test_run_black_with_no_files_is_noop(tmp_path):
    fake = _make_fake_black(tmp_path / "black")
    result = run_black(str(fake), [], cwd=tmp_path)
    assert result == BlackResult(changed=[], stdout="", stderr="")


def test_run_black_passes_extra_args_to_binary(tmp_path):
    captured = tmp_path / "captured.txt"
    fake_source = (
        f"#!{sys.executable}\n"
        "import sys, pathlib\n"
        f"pathlib.Path({str(captured)!r}).write_text(' '.join(sys.argv[1:]))\n"
        "sys.exit(0)\n"
    )
    fake = tmp_path / "black"
    fake.write_text(fake_source)
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    (tmp_path / "a.py").write_text("x=1\n")
    run_black(str(fake), ["a.py"], extra_args=["--line-length", "100"], cwd=tmp_path)
    assert captured.read_text() == "--line-length 100 a.py"
