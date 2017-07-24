#!/usr/bin/python

from __future__ import print_function
import requests
import sys
import os
import logging
from time import sleep

POLLING_INTERVAL = 5 #seconds
TV_ON_TIME = 1800 #seconds
BASE_URL = "https://api.blaulichtsms.net/blaulicht/api/alarm/v1/dashboard/"

CUSTOMER_ID = ""
USERNAME = ""
PASSWORD = ""

session_id = None
old_alarm_ids = []

def init_session():
    try:
        logging.info("Initialising session")
        content = {"username": USERNAME, "password": PASSWORD, "customerId": CUSTOMER_ID}
        response = requests.post(BASE_URL + "login", json = content)
        return response.json()["sessionId"]
    except requests.exceptions.ConnectionError:
        return None
    
def check_for_alarm():
    try:
        response = requests.get(BASE_URL + session_id)
        alarms = response.json()["alarms"]
        for alarm in alarms:
            alarm_id = alarm["alarmId"]
            if not alarm_id in old_alarm_ids:
                old_alarm_ids.append(alarm_id)
                return True
    except requests.exceptions.ConnectionError:
        pass
    return False

def handle_tv():
    logging.info("Alarm occured - power on tv")
    os.system("echo 'on 0' | cec-client RPI -s -d 1")
    sleep(TV_ON_TIME)
    logging.info("tv in standby")
    os.system("echo 'standby 0' | cec-client RPI -s -d 1")

logging.basicConfig(format="%(asctime)s %(message)s", datefmt="%Y-%m-%d %I:%M:%S %p", level=logging.DEBUG)
logging.info("Service started")
while True:
    session_id = init_session()
    if session_id:
        break
    sleep(5)

logging.info("Session init succesful")
check_for_alarm()
while True:
    try:
        is_alarm = False
        logging.debug("Checking for alarm")
        is_alarm = check_for_alarm()
        if is_alarm:
            handle_tv()
        else:
            sleep(POLLING_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt - terminating")
        sys.exit(0)

