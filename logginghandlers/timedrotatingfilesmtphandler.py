from logging.handlers import TimedRotatingFileHandler
from sendmail import MailSender
import configparser
import json
import os
import tarfile
import threading
import mmap


class TimedRotatingFileSMTPHandler(TimedRotatingFileHandler):
    """An extension of Python's TimedRotatingFileHandler that archives
    and compresses a logging file and sends the compressed archive via Email
    at the rotation of the file.

    The resulting archives are "tar.gz"s.
    The file "logging_config.yaml" configures the logging.
    The file "config.ini" configures the Email settings.
    """

    def __init__(
        self, filename, configfilename, send_log, when='h', interval=1,
        backupCount=0, encoding=None, delay=False, utc=False, atTime=None
    ):
        try:
            os.mkdir(os.path.dirname(filename))
        except FileExistsError:
            pass
        super().__init__(
            filename, when, interval, backupCount, encoding, delay, utc, atTime
        )
        config = configparser.ConfigParser()
        config.read(configfilename)
        self.mail_sender = MailSender(
            config['Email']['smtp_server'],
            config['Email']['smtp_port'],
            config['Email']['username'],
            config['Email']['password']
        )
        self.from_addr = config["Email"]["from_addr"]
        self.to_addrs = json.loads(config["Email"]["to_addrs"])
        self.subject = config["Email"]["subject"]
        self.send_log = send_log

    def doRollover(self):
        super().doRollover()
        threading.Thread(target=self._compress_log_send_mail).start()

    def _compress_log_send_mail(self):
        file_to_compress = self._get_file_to_compress()
        log_summary = self._generate_log_summary(file_to_compress)
        compressed_file = self._compress_file(file_to_compress)
        os.remove(file_to_compress)

        if self.send_log:
            self.mail_sender.send_tar_gz_attachment(
                self.from_addr,
                self.to_addrs,
                self.subject,
                log_summary,
                compressed_file
            )

    def _get_file_to_compress(self):
        file_to_compress = [
            file for file in os.listdir("log/")
            if not file.endswith(".tar.gz") and not file.endswith(".log")
        ][0]
        file_to_compress = os.path.join("log", file_to_compress)
        return file_to_compress

    def _compress_file(self, file):
        compressed_file = file + ".tar.gz"
        with tarfile.open(compressed_file, "w:gz") as tar:
            tar.add(file)
        return compressed_file

    def _generate_log_summary(self, logfile):
        with open(logfile, "r+b") as file:
            memory_mapped = mmap.mmap(
                file.fileno(), 0, access=mmap.ACCESS_READ)

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
        return self._generate_log_summary_text(
            error_count, warning_count, start_count)

    def _generate_log_summary_text(
            self, error_count, warning_count, start_count):
        summary_text = "Log contains:\n" \
            + "\t" + str(error_count) + " " \
            + self._pluralize(error_count, "error") \
            + "\t" + str(warning_count) + " " \
            + self._pluralize(warning_count, "warning") \
            + "\t" + str(start_count) + " application " \
            + self._pluralize(start_count, "start")
        return summary_text

    def _pluralize(self, count, singular):
        return singular + "\n" if count == 1 else singular + "s\n"
