"""
Tests for ZontDevice
"""

import logging
from unittest.mock import patch, MagicMock
from copy import deepcopy
from requests import exceptions as requests_exceptions
import pytest
from zont_api import ZontAPIException, ZontAPI, ZontDevice


__author__ = "Andrei Belov"
__license__ = "MIT"
__copyright__ = f"Copyright (c) {__author__}"


MOCK_API_RESPONSE_AUTH_FAILED = {
    "ok": False,
    "error": "auth_failed",
    "error_ui": "ui_message_for_auth_failed",
}

MOCK_API_RESPONSE_DEVICE_NOT_FOUND = {
    "ok": False,
    "error": "no_such_device",
    "error_ui": "ui_message_for_no_such_device",
}

MOCK_API_RESPONSE_SINGLE_DEVICE = {
    "ok": True,
    "devices": [
        {
            "id": 42,
            "name": "my_device_42",
            "last_receive_time": 1000,
        }
    ],
}

MOCK_API_RESPONSE_SINGLE_DEVICE_UPDATE = {
    "ok": True,
    "devices": [
        {
            "id": 42,
            "name": "my_device_42",
            "last_receive_time": 1060,
        }
    ],
}

MOCK_API_RESPONSE_SINGLE_DEVICE_UPDATE_NOT_FOUND = {
    "ok": True,
    "devices": [
        {
            "id": 451,
            "name": "my_device_451",
            "last_receive_time": 700,
        }
    ],
}

MOCK_API_RESPONSE_SINGLE_DEVICE_WITH_PII = {
    "ok": True,
    "devices": [
        {
            "id": 42,
            "name": "my_device_42",
            "last_receive_time": 1000,
            "ip": "10.0.0.1",
            "login": "my_login",
            "users": [
                {
                    "name": "my_user_name",
                    "phone": "+75555555555",
                    "key_and_radiotag_list": [],
                    "role_list": [],
                    "password": "my_password",
                    "setting_register": 0,
                    "id": 444555,
                },
            ],
            "sim_in_device": {
                "sim_type": "billed",
                "sim_id": {
                    "operator": "mts_nn",
                    "id": "777777",
                },
                "foreign_msisdn": None,
            },
            "stationary_location": {
                "loc": [
                    -41.114219296609804,
                    146.0738271985185,
                ],
            },
        },
    ],
}

MOCK_API_RESPONSE_SINGLE_DEVICE_WITH_PII_UPDATE = deepcopy(
    MOCK_API_RESPONSE_SINGLE_DEVICE_WITH_PII
)
MOCK_API_RESPONSE_SINGLE_DEVICE_WITH_PII_UPDATE["devices"][0][
    "last_receive_time"
] = 1060

print(MOCK_API_RESPONSE_SINGLE_DEVICE_WITH_PII_UPDATE)

MOCK_API_RESPONSE_MULTIPLE_DEVICES = {
    "ok": True,
    "devices": [
        {
            "id": 42,
            "name": "my_device_42",
        },
        {
            "id": 451,
            "name": "my_device_451",
        },
    ],
}

MOCK_API_RESPONSE_NO_DEVICES_SUBTREE = {
    "ok": True,
}

MOCK_API_RESPONSE_EMPTY_DEVICES_LIST = {
    "ok": True,
    "devices": [],
}

MOCK_API_RESPONSE_INVALID_DEVICES_TYPE = {
    "ok": True,
    "devices": "i_am_string",
}

MOCK_API_RESPONSE_SINGLE_DEVICE_WITHOUT_ID = {
    "ok": True,
    "devices": [
        {
            "name": "my_device_with_unknown_id",
        }
    ],
}

MOCK_API_RESPONSE_SINGLE_DEVICE_WITHOUT_NAME = {
    "ok": True,
    "devices": [
        {
            "id": 777,
        }
    ],
}

MOCK_API_RESPONSE_DEVICE_WITH_SENSORS = {
    "ok": True,
    "devices": [
        {
            "id": 42,
            "name": "my_device_42",
            "z3k_config": {
                "analog_inputs": [
                    {
                        "physical_input_num": 123,
                        "name": "voltage input control",
                        "id": 777123,
                    },
                ],
                "analog_temperature_sensors": [
                    {
                        "physical_input_num": 456,
                        "name": "air sensor",
                        "id": 777456,
                    }
                ],
                "boiler_adapters": [
                    {
                        "boiler_model": "baxi-eco-four",
                        "name": "opentherm adapter",
                        "slot": 0,
                        "position": 0,
                        "id": 777789,
                    }
                ],
                "wired_temperature_sensors": [],
                "radiosensors": [],
                "radiosensors433": None,
                "io_extensions": [None],
            },
        }
    ],
}


