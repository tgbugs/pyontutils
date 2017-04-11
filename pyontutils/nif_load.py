#!/usr/bin/env python3.6
""" Run in NIF-Ontology/ttl/ """
from glob import glob
import rdflib
from pyontutils.utils import makeGraph, makePrefixes  # TODO make prefixes needs an all...
from pyontutils.hierarchies import creatTree
from collections import namedtuple
from IPython import embed

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

graph = rdflib.Graph()

for f in glob('*/*.ttl') + glob('*.ttl'):
    print(f)
    graph.parse(f, format='turtle')

mg = makeGraph('nifall', makePrefixes('NIFTTL', 'owl', 'skos'), graph=graph)
j = mg.make_scigraph_json('owl:imports', direct=True)
embed()
t, te = creatTree(*Query('NIFTTL:nif.ttl', 'owl:imports', 'outgoing', 30), json=j)
print(t)
