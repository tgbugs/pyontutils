#!/usr/bin/env python3.7
<<<<<<< HEAD
#!/usr/bin/env pypy3
"""
    Build lightweight slims from curie lists.
    Used for sources that don't have an owl ontology floating.
"""
#TODO consider using some of the code from scr_sync.py???

import os
import gzip
import json
from io import BytesIO
from pathlib import Path
from datetime import date
import rdflib
import requests
from lxml import etree
from rdflib.extras import infixowl
from pyontutils.core import makeGraph, createOntology, yield_recursive, build, qname
from pyontutils.core import Ont, Source
from pyontutils.utils import chunk_list, dictParse
from pyontutils.utils_extra import memoryCheck
from pyontutils.namespaces import SO, ilxtr, makePrefixes, replacedBy, hasPart, hasRole, PREFIXES as uPREFIXES
from pyontutils.closed_namespaces import rdf, rdfs, owl, prov, oboInOwl
from IPython import embed


#ncbi_map = {
    #'name':,
    #'description':,
    #'uid':,
    #'organism':{''},
    #'otheraliases':,
    #'otherdesignations':,
#}

class ncbi(dictParse):
    superclass = SO['0000110']  # sequence feature
    def __init__(self, thing, graph):
        self.g = graph
        super().__init__(thing, order=['uid'])

    def name(self, value):
        self.g.add_trip(self.identifier, rdfs.label, value)

    def description(self, value):
        #if value:
        self.g.add_trip(self.identifier, 'skos:prefLabel', value)
=======
"""Generate slim ontology files
>>>>>>> upstream/master

Usage:
    slimgen [options] (chebi|gene)...
    slimgen [options] all

Options:
    -h --help            show this
    -j --jobs=NJOBS      number of jobs [default: 1]
    -d --debug

"""

from pyontutils import clifun as clif
import nifstd_tools.chebi_slim
import nifstd_tools.ncbigene_slim


class Options(clif.Options):
    pass


class Main(clif.Dispatcher):

    def __call__(self):
        commands = [getattr(Main, c)() for c in
                    (['chebi', 'gene']
                     if self.options.all else
                    self.options.commands)]
        lc = len(commands)
        nj = int(self.options.jobs)
        if lc < nj:
            nj = lc

        if nj == 1:
            [command() for command in commands]

        else:
            from joblib import Parallel, delayed
            Parallel(n_jobs=nj, verbose=10)(delayed(command)()
                                            for command in commands)

    @staticmethod
    def chebi():
        return nifstd_tools.chebi_slim.main

    @staticmethod
    def gene():
        return nifstd_tools.ncbigene_slim.main


def main():
    from docopt import docopt, parse_defaults
    args = docopt(__doc__, version='slimgen 0.0.0')
    defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}
    options = Options(args, defaults)
    main = Main(options)
    if main.options.debug:
        print(main.options)

    main()

<<<<<<< HEAD
    if False:
        from pyontutils.qnamefix import cull_prefixes
        with open('/tmp/chebi-debug.xml', 'wb') as f: ChebiOntSrc.raw.write(f)
        #with open('/tmp/chebi-debug.ttl', 'wb') as f: f.write(ChebiOntSrc._data[2].serialize(format='nifttl'))
        g = cull_prefixes(ChebiOntSrc._data[2])
        g.filename = '/tmp/chebi-debug.ttl'
        g.write()
        embed()
=======
>>>>>>> upstream/master

if __name__ == '__main__':
    main()
