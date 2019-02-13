import logging
from datetime import datetime
from time import sleep

import cec_helper


class HdmiCecController:
    """Handles the communication with a HDMI device over CEC."""

    def __init__(self, mode=cec_helper.CEC_LIB, monitor_check_interval=120):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialising HDMI CEC connection...")
        self.cec = cec_helper.CecLib() if mode == cec_helper.CEC_LIB else cec_helper.CecUtils()
        self.logger.info("Initialized HDMI CEC connection")

        self.monitor_is_on = False
        self.last_monitor_check = datetime(2000, 1, 1)
        self.monitor_check_interval = monitor_check_interval

    def power_on(self, duration=None):
        self.logger.info("Power on HDMI CEC device")
        self.cec.power_on()
        self.cec.activate_source()
        if duration:
            self.logger.warn("deprecated: duration")
            sleep(duration)
            self.standby()

    def standby(self):
        if self.hdmi_cec_device.is_on():
            self.logger.info("Standby HDMI CEC device")
            self.hdmi_cec_device.standby()

    def check_hdmi_cec_device_connection(self):
        self.is_on()

    def is_on(self):
        if (datetime.utcnow() - self.last_monitor_check).second > self.monitor_check_interval:
            self.monitor_is_on = self.cec.is_on()
            self.last_monitor_check = datetime.utcnow()
        return self.monitor_is_on
