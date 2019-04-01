# pyontutils
[![PyPI version](https://badge.fury.io/py/pyontutils.svg)](https://pypi.org/project/pyontutils/)
[![Build Status](https://travis-ci.org/tgbugs/pyontutils.svg?branch=master)](https://travis-ci.org/tgbugs/pyontutils)
[![Coverage Status](https://coveralls.io/repos/github/tgbugs/pyontutils/badge.svg?branch=master)](https://coveralls.io/github/tgbugs/pyontutils?branch=master)

python utilities for working with ontologies

## Requirements
This repo requires PyPy3 or >=Python3.6.
See and setup.py and Pipfile for additional requirements.
`ontload` requires Java8 and >=maven3.3 in order to build SciGraph.
[parcellation.py](pyontutils/parcellation.py) requires [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/)
to be installed or you need to obtain the [atlases](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases) in
some other way. In order to build the packages required by this repo you will need
gcc (and toolchain) installed and will need to have the development packages for
`libxml` installed. To build the development dependencies you will also need the
development packages for `postgresql`, and `protobuf` installed on your system.
Building the documentation for the ontology requires `pandoc` and `emacs` along
with [orgstrap](https://github.com/tgbugs/orgstrap). See [.travis.yml](.travis.yml)
for an example of how to bootstrap a working dev environment.

## Installation
Pyontutils is slowly approaching stability. You can obtain it and other related
packages from pypi and install them as you see fit (e.g. `pip install --user pyontutils`).
If you need a bleeding edge version I reccomend installing into whatever environment
(virtual or otherwise) using `pip install --user --editable .[dev,test]`
from your local copy of this repo.

## Development Installation
From the directory that contains this readme run the following.
Refer to [.travis.yml](.travis.yml) for full details.
```bash
for f in {librdflib,htmlfn,ttlser,.,neurondm,nifstd}; do pushd $f; pip install --user --pre --editable . ; popd; done
```
If you need even more information there is fairly exhaustive doccumentation
located in the sparc curation [setup doc](https://github.com/SciCrunch/sparc-curation/blob/master/docs/setup.org).

## Utility Scripts
pyontutils provides a set of scripts that are useful for maintaining and managing ontologies
using git, and making them available via SciGraph. Note that if you choose the development
installation option you will need to `ln -sT` the scripts to your preferred bin folder.
For the full list please see the [documentation](http://ontology.doc/pyontutils/docstrings.html).
1. [ttlfmt](pyontutils/ttlfmt.py)
	Reserialize ontology files using deterministic turtle ([spec](docs/ttlser.md)).
2. [ontutils](pyontutils/ontutils.py)
    Various useful and frequently needed commands for ontology processes as well as less frequent refactorings.
3. [ontload](pyontutils/ontload.py)
	Load an ontology managed by git into SciGraph for easy deployment of services.
4. [qnamefix](pyontutils/qnamefix.py)
    Set qnames based on the curies defined for a given ontology.
5. [necromancy](pyontutils/necromancy.py)
    Find dead ids in an ontology and raise them to be owl:Classes again.
6. [scigraph-codegen](pyontutils/scigraph.py)
	Generate a rest client against a SciGraph services endpoint.
7. [scig](pyontutils/scig.py)
	Run queries against a SciGraph endpoint from the command line.
9. [graphml_to_ttl](pyontutils/graphml_to_ttl.py)
	Convert yEd graphml files to ttl.
10. [ontree](pyontutils/ontree.py)
	Run a webserver to query and view hierarchies from the ontology.

## NIF-Ontology
Many of these scripts are written for working on the NIF standard ontology
found [here](https://github.com/SciCrunch/NIF-Ontology/).

## SciGraph
scigraph.py is code geneator for creating a python client library against a
[SciGraph](https://github.com/SciGraph/SciGraph) REST endpoint.
scigraph_client.py is the client library generated against the nif development scigraph instance.
[ontload](pyontutils/ontload.py) can be used to load your ontology into SciGraph for local use.

## Building releases
Test sdist packaging
``` bash
for f in {htmlfn,ttlser,.,neurondm,nifstd}; do pushd $f; python setup.py sdist; popd; done
```
Build wheels from the sdist NOT straight from the repo because wheels
ignore the manifest file. Make sure to clean any previous builds first.
``` bash
for f in {htmlfn,ttlser,neurondm,nifstd}; do
pushd $f/dist;
tar xvzf *.tar.gz;
pushd $f*/;
python setup.py bdist_wheel;
mv dist/*.whl ../;
popd;
rm ./$f*/ -r;
popd;
done
```
