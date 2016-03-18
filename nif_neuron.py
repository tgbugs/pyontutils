#!/usr/bin/env python3
import io
import os
import csv
import rdflib
from scr_sync import makeGraph
from obo_io import OboFile
from IPython import embed

id_ = None

(id_, rdflib.RDF.type, rdflib.OWL.Class)
(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
(id_, rdflib.RDFS.subClassOf, 'NIFCELL:sao1417703748')

syntax = '{region}{layer_or_subregion}{expression}{ephys}{molecular}{morph}{cellOrNeuron}'

ilx_base = 'ILX:{:0>7}'
ilx_start = 50020

print(ilx_base.format(ilx_start))
with open('neuron_phenotype_edges.csv', 'rt') as f:
    rows = [r for r in csv.reader(f)]


with open('neurons.csv', 'rt') as f:
    nrows = [r for r in csv.reader(f)]

PREFIXES = {
    #'ILX':'http://uri.interlex.org/base/ilx_',
    '':'http://FIXME.org/',
    'ilx':'http://uri.interlex.org/base/',
    'skos':'http://www.w3.org/2004/02/skos/core#',
    'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
    'NIFQUAL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#'
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

#phenotype sources
neuroner = '~/git/neuroNER/resources/bluima/neuroner/hbp_morphology_ontology.obo'
hbp_cell = ''
nif_qual = '~/git/NIF-Ontology/ttl/NIF-Quality.ttl'

mo = OboFile(os.path.expanduser(neuroner))
mo_ttl = mo.__ttl__()

mo_ttl = """\
@prefix : <http://FIXME.org/> .
@prefix nsu: <http://www.FIXME.org/nsupper#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
""" + mo_ttl

#sio = io.StringIO()
#sio.write(mo_ttl)
ng = rdflib.Graph()
ng.parse(data=mo_ttl, format='turtle')
ng.parse(os.path.expanduser(nif_qual), format='turtle')
#ng.namespace_manager.bind('default1', None, override=False, replace=True)
#embed()
g2 = makeGraph('pheno-comp', PREFIXES)
for t in ng.triples((None, None, None)):
    g2.add_node(*t)  # only way to clean prefixes :/
g2.write()
