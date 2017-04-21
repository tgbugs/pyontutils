#!/usr/bin/env python3.6
import rdflib
from rdflib.extras import infixowl
from IPython import embed
from pyontutils.scigraph_client import Graph, Vocabulary
from pyontutils.utils import makeGraph, makePrefixes
from pyontutils.ilx_utils import ILXREPLACE

__all__ = [
    'AND',
    'OR',
    'getPhenotypePredicates',
    'graphBase',
    'PhenotypeEdge',
    'NegPhenotypeEdge',
    'LogicalPhenoEdge',
    'DefinedNeuron',
    'NeuronArranger',
    'NIFCELL_NEURON',
]

# language constructes
AND = 'owl:intersectionOf'
OR = 'owl:unionOf'

# utility identifiers
NIFCELL_NEURON = 'NIFCELL:sao1417703748'
PHENO_ROOT = 'ilx:hasPhenotype'  # needs to be qname representation
DEF_ROOT = 'ilx:definedClassNeurons'
def getPhenotypePredicates(graph):
    # put existing predicate short names in the phenoPreds namespace (TODO change the source for these...)
    qstring = ('SELECT DISTINCT ?prop WHERE '
               '{ ?prop rdfs:subPropertyOf* %s . }') % PHENO_ROOT
    out = [_[0] for _ in graph.query(qstring)]
    literal_map = {uri.rsplit('/',1)[-1]:uri for uri in out}  # FIXME this will change
    classDict = {uri.rsplit('/',1)[-1]:uri for uri in out}  # need to use label or something
    classDict['_litmap'] = literal_map
    phenoPreds = type('PhenoPreds', (object,), classDict)
    return phenoPreds


class graphBase:
    core_graph = 'ASSIGN ME AFTER IMPORT!'
    in_graph = 'ASSIGN ME AFTER IMPORT!'
    out_graph = 'ASSIGN ME AFTER IMPORT'

    _predicates = 'ASSIGN ME AFTER IMPORT'

    _sgv = Vocabulary(cache=True)
    def __init__(self):
        if type(self.core_graph) == str:
            raise TypeError('You must have at least a core_graph')
        
        if type(self.in_graph) == str:
            self.in_graph = self.core_graph

        if type(self.out_graph) == str:
            self.out_graph = self.in_graph

        self._namespaces = {p:rdflib.Namespace(ns) for p, ns in self.in_graph.namespaces()}

    def expand(self, putativeURI):
        if type(putativeURI) == infixowl.Class:
            return putativeURI.identifier
        elif type(putativeURI) == str:
            try: prefix, suffix = putativeURI.split(':',1)
            except ValueError:  # FIXME this is wrong...
                return rdflib.URIRef(putativeURI)
            if prefix in self._namespaces:
                return self._namespaces[prefix][suffix]
            else:
                raise KeyError('Namespace prefix does exist:', prefix)
        else:  # FIXME need another check probably...
            return putativeURI


