"""This module aims to test the api functions with pytest.
Warning: A mongodb must be up&running"""
#! /bin/env python3

import sys
import os
from typing import Dict, List, Any
from time import time
import json
import yaml
import pytest
from httpx import AsyncClient
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasicCredentials
from add_fake_data_to_db import delete_all_collections_datas, add_fake_datas

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
# pylint:disable=import-error, wrong-import-position
from api_for_frontend import (
    app,
    get_graph,
    stats,
    neighborships,
    Node,
    Neighbor,
    Link,
    add_static_node,
    delete_node_by_fqdn,
    add_nodes_list_to_poll,
    delete_nodes_list,
    add_links,
    delete_links,
    disable_poll_nodes_list,
    healthz,
)
from db_layer import prep_db_if_not_exist, get_node, get_link, add_fake_iface_stats


TEST_GRAPH_DATA: Dict[str, List[Dict[str, Any]]] = {}
with open("tests/graph_datas.json", encoding="UTF-8") as graph_datas:
    TEST_GRAPH_DATA = json.load(graph_datas)

TEST_STATS_DATA: Dict[str, Dict[str, Dict[str, Any]]] = {}
with open("tests/stats_datas.json", encoding="UTF-8") as stats_datas:
    TEST_STATS_DATA = json.load(stats_datas)

TEST_NEIGHS_DATA: List[Dict[str, str]] = []
with open("tests/neighs_datas.json", encoding="UTF-8") as neighs_datas:
    TEST_NEIGHS_DATA = json.load(neighs_datas)


def test_graph_nodes() -> None:
    """Gets graph nodes from api (and thus db) and compares
    it with nodes in json file"""

    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    graph: Dict[str, List[Dict[str, Any]]] = get_graph()
    assert graph["nodes"] == TEST_GRAPH_DATA["nodes"]


def test_graph_links() -> None:
    """Gets graph links from api (and thus db) and compares
    it with links in json file"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    graph: Dict[str, List[Dict[str, Any]]] = get_graph()
    sorted_links: List[Dict[str, Any]] = sorted(
        graph["links"], key=lambda d: (d["source"], d["target"])
    )
    sorted_test_links: List[Dict[str, Any]] = sorted(
        TEST_GRAPH_DATA["links"], key=lambda d: (d["source"], d["target"])
    )
    assert sorted_links == sorted_test_links


def test_sub_graph_nodes() -> None:
    """Gets graph nodes for specific patterns from api
    (and thus db) and compares
    it with nodes in json file"""

    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    patterns = ["stage1_1", "stage1_2"]

    sub_graph: Dict[str, List[Dict[str, Any]]] = get_graph(dpat=patterns)

    for node in sub_graph["nodes"]:
        assert any(device_pattern in node["device_name"] for device_pattern in patterns)


def test_sub_graph_links() -> None:
    """Gets graph links for specific patterns from api
    (and thus db) and compares
    it with links in json file"""

    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    patterns = ["stage1_1", "stage1_2"]

    sub_graph: Dict[str, List[Dict[str, Any]]] = get_graph(dpat=patterns)

    for link in sub_graph["links"]:
        assert any(
            (device_pattern in link["source"] and device_pattern in link["target"])
            for device_pattern in patterns
        )


def test_stats_of_link_between_2_devices() -> None:
    """Tests retrieval & formatting of the stats of a
    specific link between 2 devices"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    query: List[str] = ["fake_device_stage1_1", "fake_device_stage1_2"]
    stats_retrieved: Dict[str, Dict[str, Dict[str, Any]]] = stats(query)
    # Cant check timestamp since test datas in json are static
    for device_datas in stats_retrieved.values():
        for iface_datas in device_datas.values():
            for stat in iface_datas["stats"]:
                stat["time"] = "N/A"
    assert stats_retrieved == TEST_STATS_DATA


