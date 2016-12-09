#!/usr/bin/env python3.5
import rdflib
from rdflib.extras import infixowl
from IPython import embed
from scigraph_client import Graph, Vocabulary
from utils import makeGraph

__all__ = [
    'AND',
    'OR',
    'phenoPreds',
    'PhenotypeEdge',
    'NegPhenotypeEdge',
    'LogicalPhenoEdge',
    'DefinedNeuron',
    'MeasuredNeuron',
    'NeuronArranger',
]

# language constructes
AND = 'owl:intersectionOf'
OR = 'owl:unionOf'

# utility identifiers
NIFCELL_NEURON = 'NIFCELL:sao1417703748'
PHENO_ROOT = 'ilx:hasPhenotype'  # needs to be qname representation
DEF_ROOT = 'ilx:definedClassNeurons'

# load in our existing graph
EXISTING_GRAPH = rdflib.Graph()
sources = ('/tmp/NIF-Neuron-Phenotype.ttl',
           '/tmp/NIF-Neuron-Defined.ttl',
           '/tmp/NIF-Neuron.ttl',
           '/tmp/hbp-special.ttl')
for file in sources:
        EXISTING_GRAPH.parse(file, format='turtle')

# put existing predicate short names in the phenoPreds namespace (TODO change the source for these...)
qstring = ('SELECT DISTINCT ?prop WHERE '
           '{ ?prop rdfs:subPropertyOf* %s . }') % PHENO_ROOT
out = [_[0] for _ in EXISTING_GRAPH.query(qstring)]
phenoPreds = type('PhenoPreds', (object,), {uri.rsplit('/',1)[-1]:uri for uri in out})


class graphThing:
    graph = EXISTING_GRAPH  # this allows us to build load the graph a class time
    sgv = Vocabulary(cache=True)
    def __init__(self):
        self._namespaces = {p:rdflib.Namespace(ns) for p, ns in self.graph.namespaces()}

    def expand(self, putativeURI):
        if type(putativeURI) == infixowl.Class:
            return putativeURI.identifier
        elif type(putativeURI) == str:
            try: prefix, suffix = putativeURI.split(':',1)
            except ValueError:
                return rdflib.URIRef(putativeURI)
            if prefix in self._namespaces:
                return self._namespaces[prefix][suffix]
            else:
                raise KeyError('Namespace prefix does exist:', prefix)
        else:  # FIXME need another check probably...
            return putativeURI


