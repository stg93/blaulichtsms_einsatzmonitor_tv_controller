import smtplib
import logging
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.encoders import encode_base64
import os


class MailSender:
    """A utility class for sending emails."""

    def __init__(self, smtp_server, smtp_port, user, password):
        self.logger = logging.getLogger(__name__)
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.user = user
        self.password = password

    def send_tar_gz_attachment(
            self, from_addr, to_addrs, subject, body, archive):
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)

        msg_body = MIMEText(body)
        msg.attach(msg_body)

        with open(archive, "rb") as fp:
            archive_data = fp.read()
        attachment = MIMEBase("application", "gzip")
        attachment.set_payload(archive_data)
        encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(archive)
        )
        msg.attach(attachment)

        self.send_message(from_addr, to_addrs, msg)

    def send_message(self, from_addr, to_addrs, msg):
        self.logger.info("Sending mail...")
        self.logger.debug("Mail: \n" + str(msg))
        connection = self.get_connection()
        if connection:
            connection.sendmail(from_addr, to_addrs, str(msg))
            connection.quit()
            self.logger.info("Sent mail successfully")

    def get_connection(self):
        try:
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.user, self.password)
            self.logger.debug('Logged in to server')
            return server
        except smtplib.SMTPException:
            self.logger.error('Unable to login to server')
            return None
