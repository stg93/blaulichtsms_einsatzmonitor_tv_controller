import logging
import re
import subprocess
from abc import ABC, abstractmethod
from enum import IntEnum
from queue import Empty, Queue
from threading import Thread
from typing import IO, Any

from alarmmonitormailsender import AlarmMonitorMailSender

# python-cec (trainman419) is only required for CecMode.PYTHON_CEC
try:
    import cec
except ImportError:
    cec = None


class CecMode(IntEnum):
    """How the HDMI device is controlled, set by ``cec_mode`` in ``config.ini``."""

    DISABLED = 0
    LIB_CEC = 1
    PYTHON_CEC = 2


class CecLogging(IntEnum):
    """Log levels of ``cec-client``, can be combined as bit flags."""

    # see https://github.com/Pulse-Eight/libcec/blob/master/include/cectypes.h#L829
    CEC_LOG_ERROR = 1
    CEC_LOG_WARNING = 2
    CEC_LOG_NOTICE = 4
    CEC_LOG_TRAFFIC = 8
    CEC_LOG_DEBUG = 16
    CEC_LOG_ALL = 31


class AbstractCecController(ABC):
    """Base class for controlling an HDMI device via CEC.

    Sends an email when the HDMI device cannot be reached and another one
    as soon as the problem is resolved.
    """

    def __init__(self, send_errors: bool, mail_sender: AlarmMonitorMailSender | None) -> None:
        """Initializes the controller and opens the CEC connection.

        :param send_errors: Whether to send emails about HDMI errors
        :param mail_sender: Sends the error emails, may be None if send_errors is False
        """
        self.logger = logging.getLogger(__name__)
        self._mail_sender = mail_sender

        self._send_errors = send_errors
        self._is_hdmi_error = False

        self._init_cec_connection()

    @abstractmethod
    def _init_cec_connection(self) -> None:
        """Opens the connection to the HDMI device."""

    @abstractmethod
    def power_on(self) -> None:
        """Turns the TV on."""

    @abstractmethod
    def standby(self) -> None:
        """Puts the TV into standby."""

    @abstractmethod
    def activate_source(self) -> None:
        """Makes the Raspberry Pi the active source of the TV."""

    @abstractmethod
    def is_on(self) -> bool:
        """Checks if the TV is on.

        :return: True if the TV is on, False otherwise
        """

    def _handle_hdmi_error(self) -> None:
        """Logs a connection error and sends an error email once per error period."""
        self.logger.error("Cannot connect to HDMI CEC device")

        if self._send_errors and not self._is_hdmi_error:
            self._mail_sender.send_message(
                "The AlarmMonitor cannot connect to the HDMI device.\n"
                "A mail is sent as soon as the problem is resolved."
            )
            self._is_hdmi_error = True

    def _handle_hdmi_error_resolved(self) -> None:
        """Sends an email that the HDMI connection works again."""
        self._mail_sender.send_message("The HDMI issue of the AlarmMonitor is resolved.")
        self._is_hdmi_error = False


class NoCecController(AbstractCecController):
    """Does not control any HDMI CEC device, used if CEC is disabled."""

    def _init_cec_connection(self) -> None:
        """Only logs that CEC is disabled."""
        self.logger.info("HDMI CEC is disabled")

    def power_on(self) -> None:
        """Does nothing."""

    def standby(self) -> None:
        """Does nothing."""

    def activate_source(self) -> None:
        """Does nothing."""

    def is_on(self) -> bool:
        """Always reports the TV as off.

        :return: False
        """
        return False


class PythonCecController(AbstractCecController):
    """Controls an HDMI CEC device using the libCEC Python bindings
    by `trainman419 <https://github.com/trainman419/python-cec>`_.
    """

    def _init_cec_connection(self) -> None:
        """Initializes libCEC and puts the TV into standby.

        :raises RuntimeError: If python-cec is not installed
        """
        self.logger.debug("Initializing HDMI CEC connection...")
        if cec is None or not hasattr(cec, "init"):
            raise RuntimeError(
                "python-cec by trainman419 is required for cec_mode = 2. "
                "Install it via 'pip3 install cec' or use cec_mode = 1."
            )
        cec.init()
        self.hdmi_cec_device = cec.Device(cec.CECDEVICE_TV)
        self.standby()
        self.logger.info("Successfully initialized HDMI CEC connection")

    def power_on(self) -> None:
        """Turns the TV on and activates the Raspberry Pi as source, if the TV is off."""
        if not self.is_on():
            self.logger.info("Power on HDMI CEC device")
            self.hdmi_cec_device.power_on()
            self.activate_source()

    def standby(self) -> None:
        """Puts the TV into standby, if it is on."""
        if self.is_on():
            self.logger.info("Standby HDMI CEC device")
            self.hdmi_cec_device.standby()

    def activate_source(self) -> None:
        """Makes the Raspberry Pi the active source of the TV."""
        cec.set_active_source()

    def is_on(self) -> bool:
        """Checks if the TV is on and handles connection errors.

        :return: True if the TV is on, False if it is off or cannot be reached
        """
        try:
            is_on = self.hdmi_cec_device.is_on()
            if self._is_hdmi_error:
                self._handle_hdmi_error_resolved()
            return is_on
        except OSError:
            self._handle_hdmi_error()
            return False


