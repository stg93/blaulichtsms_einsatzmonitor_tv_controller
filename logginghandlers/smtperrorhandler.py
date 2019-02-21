import configparser
import json
import logging
from email.mime.text import MIMEText

from sendmail import MailSender


class SMTPErrorHandler(logging.Handler):
    def __init__(self, configfilename):
        super().__init__()
        config = configparser.ConfigParser()
        config.read(configfilename)
        self.fromaddr = config["Email"]["from_addr"]
        self.toaddrs = json.loads(config["Email"]["to_addrs"])
        self.subject = config["Email"]["subject"]
        self.mail_sender = MailSender(
            config["Email"]["smtp_server"],
            config["Email"]["smtp_port"],
            config['Email']['username'],
            config['Email']['password']
        )

        self.send_errors = config.getboolean("Alarmmonitor", "send_errors")
        self.send_connection_errors = \
            config.getboolean("Alarmmonitor", "send_connection_errors")
        self.send_starts = config.getboolean("Alarmmonitor", "send_starts")

    def emit(self, record):
        if record.levelno == logging.ERROR:
            if self.send_errors:
                self._send_mail(record.msg)
        elif record.msg.startswith("START") and self.send_starts:
            self._send_mail(record.msg)

    def _send_mail(self, msg):
        mime_msg = MIMEText(msg)
        mime_msg["Subject"] = self.subject
        self.mail_sender.send_message(
            self.fromaddr, self.toaddrs, str(mime_msg))
