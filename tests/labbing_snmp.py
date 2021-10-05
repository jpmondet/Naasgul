#! /usr/bin/env python3

from pysnmp import hlapi
from pysnmp.entity.rfc3413.oneliner import cmdgen

SNMP_USR=""
SNMP_AUTH_PWD=""
SNMP_PRIV_PWD=""

CREDS = hlapi.UsmUserData(SNMP_USR, SNMP_AUTH_PWD, SNMP_PRIV_PWD,
        authProtocol=cmdgen.usmHMACSHAAuthProtocol,
        privProtocol=cmdgen.usmAesCfb128Protocol)
 
#CREDS = hlapi.CommunityData('lldp')
#CREDS = hlapi.CommunityData('ifmib')
CREDS = hlapi.CommunityData('TEST')

#TARGET="192.168.77.1"
#TARGET_PORT="161"
#TARGET="127.0.0.1"
TARGET="172.17.0.2"
TARGET_PORT="161"
#TARGET_PORT="1161"

def construct_value_pairs(list_of_pairs):
    pairs = []
    for key, value in list_of_pairs.items():
        pairs.append(hlapi.ObjectType(hlapi.ObjectIdentity(key), value))
    return pairs

def get_bulk_auto(target, oids, credentials, count_oid, start_from=0, port=161,
                  engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):
    count = get(target, [count_oid], credentials, port, engine, context)[count_oid]
    return get_bulk(target, oids, credentials, count, start_from, port, engine, context)

def get_bulk(target, oids, credentials, count, start_from=0, port=161,
             engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):
    handler = hlapi.bulkCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        start_from, count,
        *construct_object_types(oids)
    )
    return fetch(handler, count)


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
    for i in range(count):
        try:
            error_indication, error_status, error_index, var_binds = next(handler)
            if not error_indication and not error_status:
                items = {}
                for var_bind in var_binds:
                    items[str(var_bind[0])] = cast(var_bind[1])
                result.append(items)
            else:
                raise RuntimeError('Got SNMP error: {0}'.format(error_indication))
        except StopIteration:
            break
    return result

def construct_object_types(list_of_oids):
    object_types = []
    for oid in list_of_oids:
        object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid)))
    return object_types


def get(target, oids, credentials, port=161, engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):
    handler = hlapi.getCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        *construct_object_types(oids)
    )
    return fetch(handler, 1)[0]

def fetch2(handler):
    result = []

    for (errorIndication,
         errorStatus,
         errorIndex,
         varBinds) in handler:

        if errorIndication:
            print(errorIndication)
            raise RuntimeError('Got SNMP error: {0}'.format(errorIndication))
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
            raise RuntimeError('Got SNMP error: {0}'.format(errorStatus))
        else:
            for varBind in varBinds:
                result.append(varBind)

    print("DEBUG: len of result from fetch() " + str(len(result)) )
    return result

def get_table(target, oids, credentials, start_from=0, port=161,
              engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):
    handler = hlapi.nextCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        *construct_object_types(oids),
        lexicographicMode=False
    )
    #return cut_array_to_table(fetch2(handler),len(oids))
    return fetch(handler, 100)

def construct_object_types_from_named_oid(list_of_oid_name_tuplets):
    object_types = []
    for oid in list_of_oid_name_tuplets:
        addr = []
        for x in oid:
            addr.append(x)
        object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(*addr).addMibSource('.')))
    return object_types


def cut_array_to_table(data,collumns):
    """
    Example I have 14 items and I need to cut them to rows of 7 items in each, i use the data array and parameter 7
    """
    result = []
    row = []
    collumn_index = 0
    for x in data:
        oid, value = x[0].prettyPrint(), x[1].prettyPrint()
        if value == "No more variables left in this MIB View":
            continue
        x = (oid, value)
        if collumn_index == 0:
            row.append(x)
            collumn_index = 1
        elif collumn_index < collumns:
            collumn_index = collumn_index + 1
            row.append(x)
            if collumn_index == collumns:
                result.append(row)
        else:
            collumn_index = 1
            row = [x] #starts new row

    return result


lldp_table_named_oid = [
    ('LLDP-MIB', 'lldpRemSysName'),
    ('LLDP-MIB', 'lldpRemSysDesc'),
    ('LLDP-MIB', 'lldpRemPortId'),
    ('LLDP-MIB', 'lldpRemPortDesc'),
    ('LLDP-MIB', 'lldpLocPortId'),
    ('LLDP-MIB', 'lldpRemManAddrEntry'),
]