class PhenotypeEdge(graphBase):  # this is really just a 2 tuple...  # FIXME +/- needs to work here too? TODO sorting
    local_names = {
        'NCBITaxon:10116':'Rat',
        'PR:000004967':'CB',
        'PR:000004968':'CR',
        'PR:000011387':'NPY',
        'PR:000015665':'SOM',
        #'NIFMOL:nifext_6':'PV',
        'PR:000013502':'PV',
        'PR:000017299':'VIP',
        'PR:000005110':'CCK',
        'ilx:PetillaSustainedAccomodatingPhenotype':'AC',
        'ilx:PetillaSustainedNonAccomodatingPhenotype':'NAC',
        'ilx:PetillaSustainedStutteringPhenotype':'STUT',
        'ilx:PetillaSustainedIrregularPhenotype':'IR',
        'ilx:PetillaInitialBurstSpikingPhenotype':'b',
        'ilx:PetillaInitialClassicalSpikingPhenotype':'c',
        'ilx:PetillaInitialDelayedSpikingPhenotype':'d',
        'UBERON:0005390':'L1',
        'UBERON:0005391':'L2',
        'UBERON:0005392':'L3',
        'UBERON:0005393':'L4',
        'UBERON:0005394':'L5',
        'UBERON:0005395':'L6',
        'UBERON:0003881':'CA1',
        'UBERON:0003882':'CA2',
        'UBERON:0003883':'CA3',
        'UBERON:0001950':'Neocortex',
        'UBERON:0008933':'S1',
    }
    def __init__(self, phenotype, ObjectProperty=None, label=None):
        # label blackholes
        # TODO implement local names here? or at a layer above? (above)
        super().__init__()
        if isinstance(phenotype, PhenotypeEdge):  # simplifies negation of a phenotype
            ObjectProperty = phenotype.e
            phenotype = phenotype.p

        self.p = self.checkPhenotype(phenotype)
        if ObjectProperty is None:
            self.e = self.getObjectProperty(self.p)
        else:
            self.e = self.checkObjectProperty(ObjectProperty)  # FIXME this doesn't seem to work

        self._pClass = infixowl.Class(self.p, graph=self.in_graph)
        self._eClass = infixowl.Class(self.e, graph=self.in_graph)
        # do not call graphify here because phenotype edges may be reused in multiple places in the graph

    def checkPhenotype(self, phenotype):
        p = self.expand(phenotype)
        try: next(self.core_graph.predicate_objects(p))
        except StopIteration:
            if not self._sgv.findById(p):
                print('WARNING: unknown phenotype ', p)
        return p

    def getObjectProperty(self, phenotype):
        predicates = list(self.in_graph.objects(phenotype, self.expand('ilx:useObjectProperty')))  # useObjectProperty works for phenotypes we control

        if predicates:
            return predicates[0]
        else:
            # TODO check if falls in one of the expression categories
            predicates = [_[1] for _ in self.in_graph.subject_predicates(phenotype) if _ in self._predicates.values()]
            return self.expand(PHENO_ROOT)

    def checkObjectProperty(self, ObjectProperty):  # FIXME this doesn't seem to work
        op = self.expand(ObjectProperty)
        if op in self._predicates.__dict__.values():
            return op
        else:
            raise TypeError('Unknown ObjectProperty %s' % repr(op))

    @property
    def eLabel(self):
        return next(self._eClass.label)

    @property
    def pLabel(self):
        l = tuple(self._pClass.label)
        if not l:  # we don't want to load the whole ontology
            try:
                l = self._sgv.findById(self.p)['labels'][0]
            except TypeError:
                l = self.p
        else:
            l = l[0]
        return l

    @property
    def pHiddenLabel(self):
        l = tuple(self.in_graph.objects(self.p, rdflib.namespace.SKOS.hiddenLabel))
        if l:
            l = l[0]
        else:
            l = self.pShortName  # FIXME

        return l

    @property
    def pShortName(self):
        pn = self.in_graph.namespace_manager.qname(self.p)
        resp = self._sgv.findById(pn)
        if resp:  # DERP
            abvs = resp['abbreviations']
        else:
            abvs = None

        if abvs:
            return abvs[0]
        elif pn in self.local_names:
            return self.local_names[pn]
        else:
            return ''

    def _graphify(self, graph=None):
        if graph is None:
            graph = self.out_graph
        return infixowl.Restriction(onProperty=self.e, someValuesFrom=self.p, graph=graph)

    def __lt__(self, other):
        if type(other) == type(self):
            return sorted((self.p, other.p))[0] == self.p  # FIXME bad...
        elif type(other) == LogicalPhenoEdge:
            return True
        elif type(self) == PhenotypeEdge:
            return True
        else:
            return False

    def __gt__(self, other):
        return not self.__lt__(other)

    def __eq__(self, other):
        return self.p == other.p and self.e == other.e

    def __hash__(self):
        return hash((self.p, self.e))

    def __repr__(self):
        pn = self.in_graph.namespace_manager.qname(self.p)
        en = self.in_graph.namespace_manager.qname(self.e)
        lab = self.pLabel
        return "%s('%s', '%s', label='%s')" % (self.__class__.__name__, pn, en, lab)


class NegPhenotypeEdge(PhenotypeEdge):
    """ Class for Negative Phenotypes to simplfy things """


