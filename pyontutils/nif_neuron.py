#!/usr/bin/env python3.6
import io
import os
import re
import csv
import types
from collections import defaultdict
from urllib.parse import quote
import rdflib
from rdflib.extras import infixowl
from IPython import embed
from utils import TODAY, makePrefixes, makeGraph, rowParse, refile
from ilx_utils import ILXREPLACE
from parcellation import OntMeta
from obo_io import OboFile
from scigraph_client import Graph, Vocabulary
sgg = Graph(cache=True, verbose=True)
sgv = Vocabulary(cache=True)

# TODO future workflow: existing representation -> bags -> owl
# vastly preferred to the current nightmare
# the main things we need for the first arrow is a nice way to
# map to names of known phenotypes, so we need to load NNP and make sure
# for the second arrow we basically need to improve neuronManager

# consts
defined_class_parent = 'ilx:definedClassNeurons'
morpho_defined = 'ilx:definedClassNeuronsMorpho'
ephys_defined = 'ilx:definedClassNeuronsElectro'
morpho_phenotype =  'ilx:MorphologicalPhenotype'
morpho_edge = 'ilx:hasMorphologicalPhenotype'
ephys_phenotype = 'ilx:ElectrophysiologicalPhenotype'
ephys_edge = 'ilx:hasElectrophysiologicalPhenotype'
spiking_phenotype = 'ilx:SpikingPhenotype'
i_spiking_phenotype = 'ilx:PetillaInitialSpikingPhenotype'
s_spiking_phenotype = 'ilx:PetillaSustainedSpikingPhenotype'
spiking_edge = 'ilx:hasSpikingPhenotype'
fast_phenotype = 'ilx:FastSpikingPhenotype'
reg_phenotype = 'ilx:RegularSpikingNonPyramidalPhenotype'
expression_edge = 'ilx:hasExpressionPhenotype'
expression_defined = 'ilx:ExpressionClassifiedNeuron'
NIFCELL_NEURON = 'NIFCELL:sao1417703748'

syntax = '{region}{layer_or_subregion}{expression}{ephys}{molecular}{morph}{cellOrNeuron}'
ilx_base = 'ILX:{:0>7}'

PREFIXES = makePrefixes('ilx',
                        'ILX',
                        'ILXREPLACE',
                        'skos',
                        'owl',
                        'dc',
                        'nsu',
                        'NCBITaxon',
                        'oboInOwl',
                        'OBOANN',
                        'NIFQUAL',
                        'NIFCELL',
                        'NIFMOL',
                        'UBERON',
                        'PR',)

def replace_object(find, replace, graph):  # note that this is not a sed 's/find/replace/g'
    find = graph.expand(find)
    for s, p, o in graph.g.triples((None, None, find)):
        graph.add_node(s, p, replace)
        graph.g.remove((s, p, o))

def make_defined(graph, ilx_start, label, phenotype_id, restriction_edge, parent=None):
    ilx_start += 1
    id_ = ilx_base.format(ilx_start)
    id_ = graph.expand(id_)
    restriction = infixowl.Restriction(graph.expand(restriction_edge), graph=graph.g, someValuesFrom=phenotype_id)
    defined = infixowl.Class(id_, graph=graph.g)
    defined.label = rdflib.Literal(label + ' neuron')

    intersection = infixowl.BooleanClass(members=(graph.expand(NIFCELL_NEURON), restriction), graph=graph.g)
    #intersection = infixowl.BooleanClass(members=(restriction,), graph=self.graph.g)
    defined.equivalentClass = [intersection]
    if parent is not None:
        defined.subClassOf = [graph.expand(parent)]
    return ilx_start

    # TODO I think the defined class disjointness needs additional code... selecting from phenotype disjointness?
    #for dj in self.:
        #defined.disjointWith = [infixowl.Restriction(self.expand('ilx:hasPhenotype'), graph=self.graph.g, someValuesFrom=dj)]

def pprint(thing):
    for t in thing:
        print()
        for v in t:
            print(v)

def disjointUnionOf(graph, members):
    start = rdflib.BNode()
    current = start
    for member in members[:-1]:
        graph.add((current, rdflib.RDF.first, member))
        next_ = rdflib.BNode()
        graph.add((current, rdflib.RDF.rest, next_))
        current = next_

    graph.add((current, rdflib.RDF.first, members[-1]))
    graph.add((current, rdflib.RDF.rest, rdflib.RDF.nil))

    return start

