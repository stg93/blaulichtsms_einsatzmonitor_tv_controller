import configparser
import logging
from unittest.mock import patch

import pytest

import main
from hdmiceccontroller import CecLogging


@pytest.fixture(autouse=True)
def logger(monkeypatch):
    monkeypatch.setattr(main, "logger", logging.getLogger("test_main"))


def make_config(**alarmmonitor) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config["Alarmmonitor"] = alarmmonitor
    return config


class TestGetCecController:
    def test_disabled(self):
        with patch.object(main, "NoCecController") as controller_class:
            controller = main.get_cec_controller(make_config(cec_mode="0"), False, None)
        assert controller is controller_class.return_value
        controller_class.assert_called_once_with(False, None)

    def test_python_cec(self):
        with patch.object(main, "PythonCecController") as controller_class:
            main.get_cec_controller(make_config(cec_mode="2"), True, "sender")
        controller_class.assert_called_once_with(True, "sender")

    def test_lib_cec_with_settings(self):
        config = make_config(cec_mode="1", cec_logging="31", cec_device_id="4")
        with patch.object(main, "LibCecController") as controller_class:
            main.get_cec_controller(config, False, None)
        controller_class.assert_called_once_with(
            False, None, debug_level=CecLogging.CEC_LOG_ALL, device_id="4"
        )

    def test_lib_cec_defaults(self):
        with patch.object(main, "LibCecController") as controller_class:
            main.get_cec_controller(make_config(cec_mode="1"), False, None)
        controller_class.assert_called_once_with(
            False, None, debug_level=CecLogging.CEC_LOG_ERROR, device_id="1"
        )

    @pytest.mark.parametrize("cec_mode", ["7", "abc"])
    def test_invalid_mode_falls_back_to_lib_cec(self, cec_mode):
        with patch.object(main, "LibCecController") as controller_class:
            main.get_cec_controller(make_config(cec_mode=cec_mode), False, None)
        controller_class.assert_called_once()

    def test_invalid_logging_falls_back_to_errors(self):
        config = make_config(cec_mode="1", cec_logging="3")
        with patch.object(main, "LibCecController") as controller_class:
            main.get_cec_controller(config, False, None)
        assert controller_class.call_args.kwargs["debug_level"] == CecLogging.CEC_LOG_ERROR


def test_get_logging_config_reads_yaml(tmp_path):
    path = tmp_path / "logging.yaml"
    path.write_text("version: 1\nhandlers:\n  console:\n    class: logging.StreamHandler\n")
    assert main.get_logging_config(str(path)) == {
        "version": 1,
        "handlers": {"console": {"class": "logging.StreamHandler"}},
    }
