import configparser
from blaulichtsmscontroller import BlaulichtSmsController
from hdmiceccontroller import HdmiCecController
import logging
from chromiumbrowsercontroller import ChromiumBrowserController


class AlarmMonitorTest:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        config = configparser.ConfigParser()
        config.read("config.ini")

        self._hdmi_cec_device_on_time = 300

        self.blaulichtsms_controller = BlaulichtSmsController(
            config["blaulichtSMS Einsatzmonitor"]["customer_id"],
            config["blaulichtSMS Einsatzmonitor"]["username"],
            config["blaulichtSMS Einsatzmonitor"]["password"]
        )
        self.hdmi_cec_controller = HdmiCecController()
        session_id = self.blaulichtsms_controller.get_session()
        self.browser_controller = ChromiumBrowserController(session_id)
        self.browser_controller.start()

    def _run_helper(self):
        self.blaulichtsms_controller.is_alarm()
        if not self.browser_controller.is_alive():
            self.logger.warning(
                "Browser is no longer running - restarting it")
            session_id = self.blaulichtsms_controller.get_session()
            self.browser_controller = ChromiumBrowserController(session_id)
            self.browser_controller.start()
        self.hdmi_cec_controller \
            .power_on(duration=self._hdmi_cec_device_on_time)

    def run(self):
        self.logger.info("START - Started alarm monitor")
        self._run_helper()
        self.browser_controller.terminate()
        self.logger.info("Stopping alarm monitor")
