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

Note that the optional development packages are not strictly required and if you have
installation issues development can proceed normally without them, some database
queries will just be slower because they use a pure python mysql connector.

If you are installing a development setup note that `mysql-connector` (aka `mysql-connector-python`)
often cannot find the files it needs to build.  When installing pass them in as environment variables
(you may need to adjust exact paths for your system).
`MYSQLXPB_PROTOBUF_INCLUDE_DIR=/usr/include/google/protobuf MYSQLXPB_PROTOBUF_LIB_DIR=/usr/lib64 MYSQLXPB_PROTOC=/usr/bin/protoc pipenv install --skip-lock`.
There are some systems on which even this is not sufficient.
If you encounter this situation add `mysql-connector = "==2.1.6"` to `[dev-packages]` in the Pipfile.
And then run the command without environment variables.

If you don't want to use pipenv (which is probably most people) then the quickest
way to get up and running with a development install is `pip install --user --editable .`
from the folder that contains this readme.
