# Naasgul: Network as a Graph using lldp
(and snmp for now ;-) )

# /!\ [Work in Progress] /!\

The goal here is to have an automated replacement to weathermap.  
That means that this project aims to output a map of the network topology and regularly poll the devices to show the links utilization.

(Was greatly inspired by a similar PoC project from `zerxen` at first)

## Quick Non-prod Usage

- `python3 -m venv venv`
- `. venv/bin/activate`
- `python3 -m pip install -r requirements-dev.txt`
- `cd frontend ; nodeenv --without-ssl nodeenv ; . nodeenv/bin/activate ; npm install terser -g ; npm install html-minifier-terser -g ; cd ..`
- `export REPO_PATH=$(pwd)`
- export LLDP_INIT_NODE_FQDN="node_name" (or LLDP_INIT_NODE_IP if there is no fqdn. LLDP_INIT_NODE_PORT if different snmp port)
- If scrapping must stop at a particular device : LLDP_STOP_NODES_FQDN or LLDP_STOP_NODES_IP
  - export LLDP_STOP_NODES_FQDN=fqdn1,fqdn2
- Those LLDP variables can be specified in a `.env` file if using `docker-compose`
- `cd frontend/ ; . nodeenv/bin/activate ; terser automapping-script.js -o public-html/automapping-script.min.js ; html-minifier-terser --collapse-whitespace --remove-comments --remove-optional-tags --remove-redundant-attributes --remove-script-type-attributes --remove-tag-whitespace --use-short-doctype --minify-css true --minify-js true index.html -o public-html/index.html ;  cd .. ; docker-compose up -V --force-recreate --always-recreate-deps --build --remove-orphans`
- Browser to http://127.0.0.1:8080

### No devices to tests ? Add fake datas

You can fake a fabric with `tests/add_fake_data_to_db.py` script.

For example, a 5-stage fabric with 12 devices can be generated with : `python3 tests/add_fake_data_to_db.py -n 15 -s 5`

Interfaces will have random bytes values (but for one timestamp only).

If you want to add more stats to interfaces, you can add the flag `-a 1` (so interfaces' graphs will be a lil' more than just a point ;-) )

By throwing some `-a 1`, it should get you something like this :

![alt text](https://github.com/jpmondet/Naasgul/raw/master/resources/sample_5_stages_fabric.png "Sample 5-stage fabric")

With graphs like :

![alt text](https://github.com/jpmondet/Naasgul/raw/master/resources/sample_iface_graph.png "Sample iface graph")

## Play gitlab-ci locally

`ci_tests.sh` allows to play Gitlab-ci jobs locally for development purposes.

Simply run `./scripts/ci_tests.sh` and it should run.
