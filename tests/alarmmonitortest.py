from alarmmonitor import AlarmMonitor


class AlarmMonitorTest(AlarmMonitor):
    def __init__(self, polling_interval, blaulichtsms_controller, hdmi_cec_controller, browser_controller,
                 alarm_requests_count):
        super().__init__(polling_interval, False, False,
                         blaulichtsms_controller, hdmi_cec_controller, browser_controller, None)
        self._run_count = 0
        self._alarm_requests_count = alarm_requests_count

    def _run_helper(self):
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
