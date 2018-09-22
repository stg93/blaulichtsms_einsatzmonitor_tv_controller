import logging
from time import sleep
import cec


class HdmiCecController:
    """Handles the communication with a HDMI device over CEC."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialising HDMI CEC connection...")
        cec.init()
        self.hdmi_cec_device = cec.Device(cec.CECDEVICE_TV)
        try:
            if self.hdmi_cec_device.is_on():
                self.logger.debug("Device is on -> standby device")
                self.hdmi_cec_device.standby()
        except OSError:
            self.logger.error("Cannot connect to HDMI CEC device")
        self.logger.info("Initialized HDMI CEC connection")

    def power_on(self, duration=None):
        self.logger.info("Power on HDMI CEC device")
        self.check_hdmi_cec_device_connection()
        self.hdmi_cec_device.power_on()
        if duration:
            sleep(duration)
            self.standby()

    def standby(self):
        if self.hdmi_cec_device.is_on():
            self.logger.info("Standby HDMI CEC device")
            self.hdmi_cec_device.standby()

    def check_hdmi_cec_device_connection(self):
        self.is_on()

    def is_on(self):
        try:
            return self.hdmi_cec_device.is_on()
        except OSError:
            self.logger.error("Cannot connect to HDMI CEC device")
