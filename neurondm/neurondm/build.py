#!/usr/bin/env python3
""" run neurondm related exports and conversions
Usage:
    neurondm-build release [options]
    neurondm-build all [options]
    neurondm-build [indicators phenotypes] [options]
    neurondm-build [models bridge old dep dev] [options]
    neurondm-build [sheets] [options]

Options:
    -h --help                   Display this help message
"""

import io
import os
import re
import csv
import types
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote
import rdflib
import ontquery as oq
from rdflib.extras import infixowl
from pyontutils.core import makeGraph, createOntology, OntId as OntId_, OntConjunctiveGraph
from pyontutils.utils import TODAY, rowParse, refile, makeSimpleLogger, anyMembers
from pyontutils.obo_io import OboFile
from neurondm import _NEURON_CLASS, OntTerm
from neurondm.core import OntTermOntologyOnly, OntTermInterLexOnly, log as _log, auth
from pyontutils.scigraph import Graph, Vocabulary
from pyontutils.namespaces import (makePrefixes,
                                   makeNamespaces,
                                   TEMP,
                                   ilxtr,
                                   BFO,
                                   NIFRID,
                                   definition,
                                   ilx_partOf,
                                   partOf as BFO_partOf,
                                   rdf,
                                   rdfs,
                                   owl)
from itertools import chain
from neurondm.indicators import PhenotypeIndicators

try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint

log = _log.getChild('build')

resources = auth.get_path('resources')

NIFRAW, NIFTTL = makeNamespaces('NIFRAW', 'NIFTTL')

sgg = Graph(cache=True, verbose=True)
sgv = Vocabulary(cache=True)

# TODO future workflow: existing representation -> bags -> owl
# vastly preferred to the current nightmare
# the main things we need for the first arrow is a nice way to
# map to names of known phenotypes, so we need to load NNP and make sure
# for the second arrow we basically need to improve neuronManager

# consts
defined_class_parent = 'ilxtr:definedClassNeurons'
morpho_defined = 'ilxtr:definedClassNeuronsMorpho'
ephys_defined = 'ilxtr:definedClassNeuronsElectro'
morpho_phenotype =  'ilxtr:MorphologicalPhenotype'
morpho_edge = 'ilxtr:hasMorphologicalPhenotype'
ephys_phenotype = 'ilxtr:ElectrophysiologicalPhenotype'
ephys_edge = 'ilxtr:hasElectrophysiologicalPhenotype'
spiking_phenotype = 'ilxtr:SpikingPhenotype'
i_spiking_phenotype = 'ilxtr:PetillaInitialSpikingPhenotype'
s_spiking_phenotype = 'ilxtr:PetillaSustainedSpikingPhenotype'
spiking_edge = 'ilxtr:hasSpikingPhenotype'
fast_phenotype = 'ilxtr:FastSpikingPhenotype'
reg_phenotype = 'ilxtr:RegularSpikingNonPyramidalPhenotype'
expression_edge = 'ilxtr:hasExpressionPhenotype'
expression_defined = 'ilxtr:ExpressionClassifiedNeuron'
NIFCELL_NEURON = 'SAO:1417703748'  # 'NIFCELL:sao1417703748'

syntax = '{region}{layer_or_subregion}{expression}{ephys}{molecular}{morph}{cellOrNeuron}'
ilx_base = 'ILX:{:0>7}'

oq.OntCuries({'pheno': ilxtr['Phenotype/'],
              'MMRRC': 'http://www.mmrrc.org/catalog/getSDS.jsp?mmrrc_id='})
PREFIXES = {**makePrefixes('ilxtr',
                           'ILX',
                           'skos',
                           'owl',
                           'dc',
                           'nsu',
                           'CHEBI',
                           'NCBIGene',
                           'NCBITaxon',
                           'oboInOwl',
                           'NIFEXT',
                           'NIFRID',
                           'NLXCELL',
                           'SAO',
                           'UBERON',
                           'PR',),
            'TEMP':str(TEMP),
            'pheno':ilxtr['Phenotype/'],
}

def replace_object(find, replace, graph):  # note that this is not a sed 's/find/replace/g'
    find = graph.expand(find)
    for s, p, o in graph.g.triples((None, None, find)):
        graph.add_trip(s, p, replace)
        graph.g.remove((s, p, o))

def make_defined(graph, ilx_start, label, phenotype_id, restriction_edge, parent=None):
    ilx_start += 1
    id_ = TEMP['defined-neuron/' + label]
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
        #defined.disjointWith = [infixowl.Restriction(self.expand('ilxtr:hasPhenotype'), graph=self.graph.g, someValuesFrom=dj)]

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
            log.debug(f'{first} {r}')
            graph.add_trip(first, rdflib.OWL.disjointWith, r)
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
    inc = get_transitive_closure(graph, rdflib.RDFS.subClassOf, graph.expand('ilxtr:NeuronPhenotype'))
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


class OntId(OntId_):
    @property
    def u(self):
        return rdflib.URIRef(self)


def add_types(ng):
    graph = ng.g
    triples = (
        (ilxtr.NeuronCUT, rdf.type, owl.Class),
        (ilxtr.NeuronCUT, rdfs.subClassOf, OntId(_NEURON_CLASS).u),
        (ilxtr.NeuronEBM, rdf.type, owl.Class),
        (ilxtr.NeuronEBM, rdfs.subClassOf, OntId(_NEURON_CLASS).u),
    )
    [graph.add(t) for t in triples]


def phenotype_core_triples():
    yield ilxtr.delineates, owl.inverseOf, ilxtr.isDelineatedBy