lldp_table = [
    '1.0.8802.1.1.2.1.4.1.1.9',
    '1.0.8802.1.1.2.1.4.1.1.10',
    '1.0.8802.1.1.2.1.4.1.1.7',
    '1.0.8802.1.1.2.1.4.1.1.8',
    '1.0.8802.1.1.2.1.3.7.1.3',
    #'1.0.8802.1.1.2.1.4.1.1.1',
    #'1.0.8802.1.1.2.1.4.1.1.2',
    #'1.0.8802.1.1.2.1.4.1.1.3',
    #'1.0.8802.1.1.2.1.4.1.1.4',
    #'1.0.8802.1.1.2.1.4.1.1.5',
    #'1.0.8802.1.1.2.1.4.1.1.6',
    #'1.0.8802.1.1.2.1.4.1.1.11',
    #'1.0.8802.1.1.2.1.4.1.1.12',
    '1.0.8802.1.1.2.1.4.2.1'
]

sys_stats = [
    ###"1.3.6.1.4.1.2021.10.1.3.1", # LOAD
    ###"1.3.6.1.4.1.2021.10.1.3.2",
    ###"1.3.6.1.4.1.2021.10.1.3.3",
    ###"1.3.6.1.2.1.25.3.2.1.3", # CPU
    ###"1.3.6.1.2.1.25.3.3.1.1",
    "iso.3.6.1.2.1.47.1.1.1.1.2.1100006000", # SENSOR CONTAINER
    "iso.3.6.1.2.1.47.1.1.1.1.3.1100006000",
    "iso.3.6.1.2.1.47.1.1.1.1.4.1100006000",
    "iso.3.6.1.2.1.47.1.1.1.1.5.1100006000",
    "iso.3.6.1.2.1.47.1.1.1.1.6.1100006000",
    #"1.3.6.1.4.1.2021.11",
    #"1.3.6.1.4.1.2021.4.11",
    #"1.3.6.1.4.1.2021.4.6",
    #"1.3.6.1.4.1.2021.4.3.0",
    #"1.3.6.1.4.1.2021.4.5.0",
    #"1.3.6.1.4.1.2021.4.6.0",
    #"1.3.6.1.4.1.2021.4.11.0",
    #"1.3.6.1.4.1.9.9.109.1.1.1.1.7",
    #"1.3.6.1.4.1.9.9.109.1.1.1.1.4",
    #"1.3.6.1.4.1.9.9.109.1.1.1.1.5",
    #"1.3.6.1.4.1.2021.11.9.0",
    #"1.3.6.1.4.1.2021.11.10.0",
    #"1.3.6.1.4.1.2021.11.11.0",
    #"1.3.6.1.2.1.25",
    #"1.3.6.1.2.1.25.1.6",
    #"1.3.6.1.2.1.47.1.1.1.1.2",
    #"1.3.6.1.2.1.131.1.1.1.3",
    #"1.3.6.1.2.1.25.3.2",
    #"1.3.6.1.2.1.25.2.2",
    #"1.3.6.1.2.1.25.3.3",
    #"1.3.6.1.4.1.9.9.109.1.1.1.1.6.1",
    #"1.3.6.1.4.1.9.9.305.1.1.1.0",
    #"1.3.6.1.4.1.9.9.305.1.1.2.0",
    #".1.3.6.1.2.1.25.1.7",
    #".1.3.6.1.2.1.25.3.3",
    #".1.3.6.1.2.1.25.2.2",
]

ifaces_stats = [
"1.3.6.1.2.1.2.2.1.2",
 "1.3.6.1.2.1.31.1.1.1.18",
 "1.3.6.1.2.1.2.2.1.4",
 "1.3.6.1.2.1.31.1.1.1.15",
 "1.3.6.1.2.1.2.2.1.6",
 "1.3.6.1.2.1.2.2.1.13",
 "1.3.6.1.2.1.2.2.1.14",
 "1.3.6.1.2.1.2.2.1.19",
 "1.3.6.1.2.1.2.2.1.20",
 "1.3.6.1.2.1.31.1.1.1.6",
 "1.3.6.1.2.1.31.1.1.1.7",
 "1.3.6.1.2.1.31.1.1.1.8",
 "1.3.6.1.2.1.31.1.1.1.9",
 "1.3.6.1.2.1.31.1.1.1.10",
 "1.3.6.1.2.1.31.1.1.1.11",
 "1.3.6.1.2.1.31.1.1.1.12",
 "1.3.6.1.2.1.31.1.1.1.13",
]


# Device
#print(get('192.168.77.1', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.2', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.3', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.4', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.5', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.6', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.7', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.8', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.9', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.10', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.11', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
#print(get('192.168.77.12', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))