class LogicalPhenoEdge(graphBase):
    local_names = {
        AND:'AND',
        OR:'OR',
    }
    def __init__(self, op, *edges):
        super().__init__()
        self.op = self.expand(op)  # TODO more with op
        self.pes = edges

    @property
    def p(self):
        return tuple((pe.p for pe in self.pes))

    @property
    def e(self):
        return tuple((pe.e for pe in self.pes))

    @property
    def pHiddenLabel(self):
        label = ' '.join([pe.pHiddenLabel for pe in self.pes])  # FIXME we need to catch non-existent phenotypes BEFORE we try to get their hiddenLabel because the errors you get here are completely opaque
        op = self.local_names[self.in_graph.namespace_manager.qname(self.op)]
        return '(%s %s)' % (op, label)

    @property
    def pShortName(self):
        return ''.join([pe.pShortName for pe in self.pes])

    def _graphify(self, graph=None):
        if graph is None:
            graph = self.out_graph
        members = []
        for pe in self.pes:  # FIXME fails to work properly for negative phenotypes...
            members.append(pe._graphify(graph=graph))
        return infixowl.BooleanClass(operator=self.op, members=members, graph=graph)

    def __lt__(self, other):
        if type(other) == type(self):
            return sorted((self.p, other.p))[0] == self.p  # FIXME bad...
        else:
            return False

    def __gt__(self, other):
        return not self.__lt__(other)

    def __eq__(self, other):
        if type(other) == type(self):
            for a, b in zip(sorted(self.pes), sorted(other.pes)):
                if a != b:
                    return False
            return True
        else:
            return False

    def __hash__(self):
        return hash(tuple(sorted(self.pes)))

    def __repr__(self):
        op = self.local_names[self.in_graph.namespace_manager.qname(self.op)]
        pes = ", ".join([_.__repr__() for _ in self.pes])
        return "%s(%s, %s)" % (self.__class__.__name__, op, pes)


hashes = []
class Neuron(graphBase):
    existing_pes = {}
    existing_ids = {}
    ids_pes = {}
    pes_ids = {}
    def __init__(self, *phenotypeEdges, id_=None):
        super().__init__()
        self.ORDER = [
        # FIXME it may make more sense to manage this in the NeuronArranger
        # so that it can interconvert the two representations
        # this is really high overhead to load this here
        self._predicates.hasInstanceInSpecies,
        self._predicates.hasTaxonRank,
        self._predicates.hasSomaLocatedIn,  # hasSomaLocation?
        self._predicates.hasLayerLocationPhenotype,  # TODO soma naming...
        self._predicates.hasMorphologicalPhenotype,
        self._predicates.hasElectrophysiologicalPhenotype,
        #self._predicates.hasSpikingPhenotype,  # TODO do we need this?
        self.expand('ilx:hasSpikingPhenotype'),  # legacy support
        self._predicates.hasExpressionPhenotype,
        self._predicates.hasProjectionPhenotype,  # consider inserting after end, requires rework of code...
        ]

        if id_ and phenotypeEdges:
            raise TypeError('This has not been implemented yet. This could serve as a way to validate a match or assign an id manually?')
        elif id_:
            self.id_ = self.expand(id_)
        elif phenotypeEdges:
            #asdf = str(tuple(sorted((_.e, _.p) for _ in phenotypeEdges)))  # works except for logical phenotypes
            self.id_ = self.expand(ILXREPLACE(str(tuple(sorted(phenotypeEdges)))))  # XXX beware changing how __str__ works... really need to do this 
            hashes.append(self.id_)
        else:
            raise TypeError('Neither phenotypeEdges nor id_ were supplied!')


        if not phenotypeEdges and id_ is not None:
            self.Class = infixowl.Class(self.id_, graph=self.in_graph)  # IN
            phenotypeEdges = self.bagExisting()  # rebuild the bag from the -class- id

        self.Class = infixowl.Class(self.id_, graph=self.out_graph)  # once we get the data from existing, prep to dump OUT

        self.pes = tuple(sorted(phenotypeEdges))

        self.phenotypes = set((pe.p for pe in self.pes))
        self.edges = set((pe.e for pe in self.pes))
        self._pesDict = {}
        for pe in self.pes:  # FIXME TODO
            if pe.e in self._pesDict:
                self._pesDict[pe.e].append(pe)
            else:
                self._pesDict[pe.e] = [pe]

        if self in self.existing_pes:
            self.Class = self.existing_pes[self]
        else:
            self.Class = self._graphify()
            self.Class.label = rdflib.Literal(self.label)
            self.existing_pes[self] = self.Class

    def _tuplesToPes(self, pes):
        for p, e in pes:
            yield PhenotypeEdge(p, e)

    @property
    def label(self):  # FIXME for some reasons this doesn't always make it to the end?
        # TODO predicate actions are the right way to implement the transforms here
        def sublab(edge):
            sublabs = []
            if edge in self._pesDict:
                for pe in self._pesDict[edge]:
                    l = pe.pShortName
                    if not l:
                        l = pe.pHiddenLabel
                    if not l:
                        l = pe.pLabel

                    if pe.e == self._predicates.hasExpressionPhenotype:
                        if type(pe) == NegPhenotypeEdge:
                            l = '-' + l
                        else:
                            l = '+' + l  # this is backward from the 'traditional' placement of the + but it makes this visually much cleaner and eaiser to understand
                    elif pe.e == self._predicates.hasProjectionPhenotype:
                        l = 'Projecting To ' + l


                    sublabs.append(l)

            return sublabs

        label = []
        for edge in self.ORDER:
            label += sorted(sublab(edge))
            logical = (edge, edge)
            if logical in self._pesDict:
                label += sorted(sublab(logical))

        # species
        # developmental stage
        # brain region
        # morphology
        # ephys
        # expression
        # projection
        # cell type specific connectivity?
        # circuit role? (principle interneuron...)
        if not label:
            label.append('????')
        nin_switch = 'Neuron' if True else 'Interneuron'
        label.append(nin_switch)

        new_label = ' '.join(label)
        self.Class.label = (rdflib.Literal(new_label),)
        #try:
            #print(next(self.Class.label))  # FIXME need to set the label once we generate it and overwrite the old one...
        #except StopIteration:
            #print(new_label)
        return new_label
        
    def realize(self):  # TODO use ilx_utils
        """ Get an identifier """
        self.id_ = 'ILX:1234567'

    def validate(self):
        raise TypeError('Ur Neuron Sucks')

    def __repr__(self):  # TODO use local_names (since we will bind them in globals, but we do need a rule, and local names do need to be to pairs or full logicals? eg L2L3 issue
        return "%s%s" % (self.__class__.__name__, self.pes)


    def __hash__(self):
        return hash((self.__class__.__name__, self.pes))

    def __eq__(self, other):
        return hash(self) == hash(other)


