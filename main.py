import configparser
import logging
import logging.config
from typing import Any

import yaml

from alarmmonitor import AlarmMonitor
from alarmmonitormailsender import AlarmMonitorMailSender
from blaulichtsmscontroller import BlaulichtSmsController
from chromiumbrowsercontroller import ChromiumBrowserController
from hdmiceccontroller import (
    AbstractCecController,
    CecLogging,
    CecMode,
    LibCecController,
    NoCecController,
    PythonCecController,
)

logger = None


def set_up_logging(logging_config: dict[str, Any]) -> None:
    """Configures the logging for the module according to the dict
    logging_config.

    :param logging_config: A configuration for :func:`logging.config.dictConfig`
    """
    logging.config.dictConfig(logging_config)

    global logger
    logger = logging.getLogger(__name__)
    logger.debug("Initialized logging")


def get_logging_config(logging_config_filepath: str) -> dict[str, Any]:
    """Loads the logging configuration from a YAML file.

    :param logging_config_filepath: The path of the YAML file
    :return: The logging configuration
    """
    with open(logging_config_filepath) as logging_config_file:
        logging_config = yaml.safe_load(logging_config_file)
    return logging_config


def get_cec_controller(
    config: configparser.ConfigParser,
    send_errors: bool,
    mail_sender: AlarmMonitorMailSender | None,
) -> AbstractCecController:
    """Creates the HDMI CEC controller selected by ``cec_mode`` in the config.

    Invalid values for ``cec_mode`` or ``cec_logging`` fall back to libCEC
    with error logging.

    :param config: The parsed ``config.ini``
    :param send_errors: Whether to send emails about HDMI errors
    :param mail_sender: Sends the error emails, may be None if send_errors is False
    :return: The CEC controller
    """
    cec_mode_index = None
    try:
        cec_mode_index = config.getint("Alarmmonitor", "cec_mode")
        cec_mode = CecMode(cec_mode_index)
    except ValueError:
        logger.warning("Invalid CEC mode: %s", cec_mode_index)
        cec_mode = CecMode.LIB_CEC
    logger.info("Using CEC mode: " + cec_mode.name)

    cec_logging_index = None
    try:
        cec_logging_index = config.getint(
            "Alarmmonitor", "cec_logging", fallback=CecLogging.CEC_LOG_ERROR.value
        )
        cec_logging = CecLogging(cec_logging_index)
    except ValueError:
        logger.warning("Invalid CEC logging level: %s", cec_logging_index)
        cec_logging = CecLogging.CEC_LOG_ERROR

    try:
        device_id = config.get("Alarmmonitor", "cec_device_id", fallback="1")
    except ValueError:
        logger.warning("Invalid cec_device_id")
        device_id = "1"

    if cec_mode == CecMode.DISABLED:
        return NoCecController(send_errors, mail_sender)
    elif cec_mode == CecMode.PYTHON_CEC:
        return PythonCecController(send_errors, mail_sender)
    else:
        return LibCecController(
            send_errors, mail_sender, debug_level=cec_logging, device_id=device_id
        )


def main() -> None:
    """Reads the configuration and runs the alarm monitor."""
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
        show_infos=show_infos,
    )
    mail_sender = AlarmMonitorMailSender()
    hdmi_cec_controller = get_cec_controller(config, send_errors, mail_sender)
    browser_controller = ChromiumBrowserController(blaulichtsms_controller.get_session())
    alarm_monitor = AlarmMonitor(
        polling_interval,
        send_errors,
        send_starts,
        blaulichtsms_controller,
        hdmi_cec_controller,
        browser_controller,
        mail_sender,
    )
    alarm_monitor.run()


if __name__ == "__main__":
    main()