#print(get('127.0.0.1', ['1.3.6.1.2.1.1.5.0'], CREDS, port=1161))
#print(get('127.0.0.1', lldp_table, CREDS, port=1161))
#print(get('192.168.77.2', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.3', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.4', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.5', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.6', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.7', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.8', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.9', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.10', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.11', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get('192.168.77.12', ['1.3.6.1.2.1.1.5.0'], CREDS))
#print(get_table('192.168.77.1', lldp_table, hlapi.CommunityData('TEST')))
print(get(TARGET, sys_stats, CREDS, port=TARGET_PORT))
#for row in get_table(TARGET, ifaces_stats, CREDS, port=TARGET_PORT):
#for row in get_table(TARGET, lldp_table, CREDS, port=TARGET_PORT):
#    print(row)
for row in get_table(TARGET, sys_stats, CREDS, port=TARGET_PORT):
    print(row)
    #for item in row:
    #    #print(item)
    #    oid, value = item[0].prettyPrint(), item[1].prettyPrint()
    #    #print(' = '.join([x.prettyPrint() for x in item]))
    #    #print(item[1].prettyPrint())
    #    #print(oid, '=', value)
    #    if oid.startswith('SNMPv2-SMI::iso.0.8802.1.1.2.1.4.2.1'):
    #        ip = oid.split('.')[-4:]    
    #        #print('.'.join(ip))

# Device
#print(get('172.17.0.2', ['1.3.6.1.2.1.1.5.0'], hlapi.CommunityData('TEST')))
## LLDP
#print(get('172.17.0.2', ['1.0.8802.1.1.2'], hlapi.CommunityData('TEST')))
#print(get_bulk('192.168.77.1', ['1.0.8802.1.1.2'], hlapi.CommunityData('TEST'), 10))
#print(get('192.168.77.1', ['1.0.8802.1.1.2.1'], hlapi.CommunityData('TEST')))
## LLDP REMOTE
#print(get('172.17.0.2', ['1.0.8802.1.1.2.1.4.1'], hlapi.CommunityData('TEST')))
#its = get_bulk('192.168.77.1', ['1.0.8802.1.1.2'], hlapi.CommunityData('TEST'), 1000)
#
#print(get('172.17.0.2', ['1.3.6.1.2.1.2.1.0'], hlapi.CommunityData('TEST')))


# Oids : https://cric.grenoble.cnrs.fr/Administrateurs/Outils/MIBS/?module=IF-MIB&fournisseur=ietf

# Ifaces Names
#ifHCInOctets: 1.3.6.1.2.1.31.1.1.1.6 (64-bit Octets in counter)
#ifHCOutOctets: 1.3.6.1.2.1.31.1.1.1.10 (64-bit Octets out counter)
#ifHCInUcastPkts:  1.3.6.1.2.1.31.1.1.1.7 (64-bit Packets in counter)
#ifHCOutUcastPkts:  1.3.6.1.2.1.31.1.1.1.11 (64-bit Packets out counter)
#ifHighSpeed: 1.3.6.1.2.1.31.1.1.1.15 (An estimate of the interface's current bandwidth in units of 1Mbps)

#its = get_bulk_auto('172.17.0.2', [
#its = get_bulk_auto('192.168.77.1', [
#    #'1.3.6.1.2.1.2.2.1.2 ',
#    #'1.3.6.1.2.1.31.1.1.1.6',
#    #'1.3.6.1.2.1.31.1.1.1.6',
#    #'1.3.6.1.2.1.31.1.1.1.10',
#    #'1.3.6.1.2.1.31.1.1.1.7',
#    #'1.3.6.1.2.1.31.1.1.1.11',
#    #'1.3.6.1.2.1.31.1.1.1.15',
#    #f'1.3.6.1.2.1.2.2.1.{mib}' for mib in range(1, 23)
#    f'1.0.8802.1.1.2.1.{mib}' for mib in range(1, 6)
#    #f'1.3.6.1.2.1.31.1.1.1.{mib}' for mib in range(1, 20)
#    #'1.3.6.1.2.1.2.2.1.5',
#    #'1.3.6.1.2.1.2.2.1.10',
#    #'1.3.6.1.2.1.2.2.1.11',
#    #'1.3.6.1.2.1.2.2.1.16',
#    #'1.3.6.1.2.1.2.2.1.17',
#    #], hlapi.CommunityData('TEST'), '1.3.6.1.2.1.2.1.0')
#    ], CREDS, '1.3.6.1.2.1.2.1.0')
# We print the results in format OID=value
#for it in its:
#    for k, v in it.items():
#        print("{0}={1}".format(k, v))
#        pass
#    # We leave a blank line between the output of each interface
#    print('')

