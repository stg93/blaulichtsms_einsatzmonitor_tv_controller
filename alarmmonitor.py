import logging
import time
from sched import scheduler

from alarmmonitormailsender import AlarmMonitorMailSender
from blaulichtsmscontroller import BlaulichtSmsController
from chromiumbrowsercontroller import ChromiumBrowserController
from hdmiceccontroller import AbstractCecController


class AlarmMonitor:
    """Controls the application's execution flow.

    Polls the blaulichtSMS Dashboard API, switches the HDMI device on while an alarm
    is active and keeps the browser showing the Einsatzmonitor dashboard running.
    """

    def __init__(
        self,
        polling_interval: int,
        send_errors: bool,
        send_starts: bool,
        blaulichtsms_controller: BlaulichtSmsController,
        hdmi_cec_controller: AbstractCecController,
        browser_controller: ChromiumBrowserController,
        mail_sender: AlarmMonitorMailSender | None,
    ) -> None:
        """Initializes the alarm monitor and starts the browser.

        :param polling_interval: Seconds between two alarm checks
        :param send_errors: Whether to send emails about browser errors
        :param send_starts: Whether to send an email when the monitor starts
        :param blaulichtsms_controller: Requests the alarms
        :param hdmi_cec_controller: Controls the HDMI device
        :param browser_controller: Controls the browser showing the dashboard
        :param mail_sender: Sends the emails, may be None if no emails are sent
        """
        self.logger = logging.getLogger(__name__)
        self.scheduler = scheduler(time.time, time.sleep)
        self.blaulichtsms_controller = blaulichtsms_controller
        self.hdmi_cec_controller = hdmi_cec_controller
        self.browser_controller = browser_controller
        self.mail_sender = mail_sender
        self.browser_controller.start()

        self._polling_interval = polling_interval
        self._send_errors = send_errors
        self._send_starts = send_starts

        self._is_browser_error = False

    def _run_helper(self) -> None:
        """The main loop of the application.
        Reschedules itself to run every :_polling_interval: seconds.

        Ensures that a browser which is displaying the blaulichtSMS Einsatzmonitor dashboard is running.
        Activates the HDMI device while an alarm is active and puts it into standby otherwise.
        """
        self.logger.debug("running helper")
        self.scheduler.enter(self._polling_interval, 1, self._run_helper)

        self._check_browser_status()
        if self.blaulichtsms_controller.is_alarm():
            self.hdmi_cec_controller.activate_source()
        else:
            self.hdmi_cec_controller.standby()

    def _check_browser_status(self) -> None:
        """Checks if the browser process which is displaying the blaulichtSMS
        Einsatzmonitor dashboard is still running.

        If the process is no longer running, it starts a new one with a new session.
        Sends an email when the browser crashed and another one when it runs again.
        """
        if not self.browser_controller.is_alive():
            self.logger.warning("The browser is not running. Starting it.")

            if self._send_errors and not self._is_browser_error:
                self.mail_sender.send_message(
                    "The browser of the AlarmMonitor has crashed.\n"
                    "A mail is sent as soon as the problem is resolved."
                )
                self._is_browser_error = True

            session_id = self.blaulichtsms_controller.get_session()
            self.browser_controller = ChromiumBrowserController(session_id)
            self.browser_controller.start()
        elif self._is_browser_error:
            self.mail_sender.send_message("The browser issue of the AlarmMonitor is resolved.")
            self._is_browser_error = False

    def run(self) -> None:
        """Runs the main loop until a keyboard interrupt.

        On exit, puts the HDMI device into standby and closes the browser.
        """
        self.logger.info("START - Started alarm monitor")
        if self._send_starts:
            self.mail_sender.send_message("The AlarmMonitor has started.")
        try:
            self._run_helper()
            self.scheduler.run()
        except KeyboardInterrupt:
            self.logger.info("Stopping alarm monitor")
        finally:
            if self.hdmi_cec_controller.is_on():
                self.hdmi_cec_controller.standby()
            self.browser_controller.terminate()
