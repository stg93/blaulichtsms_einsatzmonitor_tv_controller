import hdmiceccontroller
import logging
# import cec
import time

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('test')

log.info("starting")
cec = hdmiceccontroller.LibCecController(False,
                                         "",
                                         debug_level=hdmiceccontroller.CecLogging.CEC_LOG_ERROR)
try:
    # time.sleep(8)
    log.info("activate source")
    cec.activate_source()
    time.sleep(10)
    log.info("check is on")
    is_on = cec.is_on()
    log.info('is on %s', 'yes' if is_on else 'no')

    log.info('activating standby')
    cec.standby()
    time.sleep(10)
    log.info("check is on")
    is_on = cec.is_on()
    log.info('is on %s', 'yes' if is_on else 'no')

    log.info('power on')
    cec.power_on()
    time.sleep(10)

    log.info("check is on")
    is_on = cec.is_on()
    log.info('is on %s', 'yes' if is_on else 'no')
except Exception as e:
    log.exception('cec test failed: %s', e)
    cec.__del__()
