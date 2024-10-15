#!/usr/bin/env python3

import sys
import json
from zont_api import ZontAPI


def main():
    zapi = ZontAPI()

    sensors_data = []
    devices = zapi.get_devices()

    for device in devices:
        sensors_data.extend(device.get_analog_inputs())
        sensors_data.extend(device.get_analog_temperature_sensors())
        sensors_data.extend(device.get_boiler_adapters())
        sensors_data.extend(device.get_heating_circuits())

    print(json.dumps(sensors_data, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
