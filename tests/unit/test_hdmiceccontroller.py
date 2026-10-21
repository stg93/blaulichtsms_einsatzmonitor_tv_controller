import io
from queue import Empty
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import hdmiceccontroller
from hdmiceccontroller import (
    CecLogging,
    LibCecController,
    NoCecController,
    PythonCecController,
    StdoutReader,
)


class FakeReader:
    """Replaces StdoutReader with a fixed list of lines."""

    def __init__(self, lines: list[str]) -> None:
        self.lines = list(lines)

    def get(self, block: bool = True, timeout: float | None = None) -> str:
        if not self.lines:
            raise Empty
        return self.lines.pop(0)

    def read_nonblock(self) -> str:
        return ""


class TestNoCecController:
    def test_does_nothing_and_reports_off(self):
        controller = NoCecController(False, None)
        controller.power_on()
        controller.standby()
        controller.activate_source()
        assert controller.is_on() is False


class TestHdmiErrorHandling:
    def test_sends_error_mail_once_until_resolved(self):
        mail_sender = MagicMock()
        controller = NoCecController(True, mail_sender)

        controller._handle_hdmi_error()
        controller._handle_hdmi_error()
        assert mail_sender.send_message.call_count == 1

        controller._handle_hdmi_error_resolved()
        assert mail_sender.send_message.call_count == 2
        assert "resolved" in mail_sender.send_message.call_args.args[0]

        controller._handle_hdmi_error()
        assert mail_sender.send_message.call_count == 3

    def test_sends_no_mail_if_disabled(self):
        mail_sender = MagicMock()
        NoCecController(False, mail_sender)._handle_hdmi_error()
        mail_sender.send_message.assert_not_called()


class TestPythonCecController:
    @pytest.fixture
    def tv(self, monkeypatch):
        tv = MagicMock()
        tv.is_on.return_value = False
        fake_cec = SimpleNamespace(
            init=MagicMock(),
            Device=MagicMock(return_value=tv),
            CECDEVICE_TV=0,
            set_active_source=MagicMock(),
        )
        monkeypatch.setattr(hdmiceccontroller, "cec", fake_cec)
        return tv

    def test_requires_python_cec(self, monkeypatch):
        monkeypatch.setattr(hdmiceccontroller, "cec", None)
        with pytest.raises(RuntimeError, match="python-cec"):
            PythonCecController(False, None)

    def test_power_on_turns_tv_on_and_activates_source(self, tv):
        controller = PythonCecController(False, None)
        controller.power_on()
        tv.power_on.assert_called_once()
        hdmiceccontroller.cec.set_active_source.assert_called_once()

    def test_power_on_does_nothing_if_tv_is_on(self, tv):
        controller = PythonCecController(False, None)
        tv.is_on.return_value = True
        controller.power_on()
        tv.power_on.assert_not_called()

    def test_standby_only_if_tv_is_on(self, tv):
        controller = PythonCecController(False, None)
        tv.standby.assert_not_called()
        tv.is_on.return_value = True
        controller.standby()
        tv.standby.assert_called_once()

    def test_is_on_reports_false_and_mails_on_os_error(self, tv):
        mail_sender = MagicMock()
        controller = PythonCecController(True, mail_sender)
        tv.is_on.side_effect = OSError
        assert controller.is_on() is False
        mail_sender.send_message.assert_called_once()

        tv.is_on.side_effect = None
        tv.is_on.return_value = True
        assert controller.is_on() is True
        assert mail_sender.send_message.call_count == 2


class TestStdoutReader:
    def test_reads_lines_in_background(self):
        reader = StdoutReader(io.StringIO("first\nsecond\n"))
        reader.thread.join(timeout=5)
        assert reader.get(timeout=1) == "first\n"
        assert reader.get_nowait() == "second\n"
        with pytest.raises(Empty):
            reader.get_nowait()

    def test_read_nonblock_returns_all_pending_lines(self):
        reader = StdoutReader(io.StringIO("a\nb\n"))
        reader.thread.join(timeout=5)
        assert reader.read_nonblock() == "a\n\nb\n"
        assert reader.read_nonblock() == ""


class TestLibCecController:
    @pytest.fixture
    def controller(self):
        with patch.object(LibCecController, "_init_cec_connection"):
            controller = LibCecController(
                False, None, debug_level=CecLogging.CEC_LOG_ERROR, device_id="0"
            )
        controller.cecclient = MagicMock()
        controller.cecclient.poll.return_value = None
        controller.stdout_reader = FakeReader([])
        return controller

    def written(self, controller: LibCecController) -> str:
        return "".join(call.args[0] for call in controller.cecclient.stdin.write.call_args_list)

    def test_init_starts_cec_client(self):
        process = MagicMock()
        process.stdout = io.StringIO("waiting for input\n")
        with patch("subprocess.Popen", return_value=process) as popen:
            controller = LibCecController(False, None, debug_level=CecLogging.CEC_LOG_ALL)
        assert popen.call_args.args[0] == ["cec-client", "-d", "31", "-o", "alarmmonitor"]
        assert controller.cecclient is process

    @pytest.mark.parametrize(
        ("method", "expected"),
        [("power_on", "on 0\n"), ("standby", "standby 0\n"), ("activate_source", "as\n")],
    )
    def test_commands(self, controller, method, expected):
        getattr(controller, method)()
        assert self.written(controller) == expected
        controller.cecclient.stdin.flush.assert_called()

    def test_execute_without_new_line(self, controller):
        controller.execute_cec_command("tx 10:36", new_line=False)
        assert self.written(controller) == "tx 10:36"

    @pytest.mark.parametrize(
        ("output", "expected"),
        [
            (["power status: on\n"], True),
            (["power status: standby\n"], False),
            (["something else\n"], False),
            ([], False),
        ],
    )
    def test_is_on_parses_power_status(self, controller, output, expected):
        controller.stdout_reader = FakeReader(output)
        assert controller.is_on() is expected
        assert self.written(controller) == "pow 0\n"

    def test_reconnects_if_cec_client_exited(self, controller):
        controller.cecclient.poll.return_value = 1
        assert controller.is_connected is False
        with patch.object(controller, "_init_cec_connection") as init:
            controller.connect()
        init.assert_called_once()

    def test_read_stdout_is_empty_if_not_connected(self, controller):
        controller.cecclient = None
        assert controller.read_stdout() == ""
