from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from blaulichtsmscontroller import BlaulichtSmsController, BlaulichtSmsSessionInitException

BASE_URL = "https://api.example.test/dashboard/"


def make_controller(**kwargs) -> BlaulichtSmsController:
    return BlaulichtSmsController("123456", "user", "secret", base_url=BASE_URL, **kwargs)


def api_date(moment: datetime) -> str:
    """Formats a datetime like the blaulichtSMS Dashboard API does."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def json_response(body: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = body
    return response


class TestGetSession:
    def test_returns_session_id_and_posts_credentials(self):
        controller = make_controller()
        with patch("requests.post", return_value=json_response({"sessionId": "abc"})) as post:
            assert controller.get_session() == "abc"
        post.assert_called_once_with(
            BASE_URL + "login",
            json={"customerId": "123456", "username": "user", "password": "secret"},
        )

    def test_returns_none_if_login_fails(self):
        controller = make_controller()
        with patch("requests.post", return_value=json_response({"sessionId": None})):
            assert controller.get_session() is None

    def test_raises_if_api_is_unreachable(self):
        controller = make_controller()
        with (
            patch("requests.post", side_effect=requests.exceptions.ConnectionError),
            pytest.raises(BlaulichtSmsSessionInitException),
        ):
            controller.get_session()


class TestGetAlarms:
    def test_creates_session_once_and_reuses_it(self):
        controller = make_controller()
        with (
            patch.object(controller, "get_session", return_value="token") as get_session,
            patch("requests.get", return_value=json_response({"alarms": []})) as get,
        ):
            controller._get_alarms()
            controller._get_alarms()
        get_session.assert_called_once()
        get.assert_called_with(BASE_URL + "token")

    def test_ignores_infos_by_default(self):
        controller = make_controller()
        body = {"alarms": [{"alarmId": 1}], "infos": [{"alarmId": 2}]}
        with (
            patch.object(controller, "get_session", return_value="token"),
            patch("requests.get", return_value=json_response(body)),
        ):
            assert controller._get_alarms() == [{"alarmId": 1}]

    def test_includes_infos_if_enabled(self):
        controller = make_controller(show_infos=True)
        body = {"alarms": [{"alarmId": 1}], "infos": [{"alarmId": 2}]}
        with (
            patch.object(controller, "get_session", return_value="token"),
            patch("requests.get", return_value=json_response(body)),
        ):
            assert controller._get_alarms() == [{"alarmId": 1}, {"alarmId": 2}]

    def test_returns_none_if_api_is_unreachable(self):
        controller = make_controller()
        with (
            patch.object(controller, "get_session", return_value="token"),
            patch("requests.get", side_effect=requests.exceptions.ConnectionError),
        ):
            assert controller._get_alarms() is None


class TestIsAlarm:
    @pytest.mark.parametrize(
        ("age", "expected"),
        [
            (timedelta(minutes=5), True),
            (timedelta(minutes=59), True),
            (timedelta(minutes=61), False),
            (timedelta(days=3), False),
        ],
    )
    def test_alarm_is_active_within_alarm_duration(self, age, expected):
        controller = make_controller(alarm_duration=3600)
        alarm = {"alarmId": 1, "alarmDate": api_date(datetime.now(UTC) - age)}
        with patch.object(controller, "_get_alarms", return_value=[alarm]):
            assert controller.is_alarm() is expected

    def test_any_active_alarm_is_enough(self):
        controller = make_controller(alarm_duration=3600)
        now = datetime.now(UTC)
        alarms = [
            {"alarmId": 1, "alarmDate": api_date(now - timedelta(days=1))},
            {"alarmId": 2, "alarmDate": api_date(now - timedelta(minutes=1))},
        ]
        with patch.object(controller, "_get_alarms", return_value=alarms):
            assert controller.is_alarm() is True

    @pytest.mark.parametrize("alarms", [None, []])
    def test_no_alarms_means_no_active_alarm(self, alarms):
        controller = make_controller()
        with patch.object(controller, "_get_alarms", return_value=alarms):
            assert controller.is_alarm() is False
