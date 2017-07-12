#!/usr/bin/env python3.6
""" Run in NIF-Ontology/ttl/ """

import os
from glob import glob
import rdflib
from pyontutils.utils import makeGraph, makePrefixes  # TODO make prefixes needs an all...
from pyontutils.hierarchies import creatTree
from collections import namedtuple
from IPython import embed

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

graph = rdflib.Graph()

done = []
for f in glob('*/*/*.ttl') + glob('*/*.ttl') + glob('*.ttl'):
    print(f)
    done.append(os.path.basename(f))
    graph.parse(f, format='turtle')

def repeat():
    for s, o in graph.subject_objects(rdflib.OWL.imports):
        if os.path.basename(o) not in done and o not in done:
        #if (o, rdflib.RDF.type, rdflib.OWL.Ontology) not in graph:
            print(o)
            done.append(o)
            ext = os.path.splitext(o)[1]
            fmt = 'turtle' if ext == '.ttl' else 'xml'
            #if 'go.owl' not in o and 'uberon.owl' not in o:  # NOPE
            graph.parse(o, format=fmt)

for i in range(4):
    repeat()

with open(os.path.expanduser('~/git/NIF-Ontology/scigraph/nifstd_curie_map.yaml'), 'rt') as f:
    wat = yaml.load(f)
vals = set(wat.values())

mg = makeGraph('nifall', makePrefixes('NIFTTL', 'owl', 'skos'), graph=graph)
j = mg.make_scigraph_json('owl:imports', direct=True)
#asdf = sorted(set(_ for t in graph for _ in t if type(_) == rdflib.URIRef))  # this snags a bunch of other URIs
#asdf = sorted(set(_ for _ in graph.subjects() if type(_) != rdflib.BNode))
asdf = set(_ for t in graph.subject_predicates() for _ in t if type(_) == rdflib.URIRef)
prefs = set(_.rsplit('#', 1)[0] + '#' if '#' in _
                   else (_.rsplit('_',1)[0] + '_' if '_' in _
                         else _.rsplit('/',1)[0] + '/') for _ in asdf)
nots = set(_ for _ in prefs if _ not in vals)
sos = set(prefs) - set(nots)

print(len(prefs))
t, te = creatTree(*Query('NIFTTL:nif.ttl', 'owl:imports', 'outgoing', 30), json=j)
embed()
print(t)
