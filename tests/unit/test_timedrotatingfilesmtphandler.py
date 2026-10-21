import tarfile
from unittest.mock import patch

import pytest

from logginghandlers.timedrotatingfilesmtphandler import TimedRotatingFileSMTPHandler

CONFIG_INI = """\
[Email]
username = sender@example.com
password = secret
smtp_server = smtp.example.com
smtp_port = 465
from_addr = sender@example.com
to_addrs = ["a@example.com"]
subject = Einsatzmonitor
"""

LOG_CONTENT = """\
2026-10-21 08:00:00 INFO START - Started alarm monitor
2026-10-21 08:00:01 WARNING The browser is not running. Starting it.
2026-10-21 08:00:02 ERROR Cannot connect to HDMI CEC device
2026-10-21 08:00:03 ERROR Cannot connect to HDMI CEC device
"""


@pytest.fixture
def handler(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.ini").write_text(CONFIG_INI)
    handler = TimedRotatingFileSMTPHandler("log/alarmmonitor.log", "config.ini", send_log=True)
    yield handler
    handler.close()


def test_creates_log_dir_and_reads_config(handler, tmp_path):
    assert (tmp_path / "log").is_dir()
    assert handler.from_addr == "sender@example.com"
    assert handler.to_addrs == ["a@example.com"]
    assert handler.subject == "Einsatzmonitor"


@pytest.mark.parametrize(("count", "expected"), [(0, "errors\n"), (1, "error\n"), (2, "errors\n")])
def test_pluralize(count, expected):
    assert TimedRotatingFileSMTPHandler._pluralize(count, "error") == expected


def test_generate_log_summary(handler, tmp_path):
    log_file = tmp_path / "log" / "alarmmonitor.log.2026-10-21"
    log_file.write_text(LOG_CONTENT)
    assert handler._generate_log_summary(str(log_file)) == (
        "Log contains:\n\t2 errors\n\t1 warning\n\t1 application start\n"
    )


def test_get_file_to_compress_finds_rotated_file(handler, tmp_path):
    (tmp_path / "log" / "old.log.2026-10-19.tar.gz").write_text("")
    (tmp_path / "log" / "alarmmonitor.log.2026-10-20").write_text("")
    assert handler._get_file_to_compress() == "log/alarmmonitor.log.2026-10-20"


def test_compress_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "rotated.log.1").write_text("content")
    archive = TimedRotatingFileSMTPHandler._compress_file("rotated.log.1")
    assert archive == "rotated.log.1.tar.gz"
    with tarfile.open(archive) as tar:
        assert tar.getnames() == ["rotated.log.1"]


def test_compress_log_send_mail(handler, tmp_path):
    rotated = tmp_path / "log" / "alarmmonitor.log.2026-10-20"
    rotated.write_text(LOG_CONTENT)

    with patch.object(handler.mail_sender, "send_tar_gz_attachment") as send:
        handler._compress_log_send_mail()

    assert not rotated.exists()
    send.assert_called_once()
    from_addr, to_addrs, subject, summary, archive = send.call_args.args
    assert (from_addr, to_addrs, subject) == (
        "sender@example.com",
        ["a@example.com"],
        "Einsatzmonitor",
    )
    assert summary.startswith("Log contains:")
    assert archive == "log/alarmmonitor.log.2026-10-20.tar.gz"
    assert (tmp_path / archive).exists()


def test_compress_log_without_mail(handler, tmp_path):
    handler.send_log = False
    (tmp_path / "log" / "alarmmonitor.log.2026-10-20").write_text(LOG_CONTENT)
    with patch.object(handler.mail_sender, "send_tar_gz_attachment") as send:
        handler._compress_log_send_mail()
    send.assert_not_called()
