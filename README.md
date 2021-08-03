# Naasgul: Network as a Graph using lldp (and snmp for now ;-) ) [Work in Progress]

The goal here is to have an automated replacement to weathermap.  
That means that this project aims to output a map of the network topology and regularly poll the devices to show the links utilization.

(Was greatly inspired by a similar PoC project from `zerxen` at first)

## Quick Usage

- Virtual env with requirements
- export REPO_PATH=$(pwd)
- export LLDP_INIT_NODE_FQDN="node_name" (or LLDP_INIT_NODE_IP if there is no fqdn. LLDP_INIT_NODE_PORT if different snmp port)
- If scrapping must stop at a particular device : STOP_NODES_FQDN or STOP_NODES_IP
  - export STOP_NODES_FQDN=fqdn1,fqdn2
- cd frontend/ ; terser automapping-script.js -o public-html/automapping-script.min.js ; cd .. ; docker-compose up -V --force-recreate --always-recreate-deps --build --remove-orphans
- Browser to http://127.0.0.1:8080