def make_phenotypes():
    ilx_start = 50114

    olr = auth.get_path('ontology-local-repo')
    writeloc = olr / 'ttl'
    graph = makeGraph('phenotype-core',
                      writeloc=writeloc,
                      prefixes=PREFIXES)
    graph2 = makeGraph('phenotypes',
                       writeloc=writeloc,
                       prefixes=PREFIXES)

    defined_graph = createOntology(filename='NIF-Neuron-Defined',
                                   path='ttl/',
                                   prefixes=PREFIXES)

    edg = rdflib.Graph().parse(defined_graph.filename, format='turtle')
    defined_id_lookup = {o.value:s for s, o in edg.subject_objects(rdflib.RDFS.label)}
    log.debug(defined_id_lookup)

    # do edges first since we will need them for the phenotypes later
    # TODO real ilx_ids and use prefixes to manage human readability
    with open((resources / 'neuron_phenotype_edges.csv').as_posix(), 'rt') as f:
        rows = [r for r in csv.reader(f)]

    lookup = {
        'symmetric':'owl:SymmetricProperty',
        'asymmetric':'owl:AsymmetricProperty',
        'irreflexive':'owl:IrreflexiveProperty',
        'functional':'owl:FunctionalProperty',
    }
    pedges = set()
    for row in rows[1:]:
        if row[0].startswith('#') or not row[0]:
            if row[0] == '#references':
                break
            log.debug(row)
            continue
        id_ = ilxtr[row[0]]
        pedges.add(graph.expand('ilxtr:' + row[0]))
        graph.add_trip(id_, rdflib.RDFS.label, row[0])  # FIXME
        graph.add_trip(id_, rdflib.RDF.type, rdflib.OWL.ObjectProperty)
        if row[3]:
            graph.add_trip(id_, rdflib.namespace.SKOS.definition, row[3])
        if row[5]:
            graph.add_trip(id_, 'rdfs:comment', row[5])
        if row[6]:
            supers = row[6].split(',')
            for sup in supers:
                graph.add_trip(id_, rdflib.RDFS.subPropertyOf, 'ilxtr:' + sup)
        if row[7]:
            graph.add_trip(id_, rdflib.OWL.inverseOf, 'ilxtr:' + row[7])
        if row[8]:
            for t in row[8].split(','):
                t = t.strip()
                graph.add_trip(id_, rdflib.RDF.type, lookup[t])

    with open((resources / 'neuron_phenotype.csv').as_posix(), 'rt') as f:
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
            if 'Cone' in label or 'Rod' in label or 'Disc' in label:  # sigh hard coding
                label = label.replace(' Morphological', '')
            self._label = label.capitalize()

        def subClassOf(self, value):
            if value:
                values = value.split(',')
                for v in values:
                    self.parent = graph2.expand(v)
                    self.parent_child_map[self.parent].add(self.id_)
                    self.child_parent_map[self.id_].add(self.parent)
                    self.Class.subClassOf = [self.parent]

        def label(self, value):
            if value:
                self._label = value
                self.Class.label = rdflib.Literal(value)
            else:
                self.Class.label = rdflib.Literal(self._label)

        def notes(self, value):
            if value:
                graph2.add_trip(self.id_, 'rdfs:comment', value)

        def synonyms(self, value):
            if value:
                for v in value.split(','):
                    graph2.add_trip(self.id_, 'NIFRID:synonym', v)

        def rules(self, value):
            if value == PP.SCD:
                self.scd.add(self.id_)
            elif value.startswith(PP.DJW):
                [graph2.add_trip(self.id_, rdflib.OWL.disjointWith, _) for _ in value.split(' ')[1:]]

        def use_edge(self, value):
            if value:
                graph2.add_trip(self.id_, 'ilxtr:useObjectProperty', graph.expand('ilxtr:' + value))

        def _row_post(self):
            # defined class
            lookup = {
                graph.expand('ilxtr:AxonPhenotype'):rdflib.URIRef('http://axon.org'),
                graph.expand('ilxtr:AxonMorphologicalPhenotype'):None,
                graph.expand('ilxtr:DendritePhenotype'):rdflib.URIRef('http://dendrite.org'),
                graph.expand('ilxtr:DendriteMorphologicalPhenotype'):None,
                graph.expand('ilxtr:SomaPhenotype'):rdflib.URIRef('http://soma.org'),
                graph.expand('ilxtr:SomaMorphologicalPhenotype'):None,
                graph.expand('ilxtr:NeuronPhenotype'):graph.expand(NIFCELL_NEURON),  # we changed this structure...
                graph.expand('ilxtr:CellPhenotype'):None,
                #graph.expand('ilxtr:Phenotype'):graph.expand('ilxtr:Phenotype'),
                graph.expand('ilxtr:Phenotype'):graph.expand(NIFCELL_NEURON),  # FIXME ...
            }
            if self.id_ in lookup:
                return
            #elif 'Petilla' in self.id_:
                #return
            #else:
                #print(self.id_)

            # hidden label for consturctions
            hl = self._label.rsplit(' phenotype')[0]
            if hl.endswith('Morphological'):
                hl = hl.rsplit(' Morphological')[0]

            graph2.add_trip(self.id_, rdflib.namespace.SKOS.hiddenLabel, hl)

            label = rdflib.Literal(self._label.rstrip('phenotype') + 'neuron')

            self.ilx_start += 1
            #id_ = defined_graph.expand(ilx_base.format(self.ilx_start))
            # we have to look up the ids by label now
            if label.value in defined_id_lookup:
                id_ = defined_id_lookup[label.value]
            else:
                id_ = TEMP['newDefinedName' + str(self.ilx_start)]
            defined = infixowl.Class(id_, graph=defined_graph.g)
            defined.label = label
            #defined.label = rdflib.Literal(self._label.rstrip(' Phenotype') + ' neuron')  # the extra space in rstrip removes 'et ' as well WTF!
            #print(self._label)
            log.debug(f'_row_post ilx_start {self.ilx_start} {id_.rsplit("_")[-1]} {list(defined.label)[0]}')

            def getPhenotypeEdge(phenotype):
                log.debug(phenotype)
                edge = 'ilxtr:hasPhenotype'  # TODO in neuronManager...
                return edge
            edge = getPhenotypeEdge(self.id_)
            restriction = infixowl.Restriction(graph.expand(edge), graph=defined_graph.g, someValuesFrom=self.id_)

            parent = [p for p in self.child_parent_map[self.id_] if p]
            if parent:
                parent = parent[0]
                while 1:
                    if parent == defined_graph.expand('ilxtr:NeuronPhenotype'):
                        #defined.subClassOf = [graph.expand(defined_class_parent)]  # XXX this does not produce what we want
                        break
                    #else:
                        #print(parent, graph.expand('ilxtr:NeuronPhenotype'))

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
        rank['NIFEXT'] = -50
        rank['UBERON'] = -10
        rank['NCBITaxon'] = -9
        #rank['NIFCELL'] = -8
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
        #ilx_start = make_defined(defined_graph, ilx_start, name, iri, 'ilxtr:hasExpressionPhenotype', parent=expression_defined)

    #syn_mappings['calbindin'] = graph.expand('PR:000004967')  # cheating
    #syn_mappings['calretinin'] = graph.expand('PR:000004968')  # cheating
    #ontid = 'http://ontology.neuinfo.org/NIF/ttl/' + graph.name + '.ttl'
    ontid = NIFRAW['neurons/ttl/' + graph.name + '.ttl']
    graph.add_ont(ontid, 'NIF Phenotype core', comment= 'This is the core set of predicates used to model phenotypes and the parent class for phenotypes.')
    graph.add_class('ilxtr:Phenotype', label='Phenotype')
    graph.add_trip('ilxtr:Phenotype', 'skos:definition', 'A Phenotype is a binary property of a biological entity. Phenotypes are derived from measurements made on the subject of interest. While Phenotype is not currently placed within the BFO hierarchy, if we were to place it, it would fall under BFO:0000016 -> disposition, since these phenotypes are contingent on the experimental conditions under which measurements were made and are NOT qualities. For consideration: in theory this would mean that disjointness does not make sense, even for things that would seem to be obviously disjoint such as Accommodating and Non-Accommodating. However, this information can still be captured on a subject by subject basis by asserting that for this particular entity, coocurrance of phenotypes is not possible. This still leaves the question of whether the class of biological entities that correspond to the bag of phenotypes is implicitly bounded/limited only to the extrinsic and unspecified experimental conditions, some of which are not and cannot be included in a bag of phenotypes. The way to deal with this when we want to include 2 \'same time\' disjoint phenotypes, is to use a logical phenotype to wrap them with an auxiliary variable that we think accounts for the difference.')
    #graph.add_trip(ontid, rdflib.RDFS.comment, 'The NIF Neuron ontology holds materialized neurons that are collections of phenotypes.')
    #graph.add_trip(ontid, rdflib.OWL.versionInfo, ONTOLOGY_DEF['version'])
    #graph.g.commit()
    #get_defined_classes(graph)  # oops...
    add_types(graph)
    [graph.g.add(t) for t in phenotype_core_triples()]
    graph.write()  # moved below to incorporate uwotm8

    #ontid2 = 'http://ontology.neuinfo.org/NIF/ttl/' + graph2.name + '.ttl'
    ontid2 = NIFRAW['neurons/ttl/' + graph2.name + '.ttl']
    graph2.add_ont(ontid2, 'NIF Phenotypes', comment='A taxonomy of phenotypes used to model biological types as collections of measurements.')
    graph2.add_trip(ontid2, 'owl:imports', ontid)
    graph2.write()

    syn_mappings = {}
    for sub, syn in ([_ for _ in graph2.g.subject_objects(graph2.expand('NIFRID:synonym'))] +
                     [_ for _ in graph2.g.subject_objects(rdflib.RDFS.label)]):
        syn = syn.toPython()
        if syn in syn_mappings:
            log.error(f'duplicate synonym! {syn} {sub}')
        syn_mappings[syn] = sub

    phenotypes_o = [(s, o) for s, p, o in graph2.g.triples((None, None, None)) if ' Phenotype' in o]
    extras = {o.replace('Phenotype', '').strip():s
              for s, o in phenotypes_o}
    epl = {(o.replace('Petilla', '')
            .replace('Initial', '')
            .replace('Sustained', '')
            .replace('Spiking', '')
            .strip()):s for o, s in extras.items()}
    extras.update(epl)
    el = {o.lower():s for o, s in extras.items()}
    extras.update(el)
    syn_mappings.update(extras)
    phenotypes = [s for s, o in phenotypes_o]
    inc = get_transitive_closure(graph2, rdflib.RDFS.subClassOf, graph2.expand('ilxtr:NeuronPhenotype'))  # FIXME not very configurable...

    return syn_mappings, pedges, ilx_start, inc, defined_graph

