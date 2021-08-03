#! /usr/bin/env python3

from typing import List
from pysnmp import hlapi  # type: ignore
from pysnmp.entity.rfc3413.oneliner import cmdgen  # type: ignore

# from pysnmp.error import PySnmpError # type: ignore

IFACES_TABLE_TO_COUNT = "1.3.6.1.2.1.2.1.0"
NEEDED_MIBS_FOR_STATS = {
    "iface_name": "1.3.6.1.2.1.2.2.1.2",  # ifDescr
    "mtu": "1.3.6.1.2.1.2.2.1.4",  # ifMtu
    "speed": "1.3.6.1.2.1.31.1.1.1.15",  # ifHighSpeed
    "mac": "1.3.6.1.2.1.2.2.1.6",  # ifPhysAddress
    "in_disc": "1.3.6.1.2.1.2.2.1.13",  # ifInDiscards
    "in_err": "1.3.6.1.2.1.2.2.1.14",  # ifInErrors
    "out_disc": "1.3.6.1.2.1.2.2.1.19",  # ifOutDiscards
    "out_err": "1.3.6.1.2.1.2.2.1.20",  # ifOutErrors
    "in_octets": "1.3.6.1.2.1.31.1.1.1.6",  # ifHCInOctets
    "in_ucast_pkts": "1.3.6.1.2.1.31.1.1.1.7",  # ifHCInUcastPkts
    "in_mcast_pkts": "1.3.6.1.2.1.31.1.1.1.8",  # ifHCInMulticastPkts
    "in_bcast_pkts": "1.3.6.1.2.1.31.1.1.1.9",  # ifHCInBroadcastPkts
    "out_octets": "1.3.6.1.2.1.31.1.1.1.10",  # ifHCOutOctets
    "out_ucast_pkts": "1.3.6.1.2.1.31.1.1.1.11",  # ifHCOutUcastPkts
    "out_mcast_pkts": "1.3.6.1.2.1.31.1.1.1.12",  # ifHCOutMulticastPkts
    "out_bcast_pkts": "1.3.6.1.2.1.31.1.1.1.13",  # ifHCOutBroadcastPkts
}

NEEDED_MIBS_FOR_LLDP = {
    "lldp_neigh_name": "1.0.8802.1.1.2.1.4.1.1.9",  # lldpRemSysName
    "lldp_neigh_iface": "1.0.8802.1.1.2.1.4.1.1.7",  # lldpRemPortId
    "lldp_neigh_ip": "1.0.8802.1.1.2.1.4.2.1",  # lldpRemManAddrEntry
    "lldp_local_iface": "1.0.8802.1.1.2.1.3.7.1.3",  # lldpLocPortId
    #'lldp_neigh_sys_descr': '1.0.8802.1.1.2.1.4.1.1.10', # lldpRemSysDesc
    #'lldp_neigh_iface_descr': '1.0.8802.1.1.2.1.4.1.1.8', # lldpRemPortDesc
}


def get_snmp_creds(snmp_user: str = "public", snmp_auth_pwd: str = None, snmp_priv_pwd: str = None):
    if snmp_auth_pwd and snmp_priv_pwd:
        return get_snmp_v3_creds(snmp_user, snmp_auth_pwd, snmp_priv_pwd)

    return get_snmp_v2_creds(snmp_user)


def get_snmp_v2_creds(snmp_community) -> hlapi.CommunityData:
    return hlapi.CommunityData(snmp_community)


def get_snmp_v3_creds(snmp_user, snmp_auth_pwd, snmp_priv_pwd) -> hlapi.UsmUserData:
    return hlapi.UsmUserData(
        snmp_user,
        snmp_auth_pwd,
        snmp_priv_pwd,
        authProtocol=cmdgen.usmHMACSHAAuthProtocol,
        privProtocol=cmdgen.usmAesCfb128Protocol,
    )


def construct_object_types(list_of_oids):
    object_types: List[str] = []
    for oid in list_of_oids:
        object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid)))
    return object_types


def cast(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return float(value)
        except (ValueError, TypeError):
            try:
                return str(value)
            except (ValueError, TypeError):
                pass
    return value


def fetch(handler, count):
    result = []
    for _ in range(count):
        try:
            error_indication, error_status, _, var_binds = next(handler)
            if not error_indication and not error_status:
                items = {}
                for var_bind in var_binds:
                    items[str(var_bind[0])] = cast(var_bind[1])
                result.append(items)
            else:
                raise RuntimeError("Got SNMP error: {0}".format(error_indication))
        except StopIteration:
            break
    return result


def get_table(
    target, oids, credentials, port=161, engine=hlapi.SnmpEngine(), context=hlapi.ContextData()
):
    handler = hlapi.nextCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        *construct_object_types(oids),
        lexicographicMode=False,
    )
    return fetch(handler, len(oids))


def get(
    target, oids, credentials, port=161, engine=hlapi.SnmpEngine(), context=hlapi.ContextData()
):
    # print(get)
    handler = hlapi.getCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        *construct_object_types(oids),
    )
    # print(handler)
    return fetch(handler, 1)[0]


def get_bulk(
    target,
    oids,
    credentials,
    count,
    start_from=0,
    port=161,
    engine=hlapi.SnmpEngine(),
    context=hlapi.ContextData(),
):
    handler = hlapi.bulkCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        start_from,
        count,
        *construct_object_types(oids),
    )
    return fetch(handler, count)


def get_bulk_auto(
    target,
    oids,
    credentials,
    count_oid,
    start_from=0,
    port=161,
    engine=hlapi.SnmpEngine(),
    context=hlapi.ContextData(),
):

    count = get(target, [count_oid], credentials, port, engine, context)[count_oid]
    # print(count)
    res = get_bulk(target, oids, credentials, count, start_from, port, engine, context)

    return res


# Not an actual snmp func but it's used in the context of snmp scrapping
def split_list(list_to_split, size):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(list_to_split), size):
        yield list_to_split[i : i + size]
