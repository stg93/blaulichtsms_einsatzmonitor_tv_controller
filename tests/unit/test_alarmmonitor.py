from unittest.mock import MagicMock, patch

import pytest

import alarmmonitor
from alarmmonitor import AlarmMonitor


@pytest.fixture
def parts():
    return {
        "blaulichtsms_controller": MagicMock(),
        "hdmi_cec_controller": MagicMock(),
        "browser_controller": MagicMock(),
        "mail_sender": MagicMock(),
    }


def make_monitor(parts, send_errors=True, send_starts=False) -> AlarmMonitor:
    return AlarmMonitor(30, send_errors, send_starts, **parts)


class TestRunHelper:
    def test_starts_browser_on_init(self, parts):
        make_monitor(parts)
        parts["browser_controller"].start.assert_called_once()

    def test_activates_source_on_alarm(self, parts):
        parts["blaulichtsms_controller"].is_alarm.return_value = True
        monitor = make_monitor(parts)
        monitor._run_helper()
        parts["hdmi_cec_controller"].activate_source.assert_called_once()
        parts["hdmi_cec_controller"].standby.assert_not_called()

    def test_standby_without_alarm(self, parts):
        parts["blaulichtsms_controller"].is_alarm.return_value = False
        monitor = make_monitor(parts)
        monitor._run_helper()
        parts["hdmi_cec_controller"].standby.assert_called_once()
        parts["hdmi_cec_controller"].activate_source.assert_not_called()

    def test_reschedules_itself(self, parts):
        monitor = make_monitor(parts)
        monitor._run_helper()
        (event,) = monitor.scheduler.queue
        assert event.action == monitor._run_helper


class TestCheckBrowserStatus:
    def test_restarts_crashed_browser_and_mails_once(self, parts):
        parts["browser_controller"].is_alive.return_value = False
        parts["blaulichtsms_controller"].get_session.return_value = "new-token"
        monitor = make_monitor(parts)

        with patch.object(alarmmonitor, "ChromiumBrowserController") as browser_class:
            browser_class.return_value.is_alive.return_value = False
            monitor._check_browser_status()
            monitor._check_browser_status()

        browser_class.assert_called_with("new-token")
        assert browser_class.return_value.start.call_count == 2
        parts["mail_sender"].send_message.assert_called_once()
        assert "crashed" in parts["mail_sender"].send_message.call_args.args[0]

    def test_mails_when_browser_runs_again(self, parts):
        parts["browser_controller"].is_alive.return_value = False
        monitor = make_monitor(parts)
        with patch.object(alarmmonitor, "ChromiumBrowserController") as browser_class:
            monitor._check_browser_status()
            browser_class.return_value.is_alive.return_value = True
            monitor._check_browser_status()

        assert parts["mail_sender"].send_message.call_count == 2
        assert "resolved" in parts["mail_sender"].send_message.call_args.args[0]

    def test_no_mail_if_errors_are_not_sent(self, parts):
        parts["browser_controller"].is_alive.return_value = False
        monitor = make_monitor(parts, send_errors=False)
        with patch.object(alarmmonitor, "ChromiumBrowserController"):
            monitor._check_browser_status()
        parts["mail_sender"].send_message.assert_not_called()


class TestRun:
    def test_stops_on_keyboard_interrupt_and_cleans_up(self, parts):
        parts["hdmi_cec_controller"].is_on.return_value = True
        monitor = make_monitor(parts, send_starts=True)

        with (
            patch.object(monitor, "_run_helper"),
            patch.object(monitor.scheduler, "run", side_effect=KeyboardInterrupt),
        ):
            monitor.run()

        parts["mail_sender"].send_message.assert_called_once_with("The AlarmMonitor has started.")
        parts["hdmi_cec_controller"].standby.assert_called_once()
        parts["browser_controller"].terminate.assert_called_once()

    def test_no_standby_if_tv_is_off(self, parts):
        parts["hdmi_cec_controller"].is_on.return_value = False
        monitor = make_monitor(parts)
        with (
            patch.object(monitor, "_run_helper"),
            patch.object(monitor.scheduler, "run", side_effect=KeyboardInterrupt),
        ):
            monitor.run()
        parts["hdmi_cec_controller"].standby.assert_not_called()
        parts["mail_sender"].send_message.assert_not_called()