class PhenotypeEdge(graphThing):  # this is really just a 2 tuple...  # FIXME +/- needs to work here too?
    local_names = {
        'PR:000004967':'CB',
        'PR:000004968':'CR',
        'PR:000011387':'NPY',
        'PR:000015665':'SOM',
        'NIFMOL:nifext_6':'PV',
        'PR:000017299':'VIP',
        'PR:000005110':'CCK',
        'ilx:PetillaSustainedAccomodatingPhenotype':'AC',
        'ilx:PetillaSustainedNonAccomodatingPhenotype':'NAC',
        'ilx:PetillaSustainedStutteringPhenotype':'STUT',
        'ilx:PetillaSustainedIrregularPhenotype':'IR',
        'ilx:PetillaInitialBurstSpikingPhenotype':'b',
        'ilx:PetillaInitialClassicalSpikingPhenotype':'c',
        'ilx:PetillaInitialDelayedSpikingPhenotype':'d',
        'UBERON:0005390':'Layer 1',
        'UBERON:0005391':'Layer 2',
        'UBERON:0005392':'Layer 3',
        'UBERON:0005393':'Layer 4',
        'UBERON:0005394':'Layer 5',
        'UBERON:0005396':'Layer 6',

    }
    def __init__(self, phenotype, ObjectProperty=None, label=None):
        # label blackholes
        super().__init__()
        if type(phenotype) == PhenotypeEdge:  # simplifies negation of a phenotype
            ObjectProperty = phenotype.e
            phenotype = phenotype.p

        self.p = self.expand(phenotype)
        op = self.expand(ObjectProperty)
        if op:
            if op in self.validEdges:
                self.e = op
            else:
                raise TypeError('Unknown ObjectProperty %s' % op)
        else:
            self.e = self.getPhenotypeEdge(self.p)

        self._pClass = infixowl.Class(self.p, graph=self.graph)
        self._eClass = infixowl.Class(self.e, graph=self.graph)

    def getPhenotypeEdge(self, phenotype):
        edges = list(self.graph.objects(phenotype, self.expand('ilx:useObjectProperty')))
        if edges:
            return edges[0]
        else:
            # TODO check if falls in one of the expression categories
            return self.expand(PHENO_ROOT)

    @property
    def validEdges(self):
        qstring = ('SELECT DISTINCT ?prop WHERE '
                   '{ ?prop rdfs:subPropertyOf* %s . }') % PHENO_ROOT
        out = [_[0] for _ in self.graph.query(qstring)]
        return out

    @property
    def eLabel(self):
        return tuple(self._eClass.label)[0]

    @property
    def pLabel(self):
        l = tuple(self._pClass.label)
        if not l:  # we don't want to load the whole ontology
            l = self.sgv.findById(self.p)['labels'][0]
        else:
            l = l[0]
        return l

    @property
    def pHiddenLabel(self):
        l = tuple(self.graph.objects(self.p, rdflib.namespace.SKOS.hiddenLabel))
        if l:
            l = l[0]
        else:
            l = None

        return l

    @property
    def pShortName(self):
        pn = self.graph.namespace_manager.qname(self.p)
        resp = self.sgv.findById(pn)
        if resp:  # DERP
            abvs = resp['abbreviations']
        else:
            abvs = None

        if abvs:
            return abvs[0]
        elif pn in self.local_names:
            return self.local_names[pn]
        else:
            return None

    def _graphify(self):
        return infixowl.Restriction(onProperty=self.e, someValuesFrom=self.p, graph=self.graph)

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
        pn = self.graph.namespace_manager.qname(self.p)
        en = self.graph.namespace_manager.qname(self.e)
        lab = self.pLabel
        return "%s('%s', '%s', '%s')" % (self.__class__.__name__, pn, en, lab)


class NegPhenotypeEdge(PhenotypeEdge):
    """ Class for Negative Phenotypes to simplfy things """


class LogicalPhenoEdge(graphThing):
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
        label = ' '.join([pe.pHiddenLabel for pe in self.pes])
        op = self.local_names[self.graph.namespace_manager.qname(self.op)]
        return '(%s %s)' % (op, label)

    @property
    def pShortName(self):
        return ''.join([pe.pShortName for pe in self.pes])

    def _graphify(self):
        members = []
        for pe in self.pes:
            members.append(pe._graphify())
        intersection = infixowl.BooleanClass(operator=self.op, members=members, graph=self.graph)
        return intersection

    def __repr__(self):
        op = self.local_names[self.graph.namespace_manager.qname(self.op)]
        pes = ", ".join([_.__repr__() for _ in self.pes])
        return "%s(%s, %s)" % (self.__class__.__name__, op, pes)


