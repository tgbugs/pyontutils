# pyontutils
python utilities for working with ontologies

## Requirements
This repo requires Python3.6 or later.
See Pipfile for additional requirements.
ontload requires Java8 and >=maven3.3 in order to build SciGraph.
[parcellation.py](pyontutils/parcellation.py) requires [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/)
to be installed or you need to obtain the [atlases](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases) in
some other way. In order to build all the packages required by this repo you will need
gcc (and toolchain) installed and will need to have the development packages for
`postgresql`, `libxml`, and `protobuf`  installed on your system.

## Installation
The easiest way to install pyontutils is to use pipenv. It makes it easy to manage
specific version of packages needed by pyontutils. For example in order to get good
(deterministic) ttl serialization from these tools you need to use my modified version
of rdflib (see https://github.com/RDFLib/rdflib/pull/649 and https://github.com/RDFLib/rdflib/pull/793).
[Pipenv](https://pipenv.readthedocs.io/en/latest/#install-pipenv-today) makes it easier
to accomplish this.

1. In your preferred folder `git clone https://github.com/tgbugs/pyontutils.git`
2. `cd pyontutils`
3. `pipenv install --skip-lock`. Note that `mysql-connector` (aka `mysql-connector-python`) often cannot find the
files it needs to build.  When installing pass them in as environment variables (you may need to adjust
exact paths for your system). `MYSQLXPB_PROTOBUF_INCLUDE_DIR=/usr/include/google/protobuf MYSQLXPB_PROTOBUF_LIB_DIR=/usr/lib64 MYSQLXPB_PROTOC=/usr/bin/protoc pipenv install --skip-lock`
4. `pipenv shell` to enter the virtual environment where everything should work.

Alternately, if manage your packages via another system you can create a development setup
by adding this folder to your `PYTHONPATH` environment variable using
`export PYTHONPATH=PYTHONPATH:"$(pwd)"` from the location of this readme.
If you use a development setup you will need to create symlinks described below.

## Utility Scripts
pyontutils provides a set of scripts that are useful for maintaining and managing ontologies
using git, and making them available via SciGraph. Note that if you choose the development
installation option you will need to `ln -sT` the scripts to your perferred bin folder.
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
8. [ilxcli](pyontutils/ilxcli.py)
	Given an ontlogy file with temporary identifiers, get persistent, resolvable identifers
	for them from InterLex.
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

## Neuron Types
If you have found your way to this repository because you are interested in using neuron-lang for
describing neuron types please see [this wiki page](https://github.com/SciCrunch/NIF-Ontology/wiki/Neurons).
To get started all you need to do is follow the installation instructions above and then include
`from pyontutils.neuron_lang import *` in your import statements. Please see the documentation for how to
[set up neuron-lang for jupyter notebooks](docs/neurons_notebook.md) and take a look at some
[examples of how to use neuron-lang to create new neurons](docs/NeuronLangExample.ipynb).
