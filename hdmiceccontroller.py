import logging
import re
import subprocess
from abc import ABC, abstractmethod
from enum import Enum

import cec


class CecMode(Enum):
    LIB_CEC = 1
    PYTHON_CEC = 2


class AbstractCecController(ABC):

    def __init__(self, send_errors, mail_sender):
        self.logger = logging.getLogger(__name__)
        self._mail_sender = mail_sender

        self._send_errors = send_errors
        self._is_hdmi_error = False

        self._init_cec_connection()

    @abstractmethod
    def _init_cec_connection(self):
        pass

    @abstractmethod
    def power_on(self):
        """ turn the TV on """
        pass

    @abstractmethod
    def standby(self):
        """ put the TV to standby """
        pass

    @abstractmethod
    def activate_source(self):
        """ activate raspberry pi as source """
        pass

    @abstractmethod
    def is_on(self):
        """ check if the monitor is on """
        pass

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


class PythonCecController(AbstractCecController):
    """Controls a HDMI CEC device using the libCEC Python bindings
    by {@link https://github.com/trainman419/python-cec|trainman419}
    """

    def _init_cec_connection(self):
        self.logger.debug("Initializing HDMI CEC connection...")
        cec.init()
        self.hdmi_cec_device = cec.Device(cec.CECDEVICE_TV)
        self.standby()
        self.logger.info("Successfully initialized HDMI CEC connection")

    def power_on(self):
        if not self.is_on():
            self.logger.info("Power on HDMI CEC device")
            self.hdmi_cec_device.power_on()
            self.activate_source()

    def standby(self):
        if self.is_on():
            self.logger.info("Standby HDMI CEC device")
            self.hdmi_cec_device.standby()

    def activate_source(self):
        cec.set_active_source()

    def is_on(self):
        try:
            is_on = self.hdmi_cec_device.is_on()
            if self._is_hdmi_error:
                self._handle_hdmi_error_resolved()
            return is_on
        except OSError:
            self._handle_hdmi_error()


class LibCecController(AbstractCecController):
    """Controls a HDMI CEC device using {@link https://github.com/Pulse-Eight/libcec|Pulse-Eight libCEC}
    """

    def _init_cec_connection(self):
        pass

    def power_on(self, device_id="0"):
        if not self.is_on():
            self.logger.info("Power on HDMI CEC device")
            self._execute_cec_command("on " + device_id)
            self.activate_source()

    def standby(self, device_id="0"):
        if self.is_on():
            self.logger.info("Standby HDMI CEC device")
            self._execute_cec_command("standby " + device_id)

    def activate_source(self):
        self._execute_cec_command("as")

    def is_on(self):
        cec_scan = self._execute_cec_command("scan", debug="1")
        device_type = re.search(r"osd string: *(.+)$", cec_scan, re.MULTILINE).group(1)

        if device_type == "CECTester":
            self._handle_hdmi_error()
        else:
            device_status = re.search(r"power status: *(.+)$", cec_scan, re.MULTILINE).group(1)
            if self._is_hdmi_error:
                self._handle_hdmi_error_resolved()
            return device_status == "on"

    @staticmethod
    def _execute_cec_command(command, debug="0"):
        cec_command = "echo '" + command + "' | cec-client -s -d " + debug
        return subprocess.check_output(cec_command, shell=True).decode()
