# nifstd-tools
[![PyPI version](https://badge.fury.io/py/nifstd-tools.svg)](https://pypi.org/project/nifstd-tools/)

Tools for working with the [NIF-Ontology](https://github.com/SciCrunch/NIF-Ontology).

## Installation
The use of nifstd-tools is highly intertwined with the
[pyontutils respository](https://github.com/tgbugs/pyontutils).
If you have a use case (e.g. `ontree`) where `nifstd-tools` works as a
stand-alone package install it using `pip install --user nifstd-tools`.
Otherwise see below for the full development installation instructions.

## Configuration
See pyontutils [configuration](https://github.com/tgbugs/pyontutils/#configuration).

## Development Installation
Follow the [parent instructions](https://github.com/tgbugs/pyontutils/#development-installation)
and refer to the rest of this section if you encounter issues.

Note that the optional development packages are not strictly required. If you have
installation issues development can proceed normally without them, but some database
queries will be slower because they use a pure python mysql connector.

If you don't want to use pipenv (which is probably most people) then the quickest
way to get up and running with a development install is `pip install --user --editable .`
from the folder that contains this readme.

## Workflows
See the documentation for [NIF-Ontology processes](https://github.com/SciCrunch/NIF-Ontology/blob/master/docs/processes.md).
