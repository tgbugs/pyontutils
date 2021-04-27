import rdflib
from ontquery import OntCuries
from pyontutils import combinators as cmb
from pyontutils.core import OntId, OntTerm as OntTermBase, OntGraph
from pyontutils.namespaces import ilxtr
from pyontutils.closed_namespaces import rdf, rdfs, owl


neurdf = rdflib.Namespace(str(ilxtr) + 'neurdf/')

_current_collection = None
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
__dimensions = Dimensions()
curieprefixes = CuriePrefixes()
roots = Roots()


class OntTerm(OntTermBase):
    """ ask things about a term! """
    skip_for_instrumentation = True

    def __new__(cls, *args, **kwargs):
        try:
            self = OntId.__new__(cls, *args, **kwargs)
        except:
            breakpoint()
            raise
        self._args = args
        self._kwargs = kwargs
        return self

    def fetch(self):
        newself = super().__new__(self.__class__, *self._args, **self._kwargs)
        self.__dict__ = newself.__dict__
        return self

    def isSubPropertyOf(self, property):
        return OntId(property) in self('rdfs:subPropertyOf',
                                       depth=20,
                                       direction='OUTGOING')

    def isSubClassOf(self, class_):
        return OntId(class_) in self('rdfs:subClassOf',
                                     depth=20,
                                     direction='OUTGOING')

    def asType(self, class_):
        return class_(self)

    def _isType(self, name):
        raise NotImplementedError

    def isMolecular(self): return self._isType('molecular')
    def isAnatomical(self): return self._isType('anatomical')
    def isEphys(self): return self._isType('ephys')


class PredicateTerm(OntTerm):
    skip_for_instrumentation = True
    __firsts = tuple()
    def _isType(self, name):
        return self.isSubPropertyOf(getattr(__dimensions, name))

    def _isPropertyType(self, property):
        return self.isSubPropertyOf(property)


class ObjectTerm(OntTerm):
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


class Intersection(frozenset):
    """ Composed intersectional terms are routinely needed when specifying the
    exact locations for dimensions that have cardinality > 1. Axon location is
    a good example. If I have an axon in spinal L1 and an axon in spinal L2 and
    I have an axon in spinal VII and spinal VIII, this is equivalent to at
    least at least 4 possible scenarios, whereas having an axon in spinal L1
    VII and spinal L2 VIII corresponds to only a single scenario. This is
    because hasAxonLocatedIn allows cardinality > 1 (unlike for soma location,
    though even that is somewhat flexible), and because for the card > 1 case,
    phenotype and intersection are not commutative, that is
    (phenotype (intersection region layer)) <=/=>
    (intersection (phenotype region) (phenotype layer))
    it gets worse when there are multiple possible compositions when all
    regions share a layer, but axons are present in different regions in
    different layers """

    # XXX using this complicates the neurdf representation, but sometimes
    # there isn't much we can do about it without materializing terms

    # FIXME enforce member type

    def __new__(cls, *phenotype_values):  # FIXME where to we put/manage names
        self = super().__new__(cls, [ObjectTerm(v) for v in phenotype_values])
        return self

    @property
    def combinator(self):
        return cmb.intersectionOf(*self)

    def asOwl(self, identifier_function=lambda self: rdflib.BNode()):
        s = identifier_function(self)
        yield from self.combinator(s)


# phenotypes


class PhenotypeBase(tuple):

    _defaultPredicate = ilxtr.hasPhenotype

    def __new__(cls, value, dimension=None):  # FIXME consider changing name to aspect
        if dimension is None:
            dimension = self._defaultPredicate

        return super().__new__(cls, (ObjectTerm(value), PredicateTerm(dimension)))

    def __repr__(self):
        p = f', {self.predicate.curie!r}' if self.predicate != self._defaultPredicate else ''
        return self.__class__.__name__ + f'({self.object.curie!r}{p})'

    @property
    def predicate(self):
        # yes this is backwards, but we want it to match the args TODO reconsider?
        return self[1]

    @property
    def object(self):
        return self[0]

    def triples_individual(self, bnode_subject):
        yield bnode_subject, self.predicate.as_URIRef(), self.object.as_URIRef()

    def triples(self, bnode_subject):
        """ restriction version useful for debug """
        yield from self.combinator(bnode_subject)

    def asNeurdf(self, subject):
        u = rdflib.URIRef
        yield subject, self.predicate.asType(u), self.object.asType(u)

    def asOwl(self, subject):
        yield from self.combinator(subject)

    @property
    def combinator(self):
        """ yes, this is a property that returns a function """
        # NOTE a surrounding combinator is needed at the phenotype
        # collection level
        combinator = cmb.Restriction(None)
        return combinator(self.predicate, self.object)

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

    @property
    def prefLabel(self):
        return self.wrapName(self.object.prefLabel(self.predicate))


