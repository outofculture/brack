from io import StringIO

from brack.logging import Logger


def test_info_goes_to_stream_with_prefix():
    buf = StringIO()
    Logger(stream=buf).info("hello")
    assert buf.getvalue() == "[INFO] hello\n"


def test_quiet_suppresses_info_and_success():
    buf = StringIO()
    logger = Logger(quiet=True, stream=buf)
    logger.info("x")
    logger.success("y")
    assert buf.getvalue() == ""


def test_quiet_still_emits_warn_and_error():
    buf = StringIO()
    logger = Logger(quiet=True, stream=buf)
    logger.warn("w")
    logger.error("e")
    assert "[WARN] w" in buf.getvalue()
    assert "[ERROR] e" in buf.getvalue()


def test_debug_suppressed_unless_verbose():
    buf = StringIO()
    Logger(stream=buf).debug("hidden")
    assert buf.getvalue() == ""
    buf = StringIO()
    Logger(verbose=True, stream=buf).debug("shown")
    assert buf.getvalue() == "[INFO] shown\n"


def test_out_bypasses_logger_and_goes_to_stdout(capsys):
    Logger(quiet=True).out("brack: formatted 1 file(s) in 50ms")
    captured = capsys.readouterr()
    assert captured.out == "brack: formatted 1 file(s) in 50ms\n"
