import logging
from datetime import datetime, timedelta
from pprint import pformat

import requests


class BlaulichtSmsSessionInitException(Exception):
    pass


class BlaulichtSmsController:
    """Handles the communication with the
    `blaulichtSMS Dashboard API
    <https://github.com/blaulichtSMS/docs/blob/master/dashboard_api_v1.md>`_
    """

    def __init__(self, customer_id, username, password, on_time="08:00", off_time="19:00", alarm_duration=3600, show_infos=False, 
                 base_url="https://api.blaulichtsms.net/blaulicht/api/alarm/v1/dashboard/"):
        self.logger = logging.getLogger(__name__)

        self.customer_id = customer_id
        self.username = username
        self.password = password
        self.on_time = on_time
        self.off_time = off_time
        self.alarm_duration = timedelta(seconds=alarm_duration)
        self.show_infos = show_infos
        self.base_url = base_url

        self._session_token = None

    def get_session(self):
        """Gets a new session token from the blaulichtSMS Dashboard API at every call.

        :return: The session token
        """
        try:
            self.logger.info("Initializing blaulichtSMS session...")
            content = {
                "customerId": self.customer_id,
                "username": self.username,
                "password": self.password
            }
            response = requests.post(self.base_url + "login", json=content)
            session_id = response.json()["sessionId"]
            if session_id:
                self.logger.info("Successfully initialized blaulichtSMS session")
            else:
                self.logger.warning("Failed to initialize blaulichtSMS session")
            return session_id
        except requests.exceptions.ConnectionError as e:
            raise BlaulichtSmsSessionInitException() from e

    def _get_alarms(self):
        """Gets the alarms from the blaulichtSMS Dashboard API"""
        if not self._session_token:
            self._session_token = self.get_session()

        try:
            self.logger.info("Requesting blaulichtSMS alarms...")
            response = requests.get(self.base_url + self._session_token)
            self.logger.info("Request successful")
            self.logger.debug("Response body: \n" + pformat(response.json()))
            response_json = response.json()
            alarms = response_json.get("alarms", [])
            if self.show_infos:
                alarms += response_json.get("infos", [])
            return alarms
        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to request blaulichtSMS alarms. Maybe there is no internet connection.")
            return None

    def is_alarm(self):
        """Checks if there is any active alarm.

        An alarm is active if it's datetime is greater than or equals the current datetime minus :alarm_duration:.
        The datetimes are all in UTC.

        :return: True if there is any active alarm, False otherwise
        """
        self.logger.info("Checking for new alarms...")
        alarms = self._get_alarms()
        if not alarms:
            return False
        for alarm in alarms:
            alarm_datetime = datetime.strptime(alarm["alarmDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
            self.logger.debug("Alarm " + str(alarm["alarmId"]) + " on " + str(alarm_datetime))
            if alarm_datetime >= datetime.utcnow() - self.alarm_duration:
                self.logger.debug("Alarm " + str(alarm["alarmId"]) + " is active")
                self.logger.info("There is an active alarm")
                return True
        self.logger.info("No active alarm found")
        return False


    def is_showtime(self):
        """Checks if the screen should be switched on.
        """
        
        """Get current time """
        jetzt = datetime.now().time()

        """Assign time range """
        start_time = datetime.strptime(self.on_time, "%H:%M").time()
        end_time = datetime.strptime(self.off_time, "%H:%M").time()

        show = False
        if  jetzt >= start_time:
            if jetzt < end_time:
                show = True
                
        return show
