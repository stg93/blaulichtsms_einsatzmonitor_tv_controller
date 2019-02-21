import datetime
import uuid

from flask import Flask, jsonify, request

from blaulichtsmscontroller import BlaulichtSmsController


class Alarm:
    def __init__(self, polling_interval, update_count):
        self._polling_interval = polling_interval
        self._update_count = update_count
        self.get_alarm_requests_count = 0
        self.alarm_id = uuid.uuid4()
        # microsecond > 1 is required to match format "%Y-%m-%dT%H:%M:%S.%fZ"
        self.alarm_datetime = datetime.datetime(2015, 1, 1, microsecond=1)

    def get_alarm(self):
        """Mocks an blaulichtSMS Dashboard API alarms element.

        The mocked alarm is initially inactive.
        After :_update_count: requests the alarm is active.

        :return: An blaulichtSMS Dashboard API alarms element
        """
        if self.get_alarm_requests_count == self._update_count:
            self._update_alarm()
        self.get_alarm_requests_count += 1

        alarm_date_str = self.alarm_datetime.isoformat()[:-3] + "Z"
        return {
            "alarms": [{
                "alarmDate": alarm_date_str,
                "alarmId": self.alarm_id
            }]
        }

    def _update_alarm(self):
        """Updates the alarm to be an active one."""
        self.time_delta = datetime.timedelta(seconds=int(self._polling_interval * 1.5))

        self.alarm_datetime = datetime.datetime.utcnow() - self.time_delta
        self.alarm_id = uuid.uuid4()


app = Flask(__name__)
alarm = None


# noinspection PyUnusedLocal
@app.route("/<session_token>")
def get_alarms(session_token):
    return jsonify(alarm.get_alarm())


@app.route("/login", methods=["POST"])
def login():
    """Redirects the login to the real blaulichtSMS Dashboard API to get a real session token.

    Otherwise, the application would not be able to login to the blaulichtSMS Einsatzmonitor web application.

    :return: An blaulichtSMS Dashboard API session element in JSON
    """
    login_data = request.get_json()
    blaulicht_sms_controller = BlaulichtSmsController(
        login_data["customerId"],
        login_data["username"],
        login_data["password"]
    )
    return jsonify({"sessionId": blaulicht_sms_controller.get_session()})
