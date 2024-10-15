#!/usr/bin/env python3

import sys
import json
from datetime import datetime, timedelta
from zont_api import ZontAPI


def main():
    zapi = ZontAPI()
    devices = zapi.get_devices()

    dt_to = datetime.now()
    dt_from = dt_to - timedelta(minutes=5)

    data_types = [
        "z3k_temperature",
        "z3k_heating_circuit",
        "z3k_boiler_adapter",
        "z3k_analog_input",
    ]

    data = []

    for device in devices:
        interval = (dt_from.timestamp(), dt_to.timestamp())
        data.append(zapi.load_data(device.id, data_types=data_types, interval=interval))

    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