def make_mutually_disjoint(graph, members):
    if len(members) > 1:
        first, rest = members[0], members[1:]
        for r in rest:
            print(first, r)
            graph.add_node(first, rdflib.OWL.disjointWith, r)
        return make_mutually_disjoint(graph, rest)
    else:
        return members

def type_check(tup, types):
    return all([type(t) is ty for t, ty in zip(tup, types)])

def add_types(graph, phenotypes):  # TODO missing expression phenotypes! also basket type somehow :(
    """ Add disjoint union classes so that it is possible to see the invariants
        associated with individual phenotypes """

    collect = defaultdict(set)
    def recurse(id_, start, level=0):
        #print(level)
        for t in graph.g.triples((None, None, id_)):
            if level == 0:
                if t[1] != rdflib.term.URIRef('http://www.w3.org/2002/07/owl#someValuesFrom'):
                    continue
            if type_check(t, (rdflib.term.URIRef, rdflib.term.URIRef, rdflib.term.BNode)):
                #print(start, t[0])
                collect[start].add(t[0])
                return  #  we're done here, otherwise we hit instantiated subclasses
            if level > 1:
                if t[1] == rdflib.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#first') or \
                   t[1] == rdflib.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#rest'):
                    continue

            recurse(t[0], start, level + 1)


    for phenotype in phenotypes:
        recurse(phenotype, phenotype)

    return collect

def get_defined_classes(graph):
    phenotypes = [s for s, p, o in graph.g.triples((None, None, None)) if ' Phenotype' in o]
    inc = get_transitive_closure(graph, rdflib.RDFS.subClassOf, graph.expand('ilx:NeuronPhenotype'))
    collect = []
    def recurse(id_, start, level=0):
        if type(id_) == rdflib.term.URIRef and id_ != start:
            collect.append((start, id_))
            return
            #return start, id_
        for t in graph.g.triples((None, None, id_)):
            if level == 0 and type(t[0]) != rdflib.term.BNode:
                continue
            if level == 4:
                if t[1] !=  rdflib.term.URIRef('http://www.w3.org/2002/07/owl#equivalentClass'):
                    continue
            result = recurse(t[0], start, level + 1)
            #if result:  # this only works if there is a single equivalentClass axiom...
                #return result

    for id_ in inc:
        recurse(id_, id_)

    #for pheno, equiv in collect:
        #print(pheno, equiv, [_ for _ in graph.g.objects(equiv, rdflib.RDFS.label)])

    return collect

def get_transitive_closure(graph, edge, root):
    trips = set([t for t in graph.g.triples((None, edge, None))])
    valid_parents = {root}
    include = set()
    new_vp = set()
    old_len = -1
    output = set()
    output.update(valid_parents)
    while len(trips) != old_len:
        for t in trips:
            if t[2] in valid_parents:
                new_vp.add(t[0])
                include.add(t)
        valid_parents = new_vp
        output.update(valid_parents)
        old_len = len(trips)
        trips = trips - include

    return output

