# /usr/bin/env python3

from sys import exit as sexit
from os import getenv
from typing import List, Tuple
from time import time
from argparse import ArgumentParser
from pymongo import MongoClient  # type: ignore
from pymongo.errors import DuplicateKeyError  # type: ignore

# https://pymongo.readthedocs.io/en/stable/tutorial.html

DB_STRING = getenv("DB_STRING")
if not DB_STRING:
    DB_STRING = "mongodb://localhost:27017/"
    # DB_STRING = "mongodb://mongodb:27017/"

client = MongoClient(DB_STRING)
db = client.automapping


def add_iface_utilization(device_name: str, iface_name: str) -> None:
    db.utilization.update_one(
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


def add_iface_stats(device_name: str, iface_name: str) -> None:
    db.stats.insert_one(
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


def add_static_node(
    node_name: str, node_ip: str, node_group: int, node_ifaces: List[str] = None, neigh_infos: List[Tuple[str, str, str]] = None
) -> None:
    node_name = node_name if node_name else node_ip
    try:
        db.nodes.insert_one({"device_name": node_name, "group": node_group, "image": "router.png"})
    except DuplicateKeyError:
        db.nodes.update_many(
            {"device_name": node_name},
            {"$set": {"device_name": node_name, "group": node_group, "image": "router.png"}},
        )

    if neigh_infos:
        for neigh in neigh_infos:
            local_iface, neigh_name, neigh_ip, neigh_iface = neigh
            neigh_name = neigh_name if neigh_name else neigh_ip

            db.links.insert_one(
                {
                    "device_name": node_name,
                    "iface_name": local_iface,
                    "neighbor_iface": neigh_iface,
                    "neighbor_name": neigh_name,
                }
            )

            db.links.insert_one(
                {
                    "device_name": neigh_name,
                    "iface_name": neigh_iface,
                    "neighbor_iface": local_iface,
                    "neighbor_name": node_name,
                }
            )

            add_iface_stats(node_name, local_iface)
            add_iface_utilization(node_name, local_iface)

            add_iface_stats(neigh_name, neigh_iface)
            add_iface_utilization(neigh_name, neigh_iface)

    elif node_ifaces:
        for iface in node_ifaces:
            add_iface_stats(node_name, iface)
            add_iface_utilization(node_name, iface)


def main():
    parser = ArgumentParser(
        prog="db_filler",
        description="Fill db with fake datas",
    )
    parser.add_argument(
        "-n",
        "--node_name",
        type=str,
        help="Fqdn of the node",
    )
    parser.add_argument(
        "-a",
        "--address",
        type=str,
        help="IP address of the node",
    )
    parser.add_argument(
        "-g",
        "--group",
        type=int,
        help="Group of the node (Number that drives its placement on the graph. 0 is on the left, 10 (or even more) on the right)",
        default=10,
    )
    parser.add_argument(
        "-i",
        "--ifaces_of_node",
        type=str,
        help="Ifaces separated by comma (only ifaces where there are neighbors), for exemple : 1/1,2/1",
    )

    args = parser.parse_args()

    local_ifaces: List[str] = None
    neighs: List[Tuple[str, str, str]] = None

    if not args.node_name and not args.address:
        print("Please specify at least node name or node ip")
        sexit(1)

    if not args.ifaces_of_node:
        while (
            res := input(
                "This node has no ifaces. Are you sure you wanna add a 'free' node with no links ? (Enter y/n)\n"
            )
            .lower()
            .strip()
        ) not in {"y", "n"}:
            pass
        if res == "n":
            print("Ok, bye!")
            sexit(1)
    else:
        print("OK, now we have to specify neighbor(s) infos")
        neighs = []

        local_ifaces = args.ifaces_of_node.split(",")
        for iface in local_ifaces:
            while (
                res := input(
                    f"Do you want to specify neighbor infos for the iface {iface} (Enter y/n)\n"
                )
                .lower()
                .strip()
            ) not in {"y", "n"}:
                pass
            if res == "n":
                continue
            neigh_fqdn = input(
                f"Please enter the fqdn of the neighbor of the iface {iface} (just hit ENTER if no fqdn)\n"
            ).lower()
            neigh_ip = input(f"Please enter the ip of the neighbor of the iface {iface}\n").lower()
            neigh_iface = input(
                f"Please enter the iface (like 3/1)  of the neighbor of the local iface {iface}\n"
            ).lower()
            neighs.append((iface, neigh_fqdn, neigh_ip, neigh_iface))

        print(neighs)

    add_static_node(args.node_name, args.address, args.group, local_ifaces, neighs)

    for res in db.nodes.find():
        print(res)


if __name__ == "__main__":
    main()
