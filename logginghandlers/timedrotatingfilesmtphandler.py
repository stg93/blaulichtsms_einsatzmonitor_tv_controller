import configparser
import datetime
import json
import mmap
import os
import tarfile
import threading
from logging.handlers import TimedRotatingFileHandler

from sendmail import MailSender


class TimedRotatingFileSMTPHandler(TimedRotatingFileHandler):
    """An extension of Python's TimedRotatingFileHandler that archives
    and compresses a logging file and sends the compressed archive via Email
    at the rotation of the file.

    The resulting archives are "tar.gz"s.
    The file "logging_config.yaml" configures the logging.
    The file "config.ini" configures the Email settings.
    """

    # noinspection PyPep8Naming
    def __init__(
        self,
        filename: str,
        configfilename: str,
        send_log: bool,
        when: str = "h",
        interval: int = 1,
        backupCount: int = 0,
        encoding: str | None = None,
        delay: bool = False,
        utc: bool = False,
        atTime: datetime.time | None = None,
    ) -> None:
        """Creates the log directory if needed and reads the email settings.

        :param filename: The path of the log file
        :param configfilename: The path of the config file with the email settings
        :param send_log: Whether to send the rotated log via email
        :param when: See :class:`logging.handlers.TimedRotatingFileHandler`
        :param interval: See :class:`logging.handlers.TimedRotatingFileHandler`
        :param backupCount: See :class:`logging.handlers.TimedRotatingFileHandler`
        :param encoding: See :class:`logging.handlers.TimedRotatingFileHandler`
        :param delay: See :class:`logging.handlers.TimedRotatingFileHandler`
        :param utc: See :class:`logging.handlers.TimedRotatingFileHandler`
        :param atTime: See :class:`logging.handlers.TimedRotatingFileHandler`
        """
        try:
            os.mkdir(os.path.dirname(filename))
        except FileExistsError:
            pass
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        config = configparser.ConfigParser()
        config.read(configfilename)
        self.mail_sender = MailSender(
            config["Email"]["smtp_server"],
            config["Email"]["smtp_port"],
            config["Email"]["username"],
            config["Email"]["password"],
        )
        self.from_addr = config["Email"]["from_addr"]
        self.to_addrs: list[str] = json.loads(config["Email"]["to_addrs"])
        self.subject = config["Email"]["subject"]
        self.send_log = send_log

    def doRollover(self) -> None:
        """Rotates the log file and compresses and mails the rotated file
        in a background thread."""
        super().doRollover()
        threading.Thread(target=self._compress_log_send_mail).start()

    def _compress_log_send_mail(self) -> None:
        """Compresses the rotated log file, deletes the original and mails
        the archive with a summary if :send_log: is set."""
        file_to_compress = self._get_file_to_compress()
        log_summary = self._generate_log_summary(file_to_compress)
        compressed_file = self._compress_file(file_to_compress)
        os.remove(file_to_compress)

        if self.send_log:
            self.mail_sender.send_tar_gz_attachment(
                self.from_addr, self.to_addrs, self.subject, log_summary, compressed_file
            )

    @staticmethod
    def _get_file_to_compress() -> str:
        """Finds the rotated log file, which has a date suffix instead of ``.log``.

        :return: The path of the rotated log file
        :raises StopIteration: If there is no rotated log file
        """
        file_to_compress = next(
            file
            for file in os.listdir("log/")
            if not file.endswith(".tar.gz") and not file.endswith(".log")
        )
        file_to_compress = os.path.join("log", file_to_compress)
        return file_to_compress

    @staticmethod
    def _compress_file(file: str) -> str:
        """Packs the file into a ``.tar.gz`` archive next to it.

        :param file: The path of the file to compress
        :return: The path of the archive
        """
        compressed_file = file + ".tar.gz"
        with tarfile.open(compressed_file, "w:gz") as tar:
            tar.add(file)
        return compressed_file

    def _generate_log_summary(self, logfile: str) -> str:
        """Counts the errors, warnings and application starts in the log file.

        :param logfile: The path of the log file
        :return: The summary text
        """
        with open(logfile, "r+b") as file:
            memory_mapped = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)

            error_count = 0
            warning_count = 0
            start_count = 0

            line = memory_mapped.readline()
            while line != b"":
                if b"ERROR" in line:
                    error_count += 1
                if b"WARNING" in line:
                    warning_count += 1
                if b"START" in line:
                    start_count += 1
                line = memory_mapped.readline()
            memory_mapped.close()
        return self._generate_log_summary_text(error_count, warning_count, start_count)

    def _generate_log_summary_text(
        self, error_count: int, warning_count: int, start_count: int
    ) -> str:
        """Formats the counts as the body of the log mail.

        :param error_count: The number of errors
        :param warning_count: The number of warnings
        :param start_count: The number of application starts
        :return: The summary text
        """
        summary_text = (
            "Log contains:\n"
            + "\t"
            + str(error_count)
            + " "
            + self._pluralize(error_count, "error")
            + "\t"
            + str(warning_count)
            + " "
            + self._pluralize(warning_count, "warning")
            + "\t"
            + str(start_count)
            + " application "
            + self._pluralize(start_count, "start")
        )
        return summary_text

    @staticmethod
    def _pluralize(count: int, singular: str) -> str:
        """Returns the noun in singular or plural form, followed by a newline.

        :param count: The number of items
        :param singular: The singular form of the noun
        :return: The noun matching the count
        """
        return singular + "\n" if count == 1 else singular + "s\n"
