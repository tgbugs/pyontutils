# librdflib
[![PyPI version](https://badge.fury.io/py/librdflib.svg)](https://pypi.org/project/librdflib/)

librdf parser for rdflib

Highly experimental.

## Installation
This is not faster for pypy3 but if you want install it follow these steps (ish).

``` bash
http://download.librdf.org/source/redland-bindings-1.0.17.1.tar.gz
tar xvzf redland-bindings-1.0.17.1.tar.gz
cd redland-bindings-1.0.17.1
./configure --with-python=pypy3 --prefix
make check  # will fail on storage
cp python/__pycache__/RDF.* ${site_packages}/__pycache__
cp python/__pycache__/Redland.* ${site_packages}/__pycache__
cp python/RDF.py ${site_packages}
cp python/Redland.py ${site_packages}
cp python/_Redland.pypy3*.so ${site_packages}
```
