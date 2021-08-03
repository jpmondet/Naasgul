# /usr/bin/env python3

from sys import exit as sexit
from os import getenv
from typing import List, Tuple
import re
from random import randint
from time import time
from argparse import ArgumentParser
from pymongo import MongoClient, ASCENDING, UpdateMany  # type: ignore
from pymongo.errors import DuplicateKeyError  # type: ignore

# https://pymongo.readthedocs.io/en/stable/tutorial.html

DB_STRING = getenv("DB_STRING")
if not DB_STRING:
    DB_STRING = "mongodb://localhost:27017/"
    # DB_STRING = "mongodb://mongodb:27017/"

client = MongoClient(DB_STRING)
db = client.automapping


def delete_node_from_db(node_name: str) -> None:

    db.nodes.delete_one({"device_name": node_name})
    db.links.delete_many({"device_name": node_name})
    db.links.delete_many({"neighbor_name": node_name})
    db.stats.delete_many({"device_name": node_name})
    db.utilization.delete_many({"neighbor_name": node_name})


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

    args = parser.parse_args()

    if not args.node_name:
        print("Please specify at least node name (or node ip if there is no fqdn)")
        sexit(1)

    delete_node_from_db(args.node_name)

    for res in db.nodes.find():
        print(res)


if __name__ == "__main__":
    main()
