# cec_helper.py
# This tool helps to use either libcec or cec-utils to send commands to HDMI CEC
# both should be installed on the system
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
        """ create a new CecHelper instance
        either CecLib or CecUtils
        """
        if mode == CEC_LIB:
            return CecLib()
        else:
            return CecUtils()


class CecHelper(object):
    """ CEC Helper """

    def __init__(self, *args, **kwargs):
        pass

    def power_on(self):
        pass

    def standby(self):
        pass

    def activate_source(self):
        pass

    def is_on(self):
        pass

    def is_standby(self):
        return not self.is_on()


class CecLib(CecHelper):
    """ Implement CEC Lib """

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialising HDMI CEC connection...")
        cec.init()
        self.hdmi_cec_device = cec.Device(cec.CECDEVICE_TV)

    def power_on(self):
        self.logger.info("Power on HDMI CEC device")
        self.check_hdmi_cec_device_connection()
        self.hdmi_cec_device.power_on()

    def standby(self):
        self.logger.info("Standby HDMI CEC device")
        self.hdmi_cec_device.standby()

    def activate_source(self):
        cec.set_active_source()

    def is_on(self):
        try:
            return self.hdmi_cec_device.is_on()
        except OSError:
            self.logger.error("Cannot connect to HDMI CEC device")
        return False

    def check_hdmi_cec_device_connection(self):
        return self.is_on()


class CecUtils(CecHelper):
    """ CEC Helper """

    def __init__(self, *args, **kwargs):
        self.log = self.logger = logging.getLogger(__name__)
        self.monitor_status = STATUS_UNKNOWN

    def power_on(self):
        self.change_status(STATUS_ON)
        return self.monitor_status == STATUS_ON

    def standby(self):
        self.change_status(STATUS_STANDBY)
        return self.monitor_status == STATUS_STANDBY

    def activate_source(self):
        """ activate current source """
        self.cec("as")

    def is_on(self):
        return self.get_status() == STATUS_ON

    def cec(self, command, debug=None, *args):
        """ send cec command """
        cec_args = ["cec-client", "-s"]
        if debug is not None:
            cec_args.append("-d")
            cec_args.append(str(debug))
        cec_args += args
        pipe_read, pipe_write = os.pipe()
        os.write(pipe_write, command)
        os.close(pipe_write)
        output = subprocess.check_output(cec_args, stdin=pipe_read, close_fds=True)
        os.close(pipe_read)
        return output

    def get_status(self):
        """ get the current status of the monitor """
        try:
            self.log.info("fetching monitor status")
            cec_scan = self.cec("scan", debug="1")
            match = re.search(r"power status: *(.+)$", cec_scan, re.MULTILINE)
            self.monitor_status = STATUS_UNKNOWN
            if match is not None:
                status = match.group(1)
                self.log.info("Monitor is set to %s", status)
                if status == "standby":
                    self.monitor_status = STATUS_STANDBY
                elif status == "on":
                    self.monitor_status = STATUS_ON
            return self.monitor_status
        except subprocess.CalledProcessError as err:
            self.log.warn("failed to get monitor status %s %s", err.returncode, err.output)

    def change_status(self, desired_state=STATUS_ON, device_id=0):
        """
        change the monitor to the desired status
        if the desired state is on, it will use activate source
        to turn the display on and activate itself
        """
        state_name = "on" if desired_state == STATUS_ON else "standby"
        self.log.info("changing monitor to %s", state_name)
        try:
            cec_cmd = "{} {}".format(state_name, device_id)
            output = self.cec(cec_cmd)
            self.monitor_status = desired_state
            self.log.info("monitor status changed: \n%s", output)
        except subprocess.CalledProcessError as err:
            self.log.warn("failed to set monitor status %s %s", err.returncode, err.output)
