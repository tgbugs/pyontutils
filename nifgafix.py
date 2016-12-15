#!/usr/bin/env python3.5

import rdflib
from utils import makePrefixes, makeGraph

PREFIXES = makePrefixes('NIFGA', 'NIFSTD', 'owl')

g = rdflib.Graph()
g.parse('http://purl.obolibrary.org/obo/uberon/bridge/uberon-bridge-to-nifstd.owl', format='xml')
ng = makeGraph('NIFGA-Equivs', PREFIXES)
[ng.g.add(t) for t in ((rdflib.URIRef(PREFIXES['NIFGA'] + o.rsplit('/',1)[-1]), p, o) for s, p, o in g.triples((None, rdflib.OWL.equivalentClass, None)))]
ng.write()
