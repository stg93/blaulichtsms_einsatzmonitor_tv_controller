import configparser
import logging
import logging.config

import yaml

from alarmmonitor import AlarmMonitor
from alarmmonitormailsender import AlarmMonitorMailSender
from blaulichtsmscontroller import BlaulichtSmsController
from chromiumbrowsercontroller import ChromiumBrowserController
from hdmiceccontroller import (CecLogging, CecMode, LibCecController, PythonCecController)

logger = None


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
        logging_config = yaml.safe_load(logging_config_file)
    return logging_config


def get_cec_controller(config, send_errors, mail_sender):
    cec_mode_index = None
    try:
        cec_mode_index = config.getint("Alarmmonitor", "cec_mode")
        cec_mode = CecMode(cec_mode_index)
    except ValueError:
        logger.warning("Invalid CEC mode: " + cec_mode_index)
        cec_mode = CecMode.LIB_CEC
    logger.info("Using CEC mode: " + cec_mode.name)

    cec_logging_index = None
    try:
        cec_logging_index = config.getint("Alarmmonitor",
                                          "cec_logging",
                                          fallback=CecLogging.CEC_LOG_ERROR.value)
        cec_logging = CecMode(cec_logging_index)
    except ValueError:
        logger.warning("Invalid CEC logging level: " + cec_logging_index)
        cec_logging = CecLogging.CEC_LOG_ERROR

    try:
        device_id = config.get("Alarmmonitor", "cec_device_id", fallback="1")
    except ValueError:
        logger.warning("Invalid cec_device_id")
        device_id = "1"

    if cec_mode == CecMode.PYTHON_CEC:
        return PythonCecController(send_errors, mail_sender)
    else:
        return LibCecController(send_errors,
                                mail_sender,
                                debug_level=cec_logging,
                                device_id=device_id)


def main():
    logging_config = get_logging_config("logging_config.yaml")
    set_up_logging(logging_config)

    config = configparser.ConfigParser()
    config.read("config.ini")

    alarm_duration = config.getint("Alarmmonitor", "hdmi_cec_device_on_time")
    polling_interval = config.getint("Alarmmonitor", "polling_interval")
    send_errors = config.getboolean("Alarmmonitor", "send_errors")
    send_starts = config.getboolean("Alarmmonitor", "send_starts")
    show_infos = config.getboolean("blaulichtSMS Einsatzmonitor", "show_infos")

    blaulichtsms_controller = BlaulichtSmsController(
        config["blaulichtSMS Einsatzmonitor"]["customer_id"],
        config["blaulichtSMS Einsatzmonitor"]["username"],
        config["blaulichtSMS Einsatzmonitor"]["password"],
        alarm_duration=alarm_duration,
        show_infos=show_infos)
    mail_sender = AlarmMonitorMailSender()
    hdmi_cec_controller = get_cec_controller(config, send_errors, mail_sender)
    browser_controller = ChromiumBrowserController(blaulichtsms_controller.get_session())
    alarm_monitor = AlarmMonitor(polling_interval, send_errors, send_starts,
                                 blaulichtsms_controller, hdmi_cec_controller, browser_controller,
                                 mail_sender)
    alarm_monitor.run()


if __name__ == '__main__':
    main()
