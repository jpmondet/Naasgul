#! /bin/env python3

import sys, os
import json
import pytest
import asyncio
from fastapi.exceptions import HTTPException
from add_fake_data_to_db import delete_all_collections_datas, add_fake_datas

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
from api_for_frontend import get_graph, stats, neighborships
from db_layer import prep_db_if_not_exist, get_node, get_all_links, get_stats_devices
from snmp_functions import (
        NEEDED_MIBS_FOR_LLDP,
        NEEDED_MIBS_FOR_STATS,
        IFACES_TABLE_TO_COUNT,
        get_snmp_creds
)
from snmp_get_lldp_topo import get_device_lldp_infos, lldp_scrapping
from snmp_get_ifaces_stats import get_stats_and_dump

SNMP_NODE_TO_RETRIEVE: str = os.getenv("SNMP_NODE_TO_RETRIEVE", "127.0.0.1")

def test_getting_lldp_infos():

    delete_all_collections_datas()
    prep_db_if_not_exist()

    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(asyncio.wait(
    #[ get_device_lldp_infos(SNMP_NODE_TO_RETRIEVE,
    #    NEEDED_MIBS_FOR_LLDP.values(),
    #    get_snmp_creds(snmp_user='lldp'), 
    #    port=1161)
    #]))
    lldp_scrapping(get_snmp_creds(snmp_user='lldp'), SNMP_NODE_TO_RETRIEVE)

    assert get_node(SNMP_NODE_TO_RETRIEVE)

def test_getting_iface_stats():

    iface_to_retrieve: str = "1/1"

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(
    [ get_stats_and_dump(SNMP_NODE_TO_RETRIEVE,
        NEEDED_MIBS_FOR_STATS.values(),
        get_snmp_creds(snmp_user='ifmib'), 
        IFACES_TABLE_TO_COUNT,
        SNMP_NODE_TO_RETRIEVE, 1161)
    ]))

    stats = list(get_stats_devices([SNMP_NODE_TO_RETRIEVE]))

    assert len(stats) == 8
