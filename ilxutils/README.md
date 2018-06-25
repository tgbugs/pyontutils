# ilxutils
ilxutils is an api wrapper for SciCrunch. The package has 3 core functionalities:
Add/Update/Delete SciCrunch elements (api_wrapper.py), convert elements into local turtle file
(interlex2ttl.py), and compare Interlex to NIF Ontology (nif-ilx-comparator.py).

## Requirements
aiohttp==3.1.1
asyncio==3.4.3
DateTime==4.2
docopt==0.6.2
ipython==6.3.1
jupyter==1.0.0
jupyter-client==5.2.3
jupyter-console==5.2.0
jupyter-core==4.4.0
mysql-connector-python==8.0.6
pandas==0.22.0
pathlib==1.0.1
progressbar2==3.36.0
SQLAlchemy==1.2.6
urllib3==1.22
python3==3.6.3

## Using SciCrunch Client Wrapper
Usage:

    api_wrapper.py [-h | --help]
    api_wrapper.py [-v | --version]
    api_wrapper.py <argument> [-f FILE] [-k API_KEY] [-d DB_URL] [-p | -b]
    api_wrapper.py <argument> [-f FILE] [-k API_KEY] [-d DB_URL] [-p | -b] [--index=<int>]

Arugments:

    addTerms                    Add terms|cdes|annotations|relationships to SciCrunch
    updateTerms                 Update terms|cdes|annotations|relationships in SciCrunch
    addAnnotations              Add annotations to existing elements
    updateAnntationValues       Update annotation values only
    updateAnntationType         Update annotation connector aka annotation_type via annoatation_tid

Options:

    -h, --help                  Display this help message
    -v, --version               Current version of file
    -f, --file=<path>           File that holds the data you wish to upload to Scicrunch
    -a, --api_key=<path>        Key path [default: ../production_api_scicrunch_key.txt]
    -e, --engine_key=<path>     Engine key path [default: ../production_engine_scicrunch_key.txt]
    -p, --production            Production SciCrunch
    -b, --beta                  Beta SciCrunch
    -i, --index=<int>           index of -f FILE that you which to start [default: 0]

### The functionality of scicrunch_client.py
-> GET functions need a list of term ids

-> POST functions need a list of dictionaries with their needed/optional keys & values

Functions/Parameters:

    identifierSearches          identifierSearches(self, ids=None, crawl=False, LIMIT=50, \_print=True, ...
    updateTerms                 data
    addTerms                    data
    addAnnotations              data
    getAnnotations              tids
    updateAnntationValues       data
    updateAnntationType         data
    deleteAnnotations           tids
    addRelationship             data

### The format of addTerms (list of dictionaries of the following)
need:

    label           <str>

options:

    definition      <str> #bug with qutations
    superclasses    {'id':int}
    type            term, cde, anntation, or relationship <str>
    synonym         {'literal':<str>}
    existing_ids    {'iri<str>','prefix:<str>','change':<bool>, delete:<bool>}

### The format of UpdateTerms (list of dictionaries of the following)
need:

    id              <int> or <str>

options:

    label           <str>
    definition      <str> #bug with qutations
    superclasses    {'id':int}
    type            term, cde, anntation, or relationship <str>
    synonym         {'literal':<str>}
    existing_ids    {'iri<str>','prefix:<str>','change':<bool>, delete:<bool>}

### The format of all annotation functions (list of dictionaries of the following)
need:

    tid             <int> or <str>
    annotation_tid  <int> or <str>
    value           <str>

## Using Interlex2ttl.py to create ttl of current Interlex
Usage:

    interlex2ttl.py [-h | --help]
    interlex2ttl.py [-v | --version]
    interlex2ttl.py [-d DB_URL] [-p | -b] [-o OUTPUT]

Options:

    -h, --help                  Display this help message
    -v, --version               Current version of file
    -e, --engine_key=<path>     Engine key path [default: ../production_engine_scicrunch_key.txt]
    -o, --output=<path>         Output path
    -p, --production            Production SciCrunch
    -b, --beta                  Beta SciCrunch

## Using NIF vs Interlex Graph Comparator ( nif-ilx-comparator.py )
Usage:  

    foo.py [-h | --help]
    foo.py [-v | --version]
    foo.py [-r REFERENCE_GRAPH] [-t TARGET_GRAPH] [-o OUTPUT]

Options:

    -h, --help                  Display this help message
    -v, --version               Current version of file

    -r, --ref=<path>            Graph used as base case or foundation of comparison [default: ../Interlex.ttl]
    -t, --target=<path>         Graph used as the target of comparison [default: ../NIF-ALL.pickle]
    -o, --output=<path>         Resulting Json formatted comparison [default: ../nif-ilx-comparator/dump/nif-ilx-comparison.json]