def _rest_make_phenotypes():
    glb = auth.get_path('git-local-base')
    olr = auth.get_path('ontology-local-repo')
    #phenotype sources
    neuroner = (glb /
                'neuroNER/resources/bluima/neuroner/hbp_morphology_ontology.obo').as_posix()
    neuroner1 = (glb /
                 'neuroNER/resources/bluima/neuroner/hbp_electrophysiology_ontology.obo').as_posix()
    neuroner2 = (glb /
                 'neuroNER/resources/bluima/neuroner/hbp_electrophysiology-triggers_ontology.obo').as_posix()
    nif_qual = (olr / 'ttl/NIF-Quality.ttl').as_posix()

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
            xr.add_trip(d['xrefs'][0], 'oboInOwl:replacedBy', id_)
            #dg.add_trip(d['xrefs'][0], 'oboInOwl:replacedBy', id_)
            new_terms[d['xrefs'][1]] = {'replaced_by':id_}
            xr.add_trip(d['xrefs'][1], 'oboInOwl:replacedBy', id_)
            #dg.add_trip(d['xrefs'][1], 'oboInOwl:replacedBy', id_)

            data['labels'] = [d['label'], d['o']]
            #dg.add_trip(id_, rdflib.RDFS.label, d['label'])
            dg.add_trip(id_, rdflib.RDFS.label, d['o'])
            data['xrefs'] = d['xrefs']
            for x in d['xrefs']:  # FIXME... expecting order of evaluation errors here...
                dg.add_trip(id_, 'oboInOwl:hasDbXref', x)  # xr
                xr.add_trip(id_, 'oboInOwl:hasDbXref', x)  # x

        elif (spre.toPython() != 'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Quality.owl#' or
              ng.namespace_manager.qname(s).replace('default1','NIFQUAL') in desired_nif_terms):  # skip non-xref quals
            #print(ng.namespace_manager.qname(s).replace('default1','NIFQUAL'))
            new_terms[s] = {'replaced_by':id_}
            xr.add_trip(s, 'oboInOwl:replacedBy', id_)
            data['labels'] = [o.toPython()]
            dg.add_trip(id_, rdflib.RDFS.label, o.toPython())
            data['xrefs'] = [s]
            dg.add_trip(id_, 'oboInOwl:hasDbXref', s)  # xr
            xr.add_trip(id_, 'oboInOwl:hasDbXref', s)  # xr
        else:
            ilx_start -= 1
            continue

        new_terms[id_] = data
        dg.add_trip(id_, rdflib.RDF.type, rdflib.OWL.Class)
        xr.add_trip(id_, rdflib.RDF.type, rdflib.OWL.Class)
        for syn in syns:
            if syn.toPython() not in data['labels']:
                if len(syn) > 3:
                    dg.add_trip(id_, 'NIFRID:synonym', syn)
                elif syn:
                    dg.add_trip(id_, 'NIFRID:abbrev', syn)

        if 'EPHYS' in s or any(['EPHYS' in x for x in data['xrefs']]):
            dg.add_trip(id_, rdflib.RDFS.subClassOf, ephys_phenotype)
        elif 'MORPHOLOGY' in s or any(['MORPHOLOGY' in x for x in data['xrefs']]):
            dg.add_trip(id_, rdflib.RDFS.subClassOf, morpho_phenotype)

    #dg.write(convert=False)
    xr.write(convert=False)

    #skip this for now, we can use DG to do lookups later
    #for t in dg.g.triples((None, None, None)):
        #g.add_trip(*t)  # only way to clean prefixes :/
    add_phenotypes(g)
    g.write(convert=False)

    g2 = makeGraph('pheno-comp', PREFIXES)
    for t in ng.triples((None, None, None)):
        g2.add_trip(*t)  # only way to clean prefixes :/

    g2.write(convert=False)

    syn_mappings = {}
    for sub, syn in [_ for _ in g.g.subject_objects(g.expand('NIFRID:synonym'))] + [_ for _ in g.g.subject_objects(rdflib.RDFS.label)]:
        syn = syn.toPython()
        if syn in syn_mappings:
            log.error(f'duplicate synonym! {syn} {sub}')
        syn_mappings[syn] = sub

    #breakpoint()
    return syn_mappings, pedges, ilx_start