def make_phenotypes():
    ilx_start = 50114
    graph = makeGraph('NIF-Phenotype-Core', prefixes=PREFIXES)
    graph2 = makeGraph('NIF-Phenotypes', prefixes=PREFIXES)
    

    eont = OntMeta('http://ontology.neuinfo.org/NIF/ttl/',
                   'NIF-Neuron-Defined',
                   'NIF Neuron Defined Classes',
                   'NIFNEUDEF',
                   'This file contains defined classes derived from neuron phenotypes.',
                   TODAY)
    defined_graph = makeGraph(eont.filename, prefixes=PREFIXES)
    ontid = eont.path + eont.filename + '.ttl'
    defined_graph.add_ont(ontid, *eont[2:])

    # do edges first since we will need them for the phenotypes later
    # TODO real ilx_ids and use prefixes to manage human readability
    with open(refile(__file__, 'resources/neuron_phenotype_edges.csv'), 'rt') as f:
        rows = [r for r in csv.reader(f)]
    
    lookup = {
        'asymmetric':'owl:AsymmetricProperty',
        'irreflexive':'owl:IrreflexiveProperty',
        'functional':'owl:FunctionalProperty',
    }
    pedges = set()
    def irn(inp): return ILXREPLACE(__name__ + inp)
    for row in rows[1:]:
        if row[0].startswith('#') or not row[0]:
            if row[0] == '#references':
                break
            print(row)
            continue
        id_ = PREFIXES['ilx'] + row[0]
        pedges.add(graph.expand('ilx:' + row[0]))
        graph.add_node(id_, rdflib.RDFS.label, row[0])  # FIXME
        graph.add_node(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
        if row[3]:
            graph.add_node(id_, rdflib.namespace.SKOS.definition, row[3])
        if row[6]:
            graph.add_node(id_, rdflib.RDFS.subPropertyOf, 'ilx:' + row[6])
        if row[7]:
            graph.add_node(id_, rdflib.OWL.inverseOf, 'ilx:' + row[7])
        if row[8]:
            for t in row[8].split(','):
                t = t.strip()
                graph.add_node(id_, rdflib.RDF.type, lookup[t])

    with open(refile(__file__, 'resources/neuron_phenotype.csv'), 'rt') as f:
        rows = [r for r in csv.reader(f) if any(r) and not r[0].startswith('#')]

    class PP(rowParse):  # FIXME use add_new in _row_post?
        SCD = 'subClassesDisjoint'
        DJW = 'disjointWith'
        def __init__(self):
            self.ilx_start = ilx_start
            self.parent_child_map = defaultdict(set)
            self.child_parent_map = defaultdict(set)
            self.scd = set()
            super().__init__(rows)

        def ilx_id(self, value):
            self.id_ = graph2.expand(value)
            self.Class = infixowl.Class(self.id_, graph=graph2.g)
            label = ' '.join(re.findall(r'[A-Z][a-z]*', self.id_.split(':')[1]))
            self._label = label

        def subClassOf(self, value):
            if value:
                self.parent = graph2.expand(value)
                self.parent_child_map[self.parent].add(self.id_)
                self.child_parent_map[self.id_].add(self.parent)
                self.Class.subClassOf = [self.parent]

        def label(self, value):
            if value:
                self._label = value
                self.Class.label = value
            else:
                self.Class.label = rdflib.Literal(self._label)

        def synonyms(self, value):
            if value:
                for v in value.split(','):
                    graph2.add_node(self.id_, 'OBOANN:synonym', v)

        def rules(self, value):
            if value == PP.SCD:
                self.scd.add(self.id_)
            elif value.startswith(PP.DJW):
                [graph2.add_node(self.id_, rdflib.OWL.disjointWith, _) for _ in value.split(' ')[1:]]

        def use_edge(self, value):
            if value:
                graph2.add_node(self.id_, 'ilx:useObjectProperty', graph.expand('ilx:' + value))

        def _row_post(self):
            # defined class
            lookup = {
                graph.expand('ilx:AxonPhenotype'):rdflib.URIRef('http://axon.org'),
                graph.expand('ilx:AxonMorphologicalPhenotype'):None,
                graph.expand('ilx:DendritePhenotype'):rdflib.URIRef('http://dendrite.org'),
                graph.expand('ilx:DendriteMorphologicalPhenotype'):None,
                graph.expand('ilx:SomaPhenotype'):rdflib.URIRef('http://soma.org'),
                graph.expand('ilx:SomaMorphologicalPhenotype'):None,
                graph.expand('ilx:NeuronPhenotype'):graph.expand(NIFCELL_NEURON),
                graph.expand('ilx:CellPhenotype'):None,
                graph.expand('ilx:Phenotype'):graph.expand('ilx:Phenotype'),
            }
            if self.id_ in lookup:
                return
            #elif 'Petilla' in self.id_:
                #return
            #else:
                #print(self.id_)

            # hidden label for consturctions
            graph2.add_node(self.id_, rdflib.namespace.SKOS.hiddenLabel, self._label.rsplit(' Phenotype')[0])

            self.ilx_start += 1
            id_ = defined_graph.expand(ilx_base.format(self.ilx_start))
            defined = infixowl.Class(id_, graph=defined_graph.g)
            #defined.label = rdflib.Literal(self._label.rstrip(' Phenotype') + ' neuron')  # the extra space in rstrip removes 'et ' as well WTF!
            defined.label = rdflib.Literal(self._label.rstrip('Phenotype') + 'neuron')
            #print(self._label)
            print('_row_post ilx_start', self.ilx_start, list(defined.label)[0])

            def getPhenotypeEdge(phenotype):
                print(phenotype)
                edge = 'ilx:hasPhenotype'  # TODO in neuronManager...
                return edge
            edge = getPhenotypeEdge(self.id_)
            restriction = infixowl.Restriction(graph.expand(edge), graph=defined_graph.g, someValuesFrom=self.id_)

            parent = [p for p in self.child_parent_map[self.id_] if p]
            if parent:
                parent = parent[0]
                while 1:
                    if parent == defined_graph.expand('ilx:NeuronPhenotype'):
                        #defined.subClassOf = [graph.expand(defined_class_parent)]  # XXX this does not produce what we want
                        break
                    #else:
                        #print(parent, graph.expand('ilx:NeuronPhenotype'))

                    #print('xxxxxxxxxxxxxxxx', parent)
                    new_parent = [p for p in self.child_parent_map[parent] if p]
                    if new_parent:
                        parent = new_parent[0]
                    else:
                        break
                phenotype_equiv = lookup[parent]
            else:
                return


            intersection = infixowl.BooleanClass(members=(phenotype_equiv, restriction), graph=defined_graph.g)
            ##intersection = infixowl.BooleanClass(members=(restriction,), graph=self.graph.g)

            defined.equivalentClass = [intersection]

        def _end(self):
            for parent in self.scd:
                make_mutually_disjoint(graph2, list(self.parent_child_map[parent]))

    pp = PP()
    ilx_start = pp.ilx_start

    to_add = {}
    def lsn(word):
        rank = defaultdict(lambda:0)
        rank['PR'] = -100
        rank['NIFMOL'] = -50
        rank['UBERON'] = -10
        rank['NCBITaxon'] = -9
        rank['NIFCELL'] = -8
        sort_rank = lambda r: rank[r['curie'].split(':')[0]]
        to_add[word] = graph2.expand(sorted(sgv.findByTerm(word), key=sort_rank)[0]['curie'])  # cheating

    # FIXME naming
    lsn('Parvalbumin')
    lsn('neuropeptide Y')
    lsn('VIP peptides')
    lsn('somatostatin')
    lsn('calbindin')
    lsn('calretinin')

    #for name, iri in to_add.items():  # XXX do not need, is already covered elsewhere
        #print('make_phenotypes ilx_start', ilx_start, name)
        #ilx_start = make_defined(defined_graph, ilx_start, name, iri, 'ilx:hasExpressionPhenotype', parent=expression_defined)

    #syn_mappings['calbindin'] = graph.expand('PR:000004967')  # cheating
    #syn_mappings['calretinin'] = graph.expand('PR:000004968')  # cheating
    ontid = 'http://ontology.neuinfo.org/NIF/ttl/' + graph.name + '.ttl'
    graph.add_ont(ontid, 'NIF Phenotype core', comment= 'This is the core set of predicates used to model phenotypes and the parent class for phenotypes.')
    graph.add_class('ilx:Phenotype', label='Phenotype')
    graph.add_node('ilx:Phenotype', 'skos:definition', 'A Phenotype is a binary property of a biological entity. Phenotypes are derived from measurements made on the subject of interest. While Phenotype is not currently placed within the BFO hierarchy, if we were to place it, it would fall under BFO:0000016 -> disposition, since these phenotypes are contingent on the experimental conditions under which measurements were made and are NOT qualities. For consideration: in theory this would mean that disjointness does not make sense, even for things that would seem to be obviously disjoint such as Accomodating and Non-Accomodating. However, this information can still be captured on a subject by subject basis by asserting that for this particular entity, coocurrance of phenotypes is not possilbe. This still leaves the question of whether the class of biological entities that correspond to the bag of phenotypes is implicitly bounded/limited only to the extrinsic and unspecified experimental contidions, some of which are not and cannot be included in a bag of phenotypes. The way to deal with this when we want to include 2 \'same time\' disjoint phenotypes, is to use a logical phenotype to wrap them with an auxillary variable that we think accounts for the difference.')
    #graph.add_node(ontid, rdflib.RDFS.comment, 'The NIF Neuron ontology holds materialized neurons that are collections of phenotypes.')
    #graph.add_node(ontid, rdflib.OWL.versionInfo, ONTOLOGY_DEF['version'])
    #graph.g.commit()
    #get_defined_classes(graph)  # oops...
    graph.write()  # moved below to incorporate uwotm8
    
    ontid2 = 'http://ontology.neuinfo.org/NIF/ttl/' + graph2.name + '.ttl'
    graph2.add_ont(ontid2, 'NIF Phenotypes', comment='A taxonomy of phenotypes used to model biological types as collections of measurements.')
    graph2.add_node(ontid2, 'owl:imports', ontid)
    graph2.write()
    
    syn_mappings = {}
    for sub, syn in [_ for _ in graph.g.subject_objects(graph.expand('OBOANN:synonym'))] + [_ for _ in graph.g.subject_objects(rdflib.RDFS.label)]:
        syn = syn.toPython()
        if syn in syn_mappings:
            print('ERROR duplicate synonym!', syn, sub)
        syn_mappings[syn] = sub


    phenotypes = [s for s, p, o in graph.g.triples((None, None, None)) if ' Phenotype' in o]
    inc = get_transitive_closure(graph, rdflib.RDFS.subClassOf, graph.expand('ilx:NeuronPhenotype'))  # FIXME not very configurable...

    return syn_mappings, pedges, ilx_start, inc, defined_graph

def _rest_make_phenotypes():
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
            xr.add_node(d['xrefs'][0], 'oboInOwl:replacedBy', id_)
            #dg.add_node(d['xrefs'][0], 'oboInOwl:replacedBy', id_)
            new_terms[d['xrefs'][1]] = {'replaced_by':id_}
            xr.add_node(d['xrefs'][1], 'oboInOwl:replacedBy', id_)
            #dg.add_node(d['xrefs'][1], 'oboInOwl:replacedBy', id_)

            data['labels'] = [d['label'], d['o']]
            #dg.add_node(id_, rdflib.RDFS.label, d['label'])
            dg.add_node(id_, rdflib.RDFS.label, d['o'])
            data['xrefs'] = d['xrefs']
            for x in d['xrefs']:  # FIXME... expecting order of evaluation errors here...
                dg.add_node(id_, 'oboInOwl:hasDbXref', x)  # xr
                xr.add_node(id_, 'oboInOwl:hasDbXref', x)  # x

        elif spre.toPython() != 'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#' or ng.namespace_manager.qname(s).replace('default1','NIFQUAL') in desired_nif_terms:  # skip non-xref quals
            #print(ng.namespace_manager.qname(s).replace('default1','NIFQUAL'))
            new_terms[s] = {'replaced_by':id_}
            xr.add_node(s, 'oboInOwl:replacedBy', id_)
            data['labels'] = [o.toPython()]
            dg.add_node(id_, rdflib.RDFS.label, o.toPython())
            data['xrefs'] = [s]
            dg.add_node(id_, 'oboInOwl:hasDbXref', s)  # xr
            xr.add_node(id_, 'oboInOwl:hasDbXref', s)  # xr
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

    #dg.write(convert=False)
    xr.write(convert=False)

    #skip this for now, we can use DG to do lookups later
    #for t in dg.g.triples((None, None, None)):
        #g.add_node(*t)  # only way to clean prefixes :/
    add_phenotypes(g)
    g.write(convert=False)

    g2 = makeGraph('pheno-comp', PREFIXES)
    for t in ng.triples((None, None, None)):
        g2.add_node(*t)  # only way to clean prefixes :/

    g2.write(convert=False)
    
    syn_mappings = {}
    for sub, syn in [_ for _ in g.g.subject_objects(g.expand('OBOANN:synonym'))] + [_ for _ in g.g.subject_objects(rdflib.RDFS.label)]:
        syn = syn.toPython()
        if syn in syn_mappings:
            print('ERROR duplicate synonym!', syn, sub)
        syn_mappings[syn] = sub

    #embed()
    return syn_mappings, pedges, ilx_start

def make_neurons(syn_mappings, pedges, ilx_start_, defined_graph):
    ilx_start = ilx_start_
    cheating = {'vasoactive intestinal peptide':'VIP',
                'star':None,  # is a morphological phen that is missing but hits scigraph
               }
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
    _temp = rdflib.Graph()  # use a temp to strip nasty namespaces
    _temp.parse(os.path.expanduser(hbp_cell), format='turtle')
    for s, p, o in _temp.triples((None,None,None)):
        if s != rdflib.URIRef('http://ontology.neuinfo.org/NIF/ttl/generated/NIF-Neuron-HBP-cell-import.ttl'):
            ng.g.add((s,p,o))

    base = 'http://ontology.neuinfo.org/NIF/ttl/' 

    ontid = base + ng.name + '.ttl'
    ng.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    ng.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-Phenotype.ttl')
    ng.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-Defined.ttl')
    ng.add_node(ontid, rdflib.OWL.imports, base + 'hbp-special.ttl')
    #ng.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Cell.ttl')  # NO!
    #ng.add_node(ontid, rdflib.OWL.imports, base + 'external/uberon.owl')
    #ng.add_node(ontid, rdflib.OWL.imports, base + 'external/pr.owl')
    ng.replace_uriref('ilx:hasMolecularPhenotype', 'ilx:hasExpressionPhenotype')

    #defined_graph = makeGraph('NIF-Neuron-Defined', prefixes=PREFIXES, graph=_g)
    defined_graph.add_node(base + defined_graph.name + '.ttl', rdflib.RDF.type, rdflib.OWL.Ontology)
    defined_graph.add_node(base + defined_graph.name + '.ttl', rdflib.OWL.imports, base + 'NIF-Neuron-Phenotype.ttl')

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

                ng.add_hierarchy(id_, p, s)
                ng.g.remove((s, p, o_lit))
                #print('SUCCESS, substituting', o, 'for', id_)
                success = True
                true_o = o_lit
                true_id = id_

            elif 'Location' in p.toPython() or 'LocatedIn' in p.toPython():  # lift location to restrictions
                if o.startswith('http://'):
                    ng.add_hierarchy(o_lit, p, s)
                    ng.g.remove((s, p, o_lit))

                    data = sgv.findById(o)
                    label = data['labels'][0]
                    ng.add_node(o, rdflib.RDF.type, rdflib.OWL.Class)
                    ng.add_node(o, rdflib.RDFS.label, label)

                    success = True
                    true_o = label
                    true_id = o_lit

            else:
                if o in cheating:
                    o = cheating[o]

                data = sgv.findByTerm(o)
                if data:
                    print('SCIGRAPH', [(d['curie'], d['labels']) for d in data])
                    for d in data:
                        if 'PR:' in d['curie']:
                            sgt = ng.expand(d['curie'])
                            ng.add_hierarchy(sgt, p, s)
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
                                ng.add_hierarchy(sgt, p, s)
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
                t = tuple(defined_graph.g.triples((None, rdflib.OWL.someValuesFrom, true_id)))
                if t:
                    print('ALREADY IN', t)
                else:
                    ilx_start += 1
                    id_ = ng.expand(ilx_base.format(ilx_start))
                    defined_graph.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
                    restriction = infixowl.Restriction(p, graph=defined_graph.g, someValuesFrom=true_id)
                    intersection = infixowl.BooleanClass(members=(defined_graph.expand(NIFCELL_NEURON), restriction), graph=defined_graph.g)
                    this = infixowl.Class(id_, graph=defined_graph.g)
                    this.equivalentClass = [intersection]
                    this.subClassOf = [defined_graph.expand(defined_class_parent)]
                    this.label = rdflib.Literal(true_o + ' neuron')
                    print('make_neurons ilx_start', ilx_start, list(this.label)[0])
                    if not done:
                        embed()
                        done = True

    defined_graph.add_class(defined_class_parent, NIFCELL_NEURON, label='defined class neuron')
    defined_graph.add_node(defined_class_parent, rdflib.namespace.SKOS.definition, 'Parent class For all defined class neurons')

    defined_graph.write()
    ng.write()

    for sub, syn in [_ for _ in ng.g.subject_objects(ng.expand('OBOANN:synonym'))] + [_ for _ in ng.g.subject_objects(rdflib.RDFS.label)]:
        syn = syn.toPython()
        if syn in syn_mappings:
            print('ERROR duplicate synonym!', syn, sub)
        syn_mappings[syn] = sub

    return ilx_start

def add_phenotypes(graph):

    cell_phenotype = 'ilx:CellPhenotype'
    neuron_phenotype = 'ilx:NeuronPhenotype'
    #ephys_phenotype = 'ilx:ElectrophysiologicalPhenotype'
    #spiking_phenotype = 'ilx:SpikingPhenotype'
    #i_spiking_phenotype = 'ilx:PetillaInitialSpikingPhenotype'
    burst_p = 'ilx:PetillaInitialBurstSpikingPhenotype'
    classical_p = 'ilx:PetillaInitialClassicalSpikingPhenotype'
    delayed_p = 'ilx:PetillaInitialDelayedSpikingPhenotype'
    #s_spiking_phenotype = 'ilx:PetillaSustainedSpikingPhenotype'
    #morpho_phenotype = 'ilx:MorphologicalPhenotype'
    ac_p = 'ilx:PetillaSustainedAccomodatingPhenotype'
    nac_p = 'ilx:PetillaSustainedNonAccomodatingPhenotype'
    st_p = 'ilx:PetillaSustainedStutteringPhenotype'
    ir_p = 'ilx:PetillaSustainedIrregularPhenotype'

    #fast = 'ilx:FastSpikingPhenotype'
    #reg_int = 'ilx:RegularSpikingNonPyramidalPhenotype'

    graph.add_class(cell_phenotype, autogen=True)
    graph.add_class(neuron_phenotype, cell_phenotype, autogen=True)
    graph.add_class(ephys_phenotype, neuron_phenotype, autogen=True)
    graph.add_class(spiking_phenotype, ephys_phenotype, autogen=True)
    graph.add_class(fast_phenotype, spiking_phenotype,('Fast spiking'), autogen=True)
    graph.add_class(reg_phenotype, spiking_phenotype,('Non-fast spiking','Regular spiking non-pyramidal'), autogen=True)
    graph.add_class(i_spiking_phenotype, spiking_phenotype, autogen=True)
    iClass = infixowl.Class(graph.expand(i_spiking_phenotype), graph=graph.g)

    graph.add_class(burst_p, i_spiking_phenotype, ('burst',), autogen=True)
    graph.add_class(classical_p, i_spiking_phenotype, ('classical',), autogen=True)
    graph.add_class(delayed_p, i_spiking_phenotype, ('delayed',), autogen=True)
    graph.add_class(s_spiking_phenotype, spiking_phenotype, autogen=True)
    sClass = infixowl.Class(graph.expand(s_spiking_phenotype), graph=graph.g)
    sClass.disjointWith = [iClass]

    graph.add_class(ac_p, s_spiking_phenotype, ('accomodating',), autogen=True)  # FIXME this is silly
    graph.add_class(nac_p, s_spiking_phenotype, ('non accomodating',), autogen=True)
    graph.add_class(st_p, s_spiking_phenotype, ('stuttering',), autogen=True)
    graph.add_class(ir_p, s_spiking_phenotype, ('irregular',), autogen=True)
    graph.add_class(morpho_phenotype, neuron_phenotype, autogen=True)

class table1:
    pass # dead

def make_table1(syn_mappings, ilx_start, phenotypes):
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
    #
    # need a full type restriction... property chain?

    graph = makeGraph('hbp-special', prefixes=PREFIXES)  # XXX fix all prefixes

    with open(refile(__file__, 'resources/26451489 table 1.csv'), 'rt') as f:
        rows = [list(r) for r in zip(*csv.reader(f))]

    base = 'http://ontology.neuinfo.org/NIF/ttl/' 
    ontid = base + graph.name + '.ttl'
    graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    graph.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-Phenotype.ttl')
    graph.add_node(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-Defined.ttl')

    def lsn(word):
        syn_mappings[word] = graph.expand(sgv.findByTerm(word)[0]['curie'])  # cheating
    lsn('Parvalbumin')
    lsn('neuropeptide Y')
    lsn('VIP peptides')
    lsn('somatostatin')
    syn_mappings['calbindin'] = graph.expand('PR:000004967')  # cheating
    syn_mappings['calretinin'] = graph.expand('PR:000004968')  # cheating
    t = table1(graph, rows, syn_mappings, ilx_start)
    ilx_start = t.ilx_start

    # adding fake mouse data
    #with open(refile(__file__, 'resources/26451489 table 1.csv'), 'rt') as f:  # FIXME annoying
        #rows = [list(r) for r in zip(*csv.reader(f))]
    #t2 = table1(graph, rows, syn_mappings, ilx_start, species='NCBITaxon:10090')  # FIXME double SOM+ phenos etc
    #ilx_start = t2.ilx_start

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
                d = sgv.findById(o)
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
    #graph.add_node(defined_class_parent, rdflib.RDF.type, rdflib.OWL.Class)
    #graph.add_node(defined_class_parent, rdflib.RDFS.label, 'defined class neuron')
    #graph.add_node(defined_class_parent, rdflib.namespace.SKOS.description, 'Parent class For all defined class neurons')
    #graph.add_node(defined_class_parent, rdflib.RDFS.subClassOf, NIFCELL_NEURON)
    #graph.add_node(morpho_defined, rdflib.RDFS.subClassOf, defined_class_parent)
    #graph.add_node(morpho_defined, rdflib.RDFS.label, 'Morphologically classified neuron')  # FIXME -- need asserted in here...
    #graph.add_node(ephys_defined, rdflib.RDFS.subClassOf, defined_class_parent)
    #graph.add_node(ephys_defined, rdflib.RDFS.label, 'Electrophysiologically classified neuron')

    graph.add_class(expression_defined, NIFCELL_NEURON, autogen=True)
    graph.add_class('ilx:NeuroTypeClass', NIFCELL_NEURON, label='Neuron TypeClass')

    graph.g.commit()

    phenotype_dju_dict = add_types(graph, phenotypes)
    for pheno, disjoints in phenotype_dju_dict.items():
        name = ' '.join(re.findall(r'[A-Z][a-z]*', pheno.split(':')[1])[:-1])  #-1: drops Phenotype
        ilx_start += 1# = make_defined(graph, ilx_start, name + ' neuron type', pheno, 'ilx:hasPhenotype')
        id_ = graph.expand(ilx_base.format(ilx_start))
        typeclass = infixowl.Class(id_, graph=graph.g)
        typeclass.label = rdflib.Literal(name + ' neuron type')

        restriction = infixowl.Restriction(graph.expand('ilx:hasPhenotype'), graph=graph.g, someValuesFrom=pheno)
        #typeclass.subClassOf = [restriction, graph.expand('ilx:NeuroTypeClass')]

        ntc = graph.expand('ilx:NeuroTypeClass')
        intersection = infixowl.BooleanClass(members=(ntc, restriction), graph=graph.g)
        typeclass.equivalentClass = [intersection]

        # FIXME not clear that we should be doing typeclasses this way.... :/
        # requires more thought, on the plus side you do get better reasoning...
        disjointunion = disjointUnionOf(graph=graph.g, members=list(disjoints))
        graph.add_node(id_, rdflib.OWL.disjointUnionOf, disjointunion)


    graph.write()
    return t
    #print(t._set_Electrical_types)
    #_ = [[print(v) for v in [k] + list(v) + ['\n']] for k,v in t.__dict__.items() if '_set_' in k]

#def pattern_match(start, chain):   # sparql?
    # start -> predicate1 -> anon.Class -> predicate2 -> ( -> anon.Restriction -> predicate3 -> match
    # match <- predicate3 <- [predicate2 <- ([predicate1 <- start

def expand_syns(syn_mappings):
    for syn, iri in list(syn_mappings.items()):
        lower = syn.lower()
        lower_less_phenotype = lower.rsplit(' phenotype')[0]
        syn_mappings[lower] = iri
        #print()
        #print(lower)
        #print(lower_less_phenotype)
        #print()
        if lower_less_phenotype != lower:
            syn_mappings[lower_less_phenotype] = iri

def predicate_disambig(graph):
    # the useful idiot holds 'appriopriate' predicate/phenotype mappings where there may be some ambiguity (e.g. brain region vs layer) it is OK to hardcode these
    # the ui is not an owl:Class
    ui = ILXREPLACE('phenotype predicate disambiguation')
    def uit(p, o):
        out = (ui, graph.expand(p), graph.expand(o))
        graph.add_node(*out)
        return out
        
    uit('ilx:hasLayerLocation', 'UBERON:0005390')
    uit('ilx:hasLayerLocation', 'UBERON:0005391')
    uit('ilx:hasLayerLocation', 'UBERON:0005392')
    uit('ilx:hasLayerLocation', 'UBERON:0005393')
    uit('ilx:hasLayerLocation', 'UBERON:0005394')
    uit('ilx:hasLayerLocation', 'UBERON:0005395')

def main():
    syn_mappings, pedge, ilx_start, phenotypes, defined_graph = make_phenotypes()
    return 
    syn_mappings['thalamus'] = defined_graph.expand('UBERON:0001879')
    expand_syns(syn_mappings)
    ilx_start = make_neurons(syn_mappings, pedge, ilx_start, defined_graph)
    t = make_table1(syn_mappings, ilx_start, phenotypes)
    embed()

if __name__ == '__main__':
    main()

