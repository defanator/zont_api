"""
Tests for ZontAPI
"""

import pytest
from zont_api import ZontAPIException, ZontAPI


__author__ = "Andrei Belov"
__license__ = "MIT"
__copyright__ = f"Copyright (c) {__author__}"


def test_init_api_without_params(monkeypatch):
    """
    Initialization without token or client
    """
    monkeypatch.delenv('ZONT_API_TOKEN', raising=False)
    monkeypatch.delenv('ZONT_API_CLIENT', raising=False)
    with pytest.raises(ZontAPIException, match=r'token not provided'):
        _ = ZontAPI()

    monkeypatch.setenv('ZONT_API_TOKEN', 'foo')
    with pytest.raises(ZontAPIException, match=r'client not provided'):
        _ = ZontAPI()

def test_init_api_with_params_from_args():
    """
    Initialization with token and client given to constructor
    """
    zapi = ZontAPI(token='testtoken1', client='test1@example.com')
    assert isinstance(zapi, ZontAPI)
    assert zapi.api_token == 'testtoken1'
    assert zapi.api_client == 'test1@example.com'

def test_init_api_with_params_from_env(monkeypatch):
    """
    Initialization with token and client from environment
    """
    monkeypatch.setenv('ZONT_API_TOKEN', 'testtoken2')
    monkeypatch.setenv('ZONT_API_CLIENT', 'test2@example.com')
    zapi = ZontAPI()
    assert isinstance(zapi, ZontAPI)
    assert zapi.api_token == 'testtoken2'
    assert zapi.api_client == 'test2@example.com'

def test_init_api_prioritize_args(monkeypatch):
    """
    Initialization with token and client provided both directly
    and through environment
    """
    monkeypatch.setenv('ZONT_API_TOKEN', 'testtoken_from_env')
    monkeypatch.setenv('ZONT_API_CLIENT', 'testclient_env@example.com')
    zapi = ZontAPI(token='testtoken_from_args', client='testclient_args@example.com')
    assert isinstance(zapi, ZontAPI)
    assert zapi.api_token == 'testtoken_from_args'
    assert zapi.api_client == 'testclient_args@example.com'

def test_convert_dta_default():
    """
    Convert data time array with default settings (sorted, ascending)
    """
    source_dta = [
        [1000, 1],
        [-10, 2],
        [-10, 3],
        [1030, 4],
        [-10, 5],
    ]

    result_dta = ZontAPI.convert_delta_time_array(ZontAPI, source_dta)

    assert result_dta == [
        [1000, 1],
        [1010, 2],
        [1020, 3],
        [1030, 4],
        [1040, 5],
    ]

def test_convert_dta_unsorted():
    """
    Convert data time array without sorting
    """
    source_dta = [
        [1030, 1],
        [-10, 2],
        [1000, 3],
        [-10, 4],
        [-10, 5],
    ]

    result_dta = ZontAPI.convert_delta_time_array(ZontAPI, source_dta, sort=False)

    assert result_dta == [
        [1030, 1],
        [1040, 2],
        [1000, 3],
        [1010, 4],
        [1020, 5],
    ]

def test_convert_dta_sorted_reverse():
    """
    Convert data time array with reverse (descending) sorting
    """
    source_dta = [
        [1030, 1],
        [-10, 2],
        [1000, 3],
        [-10, 4],
        [-10, 5],
    ]

    result_dta = ZontAPI.convert_delta_time_array(ZontAPI, source_dta, sort=True, reverse=True)

    assert result_dta == [
        [1040, 2],
        [1030, 1],
        [1020, 5],
        [1010, 4],
        [1000, 3],
    ]

def test_convert_dta_ignore_zero_deltas():
    """
    Convert data time array with zero delta values
    """
    source_dta = [
        [1000, 1],
        [-10, 2],
        [-10, 3],
        [0, 666],
        [-10, 4],
        [-10, 5],
    ]

    result_dta = ZontAPI.convert_delta_time_array(ZontAPI, source_dta)

    assert result_dta == [
        [1000, 1],
        [1010, 2],
        [1020, 3],
        [1030, 4],
        [1040, 5],
    ]

def test_convert_dta_combined_payload():
    """
    Convert data time array with multiple payload values per element
    """
    source_dta = [
        [1000, [1, -1]],
        [-10, [2, -2]],
        [-10, [3, -3]],
        [-10, [-4, 4]],
        [-10, [-5, 5]],
        [-10, [0, 0, 0], 42],
        [-10, 0, 0, 0, [42, 451]],
    ]

    result_dta = ZontAPI.convert_delta_time_array(ZontAPI, source_dta, sort=False)

    assert result_dta == [
        [1000, [1, -1]],
        [1010, [2, -2]],
        [1020, [3, -3]],
        [1030, [-4, 4]],
        [1040, [-5, 5]],
        [1050, [0, 0, 0], 42],
        [1060, 0, 0, 0, [42, 451]],
    ]

def test_convert_dta_no_payload():
    """
    Convert data time array without payload data (timestamps only)
    """
    result_dta = ZontAPI.convert_delta_time_array(ZontAPI, [[1], [-1], [-1]])

    assert result_dta == [[1], [2], [3]]

def test_convert_dta_handle_invalid_input():
    """
    Convert data time array with unexpected input
    """
    result_dta = ZontAPI.convert_delta_time_array(ZontAPI, [])
    assert result_dta == []

    with pytest.raises(ValueError, match=r'parent: list expected but found None'):
        _ = ZontAPI.convert_delta_time_array(ZontAPI, None)

    with pytest.raises(ValueError, match=r'parent: list expected but found tuple'):
        _ = ZontAPI.convert_delta_time_array(ZontAPI, (0, 0))

    with pytest.raises(ValueError, match=r'element: list expected but found int'):
        _ = ZontAPI.convert_delta_time_array(ZontAPI, [1, 2, 3])

    with pytest.raises(ValueError, match=r'element: list expected but found str'):
        _ = ZontAPI.convert_delta_time_array(ZontAPI, [[1], [2], "3"])

    with pytest.raises(ValueError, match=r'invalid literal for int'):
        _ = ZontAPI.convert_delta_time_array(ZontAPI, [["one"], ["two"], ["three"]])
