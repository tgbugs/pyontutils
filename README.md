# pyontutils
python utilities for working with ontologies

## Installation
You can run `python setup.py bdist_wheel && pip install dist/pyontutils*.whl` to build and install
a package version of this repository, however at the moment a number of imports may be broken.
Alternately you can simply add the parent folder for this repository to your `PYTHONPATH` eg
using `export PYTHONPATH=PYTHONPATH:"$(dirname $(pwd))"` from the location of this readme.

## Requirements
This repo requires Python3.5 or later. See setup.py for the additional requirements.

## NIF-Ontology
Many of these scripts are written for working on the NIF standard ontology
found [here](https://github.com/SciCrunch/NIF-Ontology/).

## scigraph
scigraph.py is code geneator for creating a python client library against a
[SciGraph](https://github.com/SciGraph/SciGraph) REST endpoint.
scigraph_client.py is the client library generated against the nif development scigraph instance.
