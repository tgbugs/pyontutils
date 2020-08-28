# neurondm
[![PyPI version](https://badge.fury.io/py/neurondm.svg)](https://pypi.org/project/neurondm/)

A data model for neuron types.

## Neuron Types
For a an overview of how to use neuron-lang to describing neuron types please see
[this introduction](http://github.com/SciCrunch/NIF-Ontology/blob/master/docs/Neurons.md).
For a more in-depth look at the structures that neurons translate to in OWL
and some of the modelling decisions related to which reasoner you plan to use see an
[Overview of OWL modelling decisions](https://github.com/tgbugs/pyontutils/blob/master/neurondm/docs/basic-model.org)

To get started, follow the installation instructions below and
then include `from neurondm.lang import *` in your import statements.

If you want to get started quickly, take a look at the notebook of
[examples of how to use neuron-lang to create new neurons](https://github.com/tgbugs/pyontutils/blob/master/neurondm/docs/NeuronLangExample.ipynb)

If you want to use neurondm in a jupyter notebook, see the docs for how to
[set up neurondm for jupyter notebooks](https://github.com/tgbugs/pyontutils/blob/master/neurondm/docs/neurons_notebook.md).

## Installation
You can install `neurondm` using the following commands.

### Basics
```bash
pip install neurondm
```

Once installation is complete you should be able to run the following python code.

```python
from neurondm import *
config = Config()
n = Neuron(Phenotype('TEMP:myPhenotype'))
config.write()
config.write_python()
```

### SciGraph API
Set the API key in a separate terminal to avoid losing
additional history after setting the api key.
```bash
unset HISTFILE
ontutils set scigraph-api-key <key>
```

Once that is done you should be able to run the following.
```bash
python -m neurondm.models.huang2017
```

### NIF-Ontology
To work with the NIF-Ontology and build existing models
you need to clone the ontology repository and set your
SciGraph API key or set up a local SciGraph instance.

```bash
git clone https://github.com/SciCrunch/NIF-Ontology.git
ontutils set ontology-local-repo ./NIF-Ontology
pushd ./NIF-Ontology
git checkout neurons
popd
```

### Further configuration
If you need more details on configuration see the pyontutils
[configuration](https://github.com/tgbugs/pyontutils/#configuration) section.


## Use outside the NIF ontology
It is possible to use neurondm outside the NIF ontology and the pyontutils repository,
however it has not been fully abstracted to support that use case. If you want to do something
more complicated than the example shown in the installation section you will need to perform
some additional configuration. The way to do this is to set all the relevant values via
`neurondm.Config`. See
[`test_neruons.test_roundtrip_py`](https://github.com/tgbugs/pyontutils/blob/1805879322922b3f5e78d1abcb4b6642e22c204d/neurondm/test/test_neurons.py#L55)
for an example.
