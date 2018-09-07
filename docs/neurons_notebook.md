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
This assumes that you are using python3.6.
0. Make sure you have the pre-python [requirements](./../README.md#requirements) installed.
Otherwise you will get cryptic errors from pipenv.
1. Install pyontutils using pipenv as descrited in [installation](./../README.md#installtion).

## SciGraph
Neuron Lang makes use of SciGraph for searching the ontologies that
provide identifiers for phenotypes. Neuron Lang currently defaults to
a local scigraph instance. If you want to use the SciCrunch SciGraph
instance instead [register for an account](https://scicrunch.org/register)
and [get an api key](https://scicrunch.org/account/developer).
To set the scigraph endpoint for all pyontutils run
`ontutils devconfig` and then edit the `scigraph_api` key in
[devconfig.yaml](./../pyontutils/devconfig.yaml) (file doesn't exist by default)
to `https://scicrunch.org/api/v1/scigraph`. You can they set your api key by
running `export SCICRUNCH_API_KEY=$(cat path/to/my/apikey)` or by running
``` python
with open('path/to/file/containing/only/my-api-key', 'rt') as f:
	api_key = f.read.strip().rstrip()
	graphBase._sgv.api_key = api_key
```

Beware! The following is a mess.
Alternately follow the instructions for how to set up SciGraph in
[scigraph/README.md](./../scigraph/README.md). To set up SciGraph with
the NIF-Ontology you will need Java 8 JRE and JDK and maven >=3.3. You
will also need to have either the pipenv described above or the pipenv
for pyontutils installed in order to generate certain scripts so that
the shell scrips and yaml files will be available. Once that is done
you can run the commands below (adjust your paths accordingly).

1. Download the [latest release](https://github.com/SciCrunch/NIF-Ontology/releases/latest)
of the loaded NIF-Ontology graph.
2. Make sure you have done the oneshots in [scigraph/README.md](./../scigraph/README.md).
3. Try to follow the rest of the scigraph setup README

``` bash
export GRAPH_FOLDER=/var/scigraph-services/graph
# create config files
pipenv shell     # from the folder where this README is located (pyontutils/docs/../scigraph)
cd ../scigraph
# this command will then generate all the configuration files needed (wow does this need to be reworked)
scigraph-deploy config --zip-location $PWD --build-only --local --graph-folder $GRAPH_FOLDER --local --build-user $USER --services-user $USER $HOSTNAME $HOSTNAME

# download a zip of the released graph
cd $GRAPH_FOLDER/../
curl -Lok latest.zip $(curl --silent https://api.github.com/repos/SciCrunch/NIF-Ontology/releases/latest | awk '/browser_download_url/ { print $2 }' | sed 's/"//g')
unzip latest.zip
unlink graph  # on the off chance you have done this before
ln -s NIF-Ontology-*-graph-* $GRAPH_FOLDER

# build scigraph services
cd ${HOME}/git
git clone https://github.com/SciCrunch/SciGraph.git  # use this so the version matches on the version that loaded the graph
cd SciGraph
mvn -DskipTests -DskipITs install
cd SciGraph-services
mvn exec:java -Dexec.mainClass="io.scigraph.services.MainApplication" -Dexec.args="server ${HOME}/git/pyontutils/scigraph/services.yaml"
```

# Running the notebook
From the root of this repository (../ from the folder of this README) run the following commands.
```
export SCICRUNCH_API_KEY=$(cat path/to/my/apikey)
unset PYTHONPATH  # make sure our env is really clean
pipenv shell
cd docs/
jupyter-notebook
```
At this point your browser should open up with a view of this folder
and you should be able to select NeuronLangExample.ipynb and run it.

# If you want to run this on an existing dedicated notebook server
[Create an issue](https://github.com/tgbugs/pyontutils/issues/new)
and I will help you figure out how to get all the dependencies installed.