class Neuron(graphThing):
    # FIXME it may make more sense to manage this in the NeuronArranger
    # so that it can interconvert the two representations
    ORDER = [
        phenoPreds.hasInstanceInSpecies,
        phenoPreds.hasTaxonRank,
        phenoPreds.hasSomaLocatedIn,  # hasSomaLocation?
        phenoPreds.hasLayerLocationPhenotype,  # TODO soma naming...
        phenoPreds.hasMorphologicalPhenotype,
        phenoPreds.hasElectrophysiologicalPhenotype,
        phenoPreds.hasSpikingPhenotype,
        phenoPreds.hasExpressionPhenotype,
        phenoPreds.hasProjectionPhenotype,
    ]
    def __init__(self, *phenotypeEdges, graph=None, id_=None):
        super().__init__()

        if graph: self.graph = graph

        self.id_ = self.expand(id_) if id_ else None
        self.Class = infixowl.Class(self.id_, graph=self.graph)

        if not phenotypeEdges and self.id_:
            # rebuild the bag from the -class- id
            phenotypeEdges = self.bagExisting()

        self.temp_id = rdflib.URIRef('http://TEMP.ORG/%s' % hash(tuple(sorted(phenotypeEdges))))

        self.pes = tuple(sorted(phenotypeEdges))
        self.phenotypes = set((pe.p for pe in self.pes))
        self.edges = set((pe.e for pe in self.pes))
        self._pesDict = {}
        for pe in self.pes:  # FIXME TODO
            if pe.e in self._pesDict:
                self._pesDict[pe.e].append(pe)
            else:
                self._pesDict[pe.e] = [pe]

        if not self.id_:
            self.Class = self.makeGraphStructure()
            self.Class.label = rdflib.Literal(self.label)

    def _tuplesToPes(self, pes):
        for p, e in pes:
            yield PhenotypeEdge(p, e)

    @property
    def label(self):
        def sublab(edge):
            sublabs = []
            if edge in self._pesDict:
                for pe in self._pesDict[edge]:
                    l = pe.pShortName
                    if not l:
                        l = pe.pHiddenLabel
                    if not l:
                        l = pe.pLabel

                    if pe.e == phenoPreds.hasExpressionPhenotype:
                        if type(pe) == NegPhenotypeEdge:
                            l = '-' + l
                        else:
                            l = '+' + l

                    sublabs.append(l)

            return sublabs

        label = []
        for edge in self.ORDER:
            label += sorted(sublab(edge))
            logical = (edge, edge)
            if logical in self._pesDict:
                label += sorted(sublab(logical))

        # species
        # brain region
        # morphology
        # ephys
        # expression
        # projection
        # cell type specific connectivity?
        # circuit role? (principle interneuron...)
        nin_switch = 'neuron' if True else 'interneuron'
        label.append(nin_switch)

        new_label = ' '.join(label)
        #print(tuple(self.Class.label)[0])  # FIXME need to set the label once we generate it and overwrite the old one...
        #print(new_label)
        return new_label
        
    def realize(self):
        """ Get an identifier """
        self.id_ = 'ILX:1234567'

    def validate(self):
        raise TypeError('Ur Neuron Sucks')

    def __repr__(self):
        return self.Class.__repr__()

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
                if type(pe) == tuple:  # we hit a case where we need to inherit phenos from above
                    out.update(pe)
                else:
                    out.add(pe)
        return tuple(out)

        qname = self.graph.namespace_manager.qname(self.id_)
        qstring = """
        SELECT DISTINCT ?match ?edge WHERE {
        %s owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?item .
        ?item rdf:type owl:Restriction .
        ?edge rdfs:subPropertyOf* %s .
        ?item owl:onProperty ?edge .
        ?item owl:someValuesFrom ?match . }""" % (qname,
                                                  PHENO_ROOT,)
        #print(qstring)
        pes = self.graph.query(qstring)
        out = tuple(self._tuplesToPes(pes))
        print(out)
        return out
        #assert len(out) == 1, "%s" % out
        #return out[0]

    def _unpackPheno(self, c, type_=PhenotypeEdge):  # FIXME need to deal with intersections
        if isinstance(c.identifier, rdflib.BNode):
            putativeRestriction = infixowl.CastClass(c, graph=self.graph)
            if isinstance(putativeRestriction, infixowl.BooleanClass):
                bc = putativeRestriction
                op = bc._operator
                pes = []
                for id_ in bc._rdfList:
                    print(id_)
                    pr = infixowl.CastClass(id_, graph=self.graph)
                    if isinstance(pr, infixowl.Class):
                        if id_ == self.expand(NIFCELL_NEURON):
                            print('we got neuron root', id_)
                            continue
                        else:
                            pass  # it is a restriction
                            #print('what is going on here?', pr)
                            #print(dir(pr))

                    p = pr.someValuesFrom
                    e = pr.onProperty
                    pes.append(type_(p, e))
                return tuple(pes)
            else:
                print('WHAT')
                pr = putativeRestriction
                p = pr.someValuesFrom
                e = pr.onProperty
                if p and e:
                    return PhenotypeEdge(p, e)
                else:
                    print(putativeRestriction)
        else:
            # TODO make sure that Neuron is in there somehwere...
            print('what is this thing?', c)

    def makeGraphStructure(self):
        """ Lift phenotypeEdges to Restrictions """
        id_ = self.id_ or self.temp_id
        class_ = infixowl.Class(id_, graph=self.graph)
        #class_.delete()  # this doesn't actually work... it polutes the graph :/????
        class_.subClassOf = [self.expand(DEF_ROOT)]  # convenience
        members = [self.expand(NIFCELL_NEURON)]
        anon = infixowl.Class(graph=self.graph)  # for disjointness
        for pe in self.pes:
            target = pe._graphify()
            if isinstance(pe, NegPhenotypeEdge):
                members.append(target)
            else:
                anon.disjointWith = [target]
        intersection = infixowl.BooleanClass(members=members, graph=self.graph)
        if tuple(anon.disjointWith):
            ec = [intersection, anon]
        else:
            ec = [intersection]
        class_.equivalentClass = ec
        self.Class.replace(class_)  # delete any existing annotations to prevent duplication does this work?
        return class_


