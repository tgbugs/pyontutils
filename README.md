# pyontutils
[![PyPI version](https://badge.fury.io/py/pyontutils.svg)](https://pypi.org/project/pyontutils/)
[![Build Status](https://travis-ci.org/tgbugs/pyontutils.svg?branch=master)](https://travis-ci.org/tgbugs/pyontutils)
[![Coverage Status](https://coveralls.io/repos/github/tgbugs/pyontutils/badge.svg?branch=master)](https://coveralls.io/github/tgbugs/pyontutils?branch=master)

python utilities for working with ontologies

## Installation
`pyontutils` is slowly approaching stability. You can obtain it and other related
packages from pypi and install them as you see fit (e.g. `pip install --user pyontutils`).
If you need a bleeding edge version I reccomend installing it into your environment
(virtual or otherwise) using `pip install --user --editable .[dev,test]` run from
from your local copy of this repo.

## Configuration
`pyontutils` makes use of 3 configuration files:
1. [~/.config/pyontutils/config.yaml](${HOME}/.config/pyontutils/config.yaml).
This file can be used to augment the varibles defined in [auth-config.py](./pyontutils/auth-config.py).
For more details about the config see the [orthauth guide](https://github.com/tgbugs/orthauth/blob/master/docs/guide.org).
2. [secrets.yaml](${HOME}/.config/orthauth/secrets.yaml) that you can put wherever
you want by editing the `auth-stores: secrets: path:` entry in [config.yaml](${HOME}/.config/pyontutils/config.yaml).
The file mode needs to be set to `0600` so that only you can read and write it.
It is also advisable to place it inside a folder with a mode set to `0700` since
some editors do not preserve file modes. `orthauth` will fail loudly if this happens.
3. [./nifstd/scigraph/curie_map.yaml](./nifstd/scigraph/curie_map.yaml) or
[~/.config/pyontutils/curie_map.yaml](${HOME}/.config/pyontutils/curie_map.yaml)
if a `pyontutils` git repository is not found. `pyontutils` will retrieve the
latest version of this file from github on first run if it cannot find a local copy.
The full list of locations that are searched for `curie_map.yaml` are specified in
[auth-config.py](./pyontutils/auth-config.py).  

If you are going to use the SciCrunch SciGraph production instance follow the
[instructions](https://github.com/SciCrunch/sparc-curation/blob/master/docs/setup.org#scigraph)
in the sparc curation setup guide to obtain an API key and put it in the right place.
In short you can set the key in your secrets file and specify the path to it in
[config.yaml](${HOME}/.config/pyontutils/config.yaml) under the =scigraph-api-key= variable.
Alternately you can set the key using the `SCICRUNCH_API_KEY` environment variable
(e.g., by running `export SCICRUNCH_API_KEY=$(cat path/to/my/apikey)`) or by whatever
means you prefer for managing your keys.

## Development Installation
From the directory that contains this readme run the following.
Refer to [.travis.yml](./.travis.yml) for full details.
```bash
for f in {librdflib,htmlfn,ttlser,.,neurondm,nifstd}; do pushd $f; pip install --user --pre --editable . ; popd; done
```
If you need even more information there is fairly exhaustive doccumentation
located in the sparc curation [setup doc](https://github.com/SciCrunch/sparc-curation/blob/master/docs/setup.org).

## Requirements
This repo requires PyPy3 or >=Python3.6.
See and setup.py and Pipfile for additional requirements.
`ontload` requires Java8 and >=maven3.3 in order to build SciGraph.
[parcellation](./nifstd/nifstd_tools/parcellation/__init__.py) requires [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/)
to be installed or you need to obtain the [atlases](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases) in
some other way. In order to build the packages required by this repo you will need
gcc (and toolchain) installed and will need to have the development packages for
`libxml` installed. To build the development dependencies you will also need the
development packages for `postgresql`, and `protobuf` installed on your system.
Building the documentation for the ontology requires `pandoc` and `emacs` along
with [orgstrap](https://github.com/tgbugs/orgstrap). See [.travis.yml](./.travis.yml)
for an example of how to bootstrap a working dev environment. Alternately see
[pyontutils-9999.ebuild](https://github.com/tgbugs/tgbugs-overlay/blob/master/dev-python/pyontutils/pyontutils-9999.ebuild) and
[nifstd-tools-9999.ebuild](https://github.com/tgbugs/tgbugs-overlay/blob/master/dev-python/nifstd-tools/nifstd-tools-9999.ebuild) in [tgbugs-overlay](https://github.com/tgbugs/tgbugs-overlay).

## Utility Scripts
pyontutils provides a set of scripts that are useful for maintaining and managing ontologies
using git, and making them available via SciGraph. Note that if you choose the development
installation option you will need to `ln -sT` the scripts to your preferred bin folder.
For the full list please see the [documentation](http://ontology.neuinfo.org/docs/docstrings.html).
1. [ttlfmt](./ttlser/ttlser/ttlfmt.py)
	Reserialize ontology files using deterministic turtle ([spec](./ttlser/docs/ttlser.md)).
2. [ontutils](./pyontutils/ontutils.py)
    Various useful and frequently needed commands for ontology processes as well as less frequent refactorings.
3. [ontload](./pyontutils/ontload.py)
	Load an ontology managed by git into SciGraph for easy deployment of services.
4. [qnamefix](./pyontutils/qnamefix.py)
    Set qnames based on the curies defined for a given ontology.
5. [necromancy](./pyontutils/necromancy.py)
    Find dead ids in an ontology and raise them to be owl:Classes again.
6. [scigraph-codegen](./pyontutils/scigraph_codegen.py)
	Generate a rest client against a SciGraph services endpoint.
7. [scig](./pyontutils/scig.py)
	Run queries against a SciGraph endpoint from the command line.
9. [graphml_to_ttl](./pyontutils/graphml_to_ttl.py)
	Convert yEd graphml files to ttl.
10. [ontree](./nifstd/nifstd_tools/ontree.py)
	Run a webserver to query and view hierarchies from the ontology.

## NIF-Ontology
Many of these scripts are written for working on the NIF standard ontology
found [here](https://github.com/SciCrunch/NIF-Ontology/).

## SciGraph
[scigraph_codegen.py](./pyontutils/scigraph_codegen.py) is code geneator for creating a python client library against a
[SciGraph](https://github.com/SciGraph/SciGraph) REST endpoint.
[scigraph_client.py](./pyontutils/scigraph_client.py) is the client library generated against the nif development scigraph instance.
[ontload](./pyontutils/ontload.py) can be used to load your ontology into SciGraph for local use.

## Building releases
See [release.org](./docs/release.org).
