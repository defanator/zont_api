#!/usr/bin/env python3

import sys
import logging
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_client import make_wsgi_app, Gauge
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from zont_api import ZontAPI, ZontAPIException

APP_NAME = "zont_prom_exporter"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(threadName)s: %(message)s",
)

logger = logging.getLogger(APP_NAME)

"""
urllib3_log = logging.getLogger('urllib3')
urllib3_log.setLevel(logging.DEBUG)
from http.client import HTTPConnection
HTTPConnection.debuglevel = 1
"""

app = Flask(APP_NAME)

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})

# напряжение питания
# input voltage
VOLTAGE = Gauge("zont_input_voltage", "Input voltage", ["device_id", "sensor_id"])

# температура воздуха в помещении
# indoor air temperature
INDOOR_AIR_TEMP = Gauge(
    "zont_indoor_air_temp", "Indoor air temperature", ["device_id", "sensor_id"]
)

# уличная температура
# outdoor air temperature
BOILER_OTA_OT = Gauge(
    "zont_boiler_outdoor_air_temp",
    "Outdoor air temperature",
    ["device_id", "sensor_id"],
)

# расчетная температура теплоносителя
# heat-transfer fluid design temperature
BOILER_OTA_CS = Gauge(
    "zont_boiler_htf_design_temp",
    "Heat-transfer fluid design temperature",
    ["device_id", "sensor_id"],
)

# фактическая температура теплоносителя
# heat-transfer fluid actual temperature
BOILER_OTA_BT = Gauge(
    "zont_boiler_htf_actual_temp",
    "Heat-transfer fluid actual temperature",
    ["device_id", "sensor_id"],
)

# расчетная температура ГВС
# DHW design temperature
BOILER_OTA_DS = Gauge(
    "zont_boiler_dhw_design_temp",
    "Domestic hot water design temperature",
    ["device_id", "sensor_id"],
)

# фактическая температура ГВС
# DHW actual temperature
BOILER_OTA_DT = Gauge(
    "zont_boiler_dhw_actual_temp",
    "Domestic hot water actual temperature",
    ["device_id", "sensor_id"],
)

# уровень модуляции горелки
# burner modulation level
BOILER_OTA_RML = Gauge(
    "zont_boiler_rml", "Burner modulation level", ["device_id", "sensor_id"]
)

# авария котла
# boiler failure status
BOILER_OTA_FAILED = Gauge(
    "zont_boiler_failed", "Boiler failure status", ["device_id", "sensor_id"]
)

# последний код ошибки
# boiler last error code
BOILER_OTA_ERROR = Gauge(
    "zont_boiler_error", "Latest error code", ["device_id", "sensor_id"]
)


zapi = None
zdevice = None


