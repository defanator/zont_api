"""
The :mod:`zont_api` module provides a way of interacting with Zont API

https://zont-online.ru/api/docs/
"""

import logging
import json
from os import environ
from time import time
from datetime import datetime
import requests

from .version import __version__, __build__


__author__ = "Andrei Belov"
__license__ = "MIT"
__copyright__ = f"Copyright (c) {__author__}"


logger = logging.getLogger(__name__)


class ZontAPIException(Exception):
    """
    Base class for Zont API exception
    """

    __description__ = "Zont API exception"
    __status_code__ = 500

    def __init__(self, message=None, status_code=None, description=None):
        super().__init__(message)
        self.message = message
        self.status_code = (
            status_code if status_code else ZontAPIException.__status_code__
        )
        self.description = description

    def __str__(self):
        if self.description:
            return (
                f"{self.__class__.__name__}: {self.status_code}: "
                f"{self.message} ({self.description})"
            )

        return f"{self.__class__.__name__}: {self.status_code}: " f"{self.message}"


class ZontAPI:
    """
    Base class for using Zont API

    Useful links:
    https://zont-online.ru/api/docs/
    https://www.forumhouse.ru/threads/533363/page-2
    """

    # base API URL
    __api_url_base__ = "https://lk.zont-online.ru/api"

    # keys with potential PII to filter out
    __pii_keys__ = (
        "ip",
        "login",
        "netname",
        "operator",
        "owner_username",
        "pass",
        "password",
        "phone",
        "serial",
        "usbpassword",
        "user_id",
        "username",
    )

    # dicts with potential PII to substitute
    __pii_dicts__ = {"sim_id": {"sim_id": {"operator": "***", "id": "***"}}}

    # lists with potential PII to substitute
    __pii_lists__ = {"loc": {"loc": []}}

    # API token
    api_token = None

    # API client
    api_client = None

    def __init__(self, token=None, client=None):
        """
        Initialize API object

        Both token and client values can be obtained from environment
        variables ZONT_API_TOKEN and ZONT_API_CLIENT (accordingly) if
        not specified on initialization.

        :param token: str - Zont API token
        :param client: str - Zont API client
        """

        self.api_token = token
        if not self.api_token:
            self.api_token = environ.get("ZONT_API_TOKEN")

        if not self.api_token:
            token_file = environ.get("ZONT_API_TOKEN_FILE", None)
            if token_file:
                with open(token_file, "r", encoding="ascii") as file:
                    self.api_token = file.readline().rstrip("\n")

        if not self.api_token:
            raise ZontAPIException(
                "token not provided",
                400,
                "Token must be provided either explicitly, "
                "or via ZONT_API_TOKEN environment variable, "
                "or via file pointed via ZONT_API_TOKEN_FILE environment variable",
            )

        self.api_client = client
        if not self.api_client:
            self.api_client = environ.get("ZONT_API_CLIENT")

        if not self.api_client:
            client_file = environ.get("ZONT_API_CLIENT_FILE", None)
            if client_file:
                with open(client_file, "r", encoding="ascii") as file:
                    self.api_client = file.readline().rstrip("\n")

        if not self.api_client:
            raise ZontAPIException(
                "client not provided",
                400,
                "Client must be provided either explicitly "
                "or via ZONT_API_CLIENT environment variable, "
                "or via file pointed via ZONT_API_CLIENT_FILE environment variable",
            )

        self.api_headers = {
            "User-Agent": f"zont_api/{__version__} ({__build__})",
            "X-ZONT-Client": f"{self.api_client}",
            "X-ZONT-Token": f"{self.api_token}",
        }

        logger.info(
            "%s initialized for client %s",
            self.api_headers["User-Agent"],
            self.api_client,
        )

    @staticmethod
    def filter_pii(data: dict) -> dict:
        """
        Recursive function to remove PII from API responses
        for safe logging

        :param data: dict - response data
        """

        if not isinstance(data, dict) and not isinstance(data, list):
            return data

        for k, v in data.items():
            if isinstance(v, dict):
                if k in ZontAPI.__pii_dicts__:
                    return ZontAPI.__pii_dicts__.get(k)
                data[k] = ZontAPI.filter_pii(v)

            elif isinstance(v, list):
                if k in ZontAPI.__pii_lists__:
                    return ZontAPI.__pii_lists__.get(k)
                data[k] = [ZontAPI.filter_pii(i) for i in v]

            else:
                if k in ZontAPI.__pii_keys__:
                    data[k] = "***"

        return data

    def check_for_errors(self, result, action):
        """
        Verify API response for known errors

        :param result: dict - API response
        :param action: str - action name
        """

        if not result.get("ok"):
            error = result.get("error", f"{action} failed")

            status_code = 500
            if error == "auth_failed":
                status_code = 403
            elif error == "no_such_device":
                status_code = 404

            raise ZontAPIException(error, status_code)

    def api_request(self, api_route, data):
        """
        Make a request to Zont API and return response data

        :param api_route: str - API route
        :param data: dict - request body
        :return: dict - Decoded JSON response
        """

        try:
            result = requests.post(
                f"{self.__api_url_base__}{api_route}",
                headers=self.api_headers,
                json=data,
                timeout=5,
            ).json()
        except Exception as exc:
            raise ZontAPIException("API call failed", description=str(exc)) from exc

        if result is None:
            return None

        self.check_for_errors(result, f"API call to {api_route}")

        return result

    def get_devices(self):
        """
        Obtain list of Zont devices

        :return: [] of ZontDevice objects
        """

        data = {"load_io": True}

        try:
            result = self.api_request("/devices", data)
        except ZontAPIException as exc:
            logger.error("get_devices(): %s", str(exc))
            raise exc

        if result is None:
            return []

        raw_devices = result.get("devices")

        if not raw_devices:
            return []

        if not isinstance(raw_devices, list):
            return []

        devices = []
        try:
            for device_data in raw_devices:
                self.filter_pii(device_data)
                logger.debug("device found: %s", json.dumps(device_data))
                devices.append(ZontDevice(device_data, api=self))
        except Exception as exc:
            logger.error("get_devices(): %s", str(exc))
            raise exc

        return devices

    def load_data(
        self, device_id: int, data_types: list = None, interval: tuple = None
    ) -> dict:
        """
        Obtain various data for a given device

        :param device_id: int - device ID (ZontDevice.id)
        :param data_types: list - data types to query
        :param interval: tuple - time interval (from + to in UNIX time)
        :return: dict - key is sensor ID, value is
          https://zont-online.ru/api/docs/?python#delta-time-array
        """

        # if interval not specified, return last minute value(s)
        if not interval:
            now = int(time())
            interval = (now - 60, now)

        # if data types are not specified, use z3k subset
        if not data_types:
            data_types = [
                "z3k_temperature",
                "z3k_heating_circuit",
                "z3k_boiler_adapter",
                "z3k_analog_input",
            ]

        data = {
            "requests": [
                {
                    "device_id": device_id,
                    "data_types": data_types,
                    "mintime": int(interval[0]),
                    "maxtime": int(interval[1]),
                }
            ]
        }

        try:
            result = self.api_request("/load_data", data)

        except ZontAPIException as exc:
            logger.error("load_data(): %s", str(exc))
            return None

        logger.debug("load_data: %s", json.dumps(result))

        responses = result.get("responses", [])

        if len(responses) == 0:
            raise ZontAPIException("no data found", 404)

        if responses[0].get("device_id") != device_id:
            raise ZontAPIException("no data found", 404)

        if not responses[0].get("ok"):
            raise ZontAPIException(responses[0].get("error", "load data failed"))

        if "timings" in responses[0].keys():
            del responses[0]["timings"]

        return responses[0]

    def convert_delta_time_array(self, delta_time_array, sort=True, reverse=False):
        """
        Converts delta time array to another array with absolute timestamps
        instead of relative ones

        :param delta_time_array: [] representing delta time array
          (https://zont-online.ru/api/docs/?python#delta-time-array)
        :param sort: bool - sort results by absolute timestamp
        :param reverse: bool - reverse sort order
        :return: [] with absolute timestamps
        """

        if not isinstance(delta_time_array, list):
            raise ValueError(
                f"parent: list expected but found {type(delta_time_array).__name__}"
            )

        result = []
        latest_stamp, curr_stamp = 0, 0

        for element in delta_time_array:
            if not isinstance(element, list):
                raise ValueError(
                    f"element: list expected but found {type(element).__name__}"
                )

            timestamp_or_delta = int(element[0])

            if timestamp_or_delta > 0:
                # absolute timestamp in UNIX time
                latest_stamp = timestamp_or_delta
                curr_stamp = latest_stamp

            elif timestamp_or_delta < 0:
                # time delta in seconds
                curr_stamp = curr_stamp + abs(timestamp_or_delta)

            else:
                # we do not expect zero value here
                continue

            result.append([curr_stamp] + element[1:])

        if sort:
            return sorted(result, key=lambda t: t[0], reverse=reverse)

        return result