def test_stats_of_1_device() -> None:
    """Tests retrieval & formatting of the stats of a
    uniq devices"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    query: List[str] = ["fake_device_stage1_1"]
    stats_retrieved: Dict[str, Dict[str, Dict[str, Any]]] = stats(query)
    # Cant check timestamp since test datas in json are static
    for device_datas in stats_retrieved.values():
        for iface_datas in device_datas.values():
            for stat in iface_datas["stats"]:
                stat["time"] = "N/A"
    test_datas_to_match: Dict[str, Dict[str, Dict[str, Any]]] = {
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


def test_stats_of_1_device_with_timestamp() -> None:
    """Tests retrieval & formatting of the stats of a
    uniq devices when timestamps are somewhat ok"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    query: List[str] = ["fake_device_stage1_3"]
    iface_name: str = "1/1"
    timestamp: float = time() + 1000

    add_fake_iface_stats(query[0], iface_name, timestamp, 1000, 1000)
    add_fake_iface_stats(query[0], iface_name, timestamp + 10, 2000, 2000)

    stats_retrieved: Dict[str, Dict[str, Dict[str, Any]]] = stats(query)

    assert stats_retrieved[query[0]][iface_name]["stats"][-1]["InSpeed"] == 800
    assert stats_retrieved[query[0]][iface_name]["stats"][-1]["OutSpeed"] == 800


def test_stats_bad_request_not_list() -> None:
    """Ensures that wrong request for stats where
    'devices' is not a list will end up in an exception"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    # Query should be a list
    query: str = "fake_device_stage1_1"
    with pytest.raises(HTTPException):
        _ = stats(query)  # type: ignore


def test_stats_bad_request_not_str_list() -> None:
    """Ensures that wrong request for stats where
    'devices' is not a list of strings
    will end up in an exception"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    # Query should be a list of str
    query: List[int] = [1]
    with pytest.raises(HTTPException):
        _ = stats(query)  # type: ignore


def test_neighborships() -> None:
    """Tests neighborships route"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    query: str = "fake_device_stage1_1"

    neighs: List[Dict[str, str]] = neighborships(query)

    assert neighs == TEST_NEIGHS_DATA


def test_neighborships_bad_request_with_int() -> None:
    """Ensures that neighborships route raises
    an exception when the parameter is an int"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    # Query should be a str
    query: int = 1
    with pytest.raises(HTTPException):
        _ = neighborships(query)  # type: ignore


def test_neighborships_bad_request_with_list() -> None:
    """Ensures that neighborships route raises
    an exception when the parameter is a list of str"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    add_fake_datas(12, 5, False, False)

    # Query should be a str
    query: List[str] = ["test"]
    with pytest.raises(HTTPException):
        _ = neighborships(query)  # type: ignore


def test_add_static_node_no_ifaces() -> None:
    """Ensures that route that statically add nodes
    raises an exception when no interfaces are
    specified"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node: Node = Node(name="test_static")

    neigh: Neighbor = Neighbor(name="fake_device_stage1_1", iface="11/11", node_iface="1/1")

    node_neighbors: List[Neighbor] = [neigh]

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user", password="pass")

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

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user1", password="pass")

    add_static_node(node, node_neighbors, creds)


def test_add_static_node() -> None:
    """Tests to add a node with the route that
    is supposed to statically add nodes"""
    delete_all_collections_datas()
    prep_db_if_not_exist()
    node: Node = Node(name="test_static", ifaces=["1/1"])

    neigh: Neighbor = Neighbor(name="fake_device_stage1_1", iface="11/11", node_iface="1/1")

    node_neighbors: List[Neighbor] = [neigh]

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user", password="pass")

    add_static_node(node, node_neighbors, creds)

    assert get_node(node.name)


def test_delete_node_by_fqdn() -> None:
    """Tests to delete a node with the route that
    is supposed to deletes nodes when specifying
    an fqdn"""

    node_name: str = "test_static"

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user", password="pass")

    delete_node_by_fqdn(creds, node_name)

    assert not get_node(node_name)


def test_add_nodes_list_to_poll() -> None:
    """Adds nodes list and check that they
    are correctly added to the db"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    nodes_list = ["aaa", "bbb", "ccc"]

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user", password="pass")

    add_nodes_list_to_poll(nodes_list, creds)

    for node in nodes_list:
        assert get_node(node)


def test_delete_nodes_list() -> None:
    """Adds nodes list, deletes them and
    verify that they
    are correctly deleted from the db"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    nodes_list = ["aaa", "bbb", "ccc"]

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user", password="pass")

    add_nodes_list_to_poll(nodes_list, creds)

    delete_nodes_list(nodes_list)

    for node in nodes_list:
        assert not get_node(node)


