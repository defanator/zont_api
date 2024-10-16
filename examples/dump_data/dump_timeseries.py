#!/usr/bin/env python3

import sys
import json
from datetime import datetime, timedelta
from zont_api import ZontAPI, DATA_TYPES_Z3K


def main():
    zapi = ZontAPI()
    devices = zapi.get_devices()

    dt_to = datetime.now()
    dt_from = dt_to - timedelta(minutes=5)

    data = []

    for device in devices:
        interval = (dt_from.timestamp(), dt_to.timestamp())
        data.append(
            zapi.load_data(device.id, data_types=DATA_TYPES_Z3K, interval=interval)
        )

    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
