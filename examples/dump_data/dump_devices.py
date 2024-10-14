#!/usr/bin/env python3

import sys
import json
from zont_api import ZontAPI


def main():
    zapi = ZontAPI()

    device_data = []
    devices = zapi.get_devices()

    for device in devices:
        device_data.append(device.data)

    print(json.dumps(device_data, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
