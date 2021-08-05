#! /usr/bin/env python3

from os import getenv
import asyncio
from itertools import groupby
from binascii import hexlify
from time import time, sleep
from typing import List, Dict, Any, Tuple
from pymongo.errors import InvalidOperation  # type: ignore
from pysnmp.error import PySnmpError  # type: ignore
from dpath.util import search  # type: ignore
from db_layer import (
    prep_db_if_not_exist,
    bulk_update_collection,
    NODES_COLLECTION,
    LINKS_COLLECTION,
    get_all_nodes,
)
from snmp_functions import (
    get_table,
    get_snmp_creds,
    split_list,
    NEEDED_MIBS_FOR_LLDP as NEEDED_MIBS,
)

SNMP_USR = getenv("SNMP_USR")
SNMP_AUTH_PWD = getenv("SNMP_AUTH_PWD")
SNMP_PRIV_PWD = getenv("SNMP_PRIV_PWD")
INIT_NODE_FQDN = getenv("LLDP_INIT_NODE_FQDN", "")
INIT_NODE_IP = getenv("LLDP_INIT_NODE_IP", "")
INIT_NODE_PORT = getenv("LLDP_INIT_NODE_PORT", "161")
STOP_NODES_FQDN = getenv("STOP_NODES_FQDN")
STOP_NODES_IP = getenv("STOP_NODES_IP")
NB_THREADS = getenv("AUTOMAP_NB_THREADS", "10")


def dump_results_to_db(device_name, lldp_infos) -> None:
    nodes_list: List[Tuple[Dict[str, str], Dict[str, str]]] = []
    links_list: List[Tuple[Dict[str, str], Dict[str, str]]] = []

    # Each item of the lists are composed by the "query" (so the DB knows which entry to update
    # And the actual data
    dev_name = device_name.lower()
    query = {"device_name": dev_name}
    # We add the device if it doesn't exist
    nodes_list.append((query, query))

    for lldp_nei in lldp_infos:
        # Getting neigh node infos and adding it to nodes_list
        _, neigh_name = next(search(lldp_nei, f"{NEEDED_MIBS['lldp_neigh_name']}*", yielded=True))
        if not neigh_name:
            continue
        neigh_name = neigh_name.lower()

        # IP is a lil' special since it is written in the oid (yeah weird)
        neigh_ip_oid, _ = next(search(lldp_nei, f"{NEEDED_MIBS['lldp_neigh_ip']}*", yielded=True))
        neigh_ip = ".".join(neigh_ip_oid.split(".")[-4:])
        query_neigh = {"device_name": neigh_name}
        nodes_list.append((query_neigh, {"device_name": neigh_name, "device_ip": neigh_ip}))

        # Getting neigh and local ifaces infos and adding them to link list
        _, local_iface = next(search(lldp_nei, f"{NEEDED_MIBS['lldp_local_iface']}*", yielded=True))
        _, neigh_iface = next(search(lldp_nei, f"{NEEDED_MIBS['lldp_neigh_iface']}*", yielded=True))
        # Stripping "Et, Ethernet, E,... " which can be different per equipment
        if isinstance(local_iface, str):
            dev_iface = "/".join(
                "".join(x)
                for is_number, x in groupby(local_iface, key=str.isdigit)
                if is_number is True
            )
        else:
            dev_iface = str(dev_iface)

        if isinstance(neigh_iface, str):
            neigh_iface = "/".join(
                "".join(x)
                for is_number, x in groupby(neigh_iface, key=str.isdigit)
                if is_number is True
            )
        else:
            neigh_iface = str(neigh_iface)

        query_link = {
            "device_name": dev_name,
            "iface_name": dev_iface,
            "neighbor_name": neigh_name,
            "neighbor_iface": neigh_iface,
        }

        links_list.append((query_link, query_link))

        query_neigh_link = {
            "device_name": neigh_name,
            "iface_name": neigh_iface,
            "neighbor_name": dev_name,
            "neighbor_iface": dev_iface,
        }
        links_list.append((query_neigh_link, query_neigh_link))

    try:
        bulk_update_collection(NODES_COLLECTION, nodes_list)
        bulk_update_collection(LINKS_COLLECTION, links_list)
    except InvalidOperation:
        print("Nothing to dump to db (wasn't able to scrap devices?), passing..")


async def get_device_lldp_infos(target_name, oids, credentials, target_ip=None, port=161):

    target = target_ip if target_ip else target_name
    target_name = target if not target_name else target_name

    try:
        res = get_table(target, oids, credentials, port=port)
        dump_results_to_db(target_name, res)
    except (RuntimeError, PySnmpError) as err:
        print(err, "\n (can't access to devices?) Passing for now...")


def main():

    creds = get_snmp_creds(SNMP_USR, SNMP_AUTH_PWD, SNMP_PRIV_PWD)

    prep_db_if_not_exist()

    while True:
        scrapped: List[Dict[str, str]] = get_all_nodes()
        devices: List[Tuple[str, str]] = []
        for device in scrapped:
            if "fake" in device["device_name"]:
                continue
            devices.append((device["device_name"], None, 161))

        if not devices:
            if INIT_NODE_FQDN:
                device = (INIT_NODE_FQDN, INIT_NODE_IP, int(INIT_NODE_PORT))
            elif INIT_NODE_IP:
                device = (INIT_NODE_IP, INIT_NODE_IP, int(INIT_NODE_PORT))
            else:
                # This is a test case
                device = ("fake_local_device", "127.0.0.1", 1161)
            devices.append(device)

        if STOP_NODES_FQDN:
            stop_fqdns = STOP_NODES_FQDN.split(",")
            for node in stop_fqdns:
                if node in devices:
                    devices.remove(node)
        if STOP_NODES_IP:
            stop_ips = STOP_NODES_IP.split(",")
            for node in stop_ips:
                if node in devices:
                    devices.remove(node)

        print(devices)

        for devices_to_scrap in split_list(devices, int(NB_THREADS)):

            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                asyncio.wait(
                    [
                        get_device_lldp_infos(
                            hostname, NEEDED_MIBS.values(), creds, target_ip=ip, port=port
                        )
                        for hostname, ip, port in devices_to_scrap
                    ]
                )
            )

        # sleep(300)
        sleep(int(60 * (len(devices) / int(NB_THREADS))) + 30)


if __name__ == "__main__":
    main()
