""" Handles db access and abstracts functions
that can be (and should be) abstracted """

#! /usr/bin/env python3

from os import getenv

from typing import List, Dict, Any, Optional, Iterable, Tuple
from time import time
from re import compile as rcompile, IGNORECASE as rIGNORECASE

# from itertools import chain

from pymongo import MongoClient, UpdateMany  # type: ignore
from pymongo.errors import DuplicateKeyError as MDDPK  # type: ignore

DB_STRING: Optional[str] = getenv("DB_STRING")
if not DB_STRING:
    # DB_STRING = "mongodb://mongodb:27017/"
    DB_STRING = "mongodb://127.0.0.1:27017/"

DB_CLIENT: MongoClient = MongoClient(DB_STRING)
DB = DB_CLIENT.automapping

# Collections that avoid data duplication (target)
# All nodes infos of the graph
NODES_COLLECTION = DB.nodes
# All ifaces Stats by devices
STATS_COLLECTION = DB.stats
# All ifaces current highest utilization (to colorize links accordingly)
UTILIZATION_COLLECTION = DB.utilization
# All links infos of the graph (neighborships)
LINKS_COLLECTION = DB.links


def prep_db_if_not_exist() -> None:
    """If db is empty, we create proper indexes."""

    if (
        get_entire_collection(NODES_COLLECTION)
        and get_entire_collection(LINKS_COLLECTION)
        and get_entire_collection(STATS_COLLECTION)
        and get_entire_collection(UTILIZATION_COLLECTION)
    ):
        # Looks like everything is ready
        return

    print("Preping db since at least one collection is empty")

    # We ensure that entries will be unique
    # (this is a mongodb feature)
    NODES_COLLECTION.create_index([("device_name", 1)], unique=True)
    LINKS_COLLECTION.create_index(
        [("device_name", 1), ("iface_name", 1), ("neighbor_name", 1), ("neighbor_iface", 1)],
        unique=True,
    )
    STATS_COLLECTION.create_index(
        [("device_name", 1), ("iface_name", 1), ("timestamp", 1)], unique=True
    )
    UTILIZATION_COLLECTION.create_index([("device_name", 1), ("iface_name", 1)], unique=True)


def get_entire_collection(mongodb_collection) -> List[Dict[str, Any]]:  # type: ignore
    """Returns the entire collection passed in parameter as a list"""
    return list(mongodb_collection.find({}))


def get_all_nodes() -> List[Dict[str, Any]]:
    """Returns all nodes as an iterator"""
    return get_entire_collection(NODES_COLLECTION)


def get_nodes_by_patterns(patterns: List[str]) -> List[Dict[str, Any]]:
    """Returns all nodes matched as an iterator"""
    return list(
        NODES_COLLECTION.find(
            {"$or": [{"device_name": rcompile(pattern, rIGNORECASE)} for pattern in patterns]}
        )
    )


def get_node(node_name: str) -> Dict[str, Any]:
    """Returns a single exact node from the db"""
    return NODES_COLLECTION.find_one({"device_name": node_name})  # type: ignore


def get_all_links() -> List[Dict[str, Any]]:
    """Returns all links as an iterator"""
    return get_entire_collection(LINKS_COLLECTION)


def get_links_by_patterns(patterns: List[str]) -> List[Dict[str, Any]]:
    """Returns all links matched as an iterator"""

    return list(
        LINKS_COLLECTION.find(
            {
                "$or": [
                    {"device_name": rcompile(pattern, rIGNORECASE)} for pattern in patterns
                ]  # + [
                #    {"neighbor_name": rcompile(pattern, rIGNORECASE)} for pattern in patterns
                # ]
            }
        )
    )


def get_all_highest_utilizations() -> Dict[str, int]:
    """Calculates and returns all highest links utilizations
    as a dict. Keys are constructed as 'device_name+iface_name'"""

    utilizations: Dict[str, int] = {}
    current_timestamp: int = int(time())

    for utilization in get_entire_collection(UTILIZATION_COLLECTION):
        id_utilz: str = utilization["device_name"] + utilization["iface_name"]
        if utilizations.get(id_utilz):
            continue
        try:
            if current_timestamp - utilization["timestamp"] > 1300:
                # utilization is expired... We just return 0 as 'unknown'
                # (remember, it's just to colorize links so there's no use to show
                # a link red if its utilization possibly went down already)
                highest_utilization: int = 0
            else:
                if not utilization["prev_timestamp"]:
                    highest_utilization = 0
                elif not utilization["prev_utilization"]:
                    highest_utilization = 0
                else:
                    interval: int = utilization["timestamp"] - utilization["prev_timestamp"]
                    interval = max(interval, 1)
                    highest_utilization = max(
                        utilization["last_utilization"] - utilization["prev_utilization"], 0
                    )

                    highest_utilization = int(highest_utilization / interval)
        except KeyError:
            highest_utilization = 0

        utilizations[id_utilz] = highest_utilization

    return utilizations


