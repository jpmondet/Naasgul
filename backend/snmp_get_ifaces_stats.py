"""This module is a standalone Stats scrapper that uses snmp
to get interfaces stats for a lot of devices.
Datas retrieved are then stored into db."""
#! /usr/bin/env python3

from os import getenv
import asyncio
from itertools import groupby
from binascii import hexlify
from time import time, sleep
from typing import List, Dict, Tuple, Optional, Any, Union
from pymongo.errors import InvalidOperation  # type: ignore
from pysnmp.error import PySnmpError  # type: ignore
from pysnmp import hlapi  # type: ignore
from dpath.util import search  # type: ignore
from db_layer import (
    prep_db_if_not_exist,
    bulk_update_collection,
    add_iface_stats,
    get_all_nodes,
    get_nodes_by_patterns,
    get_latest_utilization,
    UTILIZATION_COLLECTION,
)
from snmp_functions import (
    get_bulk_auto,
    get_snmp_creds,
    NEEDED_MIBS_FOR_STATS as NEEDED_MIBS,
    IFACES_TABLE_TO_COUNT,
    split_list,
)

SNMP_USR: Optional[str] = getenv("SNMP_USR")
SNMP_AUTH_PWD: Optional[str] = getenv("SNMP_AUTH_PWD")
SNMP_PRIV_PWD: Optional[str] = getenv("SNMP_PRIV_PWD")
TEST_CASE: Optional[str] = getenv("AUTOMAP_TEST_CASE")
NB_THREADS: str = getenv("AUTOMAP_NB_THREADS", "10")
NODES_PATTERNS: Optional[str] = getenv("NODES_PATTERNS")


def dump_results_to_db(  # pylint: disable=too-many-locals
    device_name: str, ifaces_infos: List[Dict[str, str]]
) -> None:
    """Format retrieved snmp datas & dumps them into db"""
    utilization_list: List[Tuple[Dict[str, str], Dict[str, str]]] = []
    stats_list: List[Dict[str, str]] = []
    for iface in ifaces_infos:
        ifname: str = ""
        _, ifname = next(search(iface, f"{NEEDED_MIBS['iface_name']}*", yielded=True))
        ifname = str(ifname).lower()
        if (  # pylint: disable=too-many-boolean-expressions
            ifname.startswith("se")
            or ifname.startswith("nu")
            or ifname.startswith("lo")
            or ifname.startswith("mgm")
            or ifname.startswith("ma")
            or ifname.startswith("po")
            or ifname == "vlan1"
        ):
            # To do: Mgmt ifaces/lo & po could actually be interesting... Need to think about this
            continue
        ifalias: str = ""
        _, ifalias = next(search(iface, f"{NEEDED_MIBS['iface_alias']}*", yielded=True))
        # if not ifalias:
        #    # We won't get stats of ifaces with no description
        #    continue
        _, mtu = next(search(iface, f"{NEEDED_MIBS['mtu']}*", yielded=True))
        _, mac = next(search(iface, f"{NEEDED_MIBS['mac']}*", yielded=True))
        _, speed = next(search(iface, f"{NEEDED_MIBS['speed']}*", yielded=True))
        _, in_disc = next(search(iface, f"{NEEDED_MIBS['in_disc']}*", yielded=True))
        _, in_err = next(search(iface, f"{NEEDED_MIBS['in_err']}*", yielded=True))
        _, out_disc = next(search(iface, f"{NEEDED_MIBS['out_disc']}*", yielded=True))
        _, out_err = next(search(iface, f"{NEEDED_MIBS['out_err']}*", yielded=True))
        _, in_octets = next(search(iface, f"{NEEDED_MIBS['in_octets']}*", yielded=True))
        _, in_ucast_pkts = next(search(iface, f"{NEEDED_MIBS['in_ucast_pkts']}*", yielded=True))
        _, in_mcast_pkts = next(search(iface, f"{NEEDED_MIBS['in_mcast_pkts']}*", yielded=True))
        _, in_bcast_pkts = next(search(iface, f"{NEEDED_MIBS['in_bcast_pkts']}*", yielded=True))
        _, out_octets = next(search(iface, f"{NEEDED_MIBS['out_octets']}*", yielded=True))
        _, out_ucast_pkts = next(search(iface, f"{NEEDED_MIBS['out_ucast_pkts']}*", yielded=True))
        _, out_mcast_pkts = next(search(iface, f"{NEEDED_MIBS['out_mcast_pkts']}*", yielded=True))
        _, out_bcast_pkts = next(search(iface, f"{NEEDED_MIBS['out_bcast_pkts']}*", yielded=True))

        iface_infos_dict: Dict[str, Any] = {
            "ifalias": str(ifalias),
            "mtu": int(mtu),
            "mac": hexlify(mac.encode()).decode(),
            "speed": int(speed),
            "in_discards": int(in_disc) % (2 ** 64 - 1),  # There are some weird devices
            # returning values greater than 2**64...
            "in_errors": int(in_err) % (2 ** 64 - 1),
            "out_discards": int(out_disc) % (2 ** 64 - 1),
            "out_errors": int(out_err) % (2 ** 64 - 1),
            "in_bytes": int(in_octets) % (2 ** 64 - 1),
            "in_ucast_pkts": int(in_ucast_pkts) % (2 ** 64 - 1),
            "in_mcast_pkts": int(in_mcast_pkts) % (2 ** 64 - 1),
            "in_bcast_pkts": int(in_bcast_pkts) % (2 ** 64 - 1),
            "out_bytes": int(out_octets) % (2 ** 64 - 1),
            "out_ucast_pkts": int(out_ucast_pkts) % (2 ** 64 - 1),
            "out_mcast_pkts": int(out_mcast_pkts) % (2 ** 64 - 1),
            "out_bcast_pkts": int(out_bcast_pkts) % (2 ** 64 - 1),
        }

        iface_name = "/".join(
            "".join(x) for is_number, x in groupby(ifname, key=str.isdigit) if is_number is True
        )
        iface_stats_dict: Dict[str, Any] = {
            "device_name": device_name,
            "iface_name": iface_name,
            "timestamp": int(time()),
        }
        iface_stats_dict.update(iface_infos_dict)
        stats_list.append(iface_stats_dict)
        # Each item of the lists are composed are the "query" (so the DB knows which entry to update
        # And the actual data
        query: Dict[str, str] = {"device_name": device_name, "iface_name": iface_name}
        highest: int = int(iface_infos_dict["in_bytes"])
        lowest: int = int(iface_infos_dict["out_bytes"])
        highest = max(highest, lowest)
        previous_utilization, previous_timestamp = get_latest_utilization(device_name, iface_name)
        utilization: Dict[str, Any] = {
            "device_name": device_name,
            "iface_name": iface_name,
            "prev_utilization": previous_utilization,
            "prev_timestamp": previous_timestamp,
            "last_utilization": highest * 8,
            "timestamp": iface_stats_dict["timestamp"],
        }
        utilization_list.append((query, utilization))

    try:
        bulk_update_collection(UTILIZATION_COLLECTION, utilization_list)
        add_iface_stats(stats_list)
    except InvalidOperation:
        print("Nothing to dump to db (wasn't able to scrap devices?), passing..")
    except OverflowError:
        print("OverflowError 0_o (int longer than 64bit) : " + str(utilization_list))


