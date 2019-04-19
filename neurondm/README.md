# neurondm
[![PyPI version](https://badge.fury.io/py/neurondm.svg)](https://pypi.org/project/neurondm/)

A data model for neuron types.

## Neuron Types
If you have found your way to this repository because you are interested in using neuron-lang for
describing neuron types please see
[this introduction](http://github.com/SciCrunch/NIF-Ontology/blob/master/docs/Neurons.md)
to the general approach.  To get started all you need to do is follow the installation instructions above and then include
`from neurondm.lang import *` in your import statements. Please see the documentation for how to
[set up neuron-lang for jupyter notebooks](docs/neurons_notebook.md) and take a look at some
[examples of how to use neuron-lang to create new neurons](./docs/NeuronLangExample.ipynb).

## Installation
`neurondm` has not yet been fully decoupled from the [pyontutils respository](https://github.com/tgbugs/pyontutils).
You can install it as stand-alone package install it using `pip install --user neurondm`,
however it is currently more useful to follow the [installation instructions](https://github.com/tgbugs/pyontutils/#installation)
for pyontutils and work within the git repo.  
If you want to make use the example notebooks you should install with
`pip install --user neurondm[notebook]`.

## Configuration
See pyontutils [configuration](https://github.com/tgbugs/pyontutils/#configuration).

## Use outside the NIF ontology
It is possible to use neurondm outside the NIF ontology and the pyontutils repository,
however it has not been fully abstracted to support that use case. The way to do this is
to set all the relevant values via `neurondm.Config`. See
[`test_neruons.test_roundtrip_py`](https://github.com/tgbugs/pyontutils/blob/1805879322922b3f5e78d1abcb4b6642e22c204d/neurondm/test/test_neurons.py#L55)
for an example.
Some key pieces that need improvement for better repository independent use are listed below.
1. Untangle the `neurondm.graphBase` code from interaction with various git repos.
2. Retool everything to work with `ttl_export_dir`, `py_export_dir`,
and the location of the generating file.
3. Something like `config.activate()` to switch the i/o for existing neurons.
