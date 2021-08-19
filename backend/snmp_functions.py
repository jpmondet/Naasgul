"""Contains all snmp function wrapping pysnmp and used
    by lldp & stats scrappers """
#! /usr/bin/env python3
# pylint: disable=too-many-arguments

from typing import List, Dict, Any, Union, Optional, Iterator, Tuple
from pysnmp import hlapi  # type: ignore
from pysnmp.entity.rfc3413.oneliner import cmdgen  # type: ignore

# from pysnmp.error import PySnmpError # type: ignore

IFACES_TABLE_TO_COUNT: str = "1.3.6.1.2.1.2.1.0"
NEEDED_MIBS_FOR_STATS: Dict[str, str] = {
    "iface_name": "1.3.6.1.2.1.2.2.1.2",  # ifDescr
    "iface_alias": "1.3.6.1.2.1.31.1.1.1.18",  # ifAlias
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

NEEDED_MIBS_FOR_LLDP: Dict[str, str] = {
    "lldp_neigh_name": "1.0.8802.1.1.2.1.4.1.1.9",  # lldpRemSysName
    "lldp_neigh_iface": "1.0.8802.1.1.2.1.4.1.1.7",  # lldpRemPortId
    "lldp_neigh_ip": "1.0.8802.1.1.2.1.4.2.1",  # lldpRemManAddrEntry
    "lldp_local_iface": "1.0.8802.1.1.2.1.3.7.1.3",  # lldpLocPortId
    #'lldp_neigh_sys_descr': '1.0.8802.1.1.2.1.4.1.1.10', # lldpRemSysDesc
    #'lldp_neigh_iface_descr': '1.0.8802.1.1.2.1.4.1.1.8', # lldpRemPortDesc
}


def get_snmp_creds(
    snmp_user: Optional[str] = "public",
    snmp_auth_pwd: Optional[str] = None,
    snmp_priv_pwd: Optional[str] = None,
) -> Union[hlapi.CommunityData, hlapi.UsmUserData]:
    """Returns snmp v2 or v3 pysnmp credentials depending on parameters"""

    snmpv2_user: str = ""

    if snmp_user and snmp_auth_pwd and snmp_priv_pwd:
        return get_snmp_v3_creds(snmp_user, snmp_auth_pwd, snmp_priv_pwd)

    if snmp_user:
        snmpv2_user = snmp_user

    return get_snmp_v2_creds(snmpv2_user)


def get_snmp_v2_creds(snmp_community: str) -> hlapi.CommunityData:
    """Returns snmp v2 pysnmp credentials"""
    return hlapi.CommunityData(snmp_community)


def get_snmp_v3_creds(snmp_user: str, snmp_auth_pwd: str, snmp_priv_pwd: str) -> hlapi.UsmUserData:
    """Returns snmp v3 pysnmp credentials"""
    return hlapi.UsmUserData(
        snmp_user,
        snmp_auth_pwd,
        snmp_priv_pwd,
        authProtocol=cmdgen.usmHMACSHAAuthProtocol,
        privProtocol=cmdgen.usmAesCfb128Protocol,
    )


def construct_object_types(list_of_oids: List[str]) -> List[hlapi.ObjectType]:
    """Builds and returns a list of special 'ObjectType'
    from pysnmp"""
    object_types: List[hlapi.ObjectType] = []
    for oid in list_of_oids:
        object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid)))
    return object_types


def cast(value: Any) -> Any:
    """Casts and return a value depending on its real type"""
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


def fetch(
    handler: Iterator[Tuple[str, str, int, Tuple[str, Any]]], count: Optional[int] = 1000
) -> List[Dict[str, str]]:
    """Actually getting snmp values from a device and
    returns a list of the results retrieved"""
    result: List[Dict[str, str]] = []
    if count:
        for _ in range(count):
            try:
                error_indication, error_status, _, var_binds = next(handler)
                if not error_indication and not error_status:
                    items: Dict[str, Any] = {}
                    for var_bind in var_binds:
                        items[str(var_bind[0])] = cast(var_bind[1])
                    result.append(items)
                else:
                    raise RuntimeError("Got SNMP error: {0}".format(error_indication))
            except StopIteration:
                break
    return result


def get_table(
    target: str,
    oids: List[str],
    credentials: Union[hlapi.CommunityData, hlapi.UsmUserData],
    port: int = 161,
    engine: hlapi.SnmpEngine = hlapi.SnmpEngine(),
    context: hlapi.ContextData = hlapi.ContextData(),
) -> List[Dict[str, str]]:
    """Prepares the handler to fetch snmp oids as a table
    and returns the actual values return by fetch"""
    handler: Iterator[Tuple[str, str, int, Tuple[str, Any]]] = hlapi.nextCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        *construct_object_types(oids),
        lexicographicMode=False,
    )
    return fetch(handler)


def get(
    target: str,
    oids: List[str],
    credentials: Union[hlapi.CommunityData, hlapi.UsmUserData],
    port: int = 161,
    engine: hlapi.SnmpEngine = hlapi.SnmpEngine(),
    context: hlapi.ContextData = hlapi.ContextData(),
) -> Dict[str, Any]:
    """Prepares the handler to fetch snmp oids and
    returns the actual values return by fetch"""
    handler: Iterator[Tuple[str, str, int, Tuple[str, Any]]] = hlapi.getCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        *construct_object_types(oids),
    )
    return fetch(handler, 1)[0]


def get_bulk(
    target: str,
    oids: List[str],
    credentials: Union[hlapi.CommunityData, hlapi.UsmUserData],
    count: int,
    start_from: int = 0,
    port: int = 161,
    engine: hlapi.SnmpEngine = hlapi.SnmpEngine(),
    context: hlapi.ContextData = hlapi.ContextData(),
) -> List[Dict[str, str]]:
    """Prepares the handler to fetch snmp oids with a bulk
    cmd and returns the actual values return by fetch"""
    handler: Iterator[Tuple[str, str, int, Tuple[str, Any]]] = hlapi.bulkCmd(
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
    target: str,
    oids: List[str],
    credentials: Union[hlapi.CommunityData, hlapi.UsmUserData],
    count_oid: str,
    start_from: int = 0,
    port: int = 161,
    engine: hlapi.SnmpEngine = hlapi.SnmpEngine(),
    context: hlapi.ContextData = hlapi.ContextData(),
) -> List[Dict[str, str]]:
    """Basically tries to automate get_bulk by discovering how much
    we have to count with a 'count_oid'"""

    count: int = get(target, [count_oid], credentials, port, engine, context)[count_oid]

    return get_bulk(target, oids, credentials, count, start_from, port, engine, context)


# Not an actual snmp func but it's used in the context of snmp scrapping
def split_list(list_to_split: List[Any], size: int) -> Iterator[List[Any]]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(list_to_split), size):
        yield list_to_split[i : i + size]
