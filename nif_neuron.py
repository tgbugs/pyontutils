#!/usr/bin/env python3
import io
import os
import csv
from urllib.parse import quote
import rdflib
from IPython import embed
from utils import makeGraph
from obo_io import OboFile
from scigraph_client import Graph

sgg = Graph(quiet=False)

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


#with open('neurons.csv', 'rt') as f:
    #nrows = [r for r in csv.reader(f)]

PREFIXES = {
    #'ILX':'http://uri.interlex.org/base/ilx_',
    '':'http://FIXME.org/',
    'ilx':'http://uri.interlex.org/base/',
    'skos':'http://www.w3.org/2004/02/skos/core#',
    'owl':'http://www.w3.org/2002/07/owl#',
    'dc':'http://purl.org/dc/elements/1.1/',
    'nsu':'http://www.FIXME.org/nsupper#',

    'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
    'NIFQUAL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#',

}
#g = makeGraph('NIF-Neuron-phenotypes', prefixes=PREFIXES)
g = makeGraph('NIF-Neuron', prefixes=PREFIXES)

for row in rows[1:]:
    if row[0].startswith('#') or not row[0]:
        if row[0] == '#references':
            break
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
neuroner1 = '~/git/neuroNER/resources/bluima/neuroner/hbp_electrophysiology_ontology.obo'
neuroner2 = '~/git/neuroNER/resources/bluima/neuroner/hbp_electrophysiology-triggers_ontology.obo'
hbp_cell = ''
nif_qual = '~/git/NIF-Ontology/ttl/NIF-Quality.ttl'

mo = OboFile(os.path.expanduser(neuroner))
mo1 = OboFile(os.path.expanduser(neuroner1))
mo2 = OboFile(os.path.expanduser(neuroner2))
mo_ttl = mo.__ttl__() + mo1.__ttl__() + mo2.__ttl__()

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
ng.remove((None, rdflib.OWL.imports, None))

exact = []
similar = []
quals = []
s2 = {}

for subject, label in sorted(ng.subject_objects(rdflib.RDFS.label)):
    #print(subject)
    #print(label.lower())
    if 'quality' in label.lower():
        quals.append((subject, label))
    subpre = ng.namespace_manager.compute_qname(subject)[1]
    llower = rdflib.Literal(label.lower(), lang='en')
    for s in ng.subjects(rdflib.RDFS.label, llower):
        if s != subject:
            exact.append((subject, s, label, llower))
    for s, p, o in sorted(ng.triples((None, rdflib.RDFS.label, None))):
        spre = ng.namespace_manager.compute_qname(s)[1]
        if subject != s and label.lower() in o.lower().split(' ') and spre != subpre:
            print()
            print(spre, subpre)
            similar.append((subject, s, label, o))
            if subpre.toPython() == 'http://FIXME.org/':
                print('YAY')
                print(label, ',', o)
                print(subject, s)
                subject, s = s, subject
                label, o = o, label

            s2[subject] = {'label': label.toPython(), 'o': o.toPython(), 'xrefs':[subject, s]}  # FIXME overwrites

print()
for k, v in s2.items():
    print(k)
    for k, v2 in sorted(v.items()):
        print('    ', k, ':', v2)

desired_nif_terms = set()
starts = [
#"NIFQUAL:sao2088691397",
#"NIFQUAL:sao1278200674",
#"NIFQUAL:sao2088691397",
#"NIFQUAL:sao-1126011106",  # FIXME WTF IS THIS NONSENSE  (scigraph bug?)
quote("http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#sao1959705051").replace('/','%2F'),
quote("http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#sao2088691397").replace('/','%2F'),
quote("http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#sao1278200674").replace('/','%2F'),
quote("http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#sao2088691397").replace('/','%2F'),
quote("http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#sao-1126011106").replace('/','%2F'),
]

for id_ in starts:
    want = sgg.getNeighbors(id_, relationshipType='subClassOf', direction='INCOMING', depth=5)
    #print(id_, want)
    desired_nif_terms.update([n['id'] for n in want['nodes']])

print(desired_nif_terms)

new_terms = {}
for s, o in sorted(ng.subject_objects(rdflib.RDFS.label))[::-1]:
    spre = ng.namespace_manager.compute_qname(s)[1]
    if s in new_terms:
        print(s, 'already in as xref probably')
        continue
    elif spre.toPython() != 'http://FIXME.org/' and s.toPython() not in desired_nif_terms:
        print('DO NOT WANT', s)
        continue

    data = {}
    id_ = ilx_base.format(ilx_start)
    ilx_start += 1
    if s in s2:
        d = s2[s]
        new_terms[d['xrefs'][0]] = {'replaced_by':id_}
        new_terms[d['xrefs'][1]] = {'replaced_by':id_}

        data['labels'] = [d['label'], d['o']]
        data['xrefs'] = d['xrefs']
    else:
        new_terms[s] = {'replaced_by':id_}
        data['labels'] = [o.toPython()]
        data['xrefs'] = [s]

    new_terms[id_] = data

def pprint(thing):
    for t in thing:
        print()
        for v in t:
            print(v)

#pprint(exact)
#pprint(similar)
#pprint(quals)

embed()
g2 = makeGraph('pheno-comp', PREFIXES)
for t in ng.triples((None, None, None)):
    g2.add_node(*t)  # only way to clean prefixes :/

g2.write()