class DefinedNeuron(Neuron):
    """ Class that takes a bag of phenotypes and adds equivalentClass axioms"""

    def bagExisting(self):  # TODO intersections
        out = set()  # prevent duplicates in cases where phenotypes are duplicated in the hierarchy
        for c in self.Class.equivalentClass:
            pe = self._unpackPheno(c)
            if pe:
                if isinstance(pe, tuple):  # we hit a case where we need to inherit phenos from above
                    out.update(pe)
                else:
                    out.add(pe)

        for c in self.Class.disjointWith:
            print(c)
            pe = self._unpackPheno(c, NegPhenotypeEdge)
            if pe:
                out.add(pe)

        return tuple(out)

        # the SPARQL equivalent that we are not using
        # qname = self.out_graph.namespace_manager.qname(self.id_)
        # qstring = """
        # SELECT DISTINCT ?match ?edge WHERE {
        # %s owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?item .
        # ?item rdf:type owl:Restriction .
        # ?edge rdfs:subPropertyOf* %s .
        # ?item owl:onProperty ?edge .
        # ?item owl:someValuesFrom ?match . }""" % (qname, PHENO_ROOT)
        # pes = self.in_graph.query(qstring)
        # out = tuple(self._tuplesToPes(pes))
        # return out

    def _unpackPheno(self, c, type_=PhenotypeEdge):  # FIXME need to deal with intersections
        if isinstance(c.identifier, rdflib.BNode):
            putativeRestriction = infixowl.CastClass(c, graph=self.in_graph)
            if isinstance(putativeRestriction, infixowl.BooleanClass):
                bc = putativeRestriction
                op = bc._operator
                pes = []
                for id_ in bc._rdfList:
                    #print(id_)
                    pr = infixowl.CastClass(id_, graph=self.in_graph)
                    if isinstance(pr, infixowl.BooleanClass):
                        lpe = self._unpackLogical(pr)
                        pes.append(lpe)
                        continue
                    if isinstance(pr, infixowl.Class):
                        if id_ == self.expand(NIFCELL_NEURON):
                            #print('we got neuron root', id_)
                            continue
                        else:
                            pass  # it is a restriction

                    p = pr.someValuesFrom  # if NIFCELL_NEURON is not a owl:Class > problems
                    e = pr.onProperty
                    pes.append(type_(p, e))
                return tuple(pes)
            else:
                print('WHAT')  # FIXME something is wrong for negative phenotypes...
                pr = putativeRestriction
                p = pr.someValuesFrom
                e = pr.onProperty
                if p and e:
                    return type_(p, e)
                else:
                    print(putativeRestriction)
        else:
            # TODO make sure that Neuron is in there somehwere...
            print('what is this thing?', c)

    def _unpackLogical(self, bc, type_=PhenotypeEdge):  # TODO this will be needed for disjoint as well
        op = bc._operator
        pes = []
        for id_ in bc._rdfList:
            pr = infixowl.CastClass(id_, graph=self.in_graph)
            p = pr.someValuesFrom
            e = pr.onProperty
            pes.append(type_(p, e))
        return LogicalPhenoEdge(op, *pes)

    def _graphify(self, *args, graph=None): #  defined
        """ Lift phenotypeEdges to Restrictions """
        if graph is None:
            graph = self.out_graph
        members = [self.expand(NIFCELL_NEURON)]
        for pe in self.pes:
            target = pe._graphify(graph=graph)
            if isinstance(pe, NegPhenotypeEdge):  # isinstance will match NegPhenotypeEdge -> PhenotypeEdge
                #self.Class.disjointWith = [target]  # FIXME for defined neurons this is what we need and I think it is strong than the complementOf version
                djc = infixowl.Class(graph=graph)  # TODO for generic neurons this is what we need
                djc.complementOf = target
                members.append(djc)
            else:
                members.append(target)  # FIXME negative logical phenotypes :/
        intersection = infixowl.BooleanClass(members=members, graph=graph)  # FIXME dupes
        ec = [intersection]
        self.Class.equivalentClass = ec
        return self.Class