class StdoutReader:
    """Reads a text stream in a background thread and queues its lines,
    so they can be read without blocking."""

    def __init__(self, stdout: IO[str]) -> None:
        """Starts the background thread that reads the stream.

        :param stdout: The stream to read, e.g. the stdout of a subprocess
        """
        self.logger = logging.getLogger("CEC")
        self.queue: Queue[str] = Queue()
        self.stdout = stdout
        self.thread = Thread(target=self.enqueue_output)
        self.thread.daemon = True  # thread dies with the program
        self.thread.start()

    def enqueue_output(self) -> None:
        """Puts every line of the stream into the queue until the stream ends,
        then closes the stream."""
        for line in iter(self.stdout.readline, ""):
            self.queue.put(line)
            self.logger.debug("< %s", line.rstrip("\n "))
        self.logger.debug("closing stdout")
        self.stdout.close()

    def get(self, block: bool = True, timeout: float | None = None) -> str:
        """Removes and returns a line from the queue.

        If block is True and timeout is None (the default), blocks until a line is
        available. If timeout is a positive number, blocks at most timeout seconds and
        raises Empty if no line was available within that time. If block is False,
        returns a line if one is immediately available, else raises Empty
        (timeout is ignored in that case).

        :param block: Whether to wait for a line
        :param timeout: The maximum number of seconds to wait
        :return: The next line of the stream
        :raises Empty: If no line is available
        """
        return self.queue.get(block, timeout)

    def get_nowait(self) -> str:
        """Equivalent to ``get(False)``.

        :return: The next line of the stream
        :raises Empty: If no line is available
        """
        return self.get(False)

    def read_nonblock(self) -> str:
        """Reads all queued lines without blocking.

        :return: The queued lines, joined by newlines
        """
        out_str = []

        try:
            while not self.queue.empty():
                out_str.append(self.queue.get_nowait())
        except Empty:
            pass

        return "\n".join(out_str)


class LibCecController(AbstractCecController):
    """Controls an HDMI CEC device using ``cec-client`` from
    `Pulse-Eight libCEC <https://github.com/Pulse-Eight/libcec>`_.
    """

    def __init__(
        self,
        *args: Any,
        debug_level: CecLogging = CecLogging.CEC_LOG_ERROR,
        device_id: str = "0",
        **kwargs: Any,
    ) -> None:
        """Starts ``cec-client`` and waits until it is ready.

        :param args: Passed on to :class:`AbstractCecController`
        :param debug_level: The log level of ``cec-client``
        :param device_id: The CEC logical address of the TV
        :param kwargs: Passed on to :class:`AbstractCecController`
        """
        # see https://github.com/Pulse-Eight/libcec/blob/master/include/cectypes.h#L829
        self._debug_level = debug_level
        self.cecclient: subprocess.Popen[str] | None = None
        self.stdout_reader: StdoutReader | None = None
        self.device_id = device_id
        self.cec_logger = logging.getLogger("CEC")
        super().__init__(*args, **kwargs)

    def _init_cec_connection(self) -> None:
        """Starts the ``cec-client`` process and waits until it accepts commands."""
        self.logger.debug("initializing CEC connection")
        self.cecclient = subprocess.Popen(
            ["cec-client", "-d", f"{self._debug_level}", "-o", "alarmmonitor"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        self.stdout_reader = StdoutReader(self.cecclient.stdout)
        self.wait_to_be_ready()

    def wait_to_be_ready(self) -> None:
        """Waits until ``cec-client`` reports that it is waiting for input.

        Gives up after two reads without any output (about 20 seconds).
        """
        count = 0
        while count < 6:
            try:
                line = self.stdout_reader.get(timeout=10)
                if "waiting for input" in line:
                    self.cec_logger.info("CEC is ready")
                    break
            except Empty:
                self.cec_logger.warning("haven't received a line from CEC")
                count += 3

    def read_stdout(self) -> str:
        """Reads all pending output of ``cec-client`` without blocking.

        :return: The pending output, or an empty string if not connected
        """
        if not self.is_connected:
            return ""
        return self.stdout_reader.read_nonblock()

    @property
    def is_connected(self) -> bool:
        """Whether the ``cec-client`` process is running."""
        return self.cecclient is not None and self.cecclient.poll() is None

    def connect(self) -> None:
        """Starts ``cec-client`` again if it is not running."""
        if not self.is_connected:
            self._init_cec_connection()

    def power_on(self) -> None:
        """Turns the TV on."""
        self.logger.info("Power on HDMI CEC device")
        self.execute_cec_command("on " + self.device_id)
        # self.activate_source()

    def standby(self) -> None:
        """Puts the TV into standby."""
        self.logger.info("Standby HDMI CEC device %s", self.device_id)
        self.execute_cec_command("standby " + self.device_id)

    def activate_source(self) -> None:
        """Makes the Raspberry Pi the active source of the TV."""
        self.execute_cec_command("as")

    def is_on(self) -> bool:
        """Queries the power status of the TV.

        Discards pending output first and waits at most 5 seconds for the answer.

        :return: True if the TV reports "on", False otherwise
        """
        self.connect()
        self.read_stdout()
        self.execute_cec_command(f"pow {self.device_id}")
        cec_scan = ""
        try:
            cec_scan = self.stdout_reader.get(True, 5)
        except Empty:
            pass
        re_match = re.search(r"power status: *([a-z]+)$", cec_scan, re.MULTILINE)
        return re_match is not None and re_match.group(1) == "on"

    def execute_cec_command(self, command: str, new_line: bool = True) -> None:
        """Writes a command to the stdin of ``cec-client``.

        :param command: The command, e.g. ``"standby 0"``
        :param new_line: Whether to append a newline, which executes the command
        """
        self.connect()
        self.cec_logger.debug("> %s", command.rstrip("\n "))
        self.cecclient.stdin.write(command)
        if new_line:
            self.cecclient.stdin.write("\n")
        self.cecclient.stdin.flush()

    def __del__(self) -> None:
        """Kills ``cec-client`` and waits at most 10 seconds for it to exit."""
        if self.cecclient:
            self.cecclient.kill()
            self.cecclient.wait(10)
