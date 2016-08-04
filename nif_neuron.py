#!/usr/bin/env python3
import io
import os
import re
import csv
import types
from urllib.parse import quote
import rdflib
from rdflib.extras import infixowl
from IPython import embed
from utils import makeGraph, add_hierarchy, rowParse
from obo_io import OboFile
from scigraph_client import Graph, Vocabulary
sgg = Graph(quiet=False)
v = Vocabulary()

# TODO
# 1) hiearchy for ephys
# 2) hiearchy for morpho
# 3) ingest table 1

# consts
defined_class_parent = 'ilx:definedClassNeurons'
morpho_phenotype =  'ilx:MorphologicalPhenotype'
morpho_edge = 'ilx:hasMorphologicalPhenotype'
ephys_phenotype = 'ilx:ElectrophysiologicalPhenotype'
ephys_edge = 'ilx:hasElectrophysiologicalPhenotype'
spiking_phenotype = 'ilx:SpikingPhenotype'
spiking_edge = 'ilx:hasSpikingPhenotype'
NIFCELL_NEURON = 'NIFCELL:sao1417703748'

#id_ = None

#(id_, rdflib.RDF.type, rdflib.OWL.Class)
#(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
#(id_, rdflib.RDFS.subClassOf, NIFCELL_NEURON)

syntax = '{region}{layer_or_subregion}{expression}{ephys}{molecular}{morph}{cellOrNeuron}'
ilx_base = 'ILX:{:0>7}'


