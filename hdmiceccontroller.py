import logging
import re
import subprocess
from abc import ABC, abstractmethod
from enum import IntEnum
from queue import Empty, Queue
from threading import Thread

import cec


class CecMode(IntEnum):
    LIB_CEC = 1
    PYTHON_CEC = 2


class CecLogging(IntEnum):
    # see https://github.com/Pulse-Eight/libcec/blob/master/include/cectypes.h#L829
    CEC_LOG_ERROR = 1
    CEC_LOG_WARNING = 2
    CEC_LOG_NOTICE = 4
    CEC_LOG_TRAFFIC = 8
    CEC_LOG_DEBUG = 16
    CEC_LOG_ALL = 31


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
            self._mail_sender.send_message("The AlarmMonitor cannot connect to the HDMI device.\n"
                                           "A mail is sent as soon as the problem is resolved.")
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


class StdoutReader():

    def __init__(self, stdout):
        self.logger = logging.getLogger('CEC')
        self.queue = Queue()
        self.stdout = stdout
        self.thread = Thread(target=self.enqueue_output)
        self.thread.daemon = True  # thread dies with the program
        self.thread.start()

    def enqueue_output(self):
        for line in iter(self.stdout.readline, ''):
            self.queue.put(line)
            self.logger.debug('< %s', line.rstrip('\n '))
        self.logger.debug('closing stdout')
        self.stdout.close()

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.
        If optional args block is true and timeout is None (the default),
        block if necessary until an item is available. If timeout is a
        positive number, it blocks at most timeout seconds and raises the
        Empty exception if no item was available within that time. Otherwise
        (block is false), return an item if one is immediately available, else
        raise the Empty exception (timeout is ignored in that case)."""
        return self.queue.get(block, timeout)

    def get_nowait(self):
        """Equivalent to `get(False).`"""
        return self.get(False)

    def read_nonblock(self):
        """read the whole contents of the stream non-blocking"""
        out_str = []

        try:
            while not self.queue.empty():
                out_str.append(self.queue.get_nowait())
        except Empty:
            pass

        return "\n".join(out_str)


class LibCecController(AbstractCecController):
    """Controls a HDMI CEC device using
    {@link https://github.com/Pulse-Eight/libcec|Pulse-Eight libCEC}
    """

    def __init__(self, *args, debug_level=CecLogging.CEC_LOG_ERROR, device_id="0", **kwargs):
        # see https://github.com/Pulse-Eight/libcec/blob/master/include/cectypes.h#L829
        self._debug_level = debug_level
        self.cecclient = None
        self.stdout_reader = None
        self.device_id = device_id
        self.cec_logger = logging.getLogger('CEC')
        super(LibCecController, self).__init__(*args, **kwargs)

    def _init_cec_connection(self):
        self.logger.debug('initializing CEC connection')
        self.cecclient = subprocess.Popen(
            ['cec-client', '-d', '{}'.format(self._debug_level)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
        )
        self.stdout_reader = StdoutReader(self.cecclient.stdout)
        self.wait_to_be_ready()

    def wait_to_be_ready(self):
        """wait for CEC to initialize"""
        count = 0
        while count < 6:
            try:
                line = self.stdout_reader.get(timeout=10)
                if "waiting for input" in line:
                    self.cec_logger.info('CEC is ready')
                    break
            except Empty:
                self.cec_logger.warning("haven't received a line from CEC")
                count += 3

    def read_stdout(self):
        if not self.is_connected:
            return ''
        return self.stdout_reader.read_nonblock()

    @property
    def is_connected(self):
        return self.cecclient is not None and self.cecclient.poll() is None

    def connect(self):
        """make sure we are connected"""
        if not self.is_connected:
            self._init_cec_connection()

    def power_on(self):
        self.logger.info("Power on HDMI CEC device")
        self.execute_cec_command("on " + self.device_id)
        # self.activate_source()

    def standby(self):
        self.logger.info("Standby HDMI CEC device %s", self.device_id)
        self.execute_cec_command("standby " + self.device_id)

    def activate_source(self):
        self.execute_cec_command("as")

    def is_on(self):
        self.connect()
        self.read_stdout()
        self.execute_cec_command("pow {}".format(self.device_id))
        cec_scan = ""
        try:
            cec_scan = self.stdout_reader.get(True, 5)
        except Empty:
            pass
        re_match = re.search(r"power status: *([a-z]+)$", cec_scan, re.MULTILINE)
        return re_match is not None and re_match.group(1) == "on"

    def execute_cec_command(self, command, new_line=True):
        """write a command to stdin of cec-client"""
        self.connect()
        self.cec_logger.debug('> %s', command.rstrip('\n '))
        self.cecclient.stdin.write(command)
        if new_line:
            self.cecclient.stdin.write('\n')
        self.cecclient.stdin.flush()

    def __del__(self):
        """shutdown cec client"""
        if self.cecclient:
            self.cecclient.kill()
            self.cecclient.wait(10)
