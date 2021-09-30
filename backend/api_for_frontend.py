#!/usr/bin/python3
"""
    Inputs :
        - graph_ct infos populated by lldp scrapping
        - interfaces infos populated by get_ifaces_stats that must be run regularly

    Expected output :
        (see in respective GET methods :
            graph,
            stats,
            neighborships
        )
"""
# pylint: disable=global-statement,global-variable-not-assigned,logging-fstring-interpolation

import logging
import re
from os import getenv
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from collections import defaultdict
from time import strftime, localtime, time
from secrets import compare_digest
from yaml import safe_load as yamload, YAMLError

from fastapi import Depends, FastAPI, HTTPException, status, Query, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.logger import logger
from pydantic import BaseModel, ValidationError

from db_layer import (
    get_stats_devices,
    get_all_nodes,
    get_nodes_by_patterns,
    get_all_links,
    get_links_by_patterns,
    get_links_device,
    get_utilizations_device,
    get_all_highest_utilizations,
    get_all_speeds,
    get_node,
    add_node,
    add_link,
    add_fake_iface_stats,
    add_fake_iface_utilization,
    delete_node,
    delete_link,
    disable_node,
)

app: FastAPI = FastAPI()

origins: List[str] = [
    "http://127.0.0.1",
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_USER: str = getenv("API_USER", "user")
API_PASS: str = getenv("API_PASS", "pass")

security: HTTPBasic = HTTPBasic()  # to do: Needs better security

CACHE: Dict[str, Any] = {}
CACHED_TIME: int = 300
TIME: int = int(time())
CACHED_TIMEOUT: Dict[str, bool] = {}


class Node(BaseModel):
    """Defines a node the 'fastapi' way
    to handle body in add_node calls"""

    name: str
    addr: Optional[str] = None
    groupx: Optional[int] = 11  # Group (function) of the node
    groupy: Optional[int] = 11  # Group (localisation) of the node
    image: Optional[str] = "router.png"
    system_description: Optional[str] = ""  # Usually contains model & OS version
    # (Number that drives its placement on the graph. 0 is on the left,
    # 10 (or even more) on the right)
    ifaces: Optional[List[str]] = None
    to_poll: Optional[bool] = True


class Neighbor(BaseModel):
    """Defines a node's neighbor the 'fastapi' way
    to handle body in add_node calls"""

    name: str
    addr: Optional[str] = None
    iface: str  # This is the actual iface of the class instance (neighbor)
    node_iface: str  # This iface is the one of the actual node of
    # which this class instance is the neighbor


class Link(BaseModel):
    """Defines a link between 2 nodes.
    Looks a lot like a neighbor definition"""

    name_node1: str
    iface_id_node1: str
    iface_descr_node1: Optional[str]
    name_node2: str
    iface_id_node2: str
    iface_descr_node2: Optional[str]


class Fabric(BaseModel):
    """Defines an entire fabric"""

    nodes: List[Node]
    links: List[Link]


def check_credentials(
    credentials: HTTPBasicCredentials = Depends(security),
) -> HTTPBasicCredentials:
    """Checks credentials on api calls"""
    correct_username: bool = compare_digest(credentials.username, API_USER)
    correct_password: bool = compare_digest(credentials.password, API_PASS)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


def get_from_db_or_cache(
    element: str, func: Optional[Callable[..., Any]] = None, query: Union[str, List[str]] = ""
) -> Any:
    """Cache most db calls if they are not already cached.
    Also handles a timeout to retrieve from db from time to time"""
    global CACHE, CACHED_TIMEOUT

    timeout: bool = False
    if CACHED_TIMEOUT.get(element):
        timeout = CACHED_TIMEOUT[element]

    if not CACHE.get(element) or timeout:
        if not func:
            return None
        logger.error(f"Oops, {element} not in cache, calling db")
        if query:
            CACHE[element] = func(query)
        else:
            CACHE[element] = func()
        CACHED_TIMEOUT[element] = False

    return CACHE[element]


def background_time_update() -> None:
    """Updates timeout so we know if we
    have to discard cached datas and retrieve from db again"""
    global CACHED_TIMEOUT, TIME
    now: int = int(time())
    # logger.error(f"bgtimeupd: {now}, {TIME}, {CACHED_TIMEOUT}")
    if now - TIME > CACHED_TIME:
        TIME = now
        for elem in CACHED_TIMEOUT:
            CACHED_TIMEOUT[elem] = True
    # logger.error(f"bgtimeupdEnd: {now}, {TIME}, {CACHED_TIMEOUT}")


def add_static_node_to_db(node: Node, neigh_infos: Optional[List[Neighbor]] = None) -> None:
    """Some nodes can't be scrapped with lldp so this function allows to add
    static nodes directly to db"""

    add_node(node.name, node.groupx, node.groupy, node.image, to_poll=False)

    if neigh_infos:
        for neigh in neigh_infos:
            if not neigh.name and neigh.addr:
                neigh.name = neigh.addr
            if get_node(neigh.name):
                add_link(node.name, neigh.name, neigh.node_iface, neigh.iface)
                add_link(neigh.name, node.name, neigh.iface, neigh.node_iface)

                add_fake_iface_stats(node.name, neigh.node_iface)
                add_fake_iface_utilization(node.name, neigh.node_iface)

                add_fake_iface_stats(neigh.name, neigh.iface)
                add_fake_iface_utilization(neigh.name, neigh.iface)
            else:
                logger.error("Node's neighbor doesn't exist, we can't add the link")

    elif node.ifaces:
        for iface in node.ifaces:
            add_fake_iface_stats(node.name, iface)
            add_fake_iface_utilization(node.name, iface)


def try_to_deduce_grouping(groups_known: Dict[str, int], node_name: str) -> Tuple[int, int]:
    """Tries to find to which groups the node should be affected
    groupx is conditioned by the function of the device (if it's a core device
    for example) and groupy is conditioned by its localisation.

    Depending on your device naming, the regex should be modified"""

    # Exemple for a device named sw1.iou
    # We assume that 'sw' is the function and '1' its localisation (yeah
    # not really a localisation but well, it's an example ;-) )
    regex_pattern: re.Pattern[str] = re.compile(  # pylint: disable=unsubscriptable-object
        "^([a-z]{2})([0-9]+).*", re.IGNORECASE
    )  # pylint: disable=unsubscriptable-object
    matched: Optional[re.Match[str]] = regex_pattern.match(
        node_name
    )  # pylint: disable=unsubscriptable-object
    if not matched:
        # It may be a "fake" node with a "fake" name:
        regex_pattern = re.compile("^fake_device_stage([0-9]+)_([0-9]+)$", re.IGNORECASE)
        matched = regex_pattern.match(node_name)
        if matched:
            # matched.group(2) could be used but it doesn't make sense right now since
            # d3.js 'force' handle it for those test devices which are at the 'same localisation'
            return (int(matched.group(1)), 1)
        # Unknown device, we push it to the right end of the graph
        return (7, 1)
    device_function: str = matched.group(1)
    device_localisation: str = matched.group(2)

    groupx: int = 1
    groupy: int = 1
    if not groups_known:
        groups_known["sw"] = 1
        groups_known["rtr"] = 2
        groups_known["groupy"] = 1

    try:
        groupx = groups_known[device_function]
    except KeyError:
        # Unknown device function
        return (7, 1)

    try:
        groupy = groups_known[device_localisation]
    except KeyError:
        groupy = groups_known["groupy"]
        groups_known[device_localisation] = groupy
        groups_known["groupy"] += 1

    return (groupx, groupy)


@app.get("/graph")
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def get_graph(dpat: Optional[List[str]] = Query(None)) -> Dict[str, List[Dict[str, Any]]]:
    """
            "links": [
                {
                    "highest_utilization": 0,
                    "source": "deviceName",
                    "source_interfaces": [
                        "Ethernet0/0"
                    ],
                    "speed": "1",
                    "target": "deviceName-2",
                    "target_interfaces": [
                        "Ethernet0/0"
                    ],
                },
                {}],
            "nodes": [
                    {
                        group: 1,
                        id: "deviceName",
                        image: "default.png",
                    },
                    {}]
            }


    Graph shouldn't be updated very much
    However, "highest_utilization" must be updated each time the API is called
     with fresh "stats" values
    """

    background_time_update()
    # logger.error(f"Caching timeout : {TIMEOUT}")

    nodes: List[Dict[str, Any]] = []
    if isinstance(dpat, list):
        nodes = list(get_from_db_or_cache(f"nodes{str(dpat)}", get_nodes_by_patterns, dpat))
    else:
        nodes = get_from_db_or_cache("nodes", get_all_nodes)

    groups: Dict[str, int] = {}

    for node in nodes:
        if (
            not node.get("groupx")
            or not node.get("groupy")
            or (node["groupx"] == 11 and node["groupy"] == 11)
        ):

            node["groupx"], node["groupy"] = try_to_deduce_grouping(groups, node["device_name"])

        node["id"] = node["device_name"]
        node["image"] = "router.png"

        try:
            del node["_id"]  # removing mongodb objectId
        except KeyError:
            pass

    formatted_links: Dict[str, Any] = {}
    if dpat:
        formatted_links = get_from_db_or_cache(f"formatted_links{dpat}")
    else:
        formatted_links = get_from_db_or_cache("formatted_links")
    highest_uses: Dict[str, int] = defaultdict(int)
    if not formatted_links:
        links: List[Dict[str, Any]] = []
        if isinstance(dpat, list):
            links = get_from_db_or_cache(f"links{str(dpat)}", get_links_by_patterns, dpat)
        else:
            links = get_from_db_or_cache("links", get_all_links)
        sorted_links: List[Dict[str, Any]] = sorted(
            links, key=lambda d: (d["device_name"], d["neighbor_name"])
        )
        formatted_links = {}

        utilizations: Dict[str, int] = get_from_db_or_cache(
            "utilizations", get_all_highest_utilizations
        )
        speeds: Dict[str, int] = get_from_db_or_cache("speeds", get_all_speeds)

        # logger.error("Utilizations: " + str(utilizations))
        # logger.error("Speeds: " + str(speeds))

        # start_format_timer = time()

        logger.error(f"Nb links to format:{len(sorted_links)}")
        for link in sorted_links:
            device: str = link["device_name"]
            iface: str = str(link["iface_name"])
            neigh: str = link["neighbor_name"]
            if isinstance(dpat, list):
                if not any(device_pattern in neigh for device_pattern in dpat):
                    continue
            neigh_iface: str = str(link["neighbor_iface"])
            if not device or not iface or not neigh or not neigh_iface:
                # Discard possible null ifaces
                logger.error(f"WARNING: Link discarded : {link}")
                continue

            id_link: str = device + neigh
            id_link_neigh: str = neigh + device

            try:
                speed: int = speeds[device + iface]  # "speed" in snmp terms
                # is actually the max speed of the iface
                speed = speed * 1000000  # Convert speed to bits
                highest_utilization: int = utilizations[device + iface]
                percent_highest: float = highest_utilization / speed * 100
                if percent_highest > 100:
                    print(device, iface, speed, highest_utilization, percent_highest)
                    percent_highest = 0
            except KeyError:
                speed = 1000000  # Can't determine speed
                highest_utilization = 0  # Can't determine utilization
                percent_highest = 0.0
                logger.error(f"Cant find speed for {device+iface} in {speeds}")

            if not formatted_links.get(id_link) and not formatted_links.get(id_link_neigh):

                f_link: Dict[str, Any] = {
                    "highest_utilization": percent_highest,
                    "source": device,
                    "source_interfaces": [iface],
                    "speed": speed,
                    "target": neigh,
                    "target_interfaces": [neigh_iface],
                    "linknum": 1,
                }
                formatted_links[id_link] = f_link
                highest_uses[id_link] = highest_utilization
            else:
                if formatted_links.get(id_link_neigh):
                    id_link, id_link_neigh = id_link_neigh, id_link
                    iface, neigh_iface = neigh_iface, iface

                if iface not in formatted_links[id_link]["source_interfaces"]:
                    formatted_links[id_link]["source_interfaces"].append(iface)
                else:
                    continue
                if neigh_iface not in formatted_links[id_link]["target_interfaces"]:
                    formatted_links[id_link]["target_interfaces"].append(neigh_iface)
                else:
                    continue

                # Since 1 (visual) link will aggregate multiple (actual) links
                # we recalculate utilization/speed for the aggregated (visual) link
                highest_uses[id_link] += highest_utilization
                formatted_links[id_link]["speed"] = formatted_links[id_link]["speed"] + speed

                highest_utilization = highest_uses[id_link]
                speed = formatted_links[id_link]["speed"]
                percent_highest = highest_utilization / speed * 100
                if percent_highest > 100:
                    print(device, iface, speed, highest_utilization, percent_highest)
                    percent_highest = 0

                formatted_links[id_link]["highest_utilization"] = percent_highest

                # If we want to dissociate agg link into multilinks
                # We have to handle "linknum"
                # But for clarity on large topologies, this is commented out
                # try:
                #    f_link_2 = formatted_links[id_link].copy()
                #    linknum = len(f_link_2["source_interfaces"])
                #    id_link_2 = id_link + str(linknum)
                # except KeyError:
                #    f_link_2 = formatted_links[id_link_neigh].copy()
                #    linknum = len(f_link_2["source_interfaces"])
                #    id_link_2 = id_link_neigh + str(linknum)

                # if linknum > 1:
                #    f_link_2["linknum"] = linknum
                #    f_link_2["highest_utilization"] = percent_highest
                #    f_link_2["speed"] = speed
                #    formatted_links[id_link_2] = f_link_2

        # logger.error(formatted_links)
        # logger.error(f'Format links End: {time() - start_format_timer}')

        global CACHE, CACHED_TIMEOUT
        if dpat:
            CACHE[f"formatted_links{dpat}"] = formatted_links
        else:
            CACHE["formatted_links"] = formatted_links
        CACHED_TIMEOUT["formatted_links"] = False

    return {"nodes": nodes, "links": list(formatted_links.values())}


@app.get("/stats/")
def stats(  # pylint: disable=too-many-locals
    devices: List[str] = Query(None),
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    {
        "ifDescr": "Ethernet0/0",
        "index": 1,
        "stats": [
            {
                "InSpeed": 0,
                "OutSpeed": 0,
                "time": "2020-12-24 23:59:59"
            },
        ]
    }
    """
    background_time_update()

    if isinstance(devices, list):
        # Validate incoming query
        for device in devices:
            if not isinstance(device, str):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
            # if len(device) != 7 and len(device) != 8:
            #    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
            # if "iou" not in device:
            #    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        # Not todo anymore :P if LEN stats_by_device = 2
        # -> find ifaces between the 2 devices to return only that
        # Would be needed if we disaggregated links again

        stats_by_device: Dict[str, Any] = get_from_db_or_cache(f"stats_by_device_{devices}")

        if not stats_by_device:

            stats_by_device = {}

            sorted_stats: List[Dict[str, Any]] = sorted(
                get_stats_devices(devices),
                key=lambda d: (d["device_name"], d["iface_name"], d["timestamp"]),
            )
            prev_inbits: int = 0
            prev_outbits: int = 0
            prev_timestamp: int = 0
            for stat in sorted_stats:
                dname: str = stat["device_name"]
                # ifname = stat["iface_name"].replace("Ethernet", "Et")
                ifname: str = stat["iface_name"]
                dbtime: int = stat["timestamp"]
                inttimestamp: int = int(dbtime)
                timestamp: str = strftime("%y-%m-%d %H:%M:%S", localtime(inttimestamp))
                stat_formatted: Dict[str, Any] = {"InSpeed": 0, "OutSpeed": 0, "time": timestamp}
                inbits: int = int(stat["in_bytes"]) * 8
                outbits: int = int(stat["out_bytes"]) * 8
                # This iface wasn't in the struct.
                # We add default infos (and speed to 0 since
                # we don't know at how much speed it was before)
                if not stats_by_device.get(dname):
                    stats_by_device[dname] = {
                        ifname: {"ifDescr": ifname, "index": ifname, "stats": [stat_formatted]}
                    }
                elif not stats_by_device[dname].get(ifname):
                    stats_by_device[dname][ifname] = {
                        "ifDescr": ifname,
                        "index": ifname,
                        "stats": [stat_formatted],
                    }
                else:
                    # Must calculate speed. Not just adding in_bytes or it will only increase.
                    # prev_date = stats_by_device[dname][ifname]["stats"][-1]["time"]
                    # prev_timestamp: int = int(
                    #    datetime.strptime(prev_date, "%y-%m-%d %H:%M:%S").timestamp()
                    # )

                    interval: int = inttimestamp - prev_timestamp
                    if interval > 0:
                        in_speed: int = inbits - prev_inbits
                        in_speed = in_speed if in_speed >= 0 else -in_speed
                        out_speed: int = outbits - prev_outbits
                        out_speed = out_speed if out_speed >= 0 else -out_speed
                        stat_formatted["InSpeed"] = int(in_speed / interval)
                        stat_formatted["OutSpeed"] = int(out_speed / interval)

                    stats_by_device[dname][ifname]["stats"].append(stat_formatted)

                prev_inbits = inbits
                prev_outbits = outbits
                prev_timestamp = inttimestamp

            global CACHE, CACHED_TIMEOUT
            CACHE[f"stats_by_device_{devices}"] = stats_by_device
            CACHED_TIMEOUT[f"stats_by_device_{devices}"] = False

        return stats_by_device
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


@app.get("/neighborships/")
# Leveraging query string validation built in FastApi to avoid having multiple IFs
def neighborships(
    device: str = Query(..., min_length=1, max_length=100)  # , regex="^[a-z]{2,3}[0-9]{1}.iou$")
) -> List[Dict[str, str]]:
    """
    {
                    "deviceName":[
                    "local_intf": "Ethernet0/0",
                    "neighbor": "deviceName2",
                    "neighbor_intf": "Ethernet0/0",
                ],
                "deviceName2" :[],
    }
    """
    background_time_update()

    if not isinstance(device, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    neighs: List[Dict[str, str]] = get_from_db_or_cache(f"neighs_{device}")

    if not neighs:

        # We use a dict to prevent duplicates
        # The end goal is to return only its values, not keys
        neighs_dict: Dict[str, Dict[str, str]] = {}

        for link in get_links_device(device):

            device1: str = link["device_name"]
            device2: str = link["neighbor_name"]
            iface1: str = link["iface_name"]
            iface2: str = link["neighbor_iface"]

            # The device queried can be seen as "device_name" or as "neighbor_name" depending
            # on the point of view
            if device != link["device_name"]:
                device1, device2 = device2, device1
                iface1, iface2 = iface2, iface1

            id_link: str = f"{device1}{device2}{iface1}{iface2}"
            if neighs_dict.get(id_link):
                continue

            neighs_dict[id_link] = {
                "local_intf": iface1,
                "neighbor": device2,
                "neighbor_intf": iface2,
            }

        neighs = list(neighs_dict.values())
        global CACHE, CACHED_TIMEOUT
        CACHE[f"neighs_{device}"] = neighs
        CACHED_TIMEOUT[f"neighs_{device}"] = False

    return neighs


@app.post("/delete_node_by_fqdn")
def delete_node_by_fqdn(
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
    node_name_or_ip: str = Query(
        ..., min_length=4, max_length=50
    ),  # , regex="^[a-z]{2,3}[0-9]{1}.iou$")
) -> Dict[str, str]:
    """Removes a node from the DB (Can't do it automatically since we can't know if the node
    is just temporary unreachable & now there are also static nodes)"""
    if not isinstance(node_name_or_ip, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    delete_node(node_name_or_ip)

    return {"response": "Ok"}


@app.post("/add_static_node")
def add_static_node(
    node: Node,
    node_neighbors: Optional[List[Neighbor]] = None,
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, str]:
    """Adds a node to the DB (static nodes that aren't lldp-discoverable)
    (see in scripts/add_non_lldp_device.py for the original script, it may be easier to use
    in some cases)

    Exple of simplest call :
    curl -X POST --user u:p -H "Content-type: application/json" \
          http://127.0.0.1/api/add_static_node \
              -d '{ "node": { "name": "test", "ifaces": ["1/1","1/2"]} }'"""

    if not node.name and not node.addr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please specify at least node name or node ip",
        )

    if not node.name and node.addr:
        node.name = node.addr

    if not isinstance(node.ifaces, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Node with no ifaces")

    add_static_node_to_db(node, node_neighbors)

    return {"response": "Ok"}


@app.get("/node/{node}")
def get_node_infos(
    node: str,
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, Any]:
    """Gets all infos about a specific node (useful
    for debugging)"""

    node_infos: Dict[str, Any] = {
        "node_details": get_node(node),
        "node_neighs": list(get_links_device(node)),
        "node_stats": get_stats_devices([node]),
        "node_links_utilizations": get_utilizations_device(node),
    }

    logger.error(node_infos)

    return node_infos


@app.post("/nodes")
def add_nodes_list_to_poll(
    nodes: List[str],
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, str]:
    """Adds a list of nodes (that are discoverables with lldp) to the db.

    Exple of simplest call :
    curl -X POST --user u:p -H "Content-type: application/json" \
          http://127.0.0.1/api/nodes \
              -d '["node1", "node2", "node3"]'"""

    for node in nodes:
        add_node(node)

    return {"response": "Ok"}


@app.delete("/nodes")
def delete_nodes_list(
    nodes: List[str],
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, str]:
    """Deletes a list of nodes (that are discoverables with lldp) to the db.

    Exple of simplest call :
    curl -X DELETE --user u:p -H "Content-type: application/json" \
          http://127.0.0.1/api/nodes \
              -d '["node1", "node2", "node3"]'"""

    for node in nodes:
        delete_node(node)

    return {"response": "Ok"}


@app.post("/links")
def add_links(
    links: List[Link],
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, str]:
    """Adds a list of links to the db.

    Exple of simplest call :
    curl -X POST --user u:p -H "Content-type: application/json" \
          http://127.0.0.1/api/links \
              -d '[
                   {
                     "name_node1": "node1",
                     "name_node2": "node2",
                     "iface_id_node1": "1/1",
                     "iface_id_node2": "2/2"
                    }
                   ]'"""

    for link in links:
        add_link(
            link.name_node1,
            link.name_node2,
            link.iface_id_node1,
            link.iface_id_node2,
            link.iface_descr_node1,
            link.iface_descr_node2,
        )
    return {"response": "Ok"}


@app.delete("/links")
def delete_links(
    links: List[Link],
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, str]:
    """Deletes a list of links to the db.

    Exple of simplest call :
    curl -X DELETE --user u:p -H "Content-type: application/json" \
          http://127.0.0.1/api/links \
              -d '[
                   {
                     "name_node1": "node1",
                     "name_node2": "node2",
                     "iface_id_node1": "1/1",
                     "iface_id_node2": "2/2"
                    }
                   ]'"""

    for link in links:
        delete_link(
            link.name_node1,
            link.name_node2,
            link.iface_id_node1,
            link.iface_id_node2,
        )
    return {"response": "Ok"}


@app.post(
    "/fabric",
    openapi_extra={
        "requestBody": {
            "content": {"application/x-yaml": {"schema": Fabric.schema()}},
            "required": True,
        },
    },
)
async def add_fabric(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, str]:
    """Add an entire fabric via a yaml file
    with a call like :
        curl -X POST --data-binary @payload.yaml \
            -H "Content-type: application/x-yaml" http://127.0.0.1/api/fabric
    """
    raw_body = await request.body()
    try:
        data = yamload(raw_body)
    except YAMLError as yamlerr:
        raise HTTPException(status_code=400, detail="Invalid YAML") from yamlerr
    try:
        fabric = Fabric.parse_obj(data)
    except ValidationError as validationerr:
        raise HTTPException(status_code=422, detail=validationerr.errors()) from validationerr

    for node in fabric.nodes:
        add_node(
            node.name, node.groupx, node.groupy, node.image, node.system_description, node.to_poll
        )
    for link in fabric.links:
        add_link(
            link.name_node1,
            link.name_node2,
            link.iface_id_node1,
            link.iface_id_node2,
            link.iface_descr_node1,
            link.iface_descr_node2,
        )
    return {"response": "Ok"}


@app.delete(
    "/fabric",
    openapi_extra={
        "requestBody": {
            "content": {"application/x-yaml": {"schema": Fabric.schema()}},
            "required": True,
        },
    },
)
async def delete_fabric(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, str]:
    """Delete an entire fabric via a yaml file
    with a call like :
        curl -X DELETE --data-binary @payload.yaml \
            -H "Content-type: application/x-yaml" http://127.0.0.1/api/fabric
    """
    raw_body = await request.body()
    try:
        data = yamload(raw_body)
    except YAMLError as yamlerr:
        raise HTTPException(status_code=422, detail="Invalid YAML") from yamlerr
    try:
        fabric = Fabric.parse_obj(data)
    except ValidationError as validationerr:
        raise HTTPException(status_code=422, detail=validationerr.errors()) from validationerr

    for node in fabric.nodes:
        delete_node(node.name)
    return {"response": "Ok"}


@app.post("/disable_poll_nodes_list")
def disable_poll_nodes_list(
    nodes: List[str],
    credentials: HTTPBasicCredentials = Depends(
        check_credentials
    ),  # pylint: disable=unused-argument
) -> Dict[str, str]:
    """Disable (snmp) polling on a list of nodes.

    Exple of simplest call :
    curl -X GET --user u:p -H "Content-type: application/json" \
          http://127.0.0.1/api/disable_poll_nodes_list \
              -d '["node1", "node2", "node3"]'"""

    for node in nodes:
        disable_node(node)

    return {"response": "Ok"}


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    """Simple func to let kubernetes know that the api is alive"""

    # Should maybe test access to the DB before answering 'OK'

    return {"response": "Ok"}


gunicorn_logger = logging.getLogger("gunicorn.info")
logger.handlers = gunicorn_logger.handlers
logger.setLevel(gunicorn_logger.level)
