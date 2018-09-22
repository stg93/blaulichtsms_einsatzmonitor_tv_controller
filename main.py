import yaml
import logging
import logging.config
import pwd
import os
import configparser

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
        logging_config = yaml.load(logging_config_file)
    return logging_config


def drop_privileges(username, logging_file):
    """Drops root privileges if the module is run as systemd service,
    as they are not required.
    """
    if os.getuid() != 0:
        logger.info("Not running as root. Cannot drop permissions.")
    else:
        logger.debug("User has root privileges. Dropping them...")

        old_uid = os.getuid()
        old_gid = os.getgid()
        old_groups = os.getgroups()

        user_db_entry = pwd.getpwnam(username)
        new_uid = user_db_entry.pw_uid
        new_gid = user_db_entry.pw_gid
        new_groups = os.getgrouplist(username, new_gid)

        os.chown(os.path.dirname(logging_file), new_uid, new_gid)
        os.chown(logging_file, new_uid, new_gid)
        logger.debug("Changed file owner and group of logging file")

        os.setgid(new_gid)
        os.setgroups(new_groups)
        os.setuid(new_uid)

        os.environ["HOME"] = user_db_entry.pw_dir
        os.environ["LOGNAME"] = user_db_entry.pw_name

        logger.debug("Changed uid from {} to {}".format(old_uid, new_uid))
        logger.debug("Changed gid from {} to {}".format(old_gid, new_gid))
        logger.debug("Changed groups from {} to {}".format(
            old_groups, new_groups))

        logger.info("Dropped privileges. No longer running as root.")


def _get_run_user():
    """Returns the preferred Linux username to run the process."""
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config["Alarmmonitor"]["run_user"]


def main():
    logging_config = get_logging_config("logging_config.yaml")
    set_up_logging(logging_config)
    drop_privileges(
        _get_run_user(),
        logging_config["handlers"]["file"]["filename"])

    # importing after drop_privileges to prevent Python from importing
    # the root cec module in hdmiceccontroller and causing problems
    # after dropping privileges
    from alarmmonitor import AlarmMonitor

    alarm_monitor = AlarmMonitor()
    alarm_monitor.run()


if __name__ == '__main__':
    main()