class MeasuredNeuron(Neuron):  # XXX DEPRECATED retained for loading from some existing ontology files
    """ Class that takes a bag of phenotypes and adds subClassOf axioms"""
    # these should probably require a species and brain region bare minimum?
    # these need to check to make sure the species specific identifiers are being used
    # and warn on mismatch

    def bagExisting(self):  # FIXME intersection an union?
        out = set()  # prevent duplicates in cases where phenotypes are duplicated in the hierarchy
        for c in self.Class.subClassOf:
            pe = self._unpackPheno(c)
            if pe:
                if isinstance(pe, tuple):  # we hit a case where we need to inherit phenos from above
                    out.update(pe)
                else:
                    out.add(pe)
        for c in self.Class.disjointWith:
            pe = self._unpackPheno(c, NegPhenotypeEdge)
            if pe:
                out.add(pe)
        return tuple(out)

        # alternate SPARQL version
        # while using the qstring is nice from a documentation standpoint... it is sllllooowww
        # check out infixowl Class.__repr__ for a potentially faster way use CastClass...
        # qname = self.in_graph.namespace_manager.qname(self.id_)
        # qstring = """
        # SELECT DISTINCT ?match ?edge WHERE {
        # %s rdfs:subClassOf ?item .
        # ?item rdf:type owl:Restriction .
        # ?item owl:onProperty ?edge .
        # ?item owl:someValuesFrom ?match . }""" % qname
        # #print(qstring)
        # pes = list(self.in_graph.query(qstring))
        # #assert len(test) == 1, "%s" % test
        # if not pes:
        #     return self._getIntersectionPhenos(qname)
        # else:
        #     out = tuple(self._tuplesToPes(pes))
        #     #print(out)
        #     return out

    def _unpackPheno(self, c, type_=PhenotypeEdge):
        if isinstance(c.identifier, rdflib.BNode):
            putativeRestriction = infixowl.CastClass(c, graph=self.in_graph)
            if isinstance(putativeRestriction, infixowl.BooleanClass):
                bc = putativeRestriction
                op = bc._operator
                pes = []
                for id_ in bc._rdfList:
                    pr = infixowl.CastClass(id_, graph=self.in_graph)
                    p = pr.someValuesFrom
                    e = pr.onProperty
                    pes.append(type_(p, e))
                    #print(id_)
                return LogicalPhenoEdge(op, *pes)
            else:
                pr = putativeRestriction
                p = pr.someValuesFrom
                e = pr.onProperty
            if p and e:
                return type_(p, e)
            else:
                raise TypeError('Something is wrong', putativeRestriction)
        elif isinstance(c.identifier, rdflib.URIRef):
            pes = MeasuredNeuron(id_=c.identifier).pes  # FIXME cooperate with neuron manager?
            if pes:
                return pes

    def _getIntersectionPhenos(self, qname):
        qstring = """
        SELECT DISTINCT ?match ?edge WHERE {
        %s rdfs:subClassOf/owl:intersectionOf/rdf:rest*/rdf:first ?item .
        ?item rdf:type owl:Restriction .
        ?item owl:onProperty ?edge .
        ?item owl:someValuesFrom ?match . }""" % qname
        #print(qstring)
        pes = self.in_graph.query(qstring)
        out = tuple(self._tuplesToPes(pes))
        #print('------------------------')
        print(out)
        #print('------------------------')
        return out

    def _graphify(self):
        class_ = infixowl.Class(self.id_, graph=self.out_graph)
        class_.delete()  # delete any existing annotations to prevent duplication
        for pe in self.pes:
            target = pe._graphify()  # restriction or intersection
            if isinstance(pe, NegPhenotypeEdge):
                class_.disjointWith = [target]
            else:
                class_.subClassOf = [target]

        return class_

    def validate(self):
        'I am validated'

    def addEvidence(self, pe, evidence):
        # add an evidence structure...
        # should also be possible to pass in a pee (phenotype edge evidence) structure at __ini__
        pass


