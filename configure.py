import configparser
import json
import re
import stat
import sys
from getpass import getpass
from os import getuid, chown, chmod
from os.path import isfile
from pwd import getpwuid, getpwnam

import yaml

from blaulichtsmscontroller import BlaulichtSmsController
from hdmiceccontroller import CecMode
from sendmail import MailSender


class AlarmMonitorConfigurator:
    def __init__(self):
        self.blaulichtsms_customer_id = ""
        self.blaulichtsms_username = ""
        self.blaulichtsms_password = ""
        self.blaulichtsms_show_infos = False

        self.hdmi_cec_device_on_time = "0"
        self.run_user = ""

        self.gmail_username = ""
        self.gmail_password = ""
        self.recipients = []
        self.send_errors = False
        self.send_starts = False
        self.send_log = False
        self.cec_mode = CecMode.PYTHON_CEC

        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = "465"
        self.subject = "Einsatzmonitor"

        self.polling_interval = "30"

    def _get_input_with_validation(
            self, prompt, invalid_prompt, validation_func):
        print(prompt)
        user_input = input()
        while not validation_func(user_input):
            print("")
            self._print_warning(invalid_prompt)
            user_input = input()
        return user_input

    def _get_password_input(self, prompt, retype_prompt="Retype password:"):
        while True:
            password = getpass(prompt=prompt + "\n")
            print("")
            retyped_pwd = getpass(prompt=retype_prompt + "\n")
            if password == retyped_pwd:
                return password
            else:
                print("")
                self._print_warning("The entered passwords did not match.")

    def _is_yes_input(self, prompt):
        user_input = self._get_input_with_validation(
            prompt + "[yes|no]",
            "Please answer with either 'yes' or 'no'",
            self._is_yes_no
        )
        return user_input == "yes" or user_input == "y"

    def _configure_blaulichtsms_account(self):
        while True:
            self._configure_blaulichtsms_customer_id()
            print("")
            self._configure_blaulichtsms_username()
            print("")
            self._configure_blaulichtsms_password()
            print("")
            if not self._are_valid_blaulichtsms_credentials():
                self._print_warning(
                    "Unable to connect with the given credentials.")
            else:
                break
        self._configure_blaulichtsms_show_infos()
        print("")

    def _configure_blaulichtsms_customer_id(self):
        self.blaulichtsms_customer_id = self._get_input_with_validation(
            "Please enter your blaulichtSMS customer id:",
            "Please enter a valid 6 digit blaulichtSMS customer id:",
            self._is_valid_blaulichtsms_customer_id
        )

    def _configure_blaulichtsms_username(self):
        print("Please enter your blaulichtSMS Einsatzmonitor username:")
        self.blaulichtsms_username = input()

    def _configure_blaulichtsms_password(self):
        self.blaulichtsms_password = self._get_password_input(
            "Please enter your blaulichtSMS Einsatzmonitor password:"
        )

    def _configure_blaulichtsms_show_infos(self):
        self.blaulichtsms_show_infos = self._is_yes_input("Do you want to show infos in addition to alarms?")

    def _configure_alarmmonitor(self):
        self._configure_hdmi_cec_device_on_time()
        print("")
        self._configure_run_user()

    def _configure_hdmi_cec_device_on_time(self):
        prompt = "Please enter the seconds the HDMI device" + \
            " should be on after receiving an alarm:"

        self.hdmi_cec_device_on_time = self._get_input_with_validation(
            prompt,
            "Please enter a positive integer value:",
            self._is_positive_int
        )

    def _configure_run_user(self):
        while True:
            print(
                "Please enter the Linux user's name under whom"
                + " the application should run:\n"
                + "(If you are unsure skip this step to use the current user)")
            run_user = input()
            if not run_user:
                current_uid = getuid()
                current_username = getpwuid(current_uid).pw_name
                self.run_user = current_username
                print("")
                break
            elif self._is_valid_system_user(run_user):
                self.run_user = run_user
                break
            else:
                print("")
                self._print_warning(
                    "Please enter a valid username for the system.")

    def _configure_gmail(self):
        email_notifications = \
            self._is_yes_input("Do you want to receive email notifications?")
        if email_notifications:
            while True:
                print("")
                self._configure_gmail_username()
                print("")
                self._configure_gmail_password()
                if self._are_valid_gmail_credentials():
                    break
                else:
                    print("")
                    self._print_warning(
                        "Unable to connect to Gmail with this credentials.")
            print("")
            self._configure_recipients()
            print("")
            self.send_errors = \
                self._is_yes_input("Do you want to send emails about errors?")
            print("")
            self.send_starts = self._is_yes_input(
                "Do you want to send emails about application starts?")
            print("")
            self.send_log = self._is_yes_input(
                "Do you want to send the log of the day via email?")

    def _configure_gmail_username(self):
        print("A Gmail account is required to send email notifications.")
        self.gmail_username = self._get_input_with_validation(
            "Please enter the Gmail account's username:",
            "Please insert a valid Gmail address:",
            self._is_valid_gmail
        )

    def _configure_gmail_password(self):
        self.gmail_password = self._get_password_input(
            "Please enter the Gmail account's password:"
        )

    def _configure_recipients(self):
        finished = False
        recipients = None
        while not finished:
            print(
                "Please enter a comma separated list"
                + " of log recipients email addresses:")
            recipients = input()
            recipients = recipients.split(",")
            finished = True
            for recipient in recipients:
                recipient = recipient.strip()
                if not self._is_valid_email(recipient):
                    self._print_warning(
                        "\n'{}' is not a valid email address"
                        .format(recipient))
                    finished = False
        self.recipients = recipients

    @staticmethod
    def _is_valid_blaulichtsms_customer_id(customer_id):
        return re.match("^[0-9]{6}$", customer_id)

    def _are_valid_blaulichtsms_credentials(self):
        blaulichtsms_controller = BlaulichtSmsController(
            self.blaulichtsms_customer_id,
            self.blaulichtsms_username,
            self.blaulichtsms_password)
        return blaulichtsms_controller.get_session() is not None

    @staticmethod
    def _is_positive_int(integer_string):
        try:
            integer = int(integer_string)
            return integer > 0
        except ValueError:
            return False

    @staticmethod
    def _is_valid_system_user(username):
        try:
            getpwnam(username)
            return True
        except KeyError:
            return False

    @staticmethod
    def _is_yes_no(user_input):
        return user_input == "yes" or user_input == "y" \
               or user_input == "no" or user_input == "n"

    @staticmethod
    def _is_valid_gmail(email):
        return re.match("^.+@gmail\\.com$", email)

    def _are_valid_gmail_credentials(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        mail_sender = MailSender(
            self.smtp_server,
            self.smtp_port,
            self.gmail_username,
            self.gmail_password
        )
        return mail_sender.get_connection() is not None

    @staticmethod
    def _is_valid_email(email):
        return re.match("^.+@.+\\.[a-z]+$", email)

    def _write(self):
        self._write_config_ini()
        self._write_send_log()
        self._write_systemd_service()

    def _write_config_ini(self):
        if isfile("config.ini"):
            config = configparser.ConfigParser()
            config.read("config.ini")
        else:
            config = self._get_config_scaffold()
        self._write_blaulichtsms_section(config)
        self._write_alarmmonitor_section(config)
        self._write_email_section(config)

        config_file_name = "config.ini"
        with open(config_file_name, "w") as config_file:
            config.write(config_file)
        self._set_config_file_permissions(config_file_name)

    def _set_config_file_permissions(self, config_file_name):
        gid = getpwnam(self.run_user).pw_gid
        chown(config_file_name, getuid(), gid)
        chmod(config_file_name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)

    @staticmethod
    def _get_config_scaffold():
        config = configparser.ConfigParser()
        config["Email"] = {}
        config["blaulichtSMS Einsatzmonitor"] = {}
        config["Alarmmonitor"] = {}
        return config

    def _write_blaulichtsms_section(self, config):
        config["blaulichtSMS Einsatzmonitor"]["customer_id"] = self.blaulichtsms_customer_id
        config["blaulichtSMS Einsatzmonitor"]["username"] = self.blaulichtsms_username
        config["blaulichtSMS Einsatzmonitor"]["password"] = self.blaulichtsms_password
        config["blaulichtSMS Einsatzmonitor"]["show_infos"] = str(self.blaulichtsms_show_infos)

    def _write_alarmmonitor_section(self, config):
        config["Alarmmonitor"]["hdmi_cec_device_on_time"] = self.hdmi_cec_device_on_time
        config["Alarmmonitor"]["polling_interval"] = self.polling_interval
        config["Alarmmonitor"]["run_user"] = self.run_user
        config["Alarmmonitor"]["send_errors"] = str(self.send_errors)
        config["Alarmmonitor"]["send_starts"] = str(self.send_starts)
        config["Alarmmonitor"]["cec_mode"] = str(self.cec_mode.value)

    def _write_email_section(self, config):
        config["Email"]["username"] = self.gmail_username
        config["Email"]["password"] = self.gmail_password
        config["Email"]["smtp_server"] = self.smtp_server
        config["Email"]["smtp_port"] = self.smtp_port
        config["Email"]["from_addr"] = self.gmail_username
        config["Email"]["to_addrs"] = json.dumps(self.recipients)
        config["Email"]["subject"] = self.subject

    def _write_send_log(self):
        with open("logging_config.yaml", "r") as logging_config:
            config = yaml.load(logging_config)
        config["handlers"]["file"]["send_log"] = self.send_log
        with open("logging_config.yaml", "w") as file:
            yaml.dump(config, file, default_flow_style=False)

    def _write_systemd_service(self):
        with open("alarmmonitor.service") as service_file:
            service_file_content = service_file.read()
            service_file_content = re.sub("User=.*", "User=" + self.run_user, service_file_content)
        with open("alarmmonitor.service", "w") as service_file:
            service_file.write(service_file_content)

    @staticmethod
    def _print_warning(msg):
        ansi_warn = "\033[93m"
        ansi_end = "\033[0m"
        print(ansi_warn + msg + ansi_end)

    @staticmethod
    def _print_error(msg):
        ansi_error = "\033[91m"
        ansi_end = "\033[0m"
        print(ansi_error + msg + ansi_end, file=sys.stderr)

    @staticmethod
    def _print_success(msg):
        ansi_success = "\033[92m"
        ansi_end = "\033[0m"
        print(ansi_success + msg + ansi_end)

    def configure(self):
        try:
            self._configure_blaulichtsms_account()
            self._configure_alarmmonitor()
            self._configure_gmail()
            self._write()

            print("")
            self._print_success("Configuration successful.")
            print(
                "There are additional settings"
                + " to configure in the config files."
            )
        except KeyboardInterrupt:
            self._print_error("Configuration was interrupted")


if __name__ == "__main__":
    configurator = AlarmMonitorConfigurator()
    configurator.configure()
