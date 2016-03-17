#!/usr/bin/env python3
import rdflib
import csv
from scr_sync import makeGraph

id_ = None

(id_, rdflib.RDF.type, rdflib.OWL.Class)
(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
(id_, rdflib.RDFS.subClassOf, 'NIFCELL:sao1417703748')

syntax = '{region}{layer_or_subregion}{expression}{ephys}{molecular}{morph}{cellOrNeuron}'

ilx_base = 'ILX:{:0>7}'
ilx_start = 50020

print(ilx_base.format(ilx_start))
with open('neuron_phenotypes.csv', 'rt') as f:
    rows = [r for r in csv.reader(f)]



PREFIXES = {
    'ILX':'http://uri.interlex.org/base/ilx_',
    'ilx':'http://uri.interlex.org/base/',
    'skos':'http://www.w3.org/2004/02/skos/core#',
}
#g = makeGraph('NIF-Neuron-phenotypes', prefixes=PREFIXES)
g = makeGraph('NIF-Neuron', prefixes=PREFIXES)

for row in rows[1:]:
    if row[0].startswith('#') or not row[0]:
        print(row)
        continue
    id_ = PREFIXES['ilx'] + row[0]
    g.add_node(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
    if row[3]:
        g.add_node(id_, rdflib.namespace.SKOS.definition, row[3])


ontid = 'http://ontology.neuinfo.org/NIF/ttl/' + g.name + '.ttl'
g.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
g.add_node(ontid, rdflib.RDFS.label, 'NIF Neuron ontology')
g.add_node(ontid, rdflib.RDFS.comment, 'The NIF Neuron ontology holds materialized neurons that are collections of phenotypes.')
#g.add_node(ontid, rdflib.OWL.versionInfo, ONTOLOGY_DEF['version'])
g.write()

