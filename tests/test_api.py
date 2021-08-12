#! /bin/env python3

import sys, os
import json
import pytest
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasicCredentials
from add_fake_data_to_db import delete_all_collections_datas, add_fake_datas

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
from api_for_frontend import (
    get_graph,
    stats,
    neighborships,
    Node,
    Neighbor,
    add_static_node,
    delete_node_by_fqdn
)
from db_layer import prep_db_if_not_exist, get_node


delete_all_collections_datas()
prep_db_if_not_exist()
add_fake_datas(12, 5, False, False)

TEST_GRAPH_DATA = {}
with open("tests/graph_datas.json") as graph_datas:
    TEST_GRAPH_DATA = json.load(graph_datas)

TEST_STATS_DATA = {}
with open("tests/stats_datas.json") as stats_datas:
    TEST_STATS_DATA = json.load(stats_datas)

TEST_NEIGHS_DATA = {}
with open("tests/neighs_datas.json") as neighs_datas:
    TEST_NEIGHS_DATA = json.load(neighs_datas)


def test_graph_nodes():
    graph = get_graph()
    assert graph["nodes"] == TEST_GRAPH_DATA["nodes"]


def test_graph_links():
    graph = get_graph()
    sorted_links = sorted(graph["links"],key=lambda d: (d["source"], d["target"]))
    sorted_test_links = sorted(TEST_GRAPH_DATA["links"], key=lambda d: (d["source"], d["target"]))
    # assert graph["links"] == TEST_GRAPH_DATA["links"]
    assert sorted_links == sorted_test_links


def test_stats_of_link_between_2_devices():
    query = ["fake_device_stage1_1", "fake_device_stage1_2"]
    stats_retrieved = stats(query)
    # Cant check timestamp since test datas in json are static
    for device_datas in stats_retrieved.values():
        for iface_datas in device_datas.values():
            for stat in iface_datas["stats"]:
                stat["time"] = "N/A"

    print(json.dumps(stats_retrieved))
    assert stats_retrieved == TEST_STATS_DATA


def test_stats_of_1_device():
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


def test_stats_bad_request_not_list():
    # Query should be a list
    query = "fake_device_stage1_1"
    with pytest.raises(HTTPException):
        stats_retrieved = stats(query)


def test_stats_bad_request_not_str_list():
    # Query should be a list of str
    query = [1]
    with pytest.raises(HTTPException):
        stats_retrieved = stats(query)


def test_neighborships():
    query = "fake_device_stage1_1"

    neighs = neighborships(query)
    print(json.dumps(neighs))

    assert neighs == TEST_NEIGHS_DATA


def test_neighborships_bad_request_with_int():
    # Query should be a str
    query = 1
    with pytest.raises(HTTPException):
        neighs = neighborships(query)


def test_neighborships_bad_request_with_list():
    # Query should be a str
    query = ["test"]
    with pytest.raises(HTTPException):
        neighs = neighborships(query)

def test_add_static_node_no_ifaces():
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node: Node = Node(name="test_static")

    neigh: Neighbor = Neighbor(name = "fake_device_stage1_1", iface = "11/11", node_iface = "1/1")

    node_neighbors: List[Neighbor] = [neigh]

    creds = HTTPBasicCredentials(username = "user", password = "pass")

    with pytest.raises(HTTPException):
        add_static_node(node, node_neighbors, creds)

def test_add_static_node_wrong_creds():
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node: Node = Node(name="test_static", ifaces=["1/1"])

    neigh: Neighbor = Neighbor(name = "fake_device_stage1_1", iface = "11/11", node_iface = "1/1")

    node_neighbors: List[Neighbor] = [neigh]

    creds = HTTPBasicCredentials(username = "user1", password = "pass")

    add_static_node(node, node_neighbors, creds)

def test_add_static_node():
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node: Node = Node(name="test_static", ifaces=["1/1"])

    neigh: Neighbor = Neighbor(name = "fake_device_stage1_1", iface = "11/11", node_iface = "1/1")

    node_neighbors: List[Neighbor] = [neigh]

    creds = HTTPBasicCredentials(username = "user", password = "pass")

    add_static_node(node, node_neighbors, creds)

    assert get_node(node.name)

def test_delete_node_by_fqdn():

    node_name: str = "test_static"

    creds = HTTPBasicCredentials(username = "user", password = "pass")

    delete_node_by_fqdn(creds, node_name)

    assert not get_node(node_name)
