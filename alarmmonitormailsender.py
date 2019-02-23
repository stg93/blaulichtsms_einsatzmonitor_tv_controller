import configparser
import json

from sendmail import MailSender


class AlarmMonitorMailSender:
    """Sends mails using the settings specified in the config of the
    alarmmonitor.

    The used settings are the SMTP settings and the from and to addresses.
    """

    def __init__(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        self.from_addr = config["Email"]["from_addr"]
        self.to_addrs = json.loads(config["Email"]["to_addrs"])
        self.subject = config["Email"]["subject"]
        self.mail_sender = MailSender(
            config["Email"]["smtp_server"],
            config["Email"]["smtp_port"],
            config['Email']['username'],
            config['Email']['password']
        )

    def send_message(self, msg):
        final_msg = "Subject: " + self.subject + "\n\n" + msg
        self.mail_sender.send_message(self.from_addr, self.to_addrs, final_msg)
