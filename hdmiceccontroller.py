import logging

import cec


class HdmiCecController:
    """Handles the communication with a HDMI device over CEC."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing HDMI CEC connection...")
        cec.init()
        self.hdmi_cec_device = cec.Device(cec.CECDEVICE_TV)
        self.standby()
        self.logger.info("Successfully initialized HDMI CEC connection")

    def power_on(self):
        self.logger.info("Power on HDMI CEC device")
        if not self.is_on():
            self.hdmi_cec_device.power_on()

    def standby(self):
        if self.is_on():
            self.logger.info("Standby HDMI CEC device")
            self.hdmi_cec_device.standby()

    def is_on(self):
        try:
            return self.hdmi_cec_device.is_on()
        except OSError:
            self.logger.error("Cannot connect to HDMI CEC device")
