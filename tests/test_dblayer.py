"""Those tests are only focused on functions that are not tested by test_api (which
    already calls most db_layer functions)"""
#! /bin/env python3

import sys, os
import json
import pytest
from fastapi.exceptions import HTTPException
from add_fake_data_to_db import delete_all_collections_datas, add_fake_datas
sys.path.append(os.path.realpath(os.path.dirname(__file__)+"/../backend/"))
from db_layer import prep_db_if_not_exist, get_latest_utilization, add_iface_stats, bulk_update_collection, get_stats_devices, UTILIZATION_COLLECTION, get_latest_utilization


delete_all_collections_datas()
prep_db_if_not_exist()
add_fake_datas(12, 5)

TEST_GRAPH_DATA = {}
with open("tests/graph_datas.json") as graph_datas:
    TEST_GRAPH_DATA = json.load(graph_datas)

TEST_STATS_DATA = {}
with open("tests/stats_datas.json") as stats_datas:
    TEST_STATS_DATA = json.load(stats_datas)

TEST_NEIGHS_DATA = {}
with open("tests/neighs_datas.json") as neighs_datas:
    TEST_NEIGHS_DATA = json.load(neighs_datas)


def test_get_latest_utilization():
    latest = get_latest_utilization('fake_device_stage1_1', '1/1')
    print(latest)
    assert latest == 1250000

def test_get_latest_utilization_not_existing():
    latest = get_latest_utilization('Device_that_not_exist', '1/1')
    assert latest == 0

def test_add_iface_stats():
    device = 'fake_device_stage1_1'
    iface = '1/1'
    timestamp = "now"
    speed = 1337

    stats_list = [
        {
            "device_name": device,
            "iface_name": iface,
            "timestamp": timestamp,
            "speed": speed,
        }
    ]
    add_iface_stats(stats_list)

    for device_stats in get_stats_devices([device]):
        if device_stats["iface_name"] == iface and device_stats["timestamp"] == timestamp and device_stats["speed"] == speed:
            return

    raise(ValueError)
    
def test_bulk_update_collection():
    device_name = 'fake_device_stage1_1'
    iface_name = '6/6'
    prev_utilization = 1337
    last_utilization = 1337

    query = {"device_name": device_name, "iface_name": iface_name}
    utilization = {
        "device_name": device_name,
        "iface_name": iface_name,
        "prev_utilization": prev_utilization,
        "last_utilization": last_utilization
    }
    utilization_list = [(query, utilization)]

    bulk_update_collection(UTILIZATION_COLLECTION, utilization_list)

    assert get_latest_utilization(device_name, iface_name) == last_utilization
