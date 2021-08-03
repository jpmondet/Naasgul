# Automapping [Work in Progress]

(will eventually be in its own repo at some point in time)

The goal here is to have an automated replacement to weathermap.  
That means that this project aims to output a map of the network topology and regularly poll the devices to show the links utilization.

This is an ambitious goal but we'll see how far we can go...


## Some ideas to start with

- [done] Get devices/links datas by leveraging LLDP recursively starting from 1 or 2 devices (recursively because we can have some unknown devices on large snow flakes topologies)
- [done] Build a graph (networkx) from those datas
- [done] Generate an html/js output to show the graph on a browser with plotly

At this point, we have the net topology drawn.  
However, still nothing about link utilization.  
Plotly doesn't allow to display a table or something when hovering links (except by hiding transparent nodes on links... Not very satisfying.) and  
colorization depending on link utilization isn't doable either.

For next steps (particularly the third one), I'll have to reshape my long forgotten frontend skills :

- [done] Scrap devices interfaces utilization (snmp or ssh? ssh seems overkill for this. Telemetry is so badly supported by net vendors that it's not really a solution right now :-\ )
  - would be interesting to look at pushing solutions instead of pulling from devices
    - [2021-05] As a first easy-to-achieve solution, I wrote a nornir script to get interfaces stats from devices periodically.
      - Won't be very scalable tho. Will have to find a better solution quickly
    - [2021-05] Stats are then converted for easier frontend usage
- Store those datas on a DB (need at least 3 months storage)
- Depending on time frame chosen, average the values and colorize the links accordingly
  - This will have to be done in javascript or something alike
    - As a PoC and to validate the backend part, I'll use the html/js part of a similar project from `zerxen`.
      - Next step will be to write my own frontend depending on my needs

Or 

- Leverage datas already stored in something like cacti as weathermap did... (but clearly not an ideal solution since cacti doesn't have a proper API)

## Next steps

- (Re)Learn JS to rewrite the frontend.
- Have a better storage than raw files (https://github.com/couchbase-guides/python-sdk ? )
  - Mongodb will do now that I'm used to it thanks to another project
- For now, tests are done with IOU devices. Must test with something else (however, I can't really test other images on my laptop since they are waaaaaay heavier... :\ )




(How to name it ? Some interesting words : discovery topograph net auto mapping drawing graph lldp... )
( Naasgul - Network as a graph using lldp 
 Naaga  - Network as a graph automated
 Automated network discovery and graphing : 
 Drawing automatically network graph : Danet
 Graphing topology : Graphology
 Service Automatically Rendering Obscure Networks: Sauron
)


## Quick Usage

- Virtual env with requirements
- export REPO_PATH=$(pwd)
- export INIT_NODE_FQDN="node_name" (or INIT_NODE_IP if there is no fqdn. INIT_NODE_PORT if different snmp port)
- If scrapping must stop at a particular device : STOP_NODES_FQDN or STOP_NODES_IP
  - export STOP_NODES_FQDN=fqdn1,fqdn2
- cd frontend/ ; terser automapping-script.js -o public-html/automapping-script.min.js ; cd .. ; docker-compose up -V --force-recreate --always-recreate-deps --build --remove-orphans
- Browser to http://127.0.0.1:8080