class MeasuredNeuron(Neuron):
    """ Class that takes a bag of phenotypes and adds subClassOf axioms"""
    # these should probably require a species and brain region bare minimum?
    # these need to check to make sure the species specific identifiers are being used
    # and warn on mismatch

    def bagExisting(self):  # FIXME intersection an union?
        out = set()  # prevent duplicates in cases where phenotypes are duplicated in the hierarchy
        for c in self.Class.subClassOf:
            pe = self._unpackPheno(c)
            if pe:
                if type(pe) == tuple:  # we hit a case where we need to inherit phenos from above
                    out.update(pe)
                else:
                    out.add(pe)
        for c in self.Class.disjointWith:
            pe = self._unpackPheno(c, NegPhenotypeEdge)
            if pe:
                out.add(pe)
        #print(tuple(self.Class.label)[0])  # FIXME not all classes have labels...
        #print(out)
        return tuple(out)

        # while using the qstring is nice from a documentation standpoint... it is sllllooowww
        # check out infixowl Class.__repr__ for a potentially faster way use CastClass...
        qname = self.graph.namespace_manager.qname(self.id_)
        qstring = """
        SELECT DISTINCT ?match ?edge WHERE {
        %s rdfs:subClassOf ?item .
        ?item rdf:type owl:Restriction .
        ?item owl:onProperty ?edge .
        ?item owl:someValuesFrom ?match . }""" % qname
        #print(qstring)
        pes = list(self.graph.query(qstring))
        #assert len(test) == 1, "%s" % test
        if not pes:
            return self._getIntersectionPhenos(qname)
        else:
            out = tuple(self._tuplesToPes(pes))
            #print(out)
            return out

    def _unpackPheno(self, c, type_=PhenotypeEdge):
        if isinstance(c.identifier, rdflib.BNode):
            putativeRestriction = infixowl.CastClass(c, graph=self.graph)
            if isinstance(putativeRestriction, infixowl.BooleanClass):
                bc = putativeRestriction
                op = bc._operator
                pes = []
                for id_ in bc._rdfList:
                    pr = infixowl.CastClass(id_, graph=self.graph)
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
        pes = self.graph.query(qstring)
        out = tuple(self._tuplesToPes(pes))
        #print('------------------------')
        print(out)
        #print('------------------------')
        return out

    def makeGraphStructure(self):
        class_ = infixowl.Class(self.id_, graph=self.graph)
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
    graph = EXISTING_GRAPH
    def __init__(self, *neurons):
        pass

    def loadDefined(self):
        pass


