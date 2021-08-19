"""Those tests are only focused on functions that are not tested by test_api and
test_snmp (which already call most db_layer functions)"""
#! /bin/env python3

import sys
import os
from typing import Dict, List, Any, Tuple
import pytest
from pymongo.errors import DuplicateKeyError as MDDPK  # type: ignore
from add_fake_data_to_db import delete_all_collections_datas, add_fake_datas

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
# pylint:disable=import-error, wrong-import-position
from db_layer import (
    prep_db_if_not_exist,
    get_all_nodes,
    get_all_links,
    get_latest_utilization,
    add_iface_stats,
    bulk_update_collection,
    get_stats_devices,
    UTILIZATION_COLLECTION,
    add_node,
    add_link,
    NODES_COLLECTION,
)


def test_db_prep() -> None:
    """Testing if uniqueness constraints are correctly applied on db preparation"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node_name: str = "test_duplicate"
    add_node(node_name)
    with pytest.raises(MDDPK):
        NODES_COLLECTION.insert_one({"device_name": node_name})


def test_get_all_nodes() -> None:
    """Test get_all_nodes func by adding
    node and retrieve it"""

    delete_all_collections_datas()
    prep_db_if_not_exist()
    node_name: str = "test_node"
    add_node(node_name)
    nodes: List[Dict[str, Any]] = list(get_all_nodes())

    assert len(nodes) == 1
    assert nodes[0]["device_name"] == node_name


def test_get_all_links() -> None:
    """Test get_all_links func by adding
    a link and retrieve it"""

    delete_all_collections_datas()
    prep_db_if_not_exist()
    node_name: str = "test_node"
    neigh_name: str = "test_neigh"
    iface_name: str = "e1/1"
    neigh_iface_name: str = "e2/1"
    add_link(node_name, neigh_name, iface_name, neigh_iface_name)

    links: List[Dict[str, Any]] = list(get_all_links())

    assert len(links) == 1
    del links[0]["_id"]
    assert links[0] == {
        "device_name": node_name,
        "neighbor_name": neigh_name,
        "iface_name": iface_name,
        "neighbor_iface": neigh_iface_name,
    }


def test_get_latest_utilization() -> None:
    """Test get_latest_utilization func by adding
    fake datas and retrieving latest utilization with
    db func"""

    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    latest: int = -1
    timestamp: int = -1

    latest, timestamp = get_latest_utilization("fake_device_stage1_1", "1/1")
    assert isinstance(latest, int)
    assert isinstance(timestamp, int)
    assert latest >= 0
    assert latest < 10000000


def test_get_latest_utilization_not_existing() -> None:
    """Ensure that get_latest_utilization func
    returns 0,0 when the couple device+iface is
    not known"""

    latest: int = -1
    timestamp: int = -1

    latest, timestamp = get_latest_utilization("Device_that_not_exist", "1/1")
    assert latest == 0
    assert timestamp == 0


def test_add_iface_stats() -> None:
    """Test add_iface_stats func by
    checking the db after using it"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    device: str = "fake_device_stage1_1"
    iface: str = "1/1"
    timestamp: str = "now"
    speed: int = 1337

    stats_list: List[Dict[str, Any]] = [
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

    raise ValueError


def test_bulk_update_collection() -> None:
    """Test bulk_update_collection func by
    checking the db after using it"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    device_name: str = "fake_device_stage1_1"
    iface_name: str = "6/6"
    prev_utilization: int = 1337
    prev_timestamp: int = 1337
    last_utilization: int = 1337
    timestamp: int = 1338

    query = {"device_name": device_name, "iface_name": iface_name}
    utilization: Dict[str, Any] = {
        "device_name": device_name,
        "iface_name": iface_name,
        "prev_utilization": prev_utilization,
        "prev_timestamp": prev_timestamp,
        "last_utilization": last_utilization,
        "timestamp": timestamp,
    }
    utilization_list: List[Tuple[Dict[str,str],Dict[str, Any]]] = [(query, utilization)]

    bulk_update_collection(UTILIZATION_COLLECTION, utilization_list)

    last_db_utilization: int = -1
    last_db_timestamp: int = -1

    last_db_utilization, last_db_timestamp = get_latest_utilization(device_name, iface_name)

    assert last_utilization == last_db_utilization
    assert timestamp == last_db_timestamp
