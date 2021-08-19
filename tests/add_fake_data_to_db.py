"""Quick scripts that helps adding fake datas into
db for tests purposes"""
# /usr/bin/env python3

from sys import exit as sexit, path as spath
from os import getenv
import os.path

# import re
from random import randint
from time import time
from argparse import ArgumentParser
from pymongo import MongoClient  # type: ignore
from pymongo.errors import DuplicateKeyError  # type: ignore

spath.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
# pylint:disable=import-error, wrong-import-position
from db_layer import (
    prep_db_if_not_exist,
    get_latest_utilization,
)

DB_STRING: str = getenv("DB_STRING", "mongodb://localhost:27017/")
client = MongoClient(DB_STRING)
db = client.automapping

def add_lots_of_nodes(number_nodes: int, fabric_stages: int) -> None:
    """Inserts or Updates number_nodes devices into db
    (nodes collection)"""

    nodes_per_stages: int = int(number_nodes / fabric_stages)

    for stage in range(fabric_stages):
        for stage_node in range(nodes_per_stages):
            try:
                db.nodes.insert_one(
                    {
                        "device_name": f"fake_device_stage{str(stage+1)}_{str(stage_node+1)}",
                        # "group": stage + 1,
                        # "image": "router.png",
                    }
                )
            except DuplicateKeyError:
                db.nodes.update_many(
                    {"device_name": f"fake_device_stage{str(stage+1)}_{str(stage_node+1)}"},
                    {
                        "$set": {
                            "device_name": f"fake_device_stage{str(stage+1)}_{str(stage_node+1)}",
                            # "group": stage + 1,
                            # "image": "router.png",
                        }
                    },
                )


def add_iface_utilization(
    device_name: str,
    iface_name: str,
    iface_bytes: int,
    previous_utilization: int,
    previous_timestamp: int,
) -> None:
    """Inserts fake iface utilization of a specific
    interface into db (utilization collection)"""

    last_utilization: int = iface_bytes * 8
    if previous_timestamp > 0:
        last_utilization = previous_utilization + last_utilization

    db.utilization.update_one(
        {"device_name": f"{device_name}", "iface_name": f"{iface_name}"},
        {
            "$set": {
                "device_name": f"{device_name}",
                "iface_name": f"{iface_name}",
                "prev_utilization": previous_utilization,
                "prev_timestamp": previous_timestamp,
                "timestamp": int(time()),
                "last_utilization": last_utilization,
            }
        },
        True,
    )


def add_iface_stats(
    device_name: str,
    iface_name: str,
    iface_bytes: int,
    previous_utilization: int
) -> None:
    """Inserts fake iface stats to a specific
    interface into db (stats collection)"""

    previous_utilization = int(previous_utilization / 8)
    db.stats.insert_one(
        {
            "device_name": f"{device_name}",
            "iface_name": f"{iface_name}",
            "ifalias": f"{iface_name}",
            "timestamp": int(time()),
            "mtu": 1500,
            "mac": "",
            "speed": 10,
            "in_discards": 0,
            "in_errors": 0,
            "out_discards": 0,
            "out_errors": 0,
            "in_bytes": previous_utilization + iface_bytes,
            "in_ucast_pkts": 0,
            "in_mcast_pkts": 0,
            "in_bcast_pkts": 0,
            "out_bytes": previous_utilization + iface_bytes,
            "out_ucast_pkts": 0,
            "out_mcast_pkts": 0,
            "out_bcast_pkts": 0,
        }
    )