class neuronManager:
    def __init__(self):
        g = makeGraph('merged', prefixes={k:str(v) for k, v in EXISTING_GRAPH.namespaces()}, graph=EXISTING_GRAPH)
        self.g = g
        self.bag_existing()
        
    def make_neuron(self, graph, bag_of_phenotypes):
        # 0) check that all phenotypes and edges are valid
        # 1) create defined class (equivalentTo) if it does not exist already
        # 2) create regular class (subClassOf) with collection of ALL phenoes
        #       a) find existing superclass candidates, requires ability to 'rebag' phenotypes (set & == set)
        # 3) create type class if not exists or update disjoint union if it does
        #       a) need a flag to check?
        for pheno in bag_of_phenotypes:
            pass

    def get_edge_for_pheno(self, pheno):
        edge = None
        # TODO use scigraph categories function for this?
        # subClassOf UBERON:1?
        #    hasSomaLocatedIn
        #    hasSomaLocatedInLayer
        # subClassOf PR:1?
        #    ilx:hasExpressionPhenotype
        # subClassOf NCBIGene:1?
        #    ilx:hasExpressionPhenotype
        # subClassOf Panther?
        #    ilx:hasExpressionPhenotype
        # subClassOf NCBITaxon:1?
        #    ilx:hasInstanceInSpecies
        # subClassOf ilx:MorphologicalPhenotype
        # subClassOf ilx:ElectrophysiologicalPhenotype
        # subClassOf ilx:parcellation_concept
        return edge, pheno

    def bag_existing(self):  # this reveals the ickyness of ontologies for this...
        reg_neurons = list(self.g.g.subjects(rdflib.RDFS.subClassOf, self.g.expand(NIFCELL_NEURON)))
        tc_neurons = [_ for (_,) in self.g.g.query('SELECT DISTINCT ?match WHERE {?match rdfs:subClassOf+ %s}' % NIFCELL_NEURON)]
        def_neurons = self.g.get_equiv_inter(NIFCELL_NEURON)

        def get_equiv_pheno(n):
            qname = self.g.g.namespace_manager.qname(n)
            qstring = """
            SELECT DISTINCT ?match WHERE {
            %s owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?item .
            ?item rdf:type owl:Restriction .
            ?prop rdfs:subPropertyOf* %s .
            ?item owl:onProperty ?prop .
            ?item owl:someValuesFrom ?match . }""" % (qname,
                                                      'ilx:hasPhenotype',)
            #print(qstring)
            out = list(self.g.g.query(qstring))
            #print(out)
            assert len(out) == 1, "%s" % out
            return out[0]

        def get_reg_pheno(n):  # FIXME fails on intersection of...
            qname = self.g.g.namespace_manager.qname(n)
            qstring = """
            SELECT DISTINCT ?match ?edge WHERE {
            %s rdfs:subClassOf ?item .
            ?item rdf:type owl:Restriction .
            ?item owl:onProperty ?edge .
            ?item owl:someValuesFrom ?match . }""" % qname
            #print(qstring)
            out = list(self.g.g.query(qstring))
            #assert len(test) == 1, "%s" % test
            if not out:
                return get_intersection_phenos(qname)
            else:
                return out

        def get_intersection_phenos(qname):  # composite phenos
            qstring = """
            SELECT DISTINCT ?match ?edge WHERE {
            %s rdfs:subClassOf/owl:intersectionOf/rdf:rest*/rdf:first ?item .
            ?item rdf:type owl:Restriction .
            ?item owl:onProperty ?edge .
            ?item owl:someValuesFrom ?match . }""" % qname
            #print(qstring)
            out = list(self.g.g.query(qstring))
            #print('------------------------')
            #print(out)
            #print('------------------------')
            return out

        #reg_neuron_phenos = [(n, get_reg_pheno(n)) for n in reg_neurons]
        #tc_neuron_phenos = [(n, get_reg_pheno(n)) for n in tc_neurons]
        #def_neuron_phenos = [(n, get_equiv_pheno(n)) for n in def_neurons]

        nodef = sorted(set(tc_neurons) - set(def_neurons))
        mns = [MeasuredNeuron(id_=n) for n in nodef]
        dns = [DefinedNeuron(id_=n) for n in sorted(def_neurons)]
        embed()


def main():
    neuronManager()
    pe = PhenotypeEdge
    asdf = MeasuredNeuron(pe('asdf1', 'ilx:hasPhenotype'), pe('asdf2', 'ilx:hasPhenotype'))

if __name__ == '__main__':
    main()
