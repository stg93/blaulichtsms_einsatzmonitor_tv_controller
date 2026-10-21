from alarmmonitor import AlarmMonitor
from blaulichtsmscontroller import BlaulichtSmsController
from chromiumbrowsercontroller import ChromiumBrowserController
from hdmiceccontroller import AbstractCecController


class AlarmMonitorTest(AlarmMonitor):
    """Alarm monitor for the system test that stops after a fixed number of
    alarm requests and never sends emails."""

    def __init__(
        self,
        polling_interval: int,
        blaulichtsms_controller: BlaulichtSmsController,
        hdmi_cec_controller: AbstractCecController,
        browser_controller: ChromiumBrowserController,
        alarm_requests_count: int,
    ) -> None:
        """Initializes the alarm monitor without email notifications.

        :param polling_interval: Seconds between two alarm checks
        :param blaulichtsms_controller: Requests the alarms
        :param hdmi_cec_controller: Controls the HDMI device
        :param browser_controller: Controls the browser showing the dashboard
        :param alarm_requests_count: The number of alarm checks before stopping
        """
        super().__init__(
            polling_interval,
            False,
            False,
            blaulichtsms_controller,
            hdmi_cec_controller,
            browser_controller,
            None,
        )
        self._run_count = 0
        self._alarm_requests_count = alarm_requests_count

    def _run_helper(self) -> None:
        """The main loop of the application.
        Reschedules itself to run every :_polling_interval: seconds for :_alarm_requests_count: times.

        Ensures that a browser which is displaying the blaulichtSMS Einsatzmonitor dashboard is running.
        Checks if communication with an HDMI device via CEC is possible.
        """
        if self._run_count < self._alarm_requests_count:
            self.scheduler.enter(self._polling_interval, 1, self._run_helper)
            self._run_count += 1

        self._check_browser_status()

        if self.blaulichtsms_controller.is_alarm():
            self.hdmi_cec_controller.power_on()
        else:
            self.hdmi_cec_controller.standby()