def test_add_links() -> None:
    """Adds links and
    verify that they
    are correctly added to the db"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    link: Link = Link(
        name_node1="aaa",
        iface_id_node1="11/11",
        name_node2="bbb",
        iface_id_node2="22/22",
    )

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user", password="pass")

    add_links([link], creds)

    assert get_link(
        link.name_node1,
        link.iface_id_node1,
        link.name_node2,
        link.iface_id_node2,
    )


def test_delete_links() -> None:
    """Adds and deletes links and
    verify that they
    are correctly deleted from the db"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    link: Link = Link(
        name_node1="aaa",
        iface_id_node1="11/11",
        name_node2="bbb",
        iface_id_node2="22/22",
    )

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user", password="pass")

    add_links([link], creds)

    delete_links([link], creds)

    assert not get_link(
        link.name_node1,
        link.iface_id_node1,
        link.name_node2,
        link.iface_id_node2,
    )


@pytest.mark.asyncio
async def test_add_fabric() -> None:
    """Adds a fabric (yaml file) and
    verify that everything is
    correctly added to the db"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    bfabric: bytes = b"0"
    with open("tests/define_fabric.yaml", "rb") as rbfabric:
        bfabric = rbfabric.read()

    async with AsyncClient(app=app, base_url="http://test") as aclient:
        response = await aclient.post(
            "/fabric",
            headers={"Content-type": "application/x-yaml"},
            content=bfabric,
            auth=("user", "pass"),
        )
    assert response.status_code == 200

    yfabric: Dict[str, List[Dict[str, Any]]] = {}
    with open("tests/define_fabric.yaml", encoding="UTF-8") as yml:
        yfabric = yaml.safe_load(yml)

    for node in yfabric["nodes"]:
        assert get_node(node["name"])
    for link in yfabric["links"]:
        assert get_link(
            link["name_node1"],
            link["iface_id_node1"],
            link["name_node2"],
            link["iface_id_node2"],
        )


@pytest.mark.asyncio
async def test_delete_fabric() -> None:
    """Adds a fabric (yaml file),
    deletes it and
    verify that everything is
    correctly added to the db"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    bfabric: bytes = b"0"
    with open("tests/define_fabric.yaml", "rb") as rbfabric:
        bfabric = rbfabric.read()

    async with AsyncClient(app=app, base_url="http://test") as aclient:
        response = await aclient.post(
            "/fabric",
            headers={"Content-type": "application/x-yaml"},
            content=bfabric,
            auth=("user", "pass"),
        )
    assert response.status_code == 200

    async with AsyncClient(app=app, base_url="http://test") as aclient:
        response = await aclient.request(
            "DELETE",
            "/fabric",
            headers={"Content-type": "application/x-yaml"},
            content=bfabric,
            auth=("user", "pass"),
        )
    assert response.status_code == 200

    yfabric: Dict[str, List[Dict[str, Any]]] = {}
    with open("tests/define_fabric.yaml", encoding="UTF-8") as yml:
        yfabric = yaml.safe_load(yml)

    for node in yfabric["nodes"]:
        assert not get_node(node["name"])
    for link in yfabric["links"]:
        assert not get_link(
            link["name_node1"],
            link["iface_id_node1"],
            link["name_node2"],
            link["iface_id_node2"],
        )


@pytest.mark.asyncio
async def test_bad_credentials() -> None:
    """Tests that bad credentials results in
    an exception."""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    bfabric: bytes = b"0"
    with open("tests/define_fabric.yaml", "rb") as rbfabric:
        bfabric = rbfabric.read()

    async with AsyncClient(app=app, base_url="http://test") as aclient:
        response = await aclient.post(
            "/fabric",
            headers={"Content-type": "application/x-yaml"},
            content=bfabric,
            auth=("wronguser", "wrongpass"),
        )
    assert response.status_code == 401


def test_disable_nodes_list() -> None:
    """Adds nodes list, Disable them and
    verify that they
    are correctly disabled (to_poll==False)"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    nodes_list = ["aaa", "bbb", "ccc"]

    creds: HTTPBasicCredentials = HTTPBasicCredentials(username="user", password="pass")

    add_nodes_list_to_poll(nodes_list, creds)

    disable_poll_nodes_list(nodes_list)

    for node in nodes_list:
        db_node: Dict[str, Any] = get_node(node)
        assert not db_node["to_poll"]


def test_healthz() -> None:
    """Just test simple healthz
    func"""

    assert healthz() == {"response": "Ok"}
