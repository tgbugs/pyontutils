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

