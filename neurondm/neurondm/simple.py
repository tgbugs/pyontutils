import rdflib
from ontquery import OntCuries
from pyontutils import combinators as cmb
from pyontutils.core import OntId, OntTerm as OntTermBase
from pyontutils.namespaces import ilxtr
from pyontutils.closed_namespaces import rdf, rdfs, owl

a = rdf.type

current_collection = None
current_conventions = None


class Dimensions:
    molecular = ilxtr.hasMolecularPhenotype
    anatomical = ilxtr.hasLocationPhenotype
    ephys = ilxtr.hasElectrophysiologicalPhenotype

class CuriePrefixes:  # TODO populate these rationally
    molecular = (
        'CHEBI', 'PR', 'NCBIGene',
    )

    anatomical = (
        'UBERON',
        'FMA',
        'MBA',
        'PAXRAT',
    )

class Roots:
    molecular = (
        'ilxtr:gene', 'molecular entity', 'chemical entity'
    )


# init because some attrs will need to be switched
# to properties
dimensions = Dimensions()
curieprefixes = CuriePrefixes()
roots = Roots()


class OntTerm(OntTermBase):
    """ ask things about a term! """
    skip_for_instrumentation = True

    def isSubPropertyOf(self, property):
        return OntId(property) in self('rdfs:subPropertyOf',
                                       depth=20,
                                       direction='OUTGOING')

    def isSubClassOf(self, class_):
        return OntId(class_) in self('rdfs:subClassOf',
                                     depth=20,
                                     direction='OUTGOING')

    def _isType(self, name):
        raise NotImplementedError

    def isMolecular(self): return self._isType('molecular')
    def isAnatomical(self): return self._isType('anatomical')
    def isEphys(self): return self._isType('ephys')


class PredicateTerm(OntTermBase):
    skip_for_instrumentation = True
    __firsts = tuple()
    def _isType(self, name):
        return self.isSubPropertyOf(getattr(dimensions, name))

    def _isPropertyType(self, property):
        return self.isSubPropertyOf(property)


class ObjectTerm(OntTermBase):
    skip_for_instrumentation = True
    __firsts = tuple()
    def _isType(self, name):
        return (self.prefix in getattr(prefixes, name)
                or any(self.subClassOf(r) for r in getattr(roots, name)))

    def shortName(self, predicate):
        pass

    def longName(self, predicate):
        pass

    def localName(self, predicate):
        global current_conventions


class PhenotypeBase(tuple):
    _defaultPredicate = ilxtr.hasPhenotype
    def __new__(cls, value, dimension=_defaultPredicate):
        return super().__new__(cls, (ObjectTerm(value), PredicateTerm(dimension)))

    def __repr__(self):
        p = f', {self.predicate}' if self.predicate != self._defaultPredicate else ''
        return self.__class__.__name__ + f'({self.object}{p})'
    @property
    def predicate(self):
        # yes this is backwards, but we want it to match the args
        return self[1]

    @property
    def object(self):
        return self[0]

    def triples_individual(self, bnode_subject):
        yield bnode_subject, self.predicate.as_URIRef(), self.object.as_URIRef()

    def triples(self, bnode_subject):
        """ restriction version useful for debug """
        yield from self.combinator(bnode_subject)

    @property
    def combinator(self):
        """ yes, this is a property that returns a function """
        return cmb.restriction(self.predicate, self.object)

    def annotate(self, neuron, *annotations):
        """ in order to annotate a phenotype you must also
        supply a neuron in which it resides """

        neuron.annotate_phenotype(*annotations)

    def wrapName(self, name):
        return self.namePrefix + name + self.nameSuffix

    @property
    def shortName(self):
        return self.wrapName(self.object.shortName(self.predicate))

    @property
    def longName(self):
        return self.wrapName(self.object.longName(self.predicate))

    @property
    def localName(self):
        return self.wrapName(self.object.localName(self.predicate))


class Phenotype(PhenotypeBase):
    """ PositivePhenotype """


class NegativePhenotype(PhenotypeBase):
    pass


NegPhenotype = NegativePhenotype  # XXX legacy support


# phenotype collections


class PhenotypeCollection(frozenset):  # set? seems... fun? ordered set?
    """ untyped bags of atomic phenotypes """

    operator = None

    def __new__(cls, *phenotypes):
        self = super().__new__(cls, phenotypes)
        return self

    def __init__(self, *phenotypes):
        self.identifier = rdflib.BNode()
        pass

    @property
    def triples(self):
        list_ = cmb.List({owl.Restriction:cmb.Restriction(rdf.first)})
        yield self.identifier, a, owl.Class
        conbinators = (p.combinator for p in self)
        yield from list_.serialize(self.identifier, self.operator, *combinators)


PhenotypeCollection(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'))


class LogicalPhenotype(PhenotypeCollection):
    """ useful for mapping naming conventions among other things """


# neurons

class NeuronBase(PhenotypeCollection):
    """ Immutable collections of phenotypes. """

    def annotate(self, *annotations):
        """ annotate the neuron as a whole """

    def annotate_phenotype(self, phenotype, *annotations):
        current_collection.annotation(self, phenotype, *annotations)


class AndNeuron(NeuronBase):
    operator = owl.intersectionOf


class OrNeuron(NeuronBase):
    operator = owl.unionOf


class Neuron(AndNeuron):
    pass


class QueryNeuron(OrNeuron):
    # FIXME not quite an OrNeuron because it is the intersection of
    # a QueryNeuron and the union of its phenotypes
    """ Parent class for all neurons that are used
        for bridging queries. """


class NeuronCollection:
    """ Heed the warnings of your ancestors!
        Just make another object. It will simplify your life!
        But do not do so needlessly! -- Ockham
    """

    def __init__(self,  # TODO the best parts from config ... (hah)
                 name=None,
                 comment=None,
                 metadata=None,):
        pass

    def activate(self):
        """ set this collection as the current
            active collection """
        global current_collection
        currrent_collection = self

    def add(self, neuron):
        # TODO, list? dict? set?
        pass

    # can't do from_python
    # this will be the config object
    # so the the latest neuron collection
    # will be where any new neurons are
    # automatically stored
    # one question is whether we use this with a context
    # manager or what ... why not both!

    def from_remote(self, url):
        """ could be a google sheet or a remote rdf representation """
    def from_file(self, filename, format=None): pass
    def from_graph(self, graph):
        """ triples can be a graph """

    def from_table(self, rows): pass

    def as_python(self): pass
    def as_owl(self, format='nifttl'):
        graph = rdflib.Graph()
        OntCuries.populate(graph)

    def as_table(self): pass

    def write_python(self, filename): pass
    def write_owl(self, filename): pass
    def write_table(self, filename): pass
    def upload_table(self, filename): pass
