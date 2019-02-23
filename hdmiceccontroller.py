import logging

import cec


class HdmiCecController:
    """Handles the communication with a HDMI device over CEC."""

    def __init__(self, send_errors, mail_sender):
        self.logger = logging.getLogger(__name__)
        self._mail_sender = mail_sender

        self._send_errors = send_errors
        self._is_hdmi_error = False

        self._init_hdmi_connection()

    def _init_hdmi_connection(self):
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
            is_on = self.hdmi_cec_device.is_on()
            if self._is_hdmi_error:
                self._handle_hdmi_error_resolved()
            return is_on
        except OSError:
            self._handle_hdmi_error()

    def _handle_hdmi_error(self):
        self.logger.error("Cannot connect to HDMI CEC device")

        if self._send_errors and not self._is_hdmi_error:
            self._mail_sender.send_message(
                "The AlarmMonitor cannot connect to the HDMI device.\n"
                "A mail is sent as soon as the problem is resolved."
            )
            self._is_hdmi_error = True

    def _handle_hdmi_error_resolved(self):
        self._mail_sender.send_message("The HDMI issue of the AlarmMonitor is resolved.")
        self._is_hdmi_error = False
