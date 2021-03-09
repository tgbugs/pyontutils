#!/usr/bin/env python3

import rdflib
from pyontutils.core import makeGraph
from pyontutils.namespaces import makePrefixes

def main():
    PREFIXES = makePrefixes('NIFGA', 'NIFSTD', 'owl')

    g = rdflib.Graph()
    g.parse('http://purl.obolibrary.org/obo/uberon/bridge/uberon-bridge-to-nifstd.owl', format='xml')
    name = 'NIFGA-Equivs'
    ng = makeGraph(name, PREFIXES)
    [ng.g.add(t) for t in ((rdflib.URIRef(PREFIXES['NIFGA'] + o.rsplit('/',1)[-1]), p, o) for s, p, o in g.triples((None, rdflib.OWL.equivalentClass, None)))]
    ng.add_ont('http://ontology.neuinfo.org/NIF/ttl/generated/' + name + '.ttl', 'NIFGA to NIFSTD mappings')
    ng.write()

if __name__ == '__main__':
    main()