def get_all_speeds() -> Dict[str, int]:
    """Returns all links speeds as a dict.
    Keys are constructed as 'device_name+iface_name'"""

    speeds: Dict[str, int] = {}
    for stat in get_entire_collection(STATS_COLLECTION):
        id_speed = stat["device_name"] + stat["iface_name"]
        if speeds.get(id_speed):
            continue
        speeds[id_speed] = stat["speed"]

    return speeds


def get_links_device(device: str) -> List[Dict[str, Any]]:
    """Returns all links of one specific device (also looks
    at links on which this device is appearing as a neighbor)"""

    query: List[Dict[str, str]] = [{"device_name": device}, {"neighbor_name": device}]
    return LINKS_COLLECTION.find({"$or": query})  # type: ignore


def get_stats_devices(devices: List[str]) -> Iterable[Dict[str, Any]]:
    """Returns all stats of all devices passed in parameter"""

    query: List[Dict[str, str]] = [{"device_name": device} for device in devices]
    return STATS_COLLECTION.find({"$or": query})  # type: ignore


def get_speed_iface(device_name: str, iface_name: str) -> int:
    """Returns speed (max bandwidth, not utilization) of a specific interface"""
    speed: int = 1
    try:
        *_, laststat = STATS_COLLECTION.find({"device_name": device_name, "iface_name": iface_name})
        speed = laststat["speed"]
    except (KeyError, IndexError) as err:
        print("oops? " + str(err))
        speed = 10
    return speed


def get_latest_utilization(device_name: str, iface_name: str) -> Tuple[int, int]:
    """Returns last link utilization) of a specific interface"""

    utilization_line = UTILIZATION_COLLECTION.find_one(
        {"device_name": device_name, "iface_name": iface_name}
    )
    try:
        return utilization_line["last_utilization"], utilization_line["timestamp"]
    except (KeyError, TypeError):
        return 0, 0


def add_iface_stats(stats: List[Dict[str, Any]]) -> None:
    """Tries to insert all stats from parameter directly to db"""

    STATS_COLLECTION.insert_many(stats)


def add_node(
    node_name: str,
    groupx: Optional[int] = 11,
    groupy: Optional[int] = 11,
    image: Optional[str] = "router.png",
) -> None:
    """Inserts (or updates) a node into db"""

    try:
        NODES_COLLECTION.insert_one(
            {"device_name": node_name, "groupx": groupx, "groupy": groupy, "image": image}
        )
    except MDDPK:
        NODES_COLLECTION.update_many(
            {"device_name": node_name},
            {
                "$set": {
                    "device_name": node_name,
                    "groupx": groupx,
                    "groupy": groupy,
                    "image": image,
                }
            },
        )


def add_link(node_name: str, neigh_name: str, local_iface: str, neigh_iface: str) -> None:
    """Tries to insert a link directly into db"""

    try:
        LINKS_COLLECTION.insert_one(
            {
                "device_name": node_name,
                "iface_name": local_iface,
                "neighbor_iface": neigh_iface,
                "neighbor_name": neigh_name,
            }
        )
    except MDDPK:
        print("Already exists, passing.")


def add_fake_iface_utilization(device_name: str, iface_name: str) -> None:
    """Inserts (or updates) default (0) link utilization into db"""

    UTILIZATION_COLLECTION.update_one(
        {"device_name": f"{device_name}", "iface_name": f"{iface_name}"},
        {
            "$set": {
                "device_name": f"{device_name}",
                "iface_name": f"{iface_name}",
                "prev_utilization": 0,
                "last_utilization": 0,
            }
        },
        True,
    )


def add_fake_iface_stats(device_name: str, iface_name: str) -> None:
    """Inserts fake stats for a specific interface into db"""

    STATS_COLLECTION.insert_one(
        {
            "device_name": f"{device_name}",
            "iface_name": f"{iface_name}",
            "timestamp": int(time()),
            "mtu": 1500,
            "mac": "",
            "speed": 10,
            "in_discards": 0,
            "in_errors": 0,
            "out_discards": 0,
            "out_errors": 0,
            "in_bytes": 0,
            "in_ucast_pkts": 0,
            "in_mcast_pkts": 0,
            "in_bcast_pkts": 0,
            "out_bytes": 0,
            "out_ucast_pkts": 0,
            "out_mcast_pkts": 0,
            "out_bcast_pkts": 0,
        }
    )


def bulk_update_collection(mongodb_collection, list_tuple_key_query) -> None:  # type: ignore
    """Update massively a collection. It uses the special 'UpdateMany'
    pymongo object :
    # (https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html\
    # ?highlight=update#pymongo.collection.Collection.update_many)
    """

    request: List[UpdateMany] = []
    for query, data in list_tuple_key_query:
        request.append(UpdateMany(query, {"$set": data}, True))

    mongodb_collection.bulk_write(request)


def delete_node(node_name: str) -> None:
    """Deletes everything related to a specific node from db.
    (everything means node, links, stats & utilizations entries)"""

    NODES_COLLECTION.delete_one({"device_name": node_name})
    LINKS_COLLECTION.delete_many({"device_name": node_name})
    LINKS_COLLECTION.delete_many({"neighbor_name": node_name})
    STATS_COLLECTION.delete_many({"device_name": node_name})
    UTILIZATION_COLLECTION.delete_many({"neighbor_name": node_name})
