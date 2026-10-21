import configparser
import getpass
import json
import os
from unittest.mock import patch

import pytest
import yaml

import configure
from configure import AlarmMonitorConfigurator


@pytest.fixture
def configurator():
    return AlarmMonitorConfigurator()


@pytest.fixture
def inputs(monkeypatch):
    """Feeds the given answers to input() one after another."""

    def feed(*answers):
        answers_iter = iter(answers)
        monkeypatch.setattr("builtins.input", lambda *args: next(answers_iter))

    return feed


class TestValidators:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("123456", True), ("12345", False), ("1234567", False), ("12345a", False)],
    )
    def test_customer_id(self, value, expected):
        assert AlarmMonitorConfigurator._is_valid_blaulichtsms_customer_id(value) is expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("1", True), ("300", True), ("0", False), ("-5", False), ("x", False)],
    )
    def test_positive_int(self, value, expected):
        assert AlarmMonitorConfigurator._is_positive_int(value) is expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("yes", True), ("y", True), ("no", True), ("n", True), ("maybe", False), ("", False)],
    )
    def test_yes_no(self, value, expected):
        assert AlarmMonitorConfigurator._is_yes_no(value) is expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("ff@example.com", True),
            ("first.last+tag@sub-domain.example.org", True),
            ("no-at-sign.example.com", False),
            ("missing@tld", False),
            ("", False),
        ],
    )
    def test_email(self, value, expected):
        assert AlarmMonitorConfigurator._is_valid_email(value) is expected
        assert AlarmMonitorConfigurator._is_valid_gmail(value) is expected

    def test_system_user(self):
        with patch.object(configure, "getpwnam", side_effect=KeyError):
            assert AlarmMonitorConfigurator._is_valid_system_user("nobody") is False
        with patch.object(configure, "getpwnam"):
            assert AlarmMonitorConfigurator._is_valid_system_user("pi") is True


class TestInput:
    def test_repeats_until_valid(self, configurator, inputs, capsys):
        inputs("abc", "12", "123456")
        result = configurator._get_input_with_validation(
            "Customer id:", "Invalid id", configurator._is_valid_blaulichtsms_customer_id
        )
        assert result == "123456"
        assert capsys.readouterr().out.count("Invalid id") == 2

    @pytest.mark.parametrize(("answer", "expected"), [("y", True), ("yes", True), ("n", False)])
    def test_is_yes_input(self, configurator, inputs, answer, expected):
        inputs(answer)
        assert configurator._is_yes_input("Continue?") is expected

    def test_password_must_match(self, configurator, monkeypatch, capsys):
        answers = iter(["one", "two", "secret", "secret"])
        monkeypatch.setattr(configure, "getpass", lambda prompt: next(answers))
        assert configurator._get_password_input("Password:") == "secret"
        assert "did not match" in capsys.readouterr().out

    def test_recipients_repeat_until_all_valid(self, configurator, inputs):
        inputs("a@example.com, invalid", "a@example.com,b@example.com")
        configurator._configure_recipients()
        assert configurator.recipients == ["a@example.com", "b@example.com"]

    def test_empty_run_user_uses_current_user(self, configurator, inputs):
        inputs("")
        configurator._configure_run_user()
        assert configurator.run_user == getpass.getuser()


class TestWrite:
    @pytest.fixture
    def filled(self, configurator):
        configurator.blaulichtsms_customer_id = "123456"
        configurator.blaulichtsms_username = "monitor"
        configurator.blaulichtsms_password = "secret"
        configurator.blaulichtsms_show_infos = True
        configurator.hdmi_cec_device_on_time = "600"
        configurator.run_user = "pi"
        configurator.gmail_username = "sender@example.com"
        configurator.gmail_password = "mailsecret"
        configurator.recipients = ["a@example.com"]
        configurator.send_errors = True
        return configurator

    def test_config_scaffold_has_all_sections(self):
        config = AlarmMonitorConfigurator._get_config_scaffold()
        assert config.sections() == ["Email", "blaulichtSMS Einsatzmonitor", "Alarmmonitor"]

    def test_write_config_ini(self, filled, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch.object(filled, "_set_config_file_permissions") as set_permissions:
            filled._write_config_ini()
        set_permissions.assert_called_once_with("config.ini")

        config = configparser.ConfigParser()
        config.read(tmp_path / "config.ini")
        assert dict(config["blaulichtSMS Einsatzmonitor"]) == {
            "customer_id": "123456",
            "username": "monitor",
            "password": "secret",
            "show_infos": "True",
        }
        assert config["Alarmmonitor"]["hdmi_cec_device_on_time"] == "600"
        assert config["Alarmmonitor"]["polling_interval"] == "30"
        assert config["Alarmmonitor"]["run_user"] == "pi"
        assert config["Alarmmonitor"]["send_errors"] == "True"
        assert config["Alarmmonitor"]["cec_mode"] == "1"
        assert config["Email"]["from_addr"] == "sender@example.com"
        assert json.loads(config["Email"]["to_addrs"]) == ["a@example.com"]

    def test_write_config_ini_keeps_other_settings(self, filled, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.ini").write_text(
            "[Email]\n[blaulichtSMS Einsatzmonitor]\n[Alarmmonitor]\ncustom = kept\n"
        )
        with patch.object(filled, "_set_config_file_permissions"):
            filled._write_config_ini()
        config = configparser.ConfigParser()
        config.read(tmp_path / "config.ini")
        assert config["Alarmmonitor"]["custom"] == "kept"

    def test_set_config_file_permissions(self, filled, tmp_path):
        config_file = tmp_path / "config.ini"
        config_file.write_text("")
        with (
            patch.object(configure, "getpwnam") as getpwnam,
            patch.object(configure, "chown") as chown,
        ):
            getpwnam.return_value.pw_gid = 1234
            filled._set_config_file_permissions(str(config_file))
        chown.assert_called_once_with(str(config_file), os.getuid(), 1234)
        assert oct(config_file.stat().st_mode & 0o777) == "0o640"

    def test_write_send_log(self, filled, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "logging_config.yaml").write_text("handlers:\n  file:\n    send_log: false\n")
        filled.send_log = True
        filled._write_send_log()
        config = yaml.safe_load((tmp_path / "logging_config.yaml").read_text())
        assert config["handlers"]["file"]["send_log"] is True

    def test_write_systemd_service(self, filled, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "alarmmonitor.service").write_text("[Service]\nUser=root\nType=simple\n")
        filled._write_systemd_service()
        assert (tmp_path / "alarmmonitor.service").read_text() == (
            "[Service]\nUser=pi\nType=simple\n"
        )


def test_configure_reports_interrupt(configurator, capsys):
    with patch.object(
        configurator, "_configure_blaulichtsms_account", side_effect=KeyboardInterrupt
    ):
        configurator.configure()
    assert "interrupted" in capsys.readouterr().err
