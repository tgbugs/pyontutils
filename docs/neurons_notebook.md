# Prerequisites
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
Neuron Lang also makes use of SciGraph for searching the ontologies that
provide identifiers for phenotypes. Neuron Lang currently defaults to
a local scigraph instance. To set up SciGraph with the NIF-Ontology you
will need Java 8 JRE and JDK and maven >=3.3. Then run the following
(adjust paths accordingly). NOTE: in the near future it will be possible
to download the loaded SciGraph database for the NIF-Ontology so it
will not me necessary to load the graph yourself.
```
cd ${HOME}/git/NIF-Ontology/scigraph
sh make_yamls.sh
cd ${HOME}/git
git clone https://github.com/SciGraph/SciGraph.git
cd SciGraph
mvn -DskipTests -DskipITs install
cd SciGraph-core
mvn exec:java -Dexec.mainClass="io.scigraph.owlapi.loader.BatchOwlLoader" -Dexec.args="-c ${HOME}/git/NIF-Ontology/scigraph/graphload.yaml"
cd ../SciGraph-services
mvn exec:java -Dexec.mainClass="io.scigraph.services.MainApplication" -Dexec.args="server ${HOME}/git/NIF-Ontology/scigraph/services.yaml"
```

# Setting up the notebook environment for neuron lang support
This assumes that you are using python3.6 (if you aren't you should be).
The first thing you need to do in order for this install to work
is to make sure that you have the libs needed for lxml and psycopg2
development installed on your platfrom as well as a working gcc
toolchain. Otherwise you will get some very cryptic errors from pip.

If you run the following from a script do it using `. script.sh`
so that it does not fork and source will work as expected.
```
#!/usr/bin/env sh
VENVS=wherever/you/keep/your/venvs  # reminder to use ${HOME} not ~ or $HOME
NOTEBOOKS=wherever/you/keep/your/notebooks

unset PYTHONPATH  # make sure our env is really clean

cd ${VENVS}
mkdir 36_neurons
python3.6 -m venv 36_neurons
source 36_neurons/bin/activate

# for the time being we need to build these ourselves
pip install wheel
mkdir sources
cd sources

# needed until we figure out exactly how we want to package everything
git clone https://github.com/tgbugs/pyontutils.git
cd pyontutils
python setup.py bdist_wheel 
pip install dist/pyontutils-*-py3-none-any.whl
cd ../

# needed until https://github.com/RDFLib/rdflib/pull/649 is merged
git clone https://github.com/tgbugs/rdflib.git
cd rdflib
python setup.py bdist_wheel
pip install dist/rdflib-*-py3-none-any.whl
cd ../

cd ../

rm -rf sources/pyontutils
rm -rf sources/rdflib
rmdir sources
# end temporary section

pip install jupyter
cd ${NOTEBOOKS}
jupyter-notebook
```

