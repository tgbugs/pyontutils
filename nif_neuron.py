#!/usr/bin/env python3
import io
import os
import csv
from urllib.parse import quote
import rdflib
from rdflib.extras import infixowl
from IPython import embed
from utils import makeGraph, add_hierarchy
from obo_io import OboFile
from scigraph_client import Graph 
sgg = Graph(quiet=False)

id_ = None

(id_, rdflib.RDF.type, rdflib.OWL.Class)
(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
(id_, rdflib.RDFS.subClassOf, 'NIFCELL:sao1417703748')

syntax = '{region}{layer_or_subregion}{expression}{ephys}{molecular}{morph}{cellOrNeuron}'


PREFIXES = {
    #'ILX':'http://uri.interlex.org/base/ilx_',
    '':'http://FIXME.org/',
    'ilx':'http://uri.interlex.org/base/',
    'ILX':'http://uri.interlex.org/base/ilx_',
    'skos':'http://www.w3.org/2004/02/skos/core#',
    'owl':'http://www.w3.org/2002/07/owl#',
    'dc':'http://purl.org/dc/elements/1.1/',
    'nsu':'http://www.FIXME.org/nsupper#',

    'OBOOWL':'http://www.geneontology.org/formats/oboInOwl#',
    'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
    'NIFQUAL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#',
    'NIFCELL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Cell.owl#',
    'UBERON':'http://purl.obolibrary.org/obo/UBERON_',
}


#with open('neurons.csv', 'rt') as f:
    #nrows = [r for r in csv.reader(f)]

def pprint(thing):
    for t in thing:
        print()
        for v in t:
            print(v)

def make_phenotypes():
    with open('neuron_phenotype_edges.csv', 'rt') as f:
        rows = [r for r in csv.reader(f)]
    g = makeGraph('NIF-Neuron-phenotypes', prefixes=PREFIXES)

    pedges = set()
    for row in rows[1:]:
        if row[0].startswith('#') or not row[0]:
            if row[0] == '#references':
                break
            print(row)
            continue
        id_ = PREFIXES['ilx'] + row[0]
        pedges.add(g.expand('ilx:' + row[0]))
        g.add_node(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
        if row[3]:
            g.add_node(id_, rdflib.namespace.SKOS.definition, row[3])
        if row[6]:
            g.add_node(id_, rdflib.RDFS.subPropertyOf, 'ilx:' + row[6])

    ontid = 'http://ontology.neuinfo.org/NIF/ttl/' + g.name + '.ttl'
    g.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    g.add_node(ontid, rdflib.RDFS.label, 'NIF Neuron phenotypes')
    g.add_node(ontid, rdflib.RDFS.comment, 'The NIF Neuron phenotype ontology holds neuron phenotypes.')
    #g.add_node(ontid, rdflib.RDFS.comment, 'The NIF Neuron ontology holds materialized neurons that are collections of phenotypes.')
    #g.add_node(ontid, rdflib.OWL.versionInfo, ONTOLOGY_DEF['version'])
    #g.write(delay=True)  # moved below to incorporate uwotm8


    #phenotype sources
    neuroner = '~/git/neuroNER/resources/bluima/neuroner/hbp_morphology_ontology.obo'
    neuroner1 = '~/git/neuroNER/resources/bluima/neuroner/hbp_electrophysiology_ontology.obo'
    neuroner2 = '~/git/neuroNER/resources/bluima/neuroner/hbp_electrophysiology-triggers_ontology.obo'
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

    bad_match = {
        'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#nlx_qual_20090505',
        'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#sao1693353776',
        'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#sao1288413465',
        'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#sao4459136323',
        'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#nlx_qual_20090507',
    }

    exact = []
    similar = []
    quals = []
    s2 = {}

    for subject, label in sorted(ng.subject_objects(rdflib.RDFS.label)):

        syns = set([a for a in ng.objects(subject, rdflib.URIRef('http://www.FIXME.org/nsupper#synonym'))])
        syns.update(set([a for a in ng.objects(subject, rdflib.URIRef('http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#synonym'))]))
        #if syns:
            #print(syns)
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
                if s.toPython() in bad_match or subject.toPython() in bad_match:
                    continue
                #print()
                #print(spre, subpre)
                similar.append((subject, s, label, o))
                if subpre.toPython() == 'http://FIXME.org/':
                    print('YAY')
                    print(label, ',', o)
                    print(subject, s)
                    subject, s = s, subject
                    label, o = o, label

                if subject in s2:
                    #print('YES IT EXISTS')
                    #print(syns, label, [subject, s])
                    s2[subject]['syns'].update(syns) 
                    s2[subject]['syns'].add(label) 
                    s2[subject]['xrefs'] += [subject, s]
                else:
                    s2[subject] = {'label': label.toPython(), 'o': o.toPython(), 'xrefs':[subject, s], 'syns':syns}  # FIXME overwrites

    pprint(quals)
    """ print stuff
    print('matches')
    pprint(exact)
    pprint(similar)

    #print('EXACT', exact)

    print()
    for k, v in s2.items():
        print(k)
        for k, v2 in sorted(v.items()):
            print('    ', k, ':', v2)
    #"""

    desired_nif_terms = set() #{
        #'NIFQUAL:sao1959705051',  # dendrite
        #'NIFQUAL:sao2088691397',  # axon
        #'NIFQUAL:sao1057800815',  # morphological
        #'NIFQUAL:sao-1126011106',  # soma
        #'NIFQUAL:',
        #'NIFQUAL:',
    #}
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


    ilx_base = 'ILX:{:0>7}'
    ilx_start = 50113
    print(ilx_base.format(ilx_start))
    new_terms = {}
    dg = makeGraph('uwotm8', prefixes=PREFIXES)
    xr = makeGraph('xrefs', prefixes=PREFIXES)
    for s, o in sorted(ng.subject_objects(rdflib.RDFS.label))[::-1]:
        spre = ng.namespace_manager.compute_qname(s)[1]
        #if spre.toPython() == g.namespaces['NIFQUAL']:
            #print('skipping', s)
            #continue  # TODO
        if s in new_terms:
            print(s, 'already in as xref probably')
            continue
        #elif spre.toPython() != 'http://uri.interlex.org/base/ilx_' or spre.toPython() != 'http://FIXME.org/' and s.toPython() not in desired_nif_terms:
        #elif spre.toPython() != 'http://FIXME.org/' and s.toPython() not in desired_nif_terms:
            #print('DO NOT WANT', s, spre)
            #continue

        syns = set([s for s in ng.objects(s, dg.namespaces['nsu']['synonym'])])
        #data['syns'] += syns

        data = {}
        id_ = ilx_base.format(ilx_start)
        ilx_start += 1
        if s in s2:
            d = s2[s]
            syns.update(d['syns'])
            new_terms[d['xrefs'][0]] = {'replaced_by':id_}
            xr.add_node(d['xrefs'][0], 'OBOOWL:replacedBy', id_)
            #dg.add_node(d['xrefs'][0], 'OBOOWL:replacedBy', id_)
            new_terms[d['xrefs'][1]] = {'replaced_by':id_}
            xr.add_node(d['xrefs'][1], 'OBOOWL:replacedBy', id_)
            #dg.add_node(d['xrefs'][1], 'OBOOWL:replacedBy', id_)

            data['labels'] = [d['label'], d['o']]
            #dg.add_node(id_, rdflib.RDFS.label, d['label'])
            dg.add_node(id_, rdflib.RDFS.label, d['o'])
            data['xrefs'] = d['xrefs']
            for x in d['xrefs']:  # FIXME... expecting order of evaluation errors here...
                dg.add_node(id_, 'OBOOWL:hasDbXref', x)  # xr
                xr.add_node(id_, 'OBOOWL:hasDbXref', x)  # x

        elif spre.toPython() != 'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#' or ng.namespace_manager.qname(s).replace('default1','NIFQUAL') in desired_nif_terms:  # skip non-xref quals
            #print(ng.namespace_manager.qname(s).replace('default1','NIFQUAL'))
            new_terms[s] = {'replaced_by':id_}
            xr.add_node(s, 'OBOOWL:replacedBy', id_)
            data['labels'] = [o.toPython()]
            dg.add_node(id_, rdflib.RDFS.label, o.toPython())
            data['xrefs'] = [s]
            dg.add_node(id_, 'OBOOWL:hasDbXref', s)  # xr
            xr.add_node(id_, 'OBOOWL:hasDbXref', s)  # xr
        else:
            ilx_start -= 1
            continue

        new_terms[id_] = data
        dg.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
        xr.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
        for syn in syns:
            if syn.toPython() not in data['labels']:
                if len(syn) > 3:
                    dg.add_node(id_, 'OBOANN:synonym', syn)
                elif syn:
                    dg.add_node(id_, 'OBOANN:abbrev', syn)

        if 'EPHYS' in s or any(['EPHYS' in x for x in data['xrefs']]):
            dg.add_node(id_, rdflib.RDFS.subClassOf, 'ilx:ElectrophysiologicalPhenotype')
        elif 'MORPHOLOGY' in s or any(['MORPHOLOGY' in x for x in data['xrefs']]):
            dg.add_node(id_, rdflib.RDFS.subClassOf, 'ilx:MorphologicalPhenotype')

    #dg.write(delay=True)
    xr.write(delay=True)

    add_pedges(dg)
    for t in dg.g.triples((None, None, None)):
        g.add_node(*t)  # only way to clean prefixes :/
    g.write(delay=True)

    g2 = makeGraph('pheno-comp', PREFIXES)
    for t in ng.triples((None, None, None)):
        g2.add_node(*t)  # only way to clean prefixes :/

    g2.write(delay=True)
    
    syn_mappings = {}
    for sub, syn in [_ for _ in g.g.subject_objects(g.expand('OBOANN:synonym'))] + [_ for _ in g.g.subject_objects(rdflib.RDFS.label)]:
        syn = syn.toPython()
        if syn in syn_mappings:
            print('ERROR duplicate synonym!', syn, sub)
        syn_mappings[syn] = sub

    #embed()
    return syn_mappings, pedges

def make_neurons(syn_mappings, pedges):
    hbp_cell = '~/git/NIF-Ontology/ttl/generated/NIF-Neuron-HBP-cell-import.ttl'  # need to be on neurons branch
    ng = makeGraph('NIF-Neuron', prefixes=PREFIXES)
    base = 'http://ontology.neuinfo.org/NIF/ttl/' 
    ontid = base + ng.name + '.ttl'
    ng.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    ng.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-phenotypes.ttl')
    ng.g.parse(os.path.expanduser(hbp_cell), format='turtle')
    for pedge in pedges:
        for s, p, o_lit in ng.g.triples((None, pedge, None)):
            #print(s, p, o_lit)
            o = o_lit.toPython()
            if o in syn_mappings:
                id_ = syn_mappings[o]

                #child = infixowl.Class(id_, graph=ng.g)
                add_hierarchy(ng.g, id_, p, s)
                print('SUCCESS, substituting', o, 'for', id_)
                ng.g.remove((s, p, o_lit))
                #try:
                    #ng.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
                #except TypeError:
                    #print('BAD id_', s, p, id_)
                    #for t in ng.g.triples((id_, None, None)):
                        #print(t)
                    #pass

                #ng.add_node(s, p, id_)
            elif 'Location' in p.toPython():
                if o.startswith('http://'):
                    add_hierarchy(ng.g, o_lit, p, s)
                    ng.g.remove((s, p, o_lit))
                    #print('WHERE YOU AT', s, p, o_lit)
                    #try:
                    #o_add = rdflib.URIRef(o_lit)
                    #ng.add_node(o_add, rdflib.RDF.type, rdflib.OWL.Class)
                        #child = infixowl.Class(o_lit, graph=ng.g)
                    #except TypeError:
                        #for t in ng.g.triples((o_lit, None, None)):
                            #print(t)
                        #pass

    ng.write(delay=True)

def add_pedges(graph):
    graph.add_node('ilx:CellPhenotype', rdflib.RDF.type, rdflib.OWL.Class)
    graph.add_node('ilx:CellPhenotype', rdflib.RDFS.label, 'Cell Phenotype')

    graph.add_node('ilx:NeuronPhenotype', rdflib.RDF.type, rdflib.OWL.Class)
    graph.add_node('ilx:NeuronPhenotype', rdflib.RDFS.label, 'Neuron Phenotype')
    graph.add_node('ilx:NeuronPhenotype', rdflib.RDFS.subClassOf, 'ilx:CellPhenotype')


    graph.add_node('ilx:ElectrophysiologicalPhenotype', rdflib.RDFS.label, 'Electrophysiological Phenotype')
    graph.add_node('ilx:ElectrophysiologicalPhenotype', rdflib.RDF.type, rdflib.OWL.Class)
    graph.add_node('ilx:ElectrophysiologicalPhenotype', rdflib.RDFS.subClassOf, 'ilx:NeuronPhenotype')
    #graph.add_node('ilx:ElectrophysiologicalPhenotype', , )

    graph.add_node('ilx:MorphologicalPhenotype', rdflib.RDF.type, rdflib.OWL.Class)
    graph.add_node('ilx:MorphologicalPhenotype', rdflib.RDFS.label, 'Morphological Phenotype')
    graph.add_node('ilx:MorphologicalPhenotype', rdflib.RDFS.subClassOf, 'ilx:NeuronPhenotype')
    #graph.add_node('ilx:MorphologicalPhenotype', , )

def replace_edge(find, replace, graph):  # note that this is not a sed 's/find/replace/g'
    for s, p, o in graph.g.triples((None, find, None)):
        graph.add_node(s, replace, o)
        graph.g.remove(s, p, o)

def main():
    with makeGraph('', {}) as _:
        syn_mappings, pedge = make_phenotypes()
        make_neurons(syn_mappings, pedge)

if __name__ == '__main__':
    main()