# pylint: disable=too-many-locals
def add_lots_of_links(
    number_nodes: int, fabric_stages: int, stats_only: bool = False, random_bytes: bool = True
) -> None :
    """Calculates and adds all the links needed so the topo looks like a fabric"""

    node_number: int = 0

    nodes_per_stages: int = int(number_nodes / fabric_stages)

    node_increment: int = int(1250000 / number_nodes)

    for stage in range(fabric_stages):
        if stage == 0:
            continue

        for up_node in range(nodes_per_stages):

            up_device: str = f"fake_device_stage{str(stage)}_{str(up_node+1)}"
            up_iface: str = f"0/{str(up_node+1)}"

            for down_node in range(nodes_per_stages):

                down_device: str = f"fake_device_stage{str(stage+1)}_{str(down_node+1)}"
                down_iface: str = f"1/{str(down_node+1)}"

                if not stats_only:
                    db.links.insert_one(
                        {
                            "device_name": f"{up_device}",
                            "iface_name": f"{down_iface}",
                            "neighbor_iface": f"{up_iface}",
                            "neighbor_name": f"{down_device}",
                        }
                    )

                    db.links.insert_one(
                        {
                            "device_name": f"{down_device}",
                            "iface_name": f"{up_iface}",
                            "neighbor_iface": f"{down_iface}",
                            "neighbor_name": f"{up_device}",
                        }
                    )

                iface_bytes: int = randint(0, 1250000) if random_bytes else node_number
                previous_utilization, previous_timestamp = get_latest_utilization(
                    up_device, down_iface
                )

                print(up_device, down_iface, down_device, up_iface, iface_bytes, number_nodes)
                add_iface_stats(up_device, down_iface, iface_bytes, previous_utilization)
                add_iface_utilization(
                    up_device, down_iface, iface_bytes, previous_utilization, previous_timestamp
                )

                add_iface_stats(down_device, up_iface, iface_bytes, previous_utilization)
                add_iface_utilization(
                    down_device, up_iface, iface_bytes, previous_utilization, previous_timestamp
                )

            node_number += node_increment

def add_fake_datas(
    nb_nodes: int, fabric_stages: int, add_stats_only: bool = False, random_bytes: bool = True
) -> None:
    """Determine the number of stages the fabric should have and calls
    the right functions depending on if user wants to create everything or
    just add stats to an already existing fake fabric"""

    fabric_stages = 1 if fabric_stages == 1 else int(fabric_stages / 2 + 1)

    if not add_stats_only:
        add_lots_of_nodes(nb_nodes, fabric_stages)
    add_lots_of_links(nb_nodes, fabric_stages, add_stats_only, random_bytes)


def delete_all_collections_datas() -> None:
    """Deletes everything in all db collections"""
    db.nodes.delete_many({})
    db.links.delete_many({})
    db.stats.delete_many({})
    db.utilization.delete_many({})


def main() -> None:
    """Handles user interface (arguments) and calls the main 'add_fake_datas' func"""
    parser = ArgumentParser(
        prog="db_filler",
        description="Fill db with fake datas",
    )
    parser.add_argument(
        "-n",
        "--number_nodes",
        type=int,
        help="How much nodes to add?",
        default="6",
    )
    parser.add_argument(
        "-s",
        "--fabric_stages",
        type=int,
        help="Will add nodes into a fabric hierarchy with 's' number of stages",
        default="5",
    )
    parser.add_argument(
        "-a",
        "--add_stats_only",
        type=bool,
        help="If this flag is set, we only add new iface stats for the current \
            timestamp (useful when you already have enough nodes/links)",
        default=False,
    )
    parser.add_argument(
        "-r",
        "--random_bytes",
        type=bool,
        help="By default, it adds fake datas with random bytes on the \
            ifaces/utilizations. Can be set to false for tests and stuff \
            to have predictive results",
        default=True,
    )
    parser.add_argument(
        "-rm",
        "--rm_db",
        type=bool,
        help="If this flag is set, we delete all db datas",
        default=False,
    )

    args = parser.parse_args()

    if args.rm_db:
        delete_all_collections_datas()
        sexit(0)

    if args.fabric_stages % 2 == 0 or args.fabric_stages < 0:
        print("Fabric stages can only by an odd number > 0")
        sexit(1)

    if args.add_stats_only:
        add_fake_datas(args.number_nodes, args.fabric_stages, True, args.random_bytes)
        sexit(0)

    prep_db_if_not_exist()

    add_fake_datas(args.number_nodes, args.fabric_stages, False, args.random_bytes)

    for res in db.nodes.find():
        print(res)


if __name__ == "__main__":
    main()
