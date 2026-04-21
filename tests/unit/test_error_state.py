from brack.error_state import (
    BACKGROUND_LOG_FILENAME,
    ERROR_FILENAME,
    append_background_error,
    background_log_path,
    clear_error_state,
    error_file_path,
    error_state_present,
    write_error_state,
)


def test_paths_are_relative_to_repo_root(tmp_path):
    assert error_file_path(tmp_path) == tmp_path / ERROR_FILENAME
    assert background_log_path(tmp_path) == tmp_path / BACKGROUND_LOG_FILENAME


def test_write_and_detect(tmp_path):
    assert not error_state_present(tmp_path)
    path = write_error_state(tmp_path, "boom", "while stashing")
    assert path.exists()
    assert error_state_present(tmp_path)
    body = path.read_text()
    assert "boom" in body
    assert "while stashing" in body


def test_clear_removes_file_and_background_log(tmp_path):
    write_error_state(tmp_path, "x")
    (tmp_path / BACKGROUND_LOG_FILENAME).write_text("log")
    assert clear_error_state(tmp_path) is True
    assert not error_state_present(tmp_path)
    assert not (tmp_path / BACKGROUND_LOG_FILENAME).exists()


def test_clear_when_nothing_present_returns_false(tmp_path):
    assert clear_error_state(tmp_path) is False


def test_append_background_error_accumulates(tmp_path):
    append_background_error(tmp_path, "github_push", 1, "git push -u origin foo")
    append_background_error(tmp_path, "github_pr", 2, "gh pr create")
    body = error_file_path(tmp_path).read_text()
    assert "github_push" in body
    assert "github_pr" in body
    assert body.count("BACKGROUND PROCESS ERROR") == 2