def make_neurons(syn_mappings, pedges, ilx_start_, defined_graph, old=False):
    ilx_start = ilx_start_
    cheating = {'vasoactive intestinal peptide':'VIP',
                'star':None,  # is a morphological phen that is missing but hits scigraph
               }
    ng = createOntology(filename='NIF-Neuron',
                        path='ttl/',
                        prefixes=PREFIXES)

    #""" It seemed like a good idea at the time...
    olr = auth.get_path('ontology-local-repo')
    nif_cell = (olr / 'ttl/NIF-Cell.ttl').as_posix()  # need to be on neurons branch
    cg = rdflib.Graph()
    cg.parse(os.path.expanduser(nif_cell), format='turtle')
    missing = (
        'NIFEXT:55',
        'NIFEXT:56',
        'NIFEXT:57',
        'NIFEXT:59',
        'NIFEXT:81',
        'NLXCELL:091205',
        NIFCELL_NEURON,
        'SAO:2128417084',
        'SAO:862606388',  # secondary, not explicitly in the hbp import
    )
    for m in missing:
        m = ng.expand(m)
        for s, p, o in cg.triples((m, None, None)):
            ng.add_trip(s, p, o)



    #cg.remove((None, rdflib.OWL.imports, None))  # DONOTWANT NIF-Cell imports
    #for t in cg.triples((None, None, None)):
        #ng.add_trip(*t)  # only way to clean prefixes :/
    #cg = None
    #"""

    hbp_cell = (olr / 'ttl/generated/NIF-Neuron-HBP-cell-import.ttl').as_posix()  # need to be on neurons branch
    _temp = rdflib.Graph()  # use a temp to strip nasty namespaces
    _temp.parse(os.path.expanduser(hbp_cell), format='turtle')
    for s, p, o in _temp.triples((None,None,None)):
        if s != rdflib.URIRef('http://ontology.neuinfo.org/NIF/ttl/generated/NIF-Neuron-HBP-cell-import.ttl'):
            ng.g.add((s,p,o))

    base = 'http://ontology.neuinfo.org/NIF/ttl/'

    ontid = base + ng.name + '.ttl'
    ng.add_trip(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    ng.add_trip(ontid, rdflib.OWL.imports, base + 'phenotypes.ttl')
    ng.add_trip(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-Defined.ttl')
    ng.add_trip(ontid, rdflib.OWL.imports, base + 'hbp-special.ttl')
    #ng.add_trip(ontid, rdflib.OWL.imports, base + 'NIF-Cell.ttl')  # NO!
    #ng.add_trip(ontid, rdflib.OWL.imports, base + 'external/uberon.owl')
    #ng.add_trip(ontid, rdflib.OWL.imports, base + 'external/pr.owl')
    ng.replace_uriref('ilxtr:hasMolecularPhenotype', 'ilxtr:hasExpressionPhenotype')

    #defined_graph = makeGraph('NIF-Neuron-Defined', prefixes=PREFIXES, graph=_g)
    #defined_graph.add_trip(base + defined_graph.name + '.ttl', rdflib.RDF.type, rdflib.OWL.Ontology)
    defined_graph.add_trip(defined_graph.ontid, rdflib.OWL.imports, base + 'phenotypes.ttl')

    #log.debug(str(list(syn_mappings)))
    done = True#False
    done_ = set()
    for pedge in pedges:
        for s, p, o_lit in ng.g.triples((None, pedge, None)):
            o = o_lit.toPython()
            success = False
            true_o = None
            true_id = None
            terms = []
            _pp = p.toPython()
            if o in syn_mappings:
                id_ = syn_mappings[o]  # FIXME can this happen more than once?

                ng.add_hierarchy(id_, p, s)
                ng.g.remove((s, p, o_lit))
                #print('SUCCESS, substituting', o, 'for', id_)
                success = True
                true_o = o_lit
                true_id = id_

            elif ('Location' in _pp or 'LocatedIn' in _pp or 'ElementsIn' in
                  _pp or 'TerminalsIn' in _pp):  # lift location to restrictions
                if o.startswith('http://'):
                    ng.add_hierarchy(o_lit, p, s)
                    ng.g.remove((s, p, o_lit))

                    data = sgv.findById(o)
                    label = data['labels'][0]
                    ng.add_trip(o, rdflib.RDF.type, rdflib.OWL.Class)
                    ng.add_trip(o, rdflib.RDFS.label, label)

                    success = True
                    true_o = label
                    true_id = o_lit

            else:
                if o in cheating:
                    o = cheating[o]
                    if o is None:
                        log.debug(f'{o_lit}')
                        continue

                terms = [t for t in OntTerm.query(term=o)]
                for t in terms:
                    if t.prefix in ('PR', 'CHEBI'):
                        sgt = t.URIRef
                        ng.add_hierarchy(sgt, p, s)
                        ng.g.remove((s, p, o_lit))

                        label = t.label
                        ng.add_trip(sgt, rdflib.RDF.type, rdflib.OWL.Class)
                        ng.add_trip(sgt, rdflib.RDFS.label, label)

                        success = True
                        true_o = label
                        true_id = sgt
                        break

                if not success:
                    for t in terms:
                        if t.prefix == 'NIFEXT':
                            sgt = t.URIRef
                            ng.add_hierarchy(sgt, p, s)
                            ng.g.remove((s, p, o_lit))

                            label = t.label
                            ng.add_trip(sgt, rdflib.RDF.type, rdflib.OWL.Class)
                            ng.add_trip(sgt, rdflib.RDFS.label, label)

                            success = True
                            true_o = label
                            true_id = sgt
                            break

                    else:
                        if terms:
                            log.warning(f'Did not succeed for {o!r} found\n{terms}')

            if o not in done_ and success:
                done_.add(o)
                t = tuple(defined_graph.g.triples((None, rdflib.OWL.someValuesFrom, true_id)))
                if t:
                    # these are 1:1 defined neurons from phenotypes so should only show up once
                    #log.debug(f'ALREADY IN {t}')
                    pass
                else:
                    ilx_start += 1
                    id_ = TEMP[str(ilx_start)]
                    defined_graph.add_trip(id_, rdflib.RDF.type, rdflib.OWL.Class)
                    restriction = infixowl.Restriction(p, graph=defined_graph.g, someValuesFrom=true_id)
                    intersection = infixowl.BooleanClass(members=(defined_graph.expand(NIFCELL_NEURON), restriction), graph=defined_graph.g)
                    this = infixowl.Class(id_, graph=defined_graph.g)
                    this.equivalentClass = [intersection]
                    this.subClassOf = [defined_graph.expand(defined_class_parent)]
                    this.label = rdflib.Literal(true_o + ' neuron')
                    log.info(f'make_neurons ilx_start {ilx_start} {list(this.label)[0]}')
                    if not done:
                        breakpoint()
                        done = True

            elif not success:
                log.warning(f'failures for {o} -> {terms}')

    defined_graph.add_class(defined_class_parent, NIFCELL_NEURON, label='defined class neuron')
    defined_graph.add_trip(defined_class_parent, rdflib.namespace.SKOS.definition, 'Parent class For all defined class neurons')

    if old:
        defined_graph.write()  # NIF-Neuron-Defined
        ng.write()  # NIF-Neuron

    for sub, syn in [_ for _ in ng.g.subject_objects(ng.expand('NIFRID:synonym'))] + [_ for _ in ng.g.subject_objects(rdflib.RDFS.label)]:
        syn = syn.toPython()
        if syn in syn_mappings:
            log.error(f'duplicate synonym! {syn} {sub}')
        syn_mappings[syn] = sub

    return ilx_start

def add_phenotypes(graph):

    cell_phenotype = 'ilxtr:CellPhenotype'
    neuron_phenotype = 'ilxtr:NeuronPhenotype'
    #ephys_phenotype = 'ilxtr:ElectrophysiologicalPhenotype'
    #spiking_phenotype = 'ilxtr:SpikingPhenotype'
    #i_spiking_phenotype = 'ilxtr:PetillaInitialSpikingPhenotype'
    burst_p = 'ilxtr:PetillaInitialBurstSpikingPhenotype'
    classical_p = 'ilxtr:PetillaInitialClassicalSpikingPhenotype'
    delayed_p = 'ilxtr:PetillaInitialDelayedSpikingPhenotype'
    #s_spiking_phenotype = 'ilxtr:PetillaSustainedSpikingPhenotype'
    #morpho_phenotype = 'ilxtr:MorphologicalPhenotype'
    ac_p = 'ilxtr:PetillaSustainedAccommodatingPhenotype'
    nac_p = 'ilxtr:PetillaSustainedNonAccommodatingPhenotype'
    st_p = 'ilxtr:PetillaSustainedStutteringPhenotype'
    ir_p = 'ilxtr:PetillaSustainedIrregularPhenotype'

    #fast = 'ilxtr:FastSpikingPhenotype'
    #reg_int = 'ilxtr:RegularSpikingNonPyramidalPhenotype'

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

    graph.add_class(ac_p, s_spiking_phenotype, ('accommodating',), autogen=True)  # FIXME this is silly
    graph.add_class(nac_p, s_spiking_phenotype, ('non accommodating',), autogen=True)
    graph.add_class(st_p, s_spiking_phenotype, ('stuttering',), autogen=True)
    graph.add_class(ir_p, s_spiking_phenotype, ('irregular',), autogen=True)
    graph.add_class(morpho_phenotype, neuron_phenotype, autogen=True)

class table1:
    pass # dead use neuron_ma2015.py

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

    with open((resources / '26451489 table 1.csv').as_posix(), 'rt') as f:
        rows = [list(r) for r in zip(*csv.reader(f))]

    base = 'http://ontology.neuinfo.org/NIF/ttl/'
    ontid = base + graph.name + '.ttl'
    graph.add_trip(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    graph.add_trip(ontid, rdflib.OWL.imports, base + 'phenotypes.ttl')
    graph.add_trip(ontid, rdflib.OWL.imports, base + 'NIF-Neuron-Defined.ttl')

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
        graph.add_trip(sgt, rdflib.RDF.type, rdflib.OWL.Class)
        graph.add_trip(sgt, rdflib.RDFS.label, label)

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
    #graph.add_trip(defined_class_parent, rdflib.RDF.type, rdflib.OWL.Class)
    #graph.add_trip(defined_class_parent, rdflib.RDFS.label, 'defined class neuron')
    #graph.add_trip(defined_class_parent, rdflib.namespace.SKOS.description, 'Parent class For all defined class neurons')
    #graph.add_trip(defined_class_parent, rdflib.RDFS.subClassOf, NIFCELL_NEURON)
    #graph.add_trip(morpho_defined, rdflib.RDFS.subClassOf, defined_class_parent)
    #graph.add_trip(morpho_defined, rdflib.RDFS.label, 'Morphologically classified neuron')  # FIXME -- need asserted in here...
    #graph.add_trip(ephys_defined, rdflib.RDFS.subClassOf, defined_class_parent)
    #graph.add_trip(ephys_defined, rdflib.RDFS.label, 'Electrophysiologically classified neuron')

    graph.add_class(expression_defined, NIFCELL_NEURON, autogen=True)
    graph.add_class('ilxtr:NeuroTypeClass', NIFCELL_NEURON, label='Neuron TypeClass')

    graph.g.commit()

    phenotype_dju_dict = add_types(graph, phenotypes)
    for pheno, disjoints in phenotype_dju_dict.items():
        name = ' '.join(re.findall(r'[A-Z][a-z]*', pheno.split(':')[1])[:-1])  #-1: drops Phenotype
        ilx_start += 1# = make_defined(graph, ilx_start, name + ' neuron type', pheno, 'ilxtr:hasPhenotype')
        id_ = TEMP[str(ilx_start)]
        typeclass = infixowl.Class(id_, graph=graph.g)
        typeclass.label = rdflib.Literal(name + ' neuron type')

        restriction = infixowl.Restriction(graph.expand('ilxtr:hasPhenotype'), graph=graph.g, someValuesFrom=pheno)
        #typeclass.subClassOf = [restriction, graph.expand('ilxtr:NeuroTypeClass')]

        ntc = graph.expand('ilxtr:NeuroTypeClass')
        intersection = infixowl.BooleanClass(members=(ntc, restriction), graph=graph.g)
        typeclass.equivalentClass = [intersection]

        # FIXME not clear that we should be doing typeclasses this way.... :/
        # requires more thought, on the plus side you do get better reasoning...
        disjointunion = disjointUnionOf(graph=graph.g, members=list(disjoints))
        graph.add_trip(id_, rdflib.OWL.disjointUnionOf, disjointunion)


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
    ui = ilxtr.PhenotypePredicateDisambiguation
    def uit(p, o):
        out = (ui, graph.expand(p), graph.expand(o))
        graph.add_trip(*out)
        return out

    uit('ilxtr:hasLayerLocation', 'UBERON:0005390')
    uit('ilxtr:hasLayerLocation', 'UBERON:0005391')
    uit('ilxtr:hasLayerLocation', 'UBERON:0005392')
    uit('ilxtr:hasLayerLocation', 'UBERON:0005393')
    uit('ilxtr:hasLayerLocation', 'UBERON:0005394')
    uit('ilxtr:hasLayerLocation', 'UBERON:0005395')


def make_models():
    from importlib import import_module
    from neurondm.models import __all__
    # skip pcl for now since it is unlifted
    skip = 'allen_type_specimen_mapping', 'phenotype_direct', 'pcl',
    skip += 'basic_neurons', # 'allen_cell_types',
    __all__ = [a for a in __all__ if a not in skip]
    for module in __all__:
        if 'CI' in os.environ and module == 'cuts':  # FIXME XXX temp fix
            continue
        m = import_module(f'neurondm.models.{module}')
        #m = import_module(f'neurondm.compiled.{module}')  # XXX
        if not hasattr(m, 'config') and hasattr(m, 'main'):
            config, *_ = m.main()  # FIXME cuts and allen ct hack
        else:
            config = m.config


def make_bridge():
    from pyontutils.utils import subclasses
    from pyontutils.core import Ont, build
    from neurondm.lang import Config, NeuronEBM  # need ebm for subclasses to work
    from neurondm.models import __all__
    #from neurondm.compiled import __all__  # XXX
    skip = 'phenotype_direct',
    __all__ = [a for a in __all__ if a not in skip]
    log.info('building the following\n' + '\n'.join(__all__))
    models_imports = 'allen', 'markram', 'huang', 'common', 'Defined', 'bolser',
    #models_imports = 'markram', 'huang', 'common', 'Defined'

    class neuronBridge(Ont):
        """ Main bridge for importing the various files that
            make up the neuron phenotype ontology. """

        remote_base = str(NIFRAW['neurons/'])
        path = 'ttl/bridge/'
        filename = 'neuron-bridge'
        name = 'Neuron Bridge'
        imports = chain((subclass.iri for subclass in subclasses(Config)
                         if anyMembers(subclass.iri, *models_imports)),
                        (NIFRAW['neurons/ttl/generated/uberon-parcellation-mappings.ttl'],
                         NIFRAW['neurons/ttl/generated/neurons/cut-roundtrip.ttl'],
                        ))

    nb, *_ = build(neuronBridge, n_jobs=1)
    #log.critical(f'{nb.imports} {models_imports}')

def make_devel():
    from ttlser import CustomTurtleSerializer
    from pyontutils import combinators as cmb
    from pyontutils.core import Ont, build
    from pyontutils.utils import Async, deferred

    # inefficient but thorough way to populate the subset of objects we need.
    terms = set()

    olr = auth.get_path('ontology-local-repo')
    n = (olr / 'ttl/generated/neurons')
    fns =('allen-cell-types.ttl',
          'cut-development.ttl',
          'common-usage-types.ttl',
          #'cut-roundtrip.ttl',
          'huang-2017.ttl',
          'markram-2015.ttl',

          #'bolser-lewis.ttl',
          'keast-2020.ttl',
          'apinatomy-neuron-populations.ttl',
          #'apinatomy-locations.ttl',
          #'nerves.ttl',
          'sparc-nlp.ttl',
          'apinat-simple-sheet.ttl',
          )
    g = OntConjunctiveGraph()
    for fn in fns:
        fp = n / fn
        g.parse(fp.as_posix(), format='ttl')

    _pi = (olr / 'ttl/phenotype-indicators.ttl')
    g.parse(_pi.as_posix(), format='ttl')

    bads = ('TEMP', 'TEMPIND', 'ilxtr', 'rdf', 'rdfs', 'owl', '_', 'prov', 'BFO1SNAP', 'NLXANAT',
            'NIFRAW', 'NLXCELL', 'NLXNEURNT', 'BFO', 'MBA', 'JAX', 'MMRRC', 'ilx', 'CARO', 'NLX',
            'BIRNLEX', 'NIFEXT', 'obo', 'NIFRID')
    ents = set(e for e in chain((o for _, o in g[:owl.someValuesFrom:]),
                                (o for _, o in g[:rdfs.subClassOf:]),
                                g.predicates(),
                                (s for s in g.subjects() if isinstance(s, rdflib.URIRef)
                                 and OntId(s).prefix not in bads))
               if isinstance(e, rdflib.URIRef) and not isinstance(e, rdflib.BNode)
               and (OntId(e).prefix not in bads or OntId(e).prefix in ('BIRNLEX', 'NIFEXT', 'NLX')))

    # deal with conflicting use cases for ilx terms in the ontology
    # yes, we really need perspectives working in interlex so that we
    # can have the FMA query use case and the UBERON use case separated
    ents_ilx = set(e for e in ents if OntId(e).prefix == 'ILX')
    terms_ilx = set(OntTermInterLexOnly(e) for e in ents_ilx)
    missing_sup = [t for t in terms_ilx if 'rdfs:subClassOf' not in t.predicates]
    ilx_supers = set(
        o for t in terms_ilx
        if 'rdfs:subClassOf' in t.predicates
        for o in t.predicates['rdfs:subClassOf'])
    fmaish = [t for t in terms_ilx
              if 'rdfs:subClassOf' in t.predicates and
              # wow if you leave the if out here it completely breaks
              # error message locations and syntax messages O_O
              [s for s in t.predicates['rdfs:subClassOf'] if s.prefix == 'FMA']]
    # supsub and sup_terms intentionally do not cover ilx_supers
    ilx_sup_terms = set(s.asTerm() for s in ilx_supers if s.prefix in ('ILX',))
    isupsub = set(s.u for s in ilx_supers
                  if s.prefix not in ('ILX', 'FMA',) and
                  s.prefix not in bads or
                  s.prefix in ('BIRNLEX', 'NIFEXT', 'NLX'))
    ilx_terms = terms_ilx | ilx_sup_terms
    #breakpoint()

    ents = (ents - ents_ilx) | isupsub
    #terms |= set(Async()(deferred(OntTerm)(e) for e in ents))
    terms |= set(OntTermOntologyOnly(e) for e in ents)

    all_defined_by = set(o for t in terms
                         if t('rdfs:isDefinedBy')
                         for o in t.predicates['rdfs:isDefinedBy']
                         if o.prefix not in bads)

    #fma_source = [t for t in terms if t('rdfs:subClassOf', depth=10, asTerm=True)
                  #and [o for o in t.predicates['rdfs:subClassOf'] if o.prefix == 'FMA']]
    #breakpoint()

    all_supers = set(o for t in terms
                     if t('rdfs:subClassOf', depth=10, asTerm=True)
                     for predicates in ([o for o in t.predicates['rdfs:subClassOf']
                                         # avoid pulling in multiparent cross ontology ?
                                         if o.prefix != 'FMA'],)
                     for o in (predicates if predicates else t.predicates['rdfs:subClassOf'])
                     if o.prefix not in bads)

    terms |= all_supers

    terms |= {OntTermOntologyOnly('UBERON:0002301'),  # cortical layer
              OntTermOntologyOnly('UBERON:0008933'),  # S1
              OntTermOntologyOnly('SAO:1813327414'),
              OntTermOntologyOnly('NCBITaxon:9606'),
              OntTermOntologyOnly('NCBITaxon:9685'),
              OntTermOntologyOnly('SO:0000704'),
    }

    def makeTraverse(*predicates):
        done = set()
        def traverse(term):
            if term in done:
                return term

            done.add(term)
            for predicate in predicates:
                if term(predicate, asTerm=True):
                    for superpart in term.predicates[predicate]:
                        if superpart.prefix not in ('BFO', 'NLX', 'BIRNLEX', 'NIFEXT', 'FMA'):  # continuant and occurent form a cycle >_<
                            yield superpart
                            yield from traverse(superpart)

        return traverse

    partOf = makeTraverse('partOf:', 'RO:0002433', 'rdfs:subClassOf', 'ilx.partOf:')  # 2433 CTMO

    all_sparts = set(o for t in terms  # FIXME this is broken ...
                     for o in partOf(t)
                     if o.prefix not in bads)

    terms |= all_sparts
    terms |= ilx_terms

    #sctrips = (t for T in sorted(set(asdf for t in terms for
                                     #asdf in (t, *t('rdfs:subClassOf', depth=1, asTerm=True))
                                     #if asdf.prefix not in bads), key=lambda t: (not t.label, t.label))
               #for t in T.triples('rdfs:subClassOf'))

    a = rdf.type
    def helper_triples():
        # model
        yield ilxtr.Phenotype, rdfs.subClassOf, OntId('BFO:0000016').u

        # part of for markram
        paxS1 = OntId('PAXRAT:794').u
        uS1 = OntId('UBERON:0008933').u
        yield paxS1, rdfs.subClassOf, uS1
        yield from cmb.restriction(ilxtr.isDelineatedBy, paxS1)(uS1)
        yield from cmb.restriction(ilxtr.delineates, uS1)(paxS1)

        # missing labels
        #yield OntId('CHEBI:18234').u, rdfs.label, rdflib.Literal("α,α'-trehalose 6-mycolate")  # off by one for dopamine CHEBI:18243
        yield OntId('BFO:0000050').u, rdfs.label, rdflib.Literal("part of")

        # receptor roles
        gar = ilxtr.GABAReceptor
        garole = OntId('NLXMOL:1006001').u
        yield gar, a, owl.Class
        yield gar, rdfs.label, rdflib.Literal('GABA receptor')
        yield gar, NIFRID.synonym, rdflib.Literal('GABAR')
        yield from cmb.Restriction(owl.equivalentClass)(OntId('hasRole:').u, garole)(gar)

        glr = ilxtr.glutamateReceptor
        glrole = OntId('SAO:1164727693').u
        yield glr, a, owl.Class
        yield glr, rdfs.label, rdflib.Literal('Glutamate receptor')
        yield glr, NIFRID.synonym, rdflib.Literal('GluR')
        yield from cmb.Restriction(owl.equivalentClass)(OntId('hasRole:').u, glrole)(glr)

        yield ilxtr.parcellationLabel, rdfs.subClassOf, OntId('UBERON:0001062').u

    def _old_trips(self):
        # alt fix using query neuron
        # TODO the proper way to implement this is using unionOf logical phenotype
        # since we do want to restrict it to Neurons
        n_query = ilxtr.NeuronQuery
        yield n_query, a, owl.Class
        yield n_query, rdfs.subClassOf, _NEURON_CLASS

        sst_query = ilxtr.NeuronQuerySST
        yield sst_query, a, owl.Class
        yield sst_query, rdfs.subClassOf, n_query
        yield sst_query, rdfs.label, rdflib.Literal('Somatostatin Neuron (query)')
        yield sst_query, NIFRID.synonym, rdflib.Literal('Sst Neuron (query)')
        rf = cmb.Restriction(rdf.first)
        yield from cmb.EquivalentClass(owl.unionOf)(
            *(rf(ilxtr.hasMolecularPhenotype, m) for m in sst_members),
        )(sst_query)

        pv_query = ilxtr.NeuronQueryPV
        yield pv_query, a, owl.Class
        yield pv_query, rdfs.subClassOf, n_query
        yield pv_query, rdfs.label, rdflib.Literal('Parvalbumin Neuron (query)')
        yield pv_query, NIFRID.synonym, rdflib.Literal('Pvalb Neuron (query)')

        yield from cmb.EquivalentClass(owl.unionOf)(
            *(rf(ilxtr.hasMolecularPhenotype, m) for m in pv_members),
        )(pv_query)


    class neuronUtility(Ont):
        remote_base = str(NIFRAW['neurons/'])
        path = 'ttl/'  # FIXME should be ttl/utility/ but would need the catalog file working
        filename = 'npo'
        name = 'Utility ontology for neuron development'
        imports = (NIFRAW['neurons/ttl/bridge/neuron-bridge.ttl'],
                   NIFRAW['neurons/ttl/generated/allen-transgenic-lines.ttl'],
                   #NIFRAW['neurons/ttl/generated/neurons/allen-cell-instances.ttl'],  # too slow
                   NIFRAW['neurons/ttl/generated/parcellation/mbaslim.ttl'],
                   rdflib.URIRef('http://purl.obolibrary.org/obo/bfo.owl'),

        )
        prefixes = oq.OntCuries._dict
        def _triples(self, terms=terms):
            yield from helper_triples()
            yield OntId('overlaps:').u, rdfs.label, rdflib.Literal('overlaps')
            yield ilx_partOf, rdfs.subPropertyOf, OntId('BFO:0000050').u

            yield OntId('BFO:0000050').u, a, owl.ObjectProperty
            yield OntId('BFO:0000050').u, a, owl.TransitiveProperty
            yield OntId('BFO:0000050').u, owl.inverseOf, OntId('BFO:0000051').u
            yield OntId('BFO:0000050').u, rdfs.subPropertyOf, OntId('overlaps:').u

            yield OntId('BFO:0000051').u, a, owl.ObjectProperty
            yield OntId('BFO:0000051').u, a, owl.TransitiveProperty
            yield OntId('BFO:0000051').u, rdfs.label, rdflib.Literal('has part')
            yield OntId('BFO:0000051').u, rdfs.subPropertyOf, OntId('overlaps:').u

            yield OntId('RO:0002433').u, rdfs.label, rdflib.Literal('contributes to morphology of')
            yield OntId('RO:0002433').u, rdfs.subPropertyOf, OntId('overlaps:').u

            done = [
                # these don't have labels in the ontology and they are cells which is bad
                # so skip them by putting them in done from the start
                OntTermOntologyOnly('NIFSTD:BAMSC1121'),
                OntTermOntologyOnly('NIFSTD:BAMSC1126'),
            ]
            _ipo_done = []
            cortical_layer = OntTermOntologyOnly('UBERON:0002301')
            #yield from cortical_layer.triples_simple
            #yield from cortical_layer('hasPart:')

            if not terms:
                raise BaseException('WHAT')

            skip = 'TEMPIND', 'npokb'
            while terms:
                next_terms = []
                for term in terms:
                    if term in done:
                        continue

                    done.append(term)
                    if term.curie and [p for p in skip if term.curie.startswith(p)]:
                        continue

                    if term.label is not None and not isinstance(term.label, str):
                        log.warning(f'bad label? {term}')  # next line will error

                    if (not term.label or (not term.label.lower().endswith('neuron') and
                                           not term.label.lower().endswith('cell') and
                                           not term.label.lower().endswith('cell outer'))
                        or term.URIRef == _NEURON_CLASS):
                        haveLabel = False
                        for s, p, o in term.triples_simple:
                            if p == rdfs.label:
                                haveLabel = True
                            if s == definition and p == rdf.type:  # FIXME :/
                                o = owl.AnnotationProperty

                            yield s, p, o
                            #log.debug(f'{o!r}')
                            if isinstance(o, rdflib.URIRef):
                                if o == owl.Restriction:
                                    continue

                                no = OntTermOntologyOnly(o)
                                if no not in done:
                                    if term.prefix not in bads and no.prefix in bads:
                                        if not no.label:
                                            continue
                                        try:
                                            gen = OntTermOntologyOnly.query(term=no.label)
                                            noo = next(gen)
                                            if noo.curie in ('owl:Class', 'owl:Thing'):
                                                continue
                                            elif noo != no and noo.prefix not in bads:
                                                no = noo
                                            else:
                                                continue
                                        except StopIteration:
                                            continue

                                    next_terms.append(no)

                        if not haveLabel:
                            ot = OntTerm(term)  # include InterLex
                            if ot.label:
                                yield ot.u, rdfs.label, rdflib.Literal(ot.label)
                                if hasattr(ot, '_graph'):
                                    ipo = str(ilx_partOf)
                                    for s, p, o in ot._graph.subjectGraphClosure(ot.u):
                                        yield s, p, o
                                        if str(p) == ipo and isinstance(o, rdflib.URIRef):
                                            if (s, o) not in _ipo_done:
                                                _ipo_done.append((s, o))
                                                yield from cmb.restriction(
                                                    BFO_partOf, o)(s)

                                                no = OntTermOntologyOnly(o)
                                                if no not in done:
                                                    next_terms.append(no)

                terms = next_terms


    class neuronUtilityBig(Ont):
        remote_base = str(NIFRAW['neurons/'])
        path = 'ttl/'  # FIXME should be ttl/utility/ but would need the catalog file working
        filename = 'npo-large'
        name = 'Utility ontology for neuron development'
        imports = (NIFRAW['neurons/ttl/bridge/neuron-bridge.ttl'],
                   NIFRAW['neurons/ttl/bridge/chemical-bridge.ttl'],
                   NIFRAW['neurons/ttl/generated/parcellation.ttl'],
                   NIFRAW['neurons/ttl/generated/parcellation-artifacts.ttl'],
                   NIFRAW['neurons/ttl/generated/uberon-parcellation-mappings.ttl'],
                   NIFRAW['neurons/ttl/generated/parcellation/mbaslim.ttl'],
                   NIFRAW['neurons/ttl/generated/parcellation/paxinos-rat-labels.ttl'],
                   rdflib.URIRef('http://purl.obolibrary.org/obo/uberon.owl'),
        )
        prefixes = oq.OntCuries._dict


        def _triples(self):
            yield from helper_triples()


    CustomTurtleSerializer.roundtrip_prefixes = ('',)
    nu, nub, *_ = build(neuronUtility, neuronUtilityBig, n_jobs=1)
    CustomTurtleSerializer.roundtrip_prefixes = True


def main():
    from docopt import docopt
    args = docopt(__doc__)
    dep = args['dep']
    all = args['all']
    old = args['old']               or all
    release = args['release']       or all
    phenotypes = args['phenotypes'] or all or release or old
    bridge = args['bridge']         or all
    models = args['models']         or all or release
    dev = args['dev']               or all or release
    indicators = args['indicators'] or all or release
    sheets = args['sheets']         or all or release

    if dep:
        from neurondm.lang import Config
        from neurondm.compiled.common_usage_types import config as c_config
        cnrns = c_config.neurons()
        config = Config('cut-development-fixed')
        nns = [n.asUndeprecated() for n in cnrns]
        config.write()
        config.write_python()
        breakpoint()
        return

    if indicators:
        from neurondm import indicators as ind
        ind.main()

    if phenotypes:
        syn_mappings, pedge, ilx_start, phenotypes, defined_graph = make_phenotypes()
        if old:
            syn_mappings['thalamus'] = defined_graph.expand('UBERON:0001879')
            expand_syns(syn_mappings)

    if models:
        make_models()

    if old:
        ilx_start = make_neurons(syn_mappings, pedge, ilx_start, defined_graph, old=old)

    if sheets:
        from neurondm import sheets
        sheets.main()

    if dev:
        make_devel()

    if bridge:
        make_bridge()

    if __name__ == '__main__':
        #breakpoint()
        pass

if __name__ == '__main__':
    main()
