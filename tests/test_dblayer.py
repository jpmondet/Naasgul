"""Those tests are only focused on functions that are not tested by test_api (which
    already calls most db_layer functions)"""
#! /bin/env python3

import sys, os
import json
import pytest
from fastapi.exceptions import HTTPException
from add_fake_data_to_db import delete_all_collections_datas, add_fake_datas

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
from db_layer import (
    prep_db_if_not_exist,
    get_all_nodes,
    get_all_links,
    get_latest_utilization,
    add_iface_stats,
    bulk_update_collection,
    get_stats_devices,
    UTILIZATION_COLLECTION,
    get_latest_utilization,
    add_node,
    add_link,
    NODES_COLLECTION,
    MDDPK,
)


def test_db_prep():
    """Testing if cuniqueness onstraints are correctly applied on db preparation"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node_name: str = "test_duplicate"
    add_node(node_name)
    with pytest.raises(MDDPK):
        NODES_COLLECTION.insert_one({"device_name": node_name})

    delete_all_collections_datas()
    prep_db_if_not_exist()


def test_get_all_nodes():
    node_name: str = "test_node"
    add_node(node_name)
    nodes = list(get_all_nodes())

    assert len(nodes) == 1
    assert nodes[0]["device_name"] == node_name

    delete_all_collections_datas()
    prep_db_if_not_exist()


def test_get_all_links():
    node_name: str = "test_node"
    neigh_name: str = "test_neigh"
    iface_name: str = "e1/1"
    neigh_iface_name: str = "e2/1"
    add_link(node_name, neigh_name, iface_name, neigh_iface_name)

    links = list(get_all_links())

    assert len(links) == 1
    del links[0]["_id"]
    assert links[0] == {
        "device_name": node_name,
        "neighbor_name": neigh_name,
        "iface_name": iface_name,
        "neighbor_iface": neigh_iface_name,
    }

    delete_all_collections_datas()
    prep_db_if_not_exist()


def test_get_latest_utilization():
    latest, timestamp = get_latest_utilization("fake_device_stage1_1", "1/1")
    assert isinstance(latest, int)
    assert isinstance(timestamp, int)
    assert latest >= 0
    assert latest < 10000000


def test_get_latest_utilization_not_existing():
    latest, timestamp = get_latest_utilization("Device_that_not_exist", "1/1")
    assert latest == 0
    assert timestamp == 0


def test_add_iface_stats():
    device = "fake_device_stage1_1"
    iface = "1/1"
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
        if (
            device_stats["iface_name"] == iface
            and device_stats["timestamp"] == timestamp
            and device_stats["speed"] == speed
        ):
            return

    raise (ValueError)


def test_bulk_update_collection():
    device_name = "fake_device_stage1_1"
    iface_name = "6/6"
    prev_utilization = 1337
    prev_timestamp = 1337
    last_utilization = 1337
    timestamp = 1338

    query = {"device_name": device_name, "iface_name": iface_name}
    utilization = {
        "device_name": device_name,
        "iface_name": iface_name,
        "prev_utilization": prev_utilization,
        "prev_timestamp": prev_timestamp,
        "last_utilization": last_utilization,
        "timestamp": timestamp,
    }
    utilization_list = [(query, utilization)]

    bulk_update_collection(UTILIZATION_COLLECTION, utilization_list)

    last_db_utilization, last_db_timestamp = get_latest_utilization(device_name, iface_name)

    assert last_utilization == last_db_utilization
    assert timestamp == last_db_timestamp
