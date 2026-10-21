import fileinput
import logging
import os
import shutil
import subprocess
from pathlib import Path

CHROMIUM_EXECUTABLES = ["chromium-browser", "chromium"]


def find_chromium_executable() -> str:
    """Finds the Chromium executable in the PATH.

    :return: The path of the first executable found in :CHROMIUM_EXECUTABLES:
    :raises FileNotFoundError: If no Chromium executable is installed
    """
    for executable in CHROMIUM_EXECUTABLES:
        path = shutil.which(executable)
        if path:
            return path
    raise FileNotFoundError("Chromium not found, tried: " + ", ".join(CHROMIUM_EXECUTABLES))


class ChromiumBrowserController:
    """Handles Chromium browser instances to show the
    blaulichtSMS Einsatzmonitor dashboard.
    """

    def __init__(self, session_id: str) -> None:
        """Initializes the controller without starting the browser.

        :param session_id: The blaulichtSMS session token used to log in to the dashboard
        """
        self.logger = logging.getLogger(__name__)
        self._session_id = session_id
        self._process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        """Starts Chromium in kiosk mode on display :0 showing the dashboard."""
        self._delete_crash_exit()
        self._process = subprocess.Popen(
            [
                find_chromium_executable(),
                "--display=:0",
                "--noerrdialogs",
                "--disable-session-restore",
                "--disable-session-crashed-bubble",
                "--disable-infobars",
                "--kiosk",
                "https://dashboard.blaulichtsms.net/#/login?token=" + self._session_id,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.logger.info("Started browser")

    def is_alive(self) -> bool:
        """Checks if the browser process is still running.

        :return: True if the browser is running, False otherwise
        """
        return self._process.poll() is None

    def _delete_crash_exit(self) -> None:
        """If Chromium starts after an unexpected exit (e.g. the host chrashed),
        Chromium displays a notification asking if the user wants to restore the crashed session.

        This method removes this notification, as it is not wanted for the alarm monitor.
        """
        self.logger.debug("Delete crashed session flag")
        file_path = os.path.join(str(Path.home()), ".config", "chromium", "Default", "Preferences")
        try:
            with fileinput.input(files=file_path, inplace=True) as file:
                for line in file:
                    replaced_line = line.replace('"exit_type":"Crashed"', '"exit_type":"Normal"')
                    print(replaced_line, end="")
        except FileNotFoundError:
            self.logger.debug(
                "Preferences file does not exist." + " No crashed session flag to delete."
            )

    def terminate(self) -> None:
        """Terminates the browser process."""
        self._process.terminate()
        self.logger.info("Closed browser")