class Phenotype(PhenotypeBase):
    """ PositivePhenotype """


class NegativePhenotype(PhenotypeBase):

    @property
    def combinator(self):
        Restriction = cmb.Restriction(None)
        combinator = cmb.ObjectCombinator.full_combinator(
            cmb.Class,
            cmb.Pair(owl.complementOf,
                     Restriction(self.predicate,
                                 self.object)))

        return combinator


# phenotype collections


class PhenotypeCollection(frozenset):  # set? seems... fun? ordered set?
    """ untyped bags of atomic phenotypes

        frozenset is used so that collections of phenotypes can be used
        as dictionary keys, uniquely identifying the neuron by type
    """

    linker = None
    operator = None
    neurdf_type = None

    def __new__(cls, *phenotypes):  # FIXME where to we put/manage names
        self = super().__new__(cls, phenotypes)

        # repeated calls to add or massive parenthized statements
        if _current_collection is not None:
            _current_collection.add(self)

        #if hasattr(cls, '_current_collection'):
            #cls._current_collection.add(self)

        return self

    def __init__(self, *phenotypes):
        pass

    def __hash__(self):
        # we cannot use super() here because in pypy3
        # different super()s have different hashes
        # this seems like it is probably a bug
        return hash((self.__class__, frozenset(self)))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def fromRow(cls, row, converter=None): pass
    def asRow(self, converter=None): pass

    @property
    def combinator(self):
        combinator = cmb.PredicateCombinator(self.linker)
        if self.operator is not None:
            cmb_operator = cmb.PredicateList(self.operator)
            class Cmb(cmb.Combinator):
                def __init__(self): pass
                def __call__(self, subject, *objects):
                    if objects:
                        return combinator(subject, cmb_operator(*objects))
                    else:
                        return tuple()

                def __repr__(self):
                    return f'{combinator}(?, {cmb_operator}(*?))'

            return Cmb()

        else:
            return combinator

        raise NotImplementedError('implement in subclass')

    def asNeurdf(self, identifier_function=lambda self: rdflib.BNode()):
        s = identifier_function(self)
        yield s, rdf.type, self.neurdf_type
        for phenotype in self:
            if isinstance(phenotype, PhenotypeCollection):
                linker = rdflib.BNode()
                yield s, ilxtr.subCell, linker
                yield from phenotype.asNeurdf(lambda self: linker)
            else:
                yield from phenotype.asNeurdf(s)

    def asOwl(self, identifier_function=lambda self: rdflib.BNode()):
        # FIXME maybe just use the render function? and control all
        # of this as part of the renderer?
        s = identifier_function(self)
        for type in (PhenotypeCollection, PhenotypeBase):
            combinators = (phenotype.combinator for phenotype in self
                           if isinstance(phenotype, type))
            combinators = list(combinators)
            if type == PhenotypeCollection and combinators:
                asdf = list(self.combinator(s, *combinators))  # reminder: self.combinator is a property that returns a function
                OntGraph().populate_from_triples(asdf).debug()
                breakpoint()  # XXX

            yield from self.combinator(s, *combinators)

    def debug(self, target=None):
        if target is None:
            target = self.asOwl
        OntGraph().populate_from_triples(target()).debug()

    def render(self, render_criteria):  # TODO naming
        """ decouple the rendering of phenotypes from their core definitions """
        yield from render_criteria.triples(self)
        # TODO vs
        #yield from render_criteria(self).triples()


# neurons