class ZontDevice:
    """
    Base class for representing Zont device
    """

    id = None
    name = None

    def __init__(self, device_data: dict = None, api: ZontAPI = None):
        """
        Initialize Zont device object

        :param device_data: dict - data from
          https://zont-online.ru/api/docs/?python#devices API call
        """

        if device_data is None:
            device_data = {}

        if "id" not in device_data:
            raise ZontAPIException("device must have an ID")

        if "name" not in device_data:
            raise ZontAPIException("device must have a name")

        self.data = device_data
        self.api = api

        self.id = self.data.get("id")
        self.name = self.data.get("name")
        self.last_seen = datetime.fromtimestamp(self.data.get("last_receive_time", 0))
        self.last_seen_relative = self.data.get("last_receive_time_relative", -1)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.name} (id={self.id})"

    def get_analog_inputs(self):
        """
        Get list of analog inputs available on a given device

        :return: [] of analog inputs
        """
        source = self.data.get("z3k_config").get("analog_inputs")

        if not isinstance(source, list):
            return None

        elements = []
        for element in source:
            elements.append(
                {
                    "device_id": self.id,
                    "id": element.get("id"),
                    "family": "analog_inputs",
                    "name": element.get("name"),
                    "sensor_type": element.get("sensor_type"),
                }
            )
        return elements

    def get_analog_temperature_sensors(self):
        """
        Get list of analog temperature sensors available on a given device

        :return: [] of analog temperature sensors
        """
        source = self.data.get("z3k_config").get("analog_temperature_sensors")

        if not isinstance(source, list):
            return None

        elements = []
        for element in source:
            elements.append(
                {
                    "device_id": self.id,
                    "id": element.get("id"),
                    "family": "analog_temperature_sensors",
                    "name": element.get("name"),
                    "type": element.get("type"),
                }
            )
        return elements

    def get_boiler_adapters(self):
        """
        Get list of boiler adapters available on a given device

        :return: [] of boiler adapters
        """
        source = self.data.get("z3k_config").get("boiler_adapters")

        if not isinstance(source, list):
            return None

        elements = []
        for element in source:
            elements.append(
                {
                    "device_id": self.id,
                    "id": element.get("id"),
                    "family": "boiler_adapters",
                    "name": element.get("name"),
                    "adapter_type": element.get("adapter_type"),
                    "type": element.get("type"),
                    "boiler_model": element.get("boiler_model"),
                }
            )
        return elements

    def get_sensor_name(self, sensor_id: int) -> str:
        """
        Obtain sensor name by its ID

        :param sensor_id: int - sensor ID
        :return: str - sensor name
        """

        for source_family in [
            "analog_inputs",
            "analog_temperature_sensors",
            "boiler_adapters",
            "heating_circuits",
            "io_extensions",
            "radiosensors",
            "radiosensors433",
            "wired_temperature_sensors",
        ]:
            source = self.data.get("z3k_config").get(source_family)
            if not isinstance(source, list):
                continue

            for sensor in source:
                if sensor is None:
                    continue

                if int(sensor.get("id")) == int(sensor_id):
                    return sensor.get("name")

        return None

    def update_info(self) -> bool:
        """
        Refresh device information

        :return: bool - status of operation
        """

        if not self.api:
            raise ZontAPIException("API object not associated with a given device", 400)

        devices = self.api.get_devices()

        if len(devices) == 0:
            return False

        for device in devices:
            if device.id == self.id:
                self.data = device.data.copy()
                self.last_seen = datetime.fromtimestamp(
                    self.data.get("last_receive_time", 0)
                )
                self.last_seen_relative = self.data.get(
                    "last_receive_time_relative", -1
                )
                return True

        return False
