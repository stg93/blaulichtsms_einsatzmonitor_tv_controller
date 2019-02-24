import configparser
from multiprocessing import Process

from blaulichtsmscontroller import BlaulichtSmsController
from chromiumbrowsercontroller import ChromiumBrowserController
from main import get_logging_config, set_up_logging, get_cec_controller
from tests import dashboardapimock
from tests.alarmmonitortest import AlarmMonitorTest
from tests.dashboardapimock import app, Alarm

logger = None


def generate_test_summary(logging_output_file):
    error_count = 0
    warning_count = 0
    with open(logging_output_file) as file:
        for line in file:
            if "ERROR" in line:
                error_count += 1
            if "WARNING" in line:
                warning_count += 1

    _print_test_summary(error_count, warning_count, logging_output_file)


def _print_test_summary(error_count, warning_count, logging_output_file):
    print("")
    print("######## TEST FINISHED ########")
    print("Expected behaviour:")
    print("")
    print("  * Starts a Chromium browser instance which is displaying the blaulichtSMS Einsatzmonitor.")
    print("  * Requests three times alarms from the blaulichtSMS mock API, with no active alarms.")
    print("  * Receives an active alarm at the fourth API request and powers the HDMI device on.")
    print("  * After 30 seconds the alarm is no longer active and the HDMI device switches to standby.")
    print("  * Requests some more alarms without any active alarms.")
    print("  * Shuts down the alarm monitor and prints this summary containing the number of errors and warnings")
    print("    and the path to the log of the test.")
    print("")
    print("Errors:   " + str(error_count))
    print("Warnings: " + str(warning_count))
    print("")
    print("Log is written to '{}'".format(logging_output_file))
    print("###############################")


def main():
    """Runs a system test for the alarm monitor.

    Expected behaviour:

    * Starts a Chromium browser instance which is displaying the blaulichtSMS Einsatzmonitor.
    * Requests :api_update_count: times alarms from the blaulichtSMS mock API, with no active alarms.
    * Receives an active alarm at the :api_request_count: + 1 API request and powers the HDMI device on.
    * After :alarm_duration: seconds the alarm is no longer active and the HDMI device switches to standby.
    * Requests some more alarms without any active alarms.
    * Shuts down the alarm monitor and prints a summary containing the number of errors and warnings
      and the path to the log of the test.
    """
    logging_config = get_logging_config("logging_config_test.yaml")
    set_up_logging(logging_config)

    config = configparser.ConfigParser()
    config.read("config.ini")

    polling_interval = 10  # alarms are requested from the API every n seconds
    alarm_duration = 60  # an alarm is active it is within the last n seconds
    api_update_count = 6  # the mock api returns an active alarm after n requests
    api_requests_count = 18  # the test requests alarms from the API n times

    dashboardapimock.alarm = Alarm(polling_interval, api_update_count)
    server_mock = Process(target=app.run)
    server_mock.start()

    mock_blaulichtsms_controller = BlaulichtSmsController(
        config["blaulichtSMS Einsatzmonitor"]["customer_id"],
        config["blaulichtSMS Einsatzmonitor"]["username"],
        config["blaulichtSMS Einsatzmonitor"]["password"],
        alarm_duration=alarm_duration,
        base_url="http://localhost:5000/"
    )
    hdmi_cec_controller = get_cec_controller(config, False, None)
    browser_controller = ChromiumBrowserController(mock_blaulichtsms_controller.get_session())

    alarm_monitor_test = AlarmMonitorTest(polling_interval, mock_blaulichtsms_controller, hdmi_cec_controller,
                                          browser_controller, api_requests_count)
    alarm_monitor_test.run()

    server_mock.terminate()
    generate_test_summary(logging_config["handlers"]["file"]["filename"])


if __name__ == '__main__':
    main()
