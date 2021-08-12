#! /bin/env python3

import sys, os
import json
import pytest
import asyncio
from fastapi.exceptions import HTTPException
from add_fake_data_to_db import delete_all_collections_datas, add_fake_datas

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
from api_for_frontend import get_graph, stats, neighborships
from db_layer import get_all_nodes, get_all_links, get_stats_devices
from snmp_functions import (
        NEEDED_MIBS_FOR_LLDP,
        NEEDED_MIBS_FOR_STATS,
        IFACES_TABLE_TO_COUNT,
        get_snmp_creds
)
from snmp_get_lldp_topo import get_device_lldp_infos
from snmp_get_ifaces_stats import get_stats_and_dump


def test_getting_lldp_infos():

    node_to_retrieve: str = "snmpsim"
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(
    [ get_device_lldp_infos(node_to_retrieve,
        NEEDED_MIBS_FOR_LLDP.values(),
        get_snmp_creds(snmp_user='lldp'), 
        port=1161)
    ]))

    nodes = list(get_all_nodes())

    assert nodes[0]["device_name"] == node_to_retrieve

def test_getting_iface_stats():

    node_to_retrieve: str = "127.0.0.1"
    iface_to_retrieve: str = "1/1"

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(
    [ get_stats_and_dump('127.0.0.1',
        NEEDED_MIBS_FOR_STATS.values(),
        get_snmp_creds(snmp_user='ifmib'), 
        IFACES_TABLE_TO_COUNT,
        '127.0.0.1', 1161)
    ]))

    stats = list(get_stats_devices([node_to_retrieve]))

    assert len(stats) == 8
