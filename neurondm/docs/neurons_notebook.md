# Prerequisites
## NIF-Ontology
Neuron Lang depends on a set of core ontology files that define the
predicates and complex neuronal phenotypes that are the building blocks
for neurons. At the moment these files live in the
[neurons branch](https://github.com/SciCrunch/NIF-Ontology/tree/neurons)
ofthe NIF-Ontology repository. As such, Neuron Lang requires a local copy
of the NIF-Ontology repository which has the neurons branch checked out.
To accomplish this run the following.
```
git clone https://github.com/SciCrunch/NIF-Ontology.git`
cd NIF-Ontology
git checkout neurons
```

## The notebook environment for neuron lang support
1. Install `neurondm` following the [installation](./../README.md#installation) and
[configuration](./../README.md#configuration) instructions.
2. If you encounter any issues the most detailed instructions can be found in the
[setup documentation](https://github.com/SciCrunch/sparc-curation/blob/master/docs/setup.org)
for bootstrapping a full pyontutils/NIF-Ontology/protc development environment.

# Running the notebook
From the outer `neurondm` folder (../ from the folder of this README) run the following commands.
```
export SCICRUNCH_API_KEY=$(cat path/to/my/apikey)
cd docs/
jupyter-notebook
```
At this point your browser should open up with a view of this folder
and you should be able to select [NeuronLangExample.ipynb](./NeuronLangExample.ipynb) and run it.

# If you want to run this on an existing dedicated notebook server
[Create an issue](https://github.com/tgbugs/pyontutils/issues/new)
and I will help you figure out how to get all the dependencies installed.
