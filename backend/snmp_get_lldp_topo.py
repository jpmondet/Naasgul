"""This module is a standalone LLDP scrapper that uses snmp.
Datas retrieved are stored into db."""
#! /usr/bin/env python3

# pylint: disable=too-many-locals,too-many-branches

from os import getenv
import asyncio
from itertools import groupby
from time import sleep, time
from typing import List, Dict, Tuple, Optional, Union, Any
from pymongo.errors import InvalidOperation  # type: ignore
from pysnmp.error import PySnmpError  # type: ignore
from pysnmp import hlapi  # type: ignore
from dpath.util import search  # type: ignore
from db_layer import (
    prep_db_if_not_exist,
    bulk_update_collection,
    NODES_COLLECTION,
    LINKS_COLLECTION,
    get_all_nodes,
    get_nodes_by_patterns,
)
from snmp_functions import (
    get_table,
    get_snmp_creds,
    split_list,
    NEEDED_MIBS_FOR_LLDP as NEEDED_MIBS,
)

SNMP_USR: Optional[str] = getenv("SNMP_USR")
SNMP_AUTH_PWD: Optional[str] = getenv("SNMP_AUTH_PWD")
SNMP_PRIV_PWD: Optional[str] = getenv("SNMP_PRIV_PWD")
INIT_NODE_FQDN: Optional[str] = getenv("LLDP_INIT_NODE_FQDN", "")
INIT_NODE_IP: str = getenv("LLDP_INIT_NODE_IP", "")
INIT_NODE_PORT: str = getenv("LLDP_INIT_NODE_PORT", "161")
STOP_NODES_FQDN: Optional[str] = getenv("STOP_NODES_FQDN")
STOP_NODES_IP: Optional[str] = getenv("STOP_NODES_IP")
NB_THREADS: str = getenv("AUTOMAP_NB_THREADS", "10")
NODES_PATTERNS: Optional[str] = getenv("NODES_PATTERNS")  # Patterns separated by a coma


def dump_results_to_db(device_name: str, lldp_infos: List[Dict[str, str]]) -> None:
    """Format retrieved snmp datas & dumps them into db"""
    nodes_list: List[Tuple[Dict[str, str], Dict[str, Any]]] = []
    links_list: List[Tuple[Dict[str, str], Dict[str, str]]] = []

    # Each item of the lists are composed by the "query" (so the DB knows which entry to update
    # And the actual data
    dev_name: str = device_name.lower()
    query: Dict[str, str] = {"device_name": dev_name}
    # We add the device if it doesn't exist
    to_poll: bool = True  # If we have to continue polling this node
    last_poll: float = time()
    nodes_list.append(
        (query, {"device_name": dev_name, "to_poll": to_poll, "last_poll": last_poll})
    )

    for lldp_nei in lldp_infos:
        # Getting neigh node infos and adding it to nodes_list
        neigh_name: str = ""
        _, neigh_name = next(search(lldp_nei, f"{NEEDED_MIBS['lldp_neigh_name']}*", yielded=True))
        neigh_name = neigh_name.lower()
        if not neigh_name or neigh_name in ["null", "localhost.localdomain"]:
            # Was using the IP at first, but it can lead to duplicates if some devices
            # are already known only by their fqdn
            continue

        # IP is a lil' special since it is written in the oid (yeah weird)
        neigh_ip_oid: str = ""
        neigh_ip_oid, _ = next(search(lldp_nei, f"{NEEDED_MIBS['lldp_neigh_ip']}*", yielded=True))
        neigh_ip: str = ".".join(neigh_ip_oid.split(".")[-4:])

        neigh_descr: str = ""
        neigh_descr, _ = next(
            search(lldp_nei, f"{NEEDED_MIBS['lldp_neigh_sys_descr']}*", yielded=True)
        )

        if NODES_PATTERNS:
            if not any(device_pattern in neigh_name for device_pattern in NODES_PATTERNS.split()):
                to_poll = False
        query_neigh: Dict[str, str] = {"device_name": neigh_name}
        nodes_list.append(
            (
                query_neigh,
                {
                    "device_name": neigh_name,
                    "device_ip": neigh_ip,
                    "device_descr": neigh_descr,
                    "to_poll": to_poll,
                },
            )
        )

        # Getting neigh and local ifaces infos and adding them to link list
        local_iface: str = ""
        neigh_iface: str = ""
        neigh_iface_descr: str = ""
        _, local_iface = next(search(lldp_nei, f"{NEEDED_MIBS['lldp_local_iface']}*", yielded=True))
        _, neigh_iface = next(search(lldp_nei, f"{NEEDED_MIBS['lldp_neigh_iface']}*", yielded=True))
        _, neigh_descr = next(
            search(lldp_nei, f"{NEEDED_MIBS['lldp_neigh_iface_descr']}*", yielded=True)
        )
        # Stripping "Et, Ethernet, E,... " which can be different per equipment
        dev_iface = "/".join(
            "".join(x)
            for is_number, x in groupby(str(local_iface), key=str.isdigit)
            if is_number is True
        )
        neigh_iface = "/".join(
            "".join(x)
            for is_number, x in groupby(str(neigh_iface), key=str.isdigit)
            if is_number is True
        )

        query_link: Dict[str, str] = {
            "device_name": dev_name,
            "iface_name": dev_iface,
            "neighbor_name": neigh_name,
            "neighbor_iface": neigh_iface,
            "neighbor_iface_descr": neigh_iface_descr,
        }

        if not dev_name or not dev_iface or not neigh_name or not neigh_iface:
            # Ensure that all values are defined
            # Else we don't add this link
            print(f"WARNING: Link not added : {query_link}")
            continue

        links_list.append((query_link, query_link))

        query_neigh_link: Dict[str, str] = {
            "device_name": neigh_name,
            "iface_name": neigh_iface,
            "iface_descr": neigh_iface_descr,
            "neighbor_name": dev_name,
            "neighbor_iface": dev_iface,
        }
        links_list.append((query_neigh_link, query_neigh_link))

    try:
        bulk_update_collection(NODES_COLLECTION, nodes_list)
        bulk_update_collection(LINKS_COLLECTION, links_list)
    except InvalidOperation:
        print("Nothing to dump to db (wasn't able to scrap devices?), passing..")