PREFIXES = {
    #'ILX':'http://uri.interlex.org/base/ilx_',
    '':'http://FIXME.org/',
    'ilx':'http://uri.interlex.org/base/',
    'ILX':'http://uri.interlex.org/base/ilx_',
    'skos':'http://www.w3.org/2004/02/skos/core#',
    'owl':'http://www.w3.org/2002/07/owl#',
    'dc':'http://purl.org/dc/elements/1.1/',
    'nsu':'http://www.FIXME.org/nsupper#',

    'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
    'OBOOWL':'http://www.geneontology.org/formats/oboInOwl#',
    'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
    'NIFQUAL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#',
    'NIFCELL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Cell.owl#',
    'NIFMOL':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Molecule.owl#',
    'UBERON':'http://purl.obolibrary.org/obo/UBERON_',
    'PR':'http://purl.obolibrary.org/obo/PR_',
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
    
    lookup = {
        'asymmetric':'owl:AsymmetricProperty',
        'irreflexive':'owl:IrreflexiveProperty',
        'functional':'owl:FunctionalProperty',
    }
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
        if row[7]:
            g.add_node(id_, rdflib.OWL.inverseOf, 'ilx:' + row[7])
        if row[8]:
            for t in row[8].split(','):
                t = t.strip()
                g.add_node(id_, rdflib.RDF.type, lookup[t])

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


    ilx_start = 50114
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
            dg.add_node(id_, rdflib.RDFS.subClassOf, ephys_phenotype)
        elif 'MORPHOLOGY' in s or any(['MORPHOLOGY' in x for x in data['xrefs']]):
            dg.add_node(id_, rdflib.RDFS.subClassOf, morpho_phenotype)

    #dg.write(delay=True)
    xr.write(delay=True)

    #skip this for now, we can use DG to do lookups later
    #for t in dg.g.triples((None, None, None)):
        #g.add_node(*t)  # only way to clean prefixes :/
    add_phenotypes(g)
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
    return syn_mappings, pedges, ilx_start

def make_neurons(syn_mappings, pedges, ilx_start_):
    ilx_start = ilx_start_
    cheating = {'vasoactive intestinal peptide':'VIP',}
    ng = makeGraph('NIF-Neuron', prefixes=PREFIXES)

    #""" It seemed like a good idea at the time...
    nif_cell = '~/git/NIF-Ontology/ttl/NIF-Cell.ttl'  # need to be on neurons branch
    cg = rdflib.Graph()
    cg.parse(os.path.expanduser(nif_cell), format='turtle')
    missing = (
    'NIFCELL:nifext_55',
    'NIFCELL:nifext_56',
    'NIFCELL:nifext_57',
    'NIFCELL:nifext_59',
    'NIFCELL:nifext_81',
    'NIFCELL:nlx_cell_091205',
    NIFCELL_NEURON,
    'NIFCELL:sao2128417084',
    'NIFCELL:sao862606388',  # secondary, not explicitly in the hbp import
    )
    for m in missing:
        m = ng.expand(m)
        for s, p, o in cg.triples((m, None, None)):
            ng.add_node(s, p, o)



    #cg.remove((None, rdflib.OWL.imports, None))  # DONOTWANT NIF-Cell imports
    #for t in cg.triples((None, None, None)):
        #ng.add_node(*t)  # only way to clean prefixes :/
    #cg = None
    #"""

    hbp_cell = '~/git/NIF-Ontology/ttl/generated/NIF-Neuron-HBP-cell-import.ttl'  # need to be on neurons branch
    base = 'http://ontology.neuinfo.org/NIF/ttl/' 
    ontid = base + ng.name + '.ttl'
    ng.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    ng.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-phenotypes.ttl')
    ng.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-defined.ttl')
    #ng.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Cell.ttl')  # NO!
    #ng.add_node(ontid, rdflib.OWL.imports, base + 'external/uberon.owl')
    #ng.add_node(ontid, rdflib.OWL.imports, base + 'external/pr.owl')
    ng.g.parse(os.path.expanduser(hbp_cell), format='turtle')
    replace_object('ilx:hasMolecularPhenotype', 'ilx:hasExpressionPhenotype', ng)

    defined_graph = makeGraph('NIF-Neuron-defined', prefixes=PREFIXES)
    defined_graph.add_node(base + defined_graph.name + '.ttl', rdflib.RDF.type, rdflib.OWL.Ontology)
    defined_graph.add_node(base + defined_graph.name + '.ttl', rdflib.OWL.imports, base + 'NIF-Neuron-phenotypes.ttl')

    done = True#False
    done_ = set()
    for pedge in pedges:
        for s, p, o_lit in ng.g.triples((None, pedge, None)):
            o = o_lit.toPython()
            success = False
            true_o = None
            true_id = None
            if o in syn_mappings:
                id_ = syn_mappings[o]

                add_hierarchy(ng.g, id_, p, s)
                ng.g.remove((s, p, o_lit))
                print('SUCCESS, substituting', o, 'for', id_)
                success = True
                true_o = o_lit
                true_id = id_

            elif 'Location' in p.toPython():
                if o.startswith('http://'):
                    add_hierarchy(ng.g, o_lit, p, s)
                    ng.g.remove((s, p, o_lit))

                    data = v.findById(o)
                    label = data['labels'][0]
                    ng.add_node(o, rdflib.RDF.type, rdflib.OWL.Class)
                    ng.add_node(o, rdflib.RDFS.label, label)

                    success = True
                    true_o = label
                    true_id = o_lit

            else:
                if o in cheating:
                    o = cheating[o]

                data = v.findByTerm(o)
                if data:
                    print('SCIGRAPH', [(d['curie'], d['labels']) for d in data])
                    for d in data:
                        if 'PR:' in d['curie']:
                            sgt = ng.expand(d['curie'])
                            add_hierarchy(ng.g, sgt, p, s)
                            ng.g.remove((s, p, o_lit))

                            label = d['labels'][0]
                            ng.add_node(sgt, rdflib.RDF.type, rdflib.OWL.Class)
                            ng.add_node(sgt, rdflib.RDFS.label, label)

                            success = True
                            true_o = label
                            true_id = sgt
                            break

                    if not success:
                        for d in data:
                            if 'NIFMOL:' in d['curie']:
                                sgt = ng.expand(d['curie'])
                                add_hierarchy(ng.g, sgt, p, s)
                                ng.g.remove((s, p, o_lit))

                                label = d['labels'][0]
                                ng.add_node(sgt, rdflib.RDF.type, rdflib.OWL.Class)
                                ng.add_node(sgt, rdflib.RDFS.label, label)

                                success = True
                                true_o = label
                                true_id = sgt
                                break

            if o not in done_ and success:
                done_.add(o)

                id_ = ng.expand(ilx_base.format(ilx_start))
                ilx_start += 1
                ng.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
                restriction = infixowl.Restriction(p, graph=defined_graph.g, someValuesFrom=true_id)
                intersection = infixowl.BooleanClass(members=(defined_graph.expand(NIFCELL_NEURON), restriction), graph=defined_graph.g)
                this = infixowl.Class(id_, graph=defined_graph.g)
                this.equivalentClass = [intersection]
                this.subClassOf = [ng.expand(defined_class_parent)]
                this.label = rdflib.Literal(true_o + ' neuron')
                if not done:
                    embed()
                    done = True
    defined_graph.add_node(defined_class_parent, rdflib.RDF.type, rdflib.OWL.Class)
    defined_graph.add_node(defined_class_parent, rdflib.RDFS.label, 'defined class neuron')
    defined_graph.add_node(defined_class_parent, rdflib.namespace.SKOS.description, 'Parent class For all defined class neurons')
    defined_graph.add_node(defined_class_parent, rdflib.RDFS.subClassOf, ng.expand(NIFCELL_NEURON))
    defined_graph.write(delay=True)
    ng.write(delay=True)

    for sub, syn in [_ for _ in ng.g.subject_objects(ng.expand('OBOANN:synonym'))] + [_ for _ in ng.g.subject_objects(rdflib.RDFS.label)]:
        syn = syn.toPython()
        if syn in syn_mappings:
            print('ERROR duplicate synonym!', syn, sub)
        syn_mappings[syn] = sub

    return ilx_start

def add_phenotypes(graph):
    def add_new(id_, sco=None, syns=tuple(), lbl=None):
        if lbl is None:
            lbl = ' '.join(re.findall(r'[A-Z][a-z]*', id_.split(':')[1]))
        graph.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
        graph.add_node(id_, rdflib.RDFS.label, lbl)
        if sco:
            graph.add_node(id_, rdflib.RDFS.subClassOf, sco)

        [graph.add_node(id_, 'OBOANN:synonym', s) for s in syns]

    cell_phenotype = 'ilx:CellPhenotype'
    neuron_phenotype = 'ilx:NeuronPhenotype'
    #ephys_phenotype = 'ilx:ElectrophysiologicalPhenotype'
    #spiking_phenotype = 'ilx:SpikingPhenotype'
    i_spiking_phenotype = 'ilx:PatillaInitialSpikingPhenotype'
    burst_p = 'ilx:PatillaInitialBurstSpikingPhenotype'
    classical_p = 'ilx:PatillaInitialClassicalSpikingPhenotype'
    delayed_p = 'ilx:PatillaInitialDelayedSpikingPhenotype'
    s_spiking_phenotype = 'ilx:PatillaSustainedSpikingPhenotype'
    #morpho_phenotype = 'ilx:MorphologicalPhenotype'
    ac_p = 'ilx:PatillaSustainedAccomodatingPhenotype'
    nac_p = 'ilx:PatillaSustainedNonAccomodatingPhenotype'
    st_p = 'ilx:PatillaSustainedStutteringPhenotype'
    ir_p = 'ilx:PatillaSustainedIrregularPhenotype'

    add_new(cell_phenotype)

    add_new(neuron_phenotype, cell_phenotype)
    add_new(ephys_phenotype, neuron_phenotype)
    add_new(spiking_phenotype, ephys_phenotype)
    add_new(i_spiking_phenotype, spiking_phenotype)
    iClass = infixowl.Class(graph.expand(i_spiking_phenotype), graph=graph.g)

    add_new(burst_p, i_spiking_phenotype, ('burst',))
    add_new(classical_p, i_spiking_phenotype, ('classical',))
    add_new(delayed_p, i_spiking_phenotype, ('delayed',))
    add_new(s_spiking_phenotype, spiking_phenotype)
    sClass = infixowl.Class(graph.expand(s_spiking_phenotype), graph=graph.g)
    sClass.disjointWith = [iClass]

    add_new(ac_p, s_spiking_phenotype, ('accomodating',))  # FIXME this is silly
    add_new(nac_p, s_spiking_phenotype, ('non accomodating',))
    add_new(st_p, s_spiking_phenotype, ('stuttering',))
    add_new(ir_p, s_spiking_phenotype, ('irregular',))
    add_new(morpho_phenotype, neuron_phenotype)

def replace_object(find, replace, graph):  # note that this is not a sed 's/find/replace/g'
    find = graph.expand(find)
    for s, p, o in graph.g.triples((None, None, find)):
        graph.add_node(s, p, replace)
        graph.g.remove((s, p, o))

class table1(rowParse):  # TODO decouple input -> tokenization to ontology structuring rules, also incremeting ilx_start is a HORRIBLE way to mint identifiers, holy crap, but to improve this we need all the edge structure and links in place so we can do a substitution
    species = 'NCBITaxon:10116'
    brain_region = 'UBERON:0008933'
    citation = 'Markhram et al Cell 2015'
    pmid = 'PMID:26451489'
    _sep = '|'
    _edge = '\x00\x01\xde\xad\xee\xef\xfe'

    def __init__(self, graph, rows, syn_mappings, ilx_start):
        self.graph = graph
        self.expand = self.graph.expand
        self.ilx_start = ilx_start
        self.syn_mappings = syn_mappings
        self.plbls = set()
        self.done_phenos = {}
        super().__init__(rows)

    #@use_decorators_to_do_mappings_to_generic_classes   # !
    def Morphological_type(self, value):
        print('--------------------')
        self.phenotype_callbacks = {}
        self.ilx_start += 1
        self.id_ = ilx_base.format(self.ilx_start)
        self.Class = infixowl.Class(self.expand(self.id_), graph=self.graph.g)

        species_rest = infixowl.Restriction(self.expand('ilx:hasInstanceInSpecies'),
                                           self.graph.g,
                                           someValuesFrom=self.expand(self.species))
        location_rest = infixowl.Restriction(self.expand('ilx:hasSomaLocatedIn'),
                                           self.graph.g,
                                           someValuesFrom=self.expand(self.brain_region))
        self.Class.subClassOf = [species_rest, location_rest,self.expand(NIFCELL_NEURON)]

        syn, abrv = value.split(' (')
        syn = syn.strip()
        abrv = abrv.rstrip(')').strip()
        #print(value)
        print((syn, abrv))

        slbl = v.findById(self.species)['labels'][0]
        brlbl = v.findById(self.brain_region)['labels'][0]
        LABEL = slbl + ' ' + brlbl + ' ' + syn.replace('cell', 'neuron').lower() # FIXME this has to be done last...

        self.Class.label = rdflib.Literal(LABEL)
        self.graph.add_node(self.id_, 'OBOANN:abbrev', abrv)

        # for phenotypes only...
        phenotype_lbl = syn.rstrip('cell').strip(), morpho_phenotype, morpho_edge, 'LOL STUPID MESSAGE PASSING SCHEME' + self.id_
        #if phenotype_lbl not in self.plbls:  # I'm guessing this is less efficient since it adds an extra hash step but haven't tested
        self.plbls.add(phenotype_lbl)


    def Other_morphological_classifications(self, value):
        values = value.split(self._sep)
        output = []
        callbacks = []

        for v in values:
            if '/' in v:
                prefix, a_b = v.split(' ')
                a, b = a_b.split('/')
                output.append(prefix + ' ' + a)
                output.append(prefix + ' ' + b)
            else:
                prefix = v.rstrip('cell').strip()
                output.append(v)
                def cb(pheno_uri, val=v):
                    print(pheno_uri, val)
                    self.graph.add_node(pheno_uri, 'OBOANN:synonym', val)
                callbacks.append(cb)

        #output = tuple(output)
        #def callback(pheno_uri, syns=[_ for _ in output]):
            #for s in syns:
                #self.graph.add_node(pheno_uri, 'OBOANN:synonym', s)
            self.phenotype_callbacks['LOL STUPID MESSAGE PASSING SCHEME' + self.id_] = lambda puri: [cb(puri) for cb in callbacks]

            #synonyms
            #phenotype_lbl = prefix, morpho_phenotype, morpho_edge, None
            #self.plbls.add(phenotype_lbl)

        #print(value)
        print(output)

    def Predominantly_expressed_Ca2_binding_proteins_and_peptides(self, value):
        CB = self.syn_mappings['calbindin']
        PV = self.syn_mappings['Parvalbumin']
        CR = self.syn_mappings['calretinin']
        NPY = self.syn_mappings['neuropeptide Y']
        VIP = self.syn_mappings['VIP peptides']
        SOM = self.syn_mappings['somatostatin']
        p_edge = 'ilx:hasExpressionPhenotype'
        p_map = {
            'CB':CB,
            'PV':PV,
            'CR':CR,
            'NPY':NPY,
            'VIP':VIP,
            'SOM':SOM,
            self._edge:p_edge,
        }
        NEGATIVE = False
        POSITIVE = True  # FIXME this requires more processing prior to dispatch...
        e_edge = ''
        e_map = {
            '-':NEGATIVE,
            '+':POSITIVE,
            '++':POSITIVE,
            '+++':POSITIVE,
            self._edge:e_edge,
        }
        NONE = 0
        LOW = 1
        MED = 2
        HIGH = 3
        s_edge = None #''  # TODO this needs to be an annotation on the (self.id_, ixl:hasExpressionPhenotype, molecule) triple
        s_map = {
            '-':NONE,
            '+':LOW,
            '++':MED,
            '+++':HIGH,
            self._edge:s_edge,
        }

        def apply(map_, val):  # XXX this turns out to be a bad idea :/
            s = self.id_  # FIXME this is what breaks things
            p = map_[self._edge]
            o = map_[val]
            if type(o) == types.FunctionType:
                o = o(val)
            if o and p:
                self.graph.add_node(s, p, o)
            return o

        values = value.split(self._sep)
        output = []
        for v in values:
            abrv, score_paren = v.split(' (')
            score = score_paren.rstrip(')')
            molecule = p_map[abrv]
            muri = molecule
            #muri = rdflib.URIRef('http://' + molecule.replace(' ','-') + '.org')  # FIXME rearchitect so that uris are already in place at map creation
            exists = e_map[score]
            score = s_map[score]
            if exists:
                restriction = infixowl.Restriction(self.expand(p_edge), graph=self.graph.g, someValuesFrom=muri)
                self.Class.subClassOf = [restriction]
            else:
                # disjointness
                restriction = infixowl.Restriction(self.expand(p_edge), graph=self.graph.g, someValuesFrom=muri)
                self.Class.disjointWith = [restriction]  # TODO do we need to manually add existing?
            output.append((molecule, exists, score))

        #print(value)
        #print(output)

    def Electrical_types(self, value):  # FIXME these are mutually exclusive types, so they force the creation of subClasses so we can't apply?
        b = self.syn_mappings['burst']
        c = self.syn_mappings['classical']  # XXX CHECK
        d = self.syn_mappings['delayed']
        e_edge = 'ilx:hasInitialSpikingPhenotype'  # XXX edge level?
        #e_edge = 'ilx:hasElectrophysiologicalPhenotype'
        e_map = {
            'b':b,
            'c':c,
            'd':d,
            self._edge:e_edge,
        }
        AC = self.syn_mappings['accomodating']
        NAC = self.syn_mappings['non accomodating']
        STUT = self.syn_mappings['stuttering']
        IR = self.syn_mappings['irregular']
        l_edge = 'ilx:hasSustainedSpikingPhenotype'  # XXX these should not be handled at the edge level?
        #l_edge = 'ilx:hasElectrophysiologicalPhenotype'
        l_map = {
            'AC':AC,
            'NAC':NAC,
            'STUT':STUT,
            'IR':IR,
            self._edge:l_edge,
        }

        def apply(map_, val):  # doesn't work, requires many subclasses
            s = self.id_
            p = map_[self._edge]
            o = map_[val]
            if o:
                self.graph.add_node(s, p, o)
            return o

        values = value.split(self._sep)
        output = []
        for v in values:
            early_late, score_pct_paren = v.split(' (')
            score = int(score_pct_paren.rstrip('%)'))
            #early = apply(e_map, early_late[0])
            #late = apply(l_map, early_late[1:])
            early, late = e_map[early_late[0]], l_map[early_late[1:]]
            # create electrical subclasses
            self.ilx_start += 1  # FIXME the other option here is to try disjoint union???
            id_ = ilx_base.format(self.ilx_start)
            c = infixowl.Class(self.expand(id_), graph=self.graph.g)
            e_res = infixowl.Restriction(self.expand(e_edge), graph=self.graph.g, someValuesFrom=early)
            l_res = infixowl.Restriction(self.expand(l_edge), graph=self.graph.g, someValuesFrom=late)
            c.subClassOf = [e_res, l_res]  # handy that...
            self.graph.add_node(id_, rdflib.RDFS.subClassOf, self.id_)  # how to do this with c.subClassOf...

            output.append((early, late, score))

        #print(value)
        #print(output)

    def Other_electrical_classifications(self, value):
        values = value.split(self._sep)
        output = []
        def callback(pheno_uri):  # terrible way to do this... XXX can order help
            restriction = infixowl.Restriction(self.expand(ephys_edge), graph=self.graph.g, someValuesFrom=pheno_uri)
            self.Class.subClassOf = [restriction]
        callback_name = 'oec'
        self.phenotype_callbacks[callback_name] = callback
        for v in values:
            output.append(v)
            phenotype_lbl = v, spiking_phenotype, spiking_edge, callback_name
            self.plbls.add(phenotype_lbl)
        #print(value)
        print(output)

    def _row_post(self):
        # electrical here? or can we do those as needed above?

        return

        for phenotype_lbl, parent_pheno, p_edge, callback_name in sorted(self.plbls):
            if phenotype_lbl not in self.done_phenos:
                #phenotype class  TODO edge too?
                print(phenotype_lbl)
                self.ilx_start += 1
                id_ = ilx_base.format(self.ilx_start)
                self.done_phenos[phenotype_lbl] = id_
                self.graph.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
                self.graph.add_node(id_, rdflib.RDFS.subClassOf, parent_pheno)
                self.graph.add_node(id_, rdflib.RDFS.label, phenotype_lbl + ' phenotype')
                restriction = infixowl.Restriction(self.expand(p_edge),
                                                   graph=self.graph.g,
                                                   someValuesFrom=self.expand(id_))
                self.Class.subClassOf = [restriction]

                #defined class
                self.ilx_start += 1
                id_ = ilx_base.format(self.ilx_start)
                defined = infixowl.Class(self.expand(id_), graph=self.graph.g)
                defined.label = rdflib.Literal(phenotype_lbl + ' neuron')
                intersection = infixowl.BooleanClass(members=(self.graph.expand(NIFCELL_NEURON), restriction), graph=self.graph.g)
                #intersection = infixowl.BooleanClass(members=(restriction,), graph=self.graph.g)
                defined.equivalentClass = [intersection]
                defined.subClassOf = [self.graph.expand(defined_class_parent)]
                dj_rest = infixowl.Restriction(self.expand('ilx:hasPhenotype'), graph=self.graph.g, someValuesFrom=self.expand('ilx:the_classes_that_are_disjoint')) # FIXME TODO this is currently more useful for ephys
                defined.disjointWith = [dj_rest]
            else:
                id_ = self.done_phenos[phenotype_lbl]


            if callback_name:
                self.phenotype_callbacks[callback_name](self.expand(id_))

def make_table1(syn_mappings, ilx_start):
    # TODO when to explicitly subClassOf? I think we want this when the higher level phenotype bag is shared
    # it may turn out that things like the disjointness exist at a higher level while correlated properties
    # should be instantiated together as sub classes, for example if cck and 
    # FIXME disagreement about nest basket cells
    # TODO hasPhenotypes needs to be function to get phenotypeOf to work via reasoner??? this seems wrong.
    #  this also works if phenotypeOf is inverseFunctional
    #  hasPhenotype shall be asymmetric, irreflexive, and intransitive
    # XXX in answer to Maryann's question about why we need the morphological phenotypes by themselves:
    #  if we don't have them we can't agregate across orthogonal phenotypes since owl correctly keeps the classes distinct
    # TODO disjointness axioms work really well on defined classes and propagate excellently
    # TODO add 'Petilla' or something like that to the phenotype definitions
    #  we want this because 'Petilla' denotes the exact ANALYSIS used to determine the phenotype
    #  there are some additional 'protocol' related restrictions on what you can apply analysis to
    #  but we don't have to model those explicitly which would be a nightmare and break the
    #  orthogonality of the cell type decomposition
    # TODO to make this explicit we need to include that phenotypes require 2 things
    #  1) a type of data (data type?) 2) a way to classify that data (analysis protocol)

    with open('resources/26451489 table 1.csv', 'rt') as f:
        rows = [r for r in zip(*csv.reader(f))]

    graph = makeGraph('hbp-special', prefixes=PREFIXES)  # XXX fix all prefixes
    base = 'http://ontology.neuinfo.org/NIF/ttl/' 
    ontid = base + graph.name + '.ttl'
    graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    graph.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-phenotypes.ttl')
    #graph.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-defined.ttl')

    syn_mappings['calbindin'] = graph.expand('PR:000004967')  # cheating
    syn_mappings['calretinin'] = graph.expand('PR:000004968')  # cheating
    t = table1(graph, rows, syn_mappings, ilx_start)

    def do_graph(d):
        sgt = graph.expand(d['curie'])
        label = d['labels'][0]
        graph.add_node(sgt, rdflib.RDF.type, rdflib.OWL.Class)
        graph.add_node(sgt, rdflib.RDFS.label, label)

    done = set()
    for s, p, o in graph.g.triples((None, None, None)): #(rdflib.RDFS.subClassOf,rdflib.OWL.Thing)):
        if o not in done and type(o) == rdflib.term.URIRef:
            done.add(o)
            if not [_ for _ in graph.g.objects((o, rdflib.RDFS.label))]:
                d = v.findById(o)
                if d:
                    if 'PR:' in d['curie']:
                        do_graph(d)
                    elif 'NIFMOL:' in d['curie']:
                        do_graph(d)
                    elif 'UBERON:' in d['curie']:
                        do_graph(d)
                    elif 'NCBITaxon:' in d['curie']:
                        do_graph(d)
                    elif 'NIFCELL:' in d['curie']:
                        do_graph(d)


    # FIXME this is a dupe with defined_class
    graph.add_node(defined_class_parent, rdflib.RDF.type, rdflib.OWL.Class)
    graph.add_node(defined_class_parent, rdflib.RDFS.label, 'defined class neuron')
    graph.add_node(defined_class_parent, rdflib.namespace.SKOS.description, 'Parent class For all defined class neurons')
    graph.add_node(defined_class_parent, rdflib.RDFS.subClassOf, graph.expand(NIFCELL_NEURON))

    graph.write(delay=True)
    #print(t._set_Electrical_types)
    #_ = [[print(v) for v in [k] + list(v) + ['\n']] for k,v in t.__dict__.items() if '_set_' in k]
    #embed()

def main():
    with makeGraph('', {}) as _:
        syn_mappings, pedge, ilx_start = make_phenotypes()
        ilx_start = make_neurons(syn_mappings, pedge, ilx_start)
        make_table1(syn_mappings, ilx_start)

if __name__ == '__main__':
    main()