class CellBase(PhenotypeCollection):
    """ Immutable collections of phenotypes. """

    def annotate(self, *annotations):
        """ annotate the neuron as a whole """

    def annotate_phenotype(self, phenotype, *annotations):
        _current_collection.annotation(self, phenotype, *annotations)


class EntailedCell(CellBase):
    linker = rdfs.subClassOf
    operator = None
    neurdf_type = neurdf.EntailedCell


class AndCell(CellBase):
    linker = owl.equivalentClass
    operator = owl.intersectionOf
    neurdf_type = neurdf.AndCell


class OrCell(CellBase):
    linker = owl.equivalentClass
    operator = owl.unionOf
    neurdf_type = neurdf.OrCell


class Cell(AndCell):
    #neurdf_type = neurdf.Cell  # leave as AndCell for clarity?
    pass


class QueryCell(OrCell):
    # FIXME not quite an OrNeuron because it is the intersection of
    # a QueryNeuron and the union of its phenotypes
    """ Parent class for all neurons that are used
        for bridging queries. """



# legacy XXX

NegPhenotype = NegativePhenotype  # XXX legacy support


class LogicalPhenotypeLegacy(PhenotypeCollection):
    """ useful for mapping naming conventions among other things """

    def __new__(cls, op, *edges):
        if op == owl.unionOf:
            cls = OrCell
        elif op == owl.intersectionOf:
            cls = AndCell
        else:
            raise TypeError(f'unknown op {op}')

        return cls(*edges)


class PhenotypeLegacy(Phenotype):

    def __new__(cls, value, dimension=None, label=None):
        self = super().__new__(cls, value, dimension)
        if label:
            self.metadata = dict(label=label)

        return self


class NeuronLegacy:
    """ convert from old implementation """

    def __new__(cls, *phenotypesEdges, id_=None, label=None, override=False,
                equivalentNeurons=tuple(), disjointNeurons=tuple()):
        cell = Cell(*phenotypesEdges)
        cell.metadata = dict(id_=id_,
                             label=label,
                             override=override,
                             equivalentNeurons=equivalentNeurons,
                             disjointNeurons=disjointNeurons)
        return cell

    def __init__(*args, **kwargs):
        pass


class CellCollection:
    """ Heed the warnings of your ancestors!
        Just make another object. It will simplify your life!
        But do not do so needlessly! -- Ockham
    """

    # collections are orthgonal to serialization and metadata,
    # thus they should not have that information included at
    # init but instead should be pop

    def __init__(self):
        self._collection = set()

    def __repr__(self):
        global _current_collection
        active = ' ACTIVE' if self == _current_collection else ''
        return self.__class__.__name__ + f' with {len(self)} cells' + active

    def __len__(self):
        return len(self._collection)

    def activate(self):
        """ set this collection as the current
            active collection """
        global _current_collection
        _current_collection = self  # FIXME consider allowing more than one active collection?

    def deactivate(self):
        global _current_collection
        _current_collection = None

    def add(self, *cells):
        # TODO, list? dict? set?
        self._collection.update(cells)

    # can't do from_python
    # this will be the config object
    # so the the latest neuron collection
    # will be where any new neurons are
    # automatically stored
    # one question is whether we use this with a context
    # manager or what ... why not both!

    def asNeurdf(self, identifier_function=lambda self: rdflib.BNode()):
        # TODO I think we definitely want the renderer here to hold
        # all the export confiruation kinds of things
        for cell in self._collection:
            yield from cell.asNeurdf(identifier_function)

    def asOwl(self, identifier_function=lambda self: rdflib.BNode()):
        for cell in self._collection:
            yield from cell.asOwl(identifier_function)

    def debug(self, target=None):
        if target is None:
            target = self.asOwl

        (OntGraph(namespace_manager=dict(OntCuries._dict))
         .populate_from_triples(target())
         .debug())

    def from_remote(self, url):
        """ could be a google sheet or a remote rdf representation """

    def fromFile(self, filename, format=None): pass
    def fromGraph(self, graph):
        """ triples can be a graph """

    def fromTabular(self, rows): pass

    def asPython(self): pass
    def asTabular(self): pass
    def write_python(self, filename): pass
    def write_owl(self, filename): pass
    def write_table(self, filename): pass
    def upload_table(self, filename): pass
