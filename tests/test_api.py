"""This module aims to test the api functions with pytest.
Warning: A mongodb must be up&running"""
#! /bin/env python3

import sys
import os
from typing import Dict, List, Any
import json
import pytest
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasicCredentials
from add_fake_data_to_db import delete_all_collections_datas, add_fake_datas

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
# pylint:disable=import-error, wrong-import-position
from api_for_frontend import ( # type: ignore
    get_graph,
    stats,
    neighborships,
    Node,
    Neighbor,
    add_static_node,
    delete_node_by_fqdn,
)
from db_layer import prep_db_if_not_exist, get_node # type: ignore


TEST_GRAPH_DATA: Dict[str, Any] = {}
with open("tests/graph_datas.json") as graph_datas:
    TEST_GRAPH_DATA = json.load(graph_datas)

TEST_STATS_DATA: Dict[str, Any] = {}
with open("tests/stats_datas.json") as stats_datas:
    TEST_STATS_DATA = json.load(stats_datas)

TEST_NEIGHS_DATA: Dict[str , Any] = {}
with open("tests/neighs_datas.json") as neighs_datas:
    TEST_NEIGHS_DATA = json.load(neighs_datas)


def test_graph_nodes() -> None:
    """Gets graph nodes from api (and thus db) and compares
    it with nodes in json file"""

    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    graph = get_graph()
    assert graph["nodes"] == TEST_GRAPH_DATA["nodes"]


def test_graph_links() -> None:
    """Gets graph links from api (and thus db) and compares
    it with links in json file"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    graph = get_graph()
    sorted_links = sorted(graph["links"], key=lambda d: (d["source"], d["target"]))
    sorted_test_links = sorted(TEST_GRAPH_DATA["links"], key=lambda d: (d["source"], d["target"]))
    assert sorted_links == sorted_test_links


def test_stats_of_link_between_2_devices() -> None:
    """Tests retrieval & formatting of the stats of a
    specific link between 2 devices"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    query = ["fake_device_stage1_1", "fake_device_stage1_2"]
    stats_retrieved = stats(query)
    # Cant check timestamp since test datas in json are static
    for device_datas in stats_retrieved.values():
        for iface_datas in device_datas.values():
            for stat in iface_datas["stats"]:
                stat["time"] = "N/A"

    print(json.dumps(stats_retrieved))
    assert stats_retrieved == TEST_STATS_DATA


def test_stats_of_1_device() -> None:
    """Tests retrieval & formatting of the stats of a
    uniq devices"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    query = ["fake_device_stage1_1"]
    stats_retrieved = stats(query)
    # Cant check timestamp since test datas in json are static
    for device_datas in stats_retrieved.values():
        for iface_datas in device_datas.values():
            for stat in iface_datas["stats"]:
                stat["time"] = "N/A"

    print(json.dumps(stats_retrieved))

    test_datas_to_match = {
        "fake_device_stage1_1": {
            "1/1": {
                "ifDescr": "1/1",
                "index": "1/1",
                "stats": [{"InSpeed": 0, "OutSpeed": 0, "time": "N/A"}],
            },
            "1/2": {
                "ifDescr": "1/2",
                "index": "1/2",
                "stats": [{"InSpeed": 0, "OutSpeed": 0, "time": "N/A"}],
            },
            "1/3": {
                "ifDescr": "1/3",
                "index": "1/3",
                "stats": [{"InSpeed": 0, "OutSpeed": 0, "time": "N/A"}],
            },
            "1/4": {
                "ifDescr": "1/4",
                "index": "1/4",
                "stats": [{"InSpeed": 0, "OutSpeed": 0, "time": "N/A"}],
            },
        }
    }
    assert stats_retrieved == test_datas_to_match


def test_stats_bad_request_not_list() -> None:
    """Ensures that wrong request for stats where
    'devices' is not a list will end up in an exception"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    # Query should be a list
    query = "fake_device_stage1_1"
    with pytest.raises(HTTPException):
        _ = stats(query)


def test_stats_bad_request_not_str_list() -> None:
    """Ensures that wrong request for stats where
    'devices' is not a list of strings
    will end up in an exception"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    # Query should be a list of str
    query = [1]
    with pytest.raises(HTTPException):
        _ = stats(query)


def test_neighborships() -> None:
    """Tests neighborships route"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    query = "fake_device_stage1_1"

    neighs = neighborships(query)
    print(json.dumps(neighs))

    assert neighs == TEST_NEIGHS_DATA


def test_neighborships_bad_request_with_int() -> None:
    """Ensures that neighborships route raises
    an exception when the parameter is an int"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    # Query should be a str
    query = 1
    with pytest.raises(HTTPException):
        _ = neighborships(query)


def test_neighborships_bad_request_with_list() -> None:
    """Ensures that neighborships route raises
    an exception when the parameter is a list of str"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    # Query should be a str
    query = ["test"]
    with pytest.raises(HTTPException):
        _ = neighborships(query)


def test_add_static_node_no_ifaces() -> None:
    """Ensures that route that statically add nodes
    raises an exception when no interfaces are
    specified"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node: Node = Node(name="test_static")

    neigh: Neighbor = Neighbor(name="fake_device_stage1_1", iface="11/11", node_iface="1/1")

    node_neighbors: List[Neighbor] = [neigh]

    creds = HTTPBasicCredentials(username="user", password="pass")

    with pytest.raises(HTTPException):
        add_static_node(node, node_neighbors, creds)


def test_add_static_node_wrong_creds() -> None:
    """Ensures that route that statically add nodes
    raises an exception when creds are wrong"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node: Node = Node(name="test_static", ifaces=["1/1"])

    neigh: Neighbor = Neighbor(name="fake_device_stage1_1", iface="11/11", node_iface="1/1")

    node_neighbors: List[Neighbor] = [neigh]

    creds = HTTPBasicCredentials(username="user1", password="pass")

    add_static_node(node, node_neighbors, creds)


def test_add_static_node() -> None:
    """Tests to add a node with the route that
    is supposed to statically add nodes"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node: Node = Node(name="test_static", ifaces=["1/1"])

    neigh: Neighbor = Neighbor(name="fake_device_stage1_1", iface="11/11", node_iface="1/1")

    node_neighbors: List[Neighbor] = [neigh]

    creds = HTTPBasicCredentials(username="user", password="pass")

    add_static_node(node, node_neighbors, creds)

    assert get_node(node.name)


def test_delete_node_by_fqdn() -> None:
    """Tests to delete a node with the route that
    is supposed to deletes nodes when specifying
    an fqdn"""

    node_name: str = "test_static"

    creds = HTTPBasicCredentials(username="user", password="pass")

    delete_node_by_fqdn(creds, node_name)

    assert not get_node(node_name)
