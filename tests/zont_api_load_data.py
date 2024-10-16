"""
Tests for Zont load_data API
"""

import logging
from unittest.mock import patch, MagicMock
from zont_api import ZontAPI, ZontDevice


__author__ = "Andrei Belov"
__license__ = "MIT"
__copyright__ = f"Copyright (c) {__author__}"


DATA_TYPES_ALL = [
    "z3k_temperature",
    "z3k_heating_circuit",
    "z3k_boiler_adapter",
    "z3k_analog_input",
]

MOCK_DATA_EMPTY_RESPONSE = {
    "ok": True,
    "responses": [
        {
            "device_id": 42,
            "ok": True,
            "time_truncated": False,
            "z3k_temperature": {},
            "z3k_heating_circuit": {},
            "z3k_boiler_adapter": {},
            "z3k_analog_input": {},
        }
    ],
}

MOCK_DATA_RESPONSE_WITH_METRICS = {
    "ok": True,
    "responses": [
        {
            "device_id": 42,
            "ok": True,
            "time_truncated": False,
            "z3k_temperature": {
                "4242": [
                    [1000, 42.2],
                    [-60, 42.2],
                    [-60, 42.2],
                ]
            },
            "z3k_heating_circuit": {
                "4343": {
                    "worktime": [
                        [1000, 0],
                        [-60, 0],
                        [-60, 0],
                    ],
                    "status": [
                        [1000, 0],
                        [-120, 0],
                    ],
                }
            },
            "z3k_boiler_adapter": {
                "4444": {
                    "s": [
                        [1000, []],
                        [-60, []],
                        [-60, []],
                    ],
                    "ot": [
                        [1000, 7.0],
                        [-60, 7.0],
                        [-60, 6.0],
                    ],
                }
            },
            "z3k_analog_input": {
                "4545": {
                    "voltage": [
                        [1000, 23.8],
                        [-120, 23.8],
                    ],
                    "value": [
                        [1000, 238],
                        [-120, 238],
                    ],
                }
            },
            "timings": {
                "z3k_temperature": {
                    "wall": 0.05566287040710449,
                    "proc": 0.002107100000102946,
                },
                "z3k_boiler_adapter": {
                    "wall": 0.08274435997009277,
                    "proc": 0.002168881000216061,
                },
                "z3k_heating_circuit": {
                    "wall": 0.05684089660644531,
                    "proc": 0.002351291000195488,
                },
                "z3k_analog_input": {
                    "wall": 0.08126425743103027,
                    "proc": 0.0019758700000238605,
                },
            },
        }
    ],
}


@patch("zont_api.zont_api.requests")
def test_load_data_no_series(mock_requests, caplog):
    """
    Load data with valid response but no serires
    """
    caplog.set_level(logging.DEBUG)

    zapi = ZontAPI(token="testtoken", client="testclient")
    zdev = ZontDevice(device_data={"id": 42, "name": "testdevice"})

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_DATA_EMPTY_RESPONSE
    mock_requests.post.return_value = mock_response

    data = zapi.load_data(zdev.id, data_types=DATA_TYPES_ALL, interval=(1000, 1120))

    assert data.get("device_id") == zdev.id
    for key_name in DATA_TYPES_ALL:
        assert key_name in data.keys(), f"{key_name} present in load_data response"
        assert isinstance(data.get(key_name), dict), f"{key_name} is dict"
        assert bool(data.get(key_name)) is False, f"{key_name} dict is empty"

    # repeat the same request without explicit data_types and interval
    data = zapi.load_data(zdev.id)
    assert data.get("device_id") == zdev.id


@patch("zont_api.zont_api.requests")
def test_load_data_with_metrics(mock_requests, caplog):
    """
    Load data with valid response and some metrics
    """
    caplog.set_level(logging.DEBUG)

    zapi = ZontAPI(token="testtoken", client="testclient")
    zdev = ZontDevice(device_data={"id": 42, "name": "testdevice"})

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_DATA_RESPONSE_WITH_METRICS
    mock_requests.post.return_value = mock_response

    data = zapi.load_data(zdev.id, data_types=DATA_TYPES_ALL, interval=(1000, 1120))

    assert data.get("device_id") == zdev.id
    for key_name in DATA_TYPES_ALL:
        assert key_name in data.keys(), f"{key_name} present in load_data response"
        assert isinstance(data.get(key_name), dict), f"{key_name} is dict"
        assert bool(data.get(key_name)) is True, f"{key_name} dict is not empty"

    assert "timings" not in data.keys(), "timings section was removed"