async def get_device_lldp_infos(
    target_name: str,
    oids: List[str],
    credentials: Union[hlapi.CommunityData, hlapi.UsmUserData],
    target_ip: Optional[str] = None,
    port: int = 161,
) -> None:
    """Using snmp to get lldp infos & dumping them into db by calling dump_results_to_db"""

    target = target_ip if target_ip else target_name
    target_name = target if not target_name else target_name

    try:
        res: List[Dict[str, str]] = get_table(target, oids, credentials, port=port)
        dump_results_to_db(target_name, res)
    except (RuntimeError, PySnmpError) as err:
        print(err, f"\n (can't access to device {target_name}?) Passing for now...")


def lldp_scrapping(
    snmp_credentials: Union[hlapi.CommunityData, hlapi.UsmUserData], init_node_fqdn: str = ""
) -> None:
    """Main lldp scrapping func that launch threads to scrap
    devices"""

    scrapped: List[Dict[str, str]] = []
    if NODES_PATTERNS:
        scrapped = get_nodes_by_patterns(NODES_PATTERNS.split(","))
    else:
        scrapped = get_all_nodes()
    devices: List[Tuple[str, str, int]] = []
    for dev in scrapped:
        if "fake" in dev["device_name"]:
            continue
        try:
            if not dev["to_poll"]:
                continue
        except KeyError:
            pass
        devices.append((dev["device_name"], "", 161))

    if not devices:
        if INIT_NODE_FQDN:
            device = (INIT_NODE_FQDN, INIT_NODE_IP, int(INIT_NODE_PORT))
        elif INIT_NODE_IP:
            device = (INIT_NODE_IP, INIT_NODE_IP, int(INIT_NODE_PORT))
        elif init_node_fqdn:
            # This is a pytest case
            device = (init_node_fqdn, "", 1161)
        else:
            # Ok we certainly have fake datas
            device = ("fake_local_device", "127.0.0.1", 1161)
        devices.append(device)

    if STOP_NODES_FQDN:
        stop_fqdns = STOP_NODES_FQDN.split(",")
        for node in stop_fqdns:
            node_tuple = (node, "", 161)
            if node_tuple in devices:
                devices.remove(node_tuple)
    if STOP_NODES_IP:
        stop_ips = STOP_NODES_IP.split(",")
        for node in stop_ips:
            node_tuple = (node, node, 161)
            if node_tuple in devices:
                devices.remove(node_tuple)

    print(devices)

    for devices_to_scrap in split_list(devices, int(NB_THREADS)):

        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            asyncio.wait(  # type: ignore
                [
                    get_device_lldp_infos(
                        hostname,
                        NEEDED_MIBS.values(),  # type: ignore
                        snmp_credentials,
                        target_ip=ip,
                        port=port,
                    )
                    for hostname, ip, port in devices_to_scrap
                ]
            )
        )

    # sleep(300)
    if not init_node_fqdn:
        sleep(int(60 * (len(devices) / int(NB_THREADS))) + 30)


def main() -> None:
    """Get hlapi credentials, prepare the db & launch the
    scrapping loop"""

    creds = get_snmp_creds(SNMP_USR, SNMP_AUTH_PWD, SNMP_PRIV_PWD)

    prep_db_if_not_exist()

    while True:
        lldp_scrapping(creds)


if __name__ == "__main__":
    main()
