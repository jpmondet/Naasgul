"""This module aims to test the snmp functions with pytest.
Warning: A mongodb and a snmpsim node must be up&running"""
#! /bin/env python3

import sys
import os
from typing import Dict, List, Any
from add_fake_data_to_db import delete_all_collections_datas

sys.path.append(os.path.realpath(os.path.dirname(__file__) + "/../backend/"))
# pylint:disable=import-error, wrong-import-position
from db_layer import prep_db_if_not_exist, get_node, get_stats_devices
from snmp_functions import (
    get_snmp_creds,
)
from snmp_get_lldp_topo import lldp_scrapping
from snmp_get_ifaces_stats import stats_scrapping

SNMP_NODE_TO_RETRIEVE: str = os.getenv("SNMP_NODE_TO_RETRIEVE", "127.0.0.1")


def test_getting_lldp_infos() -> None:
    """Launch the main lldp scrapping function on a
    dumb node and checks db to see if it was correctly scrapped
    and dumped"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    lldp_scrapping(get_snmp_creds(snmp_user="lldp"), SNMP_NODE_TO_RETRIEVE)

    assert get_node(SNMP_NODE_TO_RETRIEVE)


def test_getting_iface_stats() -> None:
    """Launch the main stats scrapping function on a
    dumb node and check db to see if stats were correctly scrapped
    and dumped"""

    delete_all_collections_datas()
    prep_db_if_not_exist()

    stats_scrapping(get_snmp_creds(snmp_user="ifmib"), SNMP_NODE_TO_RETRIEVE)

    stats_from_db: List[Dict[str, Any]] = list(get_stats_devices([SNMP_NODE_TO_RETRIEVE]))

    assert len(stats_from_db) == 8