def test_init_device_directly():
    """
    Create ZontDevice manually with a given data dict
    """
    zdev = ZontDevice(device_data={"id": 42, "name": "testdevice"})
    assert isinstance(zdev, ZontDevice)
    assert zdev.id == 42
    assert zdev.name == "testdevice"
    assert str(zdev) == "ZontDevice: testdevice (id=42)"


def test_init_device_directly_no_data():
    """
    Create ZontDevice manually without any parameters
    """
    with pytest.raises(ZontAPIException, match=r"500: device must have an ID"):
        _ = ZontDevice()


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_403(mock_requests, caplog):
    """
    Emulate 403 from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = MOCK_API_RESPONSE_AUTH_FAILED
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="wrongtoken", client="wrongclient")
    assert isinstance(zapi, ZontAPI)
    with pytest.raises(ZontAPIException, match=r"403: auth_failed"):
        _ = zapi.get_devices()


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_404(mock_requests, caplog):
    """
    Emulate 404 from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = MOCK_API_RESPONSE_DEVICE_NOT_FOUND
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    with pytest.raises(ZontAPIException, match=r"404: no_such_device"):
        _ = zapi.get_devices()


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_500(mock_requests, caplog):
    """
    Emulate 500 Internal Server Error from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {}
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    with pytest.raises(ZontAPIException, match=r"500: API call to /devices failed"):
        _ = zapi.get_devices()


@patch("zont_api.zont_api.requests.post")
def test_init_device_from_api_connection_error(mock_requests_post, caplog):
    """
    Emulate network issue in ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_requests_post.side_effect = requests_exceptions.ConnectTimeout()

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    with pytest.raises(ZontAPIException, match=r"500: API call failed"):
        _ = zapi.get_devices()


@patch("zont_api.zont_api.requests")
def test_init_device_from_api(mock_requests, caplog):
    """
    Create single ZontDevice from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 1

    assert devices[0].api.api_token == "testtoken"
    assert devices[0].api.api_client == "testclient"
    assert devices[0].id == 42
    assert devices[0].name == "my_device_42"
    assert str(devices[0]) == "ZontDevice: my_device_42 (id=42)"


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_pii_filtered(mock_requests, caplog):
    """
    Create single ZontDevice with PII from ZontAPI.get_devices() and make sure PII is filtered
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE_WITH_PII
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 1

    # verify that PII was filtered
    assert devices[0].data["ip"] == "***"
    assert devices[0].data["login"] == "***"
    assert devices[0].data["sim_in_device"]["sim_id"]["operator"] == "***"
    assert devices[0].data["sim_in_device"]["sim_id"]["id"] == "***"
    assert devices[0].data["stationary_location"]["loc"] == []
    assert devices[0].data["users"][0]["phone"] == "***"
    assert devices[0].data["users"][0]["password"] == "***"


@patch("zont_api.zont_api.requests")
def test_init_devices_from_api(mock_requests, caplog):
    """
    Create multiple ZontDevices from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_MULTIPLE_DEVICES
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 2

    assert devices[0].api.api_token == "testtoken"
    assert devices[0].api.api_client == "testclient"
    assert devices[0].id == 42
    assert devices[0].name == "my_device_42"
    assert str(devices[0]) == "ZontDevice: my_device_42 (id=42)"

    assert devices[1].api.api_token == "testtoken"
    assert devices[1].api.api_client == "testclient"
    assert devices[1].id == 451
    assert devices[1].name == "my_device_451"
    assert str(devices[1]) == "ZontDevice: my_device_451 (id=451)"


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_no_devices(mock_requests, caplog):
    """
    Emulate response without "devices" subtree from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_NO_DEVICES_SUBTREE
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 0


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_empty_devices(mock_requests, caplog):
    """
    Emulate response with empty "devices" subtree from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_EMPTY_DEVICES_LIST
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 0


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_invalid_devices_value(mock_requests, caplog):
    """
    Emulate response with unsupported "devices" value from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_INVALID_DEVICES_TYPE
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 0


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_empty_response(mock_requests, caplog):
    """
    Emulate empty response body from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = None
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 0


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_no_id(mock_requests, caplog):
    """
    Device without ID
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE_WITHOUT_ID
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    with pytest.raises(ZontAPIException, match=r"500: device must have an ID"):
        _ = zapi.get_devices()


