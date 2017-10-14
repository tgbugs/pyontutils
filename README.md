# pyontutils
python utilities for working with ontologies

## Installation
In order to get good (deterministic) ttl serialziation from these tools you need to use my modified version of rdflib (pull request submitted to upstream with a bit of work left to do).
Follow the steps below in your preferred python environment. You may need to run `pip install wheel`.
1. `git clone https://github.com/tgbugs/rdflib.git && cd rdflib && python3 setup.py bdist_wheel && pip3 install --user --upgrade dist/rdflib*.whl`
2. If you have not done so already `git clone https://github.com/tgbugs/pyontutils`
3. `cd pyontutils && python3 setup.py bdist_wheel && pip3 install --user --upgrade dist/pyontutils*.whl`

Alternately, if want a development setup or need to use these tools for working directly
with the NIF-Ontology repo you can add this folder to your `PYTHONPATH` environment
variable using `export PYTHONPATH=PYTHONPATH:"$(pwd)"` from the location of this readme.

## Utility Scripts
pyontutils provides a set of 5 scripts that are useful for maintaining and managing ontologies
using git, and making them available via SciGraph. Note that if you choose the development
installation option you will need to `ln -sT` the scripts to your perferred bin folder.
1. [ttlfmt](pyontutils/ttlfmt.py)
	Reserialize an ontology file using deterministic turtle ([spec](docs/ttlser.md)).
2. [ontload](pyontutils/ontload.py)
	Load an ontology managed by git into SciGraph for easy deployment of services.
3. [qnamefix](pyontutils/qnamefix.py)
    Set qnames based on the curies defined for a given ontology.
4. [necromancy](pyontutils/necromancy.py)
    Find dead ids in an ontology and raise them to be owl:Classes again.
5. [scigraph-codegen](pyontutils/scigraph.py)
	Generate a rest client against a SciGraph services endpoint.
6. [scig](pyontutils/scig.py)
	Run queries against a SciGraph endpoint from the command line.
7. [ilxcli](pyontutils/ilxcli.py)
	Given an ontlogy file with temporary identifiers, get persistent, resolvable identifers
	for them from InterLex.

## Requirements
This repo requires Python3.6 or later. See setup.py for additional requirements.
ontload requires Java8 and >=maven3.3 in order to build SciGraph.
[parcellation.py](pyontutils/parcellation.py) requires [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/)
to be installed or you need to obtain the [atlases](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases) in
some other way.

## NIF-Ontology
Many of these scripts are written for working on the NIF standard ontology
found [here](https://github.com/SciCrunch/NIF-Ontology/).

## SciGraph
scigraph.py is code geneator for creating a python client library against a
[SciGraph](https://github.com/SciGraph/SciGraph) REST endpoint.
scigraph_client.py is the client library generated against the nif development scigraph instance.

## Neuron Types
If you have found your way to this repository because you are interested in using neuron-lang for
describing neuron types please see [this wiki page](https://github.com/SciCrunch/NIF-Ontology/wiki/Neurons).
To get started all you need to do is follow the installation instructions above and then include
`from pyontutils.neuron_lang import *` in your import statements. Please see the documentation for how to
[set up neuron-lang for jupyter notebooks](docs/neurons_notebook.md) and take a look at some
[examples of how to use neuron-lang to create new neurons](docs/NeuronLangExample.ipynb).
