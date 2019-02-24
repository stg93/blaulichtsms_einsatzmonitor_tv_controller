import configparser
import logging
import logging.config

import yaml

from alarmmonitormailsender import AlarmMonitorMailSender
from blaulichtsmscontroller import BlaulichtSmsController
from chromiumbrowsercontroller import ChromiumBrowserController
from hdmiceccontroller import HdmiCecController

logger = None

CONFIG = configparser.ConfigParser()
CONFIG.read("config.ini")


def set_up_logging(logging_config):
    """Configures the logging for the module according to the dict
    logging_config.
    """
    logging.config.dictConfig(logging_config)

    global logger
    logger = logging.getLogger(__name__)
    logger.debug("Initialized logging")


def get_logging_config(logging_config_filepath):
    with open(logging_config_filepath) as logging_config_file:
        logging_config = yaml.load(logging_config_file)
    return logging_config


def main():
    logging_config = get_logging_config("logging_config.yaml")
    set_up_logging(logging_config)

    # importing after drop_privileges to prevent Python from importing
    # the root cec module in hdmiceccontroller and causing problems
    # after dropping privileges
    from alarmmonitor import AlarmMonitor

    alarm_duration = CONFIG.getint("Alarmmonitor", "hdmi_cec_device_on_time")
    polling_interval = CONFIG.getint("Alarmmonitor", "polling_interval")
    send_errors = CONFIG.getboolean("Alarmmonitor", "send_errors")
    send_starts = CONFIG.getboolean("Alarmmonitor", "send_starts")

    blaulichtsms_controller = BlaulichtSmsController(
        CONFIG["blaulichtSMS Einsatzmonitor"]["customer_id"],
        CONFIG["blaulichtSMS Einsatzmonitor"]["username"],
        CONFIG["blaulichtSMS Einsatzmonitor"]["password"],
        alarm_duration=alarm_duration
    )
    mail_sender = AlarmMonitorMailSender()
    hdmi_cec_controller = HdmiCecController(send_errors, mail_sender)
    browser_controller = ChromiumBrowserController(blaulichtsms_controller.get_session())

    alarm_monitor = AlarmMonitor(polling_interval, send_errors, send_starts,
                                 blaulichtsms_controller, hdmi_cec_controller, browser_controller, mail_sender)
    alarm_monitor.run()


if __name__ == '__main__':
    main()