class NeuronArranger:  # TODO should this write the graph?
    """ Class that takes a list of data neurons and optimizes their taxonomy."""
    def __init__(self, *neurons, graph):
        pass

    def loadDefined(self):
        pass


def main():
    # load in our existing graph
    # note: while it would be nice to allow specification of phenotypes to be decoupled
    # from insertion into the graph... maybe we could enable this, but it definitely seems
    # to break a number of nice features... and we would need the phenotype graph anyway
    EXISTING_GRAPH = rdflib.Graph()
    sources = ('/tmp/NIF-Neuron-Phenotype.ttl',
               '/tmp/NIF-Neuron-Defined.ttl',
               '/tmp/NIF-Neuron.ttl',
               '/tmp/hbp-special.ttl')
    for file in sources:
            EXISTING_GRAPH.parse(file, format='turtle')
    EXISTING_GRAPH.namespace_manager.bind('ILXREPLACE', makePrefixes('ILXREPLACE')['ILXREPLACE'])
    #EXISTING_GRAPH.namespace_manager.bind('PR', makePrefixes('PR')['PR'])

    PREFIXES = makePrefixes('owl',
                            'PR',
                            'UBERON',
                            'NCBITaxon',
                            'ILXREPLACE',
                            'ilx',
                            'ILX',
                            'NIFCELL',
                            'NIFMOL',)
    graphBase.core_graph = EXISTING_GRAPH
    graphBase.out_graph = rdflib.Graph()
    graphBase._predicates = getPhenotypePredicates(EXISTING_GRAPH)

    g = makeGraph('merged', prefixes={k:str(v) for k, v in EXISTING_GRAPH.namespaces()}, graph=EXISTING_GRAPH)
    reg_neurons = list(g.g.subjects(rdflib.RDFS.subClassOf, g.expand(NIFCELL_NEURON)))
    tc_neurons = [_ for (_,) in g.g.query('SELECT DISTINCT ?match WHERE {?match rdfs:subClassOf+ %s}' % NIFCELL_NEURON)]
    def_neurons = g.get_equiv_inter(NIFCELL_NEURON)

    nodef = sorted(set(tc_neurons) - set(def_neurons))
    MeasuredNeuron.out_graph = rdflib.Graph()
    DefinedNeuron.out_graph = rdflib.Graph()
    mns = [MeasuredNeuron(id_=n) for n in nodef]
    dns = [DefinedNeuron(id_=n) for n in sorted(def_neurons)]
    #dns += [DefinedNeuron(*m.pes) if m.pes else m.id_ for m in mns]
    dns += [DefinedNeuron(*m.pes) for m in mns if m.pes]

    # reset everything for export
    DefinedNeuron.out_graph = rdflib.Graph()
    ng = makeGraph('output', prefixes=PREFIXES, graph=DefinedNeuron.out_graph)
    DefinedNeuron.existing_pes = {}  # reset this as well because the old Class references have vanished
    dns = [DefinedNeuron(*d.pes) for d in set(dns)]  # TODO remove the set and use this to test existing bags?
    ng.add_ont(ILXREPLACE('defined-neurons'), 'Defined Neurons', 'NIFDEFNEU',
               'VERY EXPERIMENTAL', '0.0.0.1a')
    ng.add_node(ILXREPLACE('defined-neurons'), 'owl:imports', 'http://ontology.neuinfo.org/NIF/ttl/NIF-Phenotype-Core.ttl')
    ng.add_node(ILXREPLACE('defined-neurons'), 'owl:imports', 'http://ontology.neuinfo.org/NIF/ttl/NIF-Phenotypes.ttl')
    ng.write()
    bads = [n for n in ng.g.subjects(rdflib.RDF.type,rdflib.OWL.Class)
            if len(list(ng.g.predicate_objects(n))) == 1]
    embed()

if __name__ == '__main__':
    main()
