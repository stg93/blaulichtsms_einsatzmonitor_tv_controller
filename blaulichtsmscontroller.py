import logging
import requests
from pprint import pformat
from datetime import datetime


class BlaulichtSmsException(Exception):
    pass


class BlaulichtSmsSessionInitException(BlaulichtSmsException):
    def __init__(self):
        self.message = "Unable to initialize session"


class BlaulichtSmsAlarmRequestException(BlaulichtSmsException):
    EXCEPTION_MSG = "Request for blaulichtSMS alarms failed"

    def __init__(self):
        self.message = self.EXCEPTION_MSG


class BlaulichtSmsController:
    """Handles the communication with the
    `blaulichtSMS Dashboard API
    <https://github.com/blaulichtSMS/docs/blob/master/dashboard_api_v1.md>`_
    """

    _BASE_URL = \
        "https://api.blaulichtsms.net/blaulicht/api/alarm/v1/dashboard/"

    def __init__(self, customer_id, username, password):
        self.logger = logging.getLogger(__name__)
        self.customer_id = customer_id
        self.username = username
        self.password = password
        self.last_alarm_check = datetime.now()
        self.session = self.get_session()

    def get_session(self):
        try:
            self.logger.info("Initialising blaulichtSMS session...")
            content = {
                "customerId": self.customer_id,
                "username": self.username,
                "password": self.password
            }
            response = requests.post(self._BASE_URL + "login", json=content)
            session_id = response.json()["sessionId"]
            if not session_id:
                raise BlaulichtSmsSessionInitException()
            self.logger.info("Session initialized succesfully")
            return session_id
        except requests.exceptions.ConnectionError:
            raise BlaulichtSmsSessionInitException()
        except BlaulichtSmsSessionInitException as e:
            self.logger.error(e.message)
            raise e

    def _get_alarms(self):
        try:
            self.logger.info("Requesting blaulichtSMS alarms...")
            response = requests.get(self._BASE_URL + self.session)
            self.logger.info("Request succesful")
            self.logger.debug("Response body: \n" + pformat(response.json()))
            return response.json()["alarms"]
        except requests.exceptions.ConnectionError:
            request_exception = BlaulichtSmsAlarmRequestException()
            self.logger.error(request_exception.message)
            raise request_exception

    def is_alarm(self):
        self.logger.info("Checking for new alarms...")
        self.logger.debug(
                "Last time checked for new alarms: "
                + str(self.last_alarm_check)
        )
        alarms = self._get_alarms()
        for alarm in alarms:
            alarm_datetime = datetime.strptime(
                alarm["alarmDate"],
                '%Y-%m-%dT%H:%M:%S.%fZ'
            )
            self.logger.debug(
                "Alarm " + str(alarm["alarmId"])
                + " on " + str(alarm_datetime)
            )
            if self.last_alarm_check < alarm_datetime:
                self.logger.debug(
                    "Alarm " + str(alarm["alarmId"]) + " is new")
                self.logger.info("There is a new alarm")
                self.last_alarm_check = datetime.now()
                return True
        self.logger.info("No new alarm found")
        self.last_alarm_check = datetime.now()
        return False
