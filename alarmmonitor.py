import logging
import time
from sched import scheduler

from chromiumbrowsercontroller import ChromiumBrowserController


class AlarmMonitor:
    """Controls the application's execution flow."""

    def __init__(self, polling_interval, blaulichtsms_controller, hdmi_cec_controller, browser_controller):
        self.logger = logging.getLogger(__name__)
        self.scheduler = scheduler(time.time, time.sleep)
        self.blaulichtsms_controller = blaulichtsms_controller
        self.hdmi_cec_controller = hdmi_cec_controller
        self.browser_controller = browser_controller
        self.browser_controller.start()

        self._polling_interval = polling_interval

    def _run_helper(self):
        """The main loop of the application.
        Reschedules itself to run every :_polling_interval: seconds.

        Ensures that a browser which is displaying the blaulichtSMS Einsatzmonitor dashboard is running.
        Checks if communication with an HDMI device via CEC is possible.
        """
        self.scheduler.enter(self._polling_interval, 1, self._run_helper)

        self._check_browser_status()
        if self.blaulichtsms_controller.is_alarm():
            self.hdmi_cec_controller.power_on()
        else:
            self.hdmi_cec_controller.standby()

    def _check_browser_status(self):
        """Checks if the browser process which is displaying the blaulichtSMS
        Einsatzmonitor dashboard is still running.

        If the process is no longer running, it starts a new one.
        """
        if not self.browser_controller.is_alive():
            self.logger.warning("The browser is not running. Starting it.")
            session_id = self.blaulichtsms_controller.get_session()
            self.browser_controller = ChromiumBrowserController(session_id)
            self.browser_controller.start()

    def run(self):
        self.logger.info("START - Started alarm monitor")
        try:
            self._run_helper()
            self.scheduler.run()
        except KeyboardInterrupt:
            self.logger.info("Stopping alarm monitor")
        finally:
            if self.hdmi_cec_controller.is_on():
                self.hdmi_cec_controller.standby()
            self.browser_controller.terminate()
