import configparser
from blaulichtsmscontroller import BlaulichtSmsController
from hdmiceccontroller import HdmiCecController
from sched import scheduler
import time
import logging
from chromiumbrowsercontroller import ChromiumBrowserController


class AlarmMonitor:
    """Controls the application's execution flow."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scheduler = scheduler(time.time, time.sleep)

        config = configparser.ConfigParser()
        config.read("config.ini")

        self._hdmi_cec_device_on_time = \
            int(config["Alarmmonitor"]["hdmi_cec_device_on_time"])
        self._polling_interval = \
            int(config["Alarmmonitor"]["polling_interval"])

        self.blaulichtsms_controller = BlaulichtSmsController(
            config["blaulichtSMS Einsatzmonitor"]["customer_id"],
            config["blaulichtSMS Einsatzmonitor"]["username"],
            config["blaulichtSMS Einsatzmonitor"]["password"])
        self.hdmi_cec_controller = HdmiCecController()
        session_id = self.blaulichtsms_controller.get_session()
        self.browser_controller = ChromiumBrowserController(session_id)
        self.browser_controller.start()

    def _run_helper(self):
        """The main loop of the application.
        Reschedules itself to run every :_polling_interval: seconds.

        Ensures that a browser which is displaying the
        blaulichtSMS Einsatzmonitor dashboard is running.
        Checks if communication with an HDMI device via CEC is possible.
        """
        self.logger.debug("running helper")
        self.scheduler.enter(self._polling_interval, 1, self._run_helper)
        try:
            self._check_browser_status()
            if self.blaulichtsms_controller.is_alarm(self._hdmi_cec_device_on_time):
                self.hdmi_cec_controller \
                    .power_on()
            else:
                if self.hdmi_cec_controller.is_on():
                    self.hdmi_cec_controller.standby()
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            pass
            self.logger.exception("helper failed")

    def _check_browser_status(self):
        """Checks if the browser process which is displaying the blaulichtSMS
        Einsatzmonitor dashboard is still running.

        If the process is no longer running, it starts a new one.
        """
        if not self.browser_controller.is_alive():
            self.logger.warning("Browser is no longer running - restarting it")
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