# pylint: disable=too-many-arguments
async def get_stats_and_dump(
    target_name: str,
    oids: List[str],
    credentials: Union[hlapi.CommunityData, hlapi.UsmUserData],
    count_oid: str,
    target_ip: Optional[str] = None,
    port: int = 161,
) -> None:
    """Using snmp to get iface(stats) infos & dumping them into db by calling dump_results_to_db"""

    target: str = target_ip if target_ip else target_name

    try:
        res: List[Dict[str, str]] = get_bulk_auto(target, oids, credentials, count_oid, port=port)
        dump_results_to_db(target_name, res)
    except (RuntimeError, PySnmpError) as err:
        print(err, "\n (can't access to devices?) Passing for now...")


def stats_scrapping(
    snmp_credentials: Union[hlapi.CommunityData, hlapi.UsmUserData], init_node_fqdn: str = ""
) -> None:
    """Main ifaces(stats) scrapping func that launch threads to scrap
    devices"""
    scrapped: List[Dict[str, str]] = []
    if NODES_PATTERNS:
        scrapped = get_nodes_by_patterns(NODES_PATTERNS.split(','))
    else:
        scrapped = get_all_nodes()
    devices: List[Tuple[str, str, int]] = []
    if init_node_fqdn:
        # This is a pytest case
        devices.append((init_node_fqdn, "", 1161))
    for device in scrapped:
        if "fake" in device["device_name"]:
            continue
        devices.append((device["device_name"], "", 161))

    if TEST_CASE:
        devices.append(("fake_local_device", "127.0.0.1", 1161))

    if devices:
        for devices_to_scrap in split_list(devices, int(NB_THREADS)):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                asyncio.wait(  # type: ignore
                    [
                        get_stats_and_dump(
                            hostname,
                            NEEDED_MIBS.values(),  # type: ignore
                            snmp_credentials,
                            IFACES_TABLE_TO_COUNT,
                            target_ip=ip,
                            port=port,
                        )
                        for hostname, ip, port in devices_to_scrap
                    ]
                )
            )
            # sleep(10)
        if not init_node_fqdn:
            sleep(int(60 + (len(devices) / int(NB_THREADS))))
    else:
        print("No devices retrieved from db... Waiting till there are any.")
        sleep(60)


def main() -> None:
    """Get hlapi credentials, prepare the db & launch the
    scrapping loop"""

    creds = get_snmp_creds(SNMP_USR, SNMP_AUTH_PWD, SNMP_PRIV_PWD)

    prep_db_if_not_exist()

    while True:
        stats_scrapping(creds)


if __name__ == "__main__":
    main()
