# cec_helper.py
"""
This tool helps to use either libcec or cec-utils to send commands to HDMI CEC
both should be installed on the system
"""
import logging
import cec
import re
import os
import subprocess

CEC_LIB = 1
CEC_UTILS = 2

STATUS_STANDBY = 0
STATUS_ON = 1
STATUS_UNKNOWN = -1


class CecFactory(object):
    """ Factory for CEC Helper objects """

    @staticmethod
    def create(cls, mode=CEC_LIB):
        """
        create a new CecHelper instance
        either CecLib or CecUtils
        """
        if mode == CEC_LIB:
            return CecLib()
        else:
            return CecUtils()


class CecHelper(object):
    """ CEC Helper """

    def __init__(self, *args, **kwargs):
        """ default constructor """
        pass

    def power_on(self):
        """ turn the TV on """
        pass

    def standby(self):
        """ put the TV to standby """
        pass

    def activate_source(self):
        """ activate raspberry pi as source """
        pass

    def is_on(self):
        """ check if the monitor is on """
        pass

    def is_standby(self):
        """ check if the monitor is standby """
        return not self.is_on()


class CecLib(CecHelper):
    """ Implement CEC Lib """

    def __init__(self, *args, **kwargs):
        """ create a HDMI CEC connection """
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialising HDMI CEC connection...")
        cec.init()
        self.hdmi_cec_device = cec.Device(cec.CECDEVICE_TV)

    def power_on(self):
        """ turn the TV on """
        self.logger.info("Power on HDMI CEC device")
        self.check_hdmi_cec_device_connection()
        self.hdmi_cec_device.power_on()

    def standby(self):
        """ put the TV to standby """
        self.logger.info("Standby HDMI CEC device")
        self.hdmi_cec_device.standby()

    def activate_source(self):
        """ activate raspberry pi as source """
        cec.set_active_source()

    def is_on(self):
        """ check if the monitor is on """
        try:
            return self.hdmi_cec_device.is_on()
        except OSError:
            self.logger.error("Cannot connect to HDMI CEC device")
        return False

    def check_hdmi_cec_device_connection(self):
        """ try to get the monitor status, same as is_on """
        return self.is_on()


class CecUtils(CecHelper):
    """ CEC Helper """

    def __init__(self, *args, **kwargs):
        """ setup status for cec utils """
        self.logger = logging.getLogger(__name__)
        self.monitor_status = STATUS_UNKNOWN

    def power_on(self):
        """ turn the TV on """
        self.change_status(STATUS_ON)
        return self.monitor_status == STATUS_ON

    def standby(self):
        """ put the TV to standby """
        self.change_status(STATUS_STANDBY)
        return self.monitor_status == STATUS_STANDBY

    def activate_source(self):
        """ activate current source """
        self.cec("as")

    def is_on(self):
        """ check if the monitor is on """
        return self.get_status() == STATUS_ON

    def cec(self, command, debug=None, *args):
        """ send cec command """
        cec_args = ["cec-client", "-s"]
        if debug is not None:
            cec_args.append("-d")
            cec_args.append(str(debug))
        cec_args += args
        pipe_read, pipe_write = os.pipe()
        os.write(pipe_write, command.encode() if isinstance(command, str) else command)
        os.close(pipe_write)
        output = subprocess.check_output(cec_args, stdin=pipe_read, close_fds=True)
        os.close(pipe_read)
        return output.decode()

    def get_status(self):
        """ get the current status of the monitor """
        try:
            self.logger.info("fetching monitor status")
            cec_scan = self.cec("scan", debug="1")
            match = re.search(r"power status: *(.+)$", cec_scan, re.MULTILINE)
            self.monitor_status = STATUS_UNKNOWN
            if match is not None:
                status = match.group(1)
                self.logger.info("Monitor is set to %s", status)
                if status == "standby":
                    self.monitor_status = STATUS_STANDBY
                elif status == "on" or status == "in transition from standby to on":
                    self.monitor_status = STATUS_ON
            return self.monitor_status
        except subprocess.CalledProcessError as err:
            self.logger.warning("failed to get monitor status %s %s", err.returncode, err.output)

    def change_status(self, desired_state=STATUS_ON, device_id=0):
        """
        change the monitor to the desired status
        if the desired state is on, it will use activate source
        to turn the display on and activate itself
        """
        state_name = "on" if desired_state == STATUS_ON else "standby"
        self.logger.info("changing monitor to %s", state_name)
        try:
            cec_cmd = "{} {}".format(state_name, device_id)
            output = self.cec(cec_cmd)
            # self.monitor_status = desired_state
            self.logger.debug("monitor status change: \n%s", output)
            self.logger.info("monitor status is now %s", "ON"
                             if self.monitor_status == STATUS_ON else "STANDBY")
        except subprocess.CalledProcessError as err:
            self.logger.warning("failed to set monitor status %s %s", err.returncode, err.output)