@patch("zont_api.zont_api.requests")
def test_init_device_from_api_no_name(mock_requests, caplog):
    """
    Device without name
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE_WITHOUT_NAME
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    with pytest.raises(ZontAPIException, match=r"500: device must have a name"):
        _ = zapi.get_devices()


@patch("zont_api.zont_api.requests")
def test_device_sensors(mock_requests, caplog):
    """
    Look for sensors information provided with device
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_DEVICE_WITH_SENSORS
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    zdev = zapi.get_devices()[0]

    assert zdev.get_sensor_name(777123) == "voltage input control"
    assert zdev.get_sensor_name(777456) == "air sensor"
    assert zdev.get_sensor_name(777789) == "opentherm adapter"
    assert zdev.get_sensor_name(4242) is None


def test_update_device_without_api():
    """
    Create ZontDevice manually and try to trigger the update
    """
    zdev = ZontDevice(device_data={"id": 42, "name": "testdevice"})
    assert isinstance(zdev, ZontDevice)

    with pytest.raises(
        ZontAPIException, match=r"400: API object not associated with a given device"
    ):
        zdev.update_info()


@patch("zont_api.zont_api.requests")
def test_update_device_with_api(mock_requests, caplog):
    """
    Create single ZontDevice via API and call for update
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 1
    assert devices[0].id == 42
    assert isinstance(devices[0].api, ZontAPI)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE_UPDATE
    mock_requests.post.return_value = mock_response

    last_seen = devices[0].last_seen
    assert devices[0].update_info() is True
    assert devices[0].last_seen > last_seen


@patch("zont_api.zont_api.requests")
def test_update_device_with_api_empty_devices(mock_requests, caplog):
    """
    Update device with empty devices list
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 1
    assert devices[0].id == 42
    assert isinstance(devices[0].api, ZontAPI)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_EMPTY_DEVICES_LIST
    mock_requests.post.return_value = mock_response

    last_seen = devices[0].last_seen
    assert devices[0].update_info() is False
    assert devices[0].last_seen == last_seen


@patch("zont_api.zont_api.requests")
def test_update_device_with_api_not_found(mock_requests, caplog):
    """
    Update device with initial device absent in devices list
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 1
    assert devices[0].id == 42
    assert isinstance(devices[0].api, ZontAPI)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE_UPDATE_NOT_FOUND
    mock_requests.post.return_value = mock_response

    last_seen = devices[0].last_seen
    assert devices[0].update_info() is False
    assert devices[0].last_seen == last_seen


@patch("zont_api.zont_api.requests")
def test_update_device_with_api_pii_filtered(mock_requests, caplog):
    """
    Update device and make sure PII is filtered from updated data dict
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE_WITH_PII
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 1
    last_seen = devices[0].last_seen

    # update device info
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE_WITH_PII_UPDATE
    mock_requests.post.return_value = mock_response
    assert devices[0].update_info() is True
    assert devices[0].last_seen > last_seen

    # verify that PII was filtered from updated info
    assert devices[0].data["ip"] == "***"
    assert devices[0].data["login"] == "***"
    assert devices[0].data["sim_in_device"]["sim_id"]["operator"] == "***"
    assert devices[0].data["sim_in_device"]["sim_id"]["id"] == "***"
    assert devices[0].data["stationary_location"]["loc"] == []
    assert devices[0].data["users"][0]["phone"] == "***"
    assert devices[0].data["users"][0]["password"] == "***"


@patch("zont_api.zont_api.requests")
def test_update_device_with_api_exception(mock_requests, caplog):
    """
    Update device with exception from ZontAPI.get_devices()
    """
    caplog.set_level(logging.DEBUG)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_RESPONSE_SINGLE_DEVICE
    mock_requests.post.return_value = mock_response

    zapi = ZontAPI(token="testtoken", client="testclient")
    assert isinstance(zapi, ZontAPI)
    devices = zapi.get_devices()
    assert len(devices) == 1
    assert devices[0].id == 43
    assert isinstance(devices[0].api, ZontAPI)

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {}
    mock_requests.post.return_value = mock_response

    with pytest.raises(ZontAPIException, match=r"500: API call to /devices failed"):
        devices[0].update_info()
