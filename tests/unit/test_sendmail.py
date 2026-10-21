import email
import smtplib
from unittest.mock import patch

from alarmmonitormailsender import AlarmMonitorMailSender
from sendmail import MailSender

CONFIG_INI = """\
[Email]
username = sender@example.com
password = secret
smtp_server = smtp.example.com
smtp_port = 465
from_addr = sender@example.com
to_addrs = ["a@example.com", "b@example.com"]
subject = Einsatzmonitor
"""


def make_sender() -> MailSender:
    return MailSender("smtp.example.com", "465", "user", "secret")


class TestMailSender:
    def test_get_connection_logs_in(self):
        with patch("smtplib.SMTP_SSL") as smtp:
            connection = make_sender().get_connection()
        smtp.assert_called_once_with("smtp.example.com", 465)
        connection.login.assert_called_once_with("user", "secret")

    def test_get_connection_returns_none_if_login_fails(self):
        with patch("smtplib.SMTP_SSL") as smtp:
            smtp.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"no")
            assert make_sender().get_connection() is None

    def test_send_message_sends_and_quits(self):
        with patch("smtplib.SMTP_SSL") as smtp:
            make_sender().send_message("from@example.com", ["to@example.com"], "hello")
        connection = smtp.return_value
        connection.sendmail.assert_called_once_with(
            "from@example.com", ["to@example.com"], "hello"
        )
        connection.quit.assert_called_once()

    def test_send_message_does_nothing_without_connection(self):
        sender = make_sender()
        with patch.object(sender, "get_connection", return_value=None):
            sender.send_message("from@example.com", ["to@example.com"], "hello")

    def test_send_tar_gz_attachment_attaches_archive(self, tmp_path):
        archive = tmp_path / "log.tar.gz"
        archive.write_bytes(b"archive-content")
        sender = make_sender()

        with patch.object(sender, "send_message") as send_message:
            sender.send_tar_gz_attachment(
                "from@example.com", ["a@example.com", "b@example.com"], "Log", "body", str(archive)
            )

        from_addr, to_addrs, msg = send_message.call_args.args
        assert from_addr == "from@example.com"
        assert to_addrs == ["a@example.com", "b@example.com"]
        parsed = email.message_from_string(str(msg))
        assert parsed["Subject"] == "Log"
        assert parsed["To"] == "a@example.com, b@example.com"
        text, attachment = parsed.get_payload()
        assert text.get_payload() == "body"
        assert attachment.get_filename() == "log.tar.gz"
        assert attachment.get_payload(decode=True) == b"archive-content"


class TestAlarmMonitorMailSender:
    def test_reads_config_and_prepends_subject(self, tmp_path, monkeypatch):
        (tmp_path / "config.ini").write_text(CONFIG_INI)
        monkeypatch.chdir(tmp_path)

        sender = AlarmMonitorMailSender()
        with patch.object(sender.mail_sender, "send_message") as send_message:
            sender.send_message("The AlarmMonitor has started.")

        send_message.assert_called_once_with(
            "sender@example.com",
            ["a@example.com", "b@example.com"],
            "Subject: Einsatzmonitor\n\nThe AlarmMonitor has started.",
        )
        assert sender.mail_sender.smtp_server == "smtp.example.com"
