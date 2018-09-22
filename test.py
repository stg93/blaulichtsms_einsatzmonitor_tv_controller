from main import get_logging_config, set_up_logging
from main import drop_privileges, _get_run_user

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
    print("######## TEST FINISHED ########")
    print("The HDMI CEC device should have been turned on for 5 minutes.")
    print("The blaulichtSMS Einsatzmonitor should have been displayed.")
    print("Errors: " + str(error_count))
    print("Warnings:" + str(warning_count))
    print("")
    print("Log is written to '{}'".format(logging_output_file))
    print("###############################")


def main():
    """Starts a Chromium browser instance which is displaying
    the blaulichtSMS Einsatzmonitor.
    Requests alarms from blaulichtSMS.
    Turns the HDMI device on.
    After 5 minutes closes the browser,
    turns the HDMI device off and
    prints a summary containing the number of errors and warnings
    and the path to the log of the test.
    """
    logging_config = get_logging_config("logging_config_test.yaml")
    set_up_logging(logging_config)
    drop_privileges(
            _get_run_user(),
            logging_config["handlers"]["file"]["filename"])

    # importing after drop_privileges to prevent Python from importing
    # the root cec module in hdmiceccontroller and causing problems
    # after dropping privileges
    from alarmmonitortest import AlarmMonitorTest

    alarm_monitor_test = AlarmMonitorTest()
    alarm_monitor_test.run()
    generate_test_summary(logging_config["handlers"]["file"]["filename"])


if __name__ == '__main__':
    main()