def update_metrics() -> bool:
    """
    Update Prometheus metrics based on recent data obtained
    from Zont API

    :return: bool - status of operation
    """
    global zdevice

    voltage_inputs = zdevice.get_analog_inputs()
    temperature_sensors = zdevice.get_analog_temperature_sensors()
    boiler_adapters = zdevice.get_boiler_adapters()

    z3k = zdevice.data.get("io").get("z3k-state")

    if not z3k:
        logger.error(
            'z3k-state subtree not found for "%s" (%d})', zdevice.name, zdevice.id
        )
        return False

    rc = True

    for voltage_input in voltage_inputs:
        sensor_id = str(voltage_input.get("id"))
        sensor_name = voltage_input.get("name")
        try:
            VOLTAGE.labels(zdevice.id, sensor_id).set(z3k.get(sensor_id).get("voltage"))
            logger.info("%s/%s (%s) updated", zdevice.id, sensor_id, sensor_name)
        except Exception as e:
            logger.error(
                "%s/%s (%s) update failed: %s",
                zdevice.id,
                sensor_id,
                sensor_name,
                str(e),
            )
            rc = False

    for temperature_sensor in temperature_sensors:
        sensor_id = str(temperature_sensor.get("id"))
        sensor_name = temperature_sensor.get("name")
        try:
            INDOOR_AIR_TEMP.labels(zdevice.id, sensor_id).set(
                z3k.get(sensor_id).get("curr_temp")
            )
            logger.info("%s/%s (%s) updated", zdevice.id, sensor_id, sensor_name)
        except Exception as e:
            logger(
                "%s/%s (%s) update failed: %s",
                zdevice.id,
                sensor_id,
                sensor_name,
                str(e),
            )
            rc = False

    for boiler_adapter in boiler_adapters:
        adapter_id = str(boiler_adapter.get("id"))
        adapter_name = boiler_adapter.get("name")
        try:
            z3k_ot = z3k.get(adapter_id).get("ot")
            BOILER_OTA_OT.labels(zdevice.id, adapter_id).set(z3k_ot.get("ot"))
            BOILER_OTA_CS.labels(zdevice.id, adapter_id).set(z3k_ot.get("cs"))
            BOILER_OTA_BT.labels(zdevice.id, adapter_id).set(z3k_ot.get("bt"))
            BOILER_OTA_DS.labels(zdevice.id, adapter_id).set(z3k_ot.get("ds"))
            BOILER_OTA_DT.labels(zdevice.id, adapter_id).set(z3k_ot.get("dt"))
            BOILER_OTA_RML.labels(zdevice.id, adapter_id).set(z3k_ot.get("rml"))

            status = z3k_ot.get("s", [])
            # TODO: should we keep these metrics permanently instead of setting on error only?
            if len(status) > 0:
                if "f" in status:
                    boiler_error = z3k_ot.get("ff", {}).get("c", 0)
                    logger.info("boiler error detected: E%02d", boiler_error)
                    BOILER_OTA_FAILED.labels(zdevice.id, adapter_id).set(1)
                    BOILER_OTA_ERROR.labels(zdevice.id, adapter_id).set(boiler_error)

            logger.info("%s/%s (%s) updated", zdevice.id, adapter_id, adapter_name)
        except Exception as e:
            logger.error(
                "%s/%s (%s) update failed: %s",
                zdevice.id,
                adapter_id,
                adapter_name,
                str(e),
            )
            rc = False

    return rc


def initialize_zont_device() -> bool:
    """
    Gather initial information on monitored device

    :return: bool - status of operation
    """
    global zapi, zdevice

    try:
        zapi = ZontAPI()
        zdevice = zapi.get_devices()[0]

    except ZontAPIException as e:
        logger.error("error while initializing ZontAPI: %s", str(e))
        return False

    except IndexError:
        logger.error("no devices found")
        return False

    logger.info('found device "%s" (%d)', zdevice.name, zdevice.id)
    return True


def update_zont_data():
    """
    Auxiliary function that is intended to be called periodically
    from a scheduler with a goal of polling fresh device data from
    Zont API and update Prometheus metrics
    """
    global zdevice

    if not zdevice.update_info():
        logger.error('failed to update data for "%s" (%d)', zdevice.name, zdevice.id)
        return

    logger.info(
        'refreshed data for "%s" (%d) as of %s (%d seconds ago)',
        zdevice.name,
        zdevice.id,
        zdevice.last_seen.strftime("%Y-%m-%d %H:%M:%S"),
        zdevice.last_seen_relative,
    )

    if not update_metrics():
        logger.error('failed to update metrics for "%s" (%d)', zdevice.name, zdevice.id)
        return


def main():
    """
    Entrypoint function
    """

    if not initialize_zont_device():
        logger.error("failed to initialize device")
        sys.exit(1)

    if not update_metrics():
        logger.error("failed to do initial metrics update")
        sys.exit(1)

    scheduler = BackgroundScheduler()
    scheduler.add_job(update_zont_data, "interval", seconds=60)
    scheduler.start()

    app.run(host="0.0.0.0", port=6000)


@app.route("/")
def default():
    """
    Placeholder for the default route
    """
    return "Try /metrics!\n"


if __name__ == "__main__":
    main()
