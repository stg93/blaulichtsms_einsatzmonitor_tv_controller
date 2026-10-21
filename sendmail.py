import logging
import os
import smtplib
from email.encoders import encode_base64
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class MailSender:
    """A utility class for sending emails."""

    def __init__(self, smtp_server: str, smtp_port: str | int, user: str, password: str) -> None:
        """Stores the SMTP settings, no connection is opened yet.

        :param smtp_server: The host name of the SMTP server
        :param smtp_port: The SSL port of the SMTP server
        :param user: The login user name
        :param password: The login password
        """
        self.logger = logging.getLogger(__name__)
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.user = user
        self.password = password

    def send_tar_gz_attachment(
        self, from_addr: str, to_addrs: list[str], subject: str, body: str, archive: str
    ) -> None:
        """Sends a mail with a ``.tar.gz`` archive attached.

        :param from_addr: The sender address
        :param to_addrs: The recipient addresses
        :param subject: The subject of the mail
        :param body: The plain text body of the mail
        :param archive: The path of the archive to attach
        """
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
            "Content-Disposition", "attachment", filename=os.path.basename(archive)
        )
        msg.attach(attachment)

        self.send_message(from_addr, to_addrs, msg)

    def send_message(self, from_addr: str, to_addrs: list[str], msg: str | Message) -> None:
        """Sends a mail. Logs an error and sends nothing if the login fails.

        :param from_addr: The sender address
        :param to_addrs: The recipient addresses
        :param msg: The complete mail including its headers
        """
        self.logger.info("Sending mail...")
        self.logger.debug("Mail: \n" + str(msg))
        connection = self.get_connection()
        if connection:
            connection.sendmail(from_addr, to_addrs, str(msg))
            connection.quit()
            self.logger.info("Sent mail successfully")

    def get_connection(self) -> smtplib.SMTP_SSL | None:
        """Opens an SSL connection to the SMTP server and logs in.

        :return: The logged in connection, or None if the login failed
        """
        try:
            server = smtplib.SMTP_SSL(self.smtp_server, int(self.smtp_port))
            server.login(self.user, self.password)
            self.logger.debug("Logged in to server")
            return server
        except smtplib.SMTPException:
            self.logger.error("Unable to login to server")
            return None
