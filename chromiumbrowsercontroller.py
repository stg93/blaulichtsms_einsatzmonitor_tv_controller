import subprocess
import logging
from pathlib import Path
import os
import fileinput


class ChromiumBrowserController:
    """Handles Chromium browser instances to show the
    blaulichtSMS Einsatzmonitor dashboard.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def start(self):
        self._delete_crash_exit()
        self.process = subprocess.Popen(
            [
                "/usr/bin/chromium-browser",
                "--display=:0",
                "--noerrdialogs",
                "--disable-session-restore",
                "--disable-session-crashed-bubble",
                "--disable-infobars",
                "--start-fullscreen",
                "https://dashboard.blaulichtsms.net"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.logger.info("Started browser")

    def is_alive(self):
        return self.process.poll() is None

    def _delete_crash_exit(self):
        self.logger.debug("Delete crashed session flag")
        file_path = os.path.join(
            str(Path.home()), ".config", "chromium", "Default", "Preferences")
        try:
            with fileinput.input(files=(file_path), inplace=True) as file:
                for line in file:
                    replaced_line = line.replace(
                        "\"exit_type\":\"Crashed\"",
                        "\"exit_type\":\"Normal\""
                    )
                    print(replaced_line, end="")
        except FileNotFoundError:
            self.logger.debug(
                "Preferences file does not exist."
                + " No crashed session flag to delete."
            )

    def terminate(self):
        self.process.terminate()
        self.logger.info("Closed browser")
