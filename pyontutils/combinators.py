import types
import rdflib
from ontquery.terms import OntId
from pyontutils.utils_extra import check_value
from pyontutils.namespaces import TEMP
from pyontutils.closed_namespaces import rdf, rdfs, owl
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint


def flattenTriples(triples):
    for triple_or_generator in triples:
        if isinstance(triple_or_generator, tuple):
            yield triple_or_generator
        else:
            yield from triple_or_generator


def make_predicate_object_combinator(function, p, o):
    """ Combinator to hold predicate object pairs until a subject is supplied and then
        call a function that accepts a subject, predicate, and object.

        Create a combinator to defer production of a triple until the missing pieces are supplied.
        Note that the naming here tells you what is stored IN the combinator. The argument to the
        combinator is the piece that is missing. """
    def predicate_object_combinator(subject):
        return function(subject, p, o)
    return predicate_object_combinator


def make_object_combinator(function, o):
    def object_combinator(subject, predicate):
        return function(subject, predicate, o)
    return object_combinator


def make_subject_object_combinator(s, function, o):
    def subject_object_combinator(predicate):
        return function(s, predicate, o)
    return subject_object_combinator


def oc(iri, subClassOf=None):
    yield iri, rdf.type, owl.Class
    if subClassOf is not None:
        yield iri, rdfs.subClassOf, subClassOf


def oop(iri, subPropertyOf=None):
    yield iri, rdf.type, owl.ObjectProperty
    if subPropertyOf is not None:
        yield iri, rdfs.subPropertyOf, subPropertyOf


def odp(iri, subPropertyOf=None):
    yield iri, rdf.type, owl.DatatypeProperty
    if subPropertyOf is not None:
        yield iri, rdfs.subPropertyOf, subPropertyOf


def olit(subject, predicate, *objects):
    if not objects:
        raise ValueError(f'{subject} {predicate} Objects is empty?')
    for object in objects:
        if object not in (None, ''):
            yield subject, predicate, rdflib.Literal(object)


class Combinator:  # FIXME naming, these aren't really thunks, they are combinators

    def __init__(self, *present):
        raise NotImplementedError('subclassit')

    def __call__(self, subject, predicate, object):
        yield subject, predicate, object

    @property
    def value(self):
        return tuple(self.__call__())

    def debug(self, *args, l=None, ret=False):
        graph = rdflib.Graph()
        graph.bind('owl', str(owl))
        if l is None:
            l = self.__call__(*args)
        [graph.add(t) for t in l]
        out = graph.serialize(format='nifttl', encoding='utf-8').decode()
        if ret:
            return out
        else:
            print(out)


class CombinatorIt(Combinator):

    def __init__(self, outer_self, *args, **kwargs):
        self.outer_self = outer_self
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        # FIXME might get two subjects by accident...
        if (isinstance(self.outer_self, Combinator) and
            args and
            not isinstance(args[0], str) or
            self.args and self.args[0] is None):
            args = (rdflib.BNode(),) + args
            if self.args[0] is None:
                self.args = self.args[1:]
        elif not args and not self.args:
            args = rdflib.BNode(),

        if (all(hasattr(arg, 'predicate') for arg in self.args) and
            len(args) == 2):
            # all self.args are combinators and
            # subject and predicate were provided
            # mostly for use with ObjectCombinator.full_combinator
            subject_linker = rdflib.BNode()
            yield (*args, subject_linker)
            args = subject_linker,

        yield from self.outer_self.__call__(*args, *self.args, **kwargs, **self.kwargs)

    def __repr__(self):
        return f'{self.outer_self.__class__.__name__} {self.args} {self.kwargs}'

    def serialize(self, graph=None):
        for t in self():
            yield t
            if graph is not None:
                graph.add(t)


class PredicateCombinator(Combinator):

    def __init__(self, predicate):
        self.predicate = predicate

    def __call__(self, subject, *objects):
        for object in objects:
            if isinstance(object, Combinator):
                yield from object(subject, self.predicate)

            elif isinstance(object, rdflib.term.Node):
                yield subject, self.predicate, object

            else:
                msg = f'unhandled type {type(object)} for {object}'
                raise TypeError(msg)

    def __repr__(self):
        if isinstance(self.predicate, rdflib.URIRef):
            o = OntId(self.predicate).curie
        else:
            o = self.predicate

        return f"{self.__class__.__name__}({o!r})"


class ObjectCombinator(Combinator):
    def __init__(self, object):
        self.object = object

    def full_combinator(self, *combinators):  # FIXME this is not right...?
        return CombinatorIt(self, *combinators)

    def __call__(self, subject, predicate):
        if isinstance(self.object, Combinator):
            if hasattr(self.object, 'predicate'):
                yield from self.object(subject)
            else:
                yield from self.object(subject, predicate)
        else:
            yield subject, predicate, self.object

    def __repr__(self):
        if isinstance(self.object, rdflib.URIRef):
            o = OntId(self.object).curie
        elif isinstance(self.object, rdflib.Literal):
            o = self.object.value
        else:
            o = self.object
        return f"{self.__class__.__name__}({o!r})"


class _POCombinator(Combinator):
    def __init__(self, predicate, object):
        self.predicate = predicate
        self.object = object

    def full_combinator(self, subject_or_pocombinator, *pocombinators):  # FIXME this is not right...?
        return CombinatorIt(self, subject_or_pocombinator, *pocombinators)

    def __call__(self, subject, *pocombinators):
        """ Overwrite this function for more complex expansions. """
        # seems unlikely that same object multiple predicates would occur, will impl if needed
        if subject is None:
            subject = rdflib.BNode()

        if isinstance(self.object, Combinator):
            o = rdflib.BNode()
            yield subject, self.predicate, o
            yield from self.object(o)
        else:
            yield subject, self.predicate, self.object
        for combinator in pocombinators:
            try:
                yield from combinator(subject)
            except TypeError as e:
                raise TypeError(f'{combinator} not a combinator!') from e

    def __repr__(self):
        p = OntId(self.predicate).curie
        if isinstance(self.object, rdflib.URIRef):
            o = OntId(self.object).curie
        elif isinstance(self.object, rdflib.Literal):
            o = self.object.value
        else:
            o = self.object
        return f"{self.__class__.__name__}({p!r}, {o!r})"


class POCombinator(_POCombinator):
    def __new__(cls, predicate_, object):
        if isinstance(object, type) and issubclass(object, ObjectCombinator):
            class InnerCombinator(object):
                predicate = predicate_
                def __call__(self, subject):
                    return super().__call__(subject, self.predicate)

            return InnerCombinator
        else:
            self = super().__new__(cls)
            self.__init__(predicate_, object)
            return self


Pair = POCombinator

oc_ = POCombinator(rdf.type, owl.Class)
Class = oc_

Ontology = POCombinator(rdf.type, owl.Ontology)

allDifferent = POCombinator(rdf.type, owl.AllDifferent)


class RestrictionCombinator(_POCombinator):
    def __call__(self, subject, linking_predicate=None):
        if self.outer_self.predicate is not None and linking_predicate is not None:
            if self.outer_self.predicate != linking_predicate:
                raise TypeError(f'Predicates {self.outer_self.predicate} '
                                f'{linking_predicate} do not match on {self!r}')

        yield from self.outer_self.serialize(subject, self.predicate, self.object, linking_predicate)


class RestrictionsCombinator(RestrictionCombinator):
    def __init__(self, *predicate_objects):
        self.predicate_objects = predicate_objects

    def __call__(self, subject, predicate=None):  # FIXME this attaches everything to the same subject
        call = super().__call__
        try:
            for self.predicate, self.object in self.predicate_objects:
                yield from call(subject, predicate)
        except ValueError as e:
            raise ValueError(f'tried to unpack {self.predicate_objects} into predicate, object') from e

        if hasattr(self, 'predicate'):
            del self.predicate
        if hasattr(self, 'object'):
            del self.object

    def __repr__(self):
        return f"{self.__class__.__name__}{tuple(sorted(self.predicate_objects))!r}"


class Triple:
    """ All the BNodes should remain hidden. """

    def _objects(self, graph, subject, predicate):
        yield from graph.objects(subject, predicate)

    def __init__(self):
        pass

    def __call__(self, s, p, o):
        yield from self.serialize(s, p, o)

    def parse(self, *triples, graph=None):
        """ Convert a subgraph into a triple. """
        raise NotImplemented('Do this in derived classes.')
        return 'subject', 'predicate', 'object', self.__class__.__name__

    def serialize(self, s, p, o, *args, **kwargs):
        raise NotImplemented('Do this in derived classes.')

    def _test_roundtrip(self, s, p, o):
        assert self.parse(self.serialize(s, p, o)) == (s, p, o, self.__class__.__name__)


class Restriction2(Triple):
    def __init__(self, linking_predicate, *internal_predicates):
        self.linking_predicate = linking_predicate
        if not internal_predicates:
            self.internal_predicates = owl.someValuesFrom,
        else:
            self.internal_predicates = internal_predicates

    def __call__(self, *internal_objects):
        if len(internal_objects) != len(self.internal_predicates):
            raise ValueError('not enough objects for predicates\n'
                             '{internal_objects} {self.internal_predicates}')

        class Awaiting(Combinator):
            def __init__(self, outer_self, predicates, objects):
                self.outer_self = outer_self
                self.predicates = predicates
                self.objects = objects

            def __call__(self, subject, predicate=self.linking_predicate):
                yield from self.outer_self.serialize(subject, predicate, None,
                                                     self.predicates, self.objects)

        return Awaiting(self, self.internal_predicates, internal_objects)

    def serialize(self, subject, predicate, inner_subject, inner_predicates, inner_objects):
        if subject is None:
            raise TypeError(f'None subject {self}')

        if predicate is None and inner_subject is None:
            inner_subject = subject
        elif predicate is None:
            raise TypeError(f'None predicate {self}')
        elif inner_subject is None:
            inner_subject = rdflib.BNode()
            yield subject, predicate, inner_subject
        else:
            raise ValueError(f'wat')

        yield inner_subject, rdf.type, owl.Restriction
        for p, o in zip(inner_predicates, inner_objects):
            if isinstance(o, Combinator):  # as noted before has to be a poc
                combinator = o
                o = rdflib.BNode()
                yield from combinator(o)
            yield inner_subject, p, o


class Restriction(Triple):
    class RestrictionTriple(tuple):
        @property
        def s(self):
            return self[0]

        @property
        def p(self):
            return self[1]

        @property
        def o(self):
            return self[2]

        def __repr__(self):
            return f"{self.__class__.__name__}{super().__repr__()}"

    def __init__(self, predicate, scope=owl.someValuesFrom):
        """ You may explicitly pass None to predicate if the call to the combinator
            will recieve the predicate. """
        self.predicate = predicate
        self.scope = scope

    def __call__(self, predicate=None, object=None):
        """ combinator maker """
        if object is not None:
            p = predicate
            o = object
        else:
            _, p, o = predicate

        rt = type('RestrictionCombinator', (RestrictionCombinator,), dict(outer_self=self))
        return rt(p, o)

    def serialize(self, s, p, o, linking_predicate=None):  # lift, serialize, expand
        subject = rdflib.BNode()
        if self.predicate is not None:
            yield s, self.predicate, subject
        elif linking_predicate is not None:
            yield s, linking_predicate, subject
        else:
            subject = s  # link directly

        yield subject, rdf.type, owl.Restriction
        yield subject, owl.onProperty, p
        if isinstance(o, Combinator):
            # only pocombinators really work here
            combinator = o
            o = rdflib.BNode()
            yield from combinator(o)
        yield subject, self.scope, o  # TODO serialization of the combinators

    def parse(self, *triples, root=None, graph=None):  # drop, parse, contract
        if graph is None:
            graph = rdflib.Graph()
            [graph.add(t) for t in triples]

        self.triples = []
        for r_s in graph.subjects(rdf.type, owl.Restriction):
            local_trips = [(r_s, rdf.type, owl.Restriction)]
            try:
                s = next(graph.subjects(self.predicate, r_s))  # FIXME cases where there is more than one???
                t = s, self.predicate, r_s
                local_trips.append(t)
                p = next(graph.objects(r_s, owl.onProperty))
                t = r_s, owl.onProperty, p
                local_trips.append(t)
                o = next(graph.objects(r_s, self.scope))
                t = r_s, self.scope, o
                local_trips.append(t)
            except StopIteration:
                print(f'failed to parse {r_s} {self.predicate} {self.scope} {local_trips}')
                continue
            self.triples.extend(local_trips)
            yield self.RestrictionTriple((s, p, o))  # , self.__class__.__name__


restriction = Restriction(rdfs.subClassOf)
restrictionN = Restriction(None)


class Restrictions(Restriction):
    def __call__(self, *predicate_objects):
        #rt = type('RestrictionsCombinator', (RestrictionsCombinator,), dict(outer_self=self))
        #return rt(*predicate_objects)
        rt = type('RestrictionCombinator', (RestrictionCombinator,), dict(outer_self=self))
        return (rt(*p_o) for p_o in predicate_objects)


restrictions = Restrictions(None)


class List(Triple):
    def __init__(self, lift_rules=None):
        if lift_rules is not None:
            self.lift_rules = lift_rules
        else:
            self.lift_rules = {}

    def __call__(self, *objects_or_combinators):
        """ combinator maker """
        class ListCombinator(Combinator):
            outer_self = self
            def __init__(self, *objects_or_combinator):
                self.predicate = rdf.first
                self.objects = objects_or_combinator

            def __call__(self, subject, predicate):
                yield from self.outer_self.serialize(subject, predicate, *self.objects)

            def __repr__(self):
                return f'{self.__class__.__name__}{self.objects!r}'

        return ListCombinator(*objects_or_combinators)

    def __repr__(self):
        return '<List(Triple)>'

    def serialize(self, s, p, *objects_or_combinators):
        # FIXME for restrictions we can't pass the restriction in, we have to know the bnode in advance
        # OR list has to deal with restrictions which is NOT what we want at all...
        subject = rdflib.BNode()
        yield s, p, subject
        stop = len(objects_or_combinators) - 1
        for i, object_combinator in enumerate(objects_or_combinators):
            if isinstance(object_combinator, types.FunctionType) or isinstance(object_combinator, Combinator):
                #if isinstance(object_combinator, POCombinator):
                    #yield from object_combinator(subject)  # in cases where rdf.first already specified
                #elif isinstance(object_combinator, ObjectCombinator):
                yield from object_combinator(subject, rdf.first)  # combinator call must accept a predicate
                #else:
                    #raise TypeError('Unknown Combinator type {object_combinator}')
            else:
                # assume that it is a URIRef or Literal
                yield subject, rdf.first, object_combinator

            if i < stop:  # why would you design a list this way >_<
                next_subject = rdflib.BNode()
            else:
                next_subject = rdf.nil

            yield subject, rdf.rest, next_subject
            subject = next_subject

    def parse(self, *triples, root=None, graph=None):
        if graph is None:
            graph = rdflib.Graph()
            [graph.add(t) for t in triples]
        objects = triples  # TODO
        def firsts(subject):
            for object_first in graph.objects(subject, rdf.first): # should only be one normally
                if isinstance(object_first, rdflib.BNode):
                    rdftype = next(graph.objects(object_first, rdf.type))  # FIXME > 1 types
                    print(rdftype)
                    typep = self.lift_rules[rdftype]
                    yield from (typep(t) for t in # FIXME rule needs to be prefixed...
                                typep.parse(*((object_first, p, o)
                                             for p, o in
                                              graph.predicate_objects(object_first)),
                                            *((s, p, object_first)
                                             for s, p in
                                              graph.subject_predicates(object_first))))
                else:
                    yield object_first
            for object_rest in graph.objects(subject, rdf.rest):
                if object_rest != rdf.nil:
                    yield from firsts(object_rest)

        def process_list(subject):
            try:  # subject should not be the member of a rdf.rest
                next(graph.subjects(rdf.rest, subject))
            except StopIteration:
                print(subject)
                yield self(*firsts(subject))

        if root is not None:
            yield from process_list(root)
        else:
            # find heads of lists
            for subject in graph.subjects(rdf.first, None):
                yield from process_list(subject)

olist = List()

def oec(subject, *object_combinators, relation=owl.intersectionOf):
    n0 = rdflib.BNode()
    yield subject, owl.equivalentClass, n0
    yield from oc(n0)
    yield from olist.serialize(n0, relation, *object_combinators)

def _restriction(lift, s, p, o):
    n0 = rdflib.BNode()
    yield s, rdfs.subClassOf, n0
    yield n0, rdf.type, owl.Restriction
    yield n0, owl.onProperty, p
    yield n0, lift, o


class Annotation(Triple):
    def __call__(self, triple, *predicate_objects):
        if not isinstance(triple, tuple) or isinstance(triple, list):
            raise TypeError(f'{triple} is not a tuple or list!')
        elif len(triple) != 3:
            raise TypeError(f'your triple {triple} is not a triple! it is has len {len(triple)}')
        class AnnotationCombinator(Combinator):
            a_s = rdflib.BNode()
            outer_self = self
            existing = predicate_objects
            def __init__(self, triple):
                self.triple = triple

            @property
            def stored(self):
                for p, o in ((rdf.type, owl.Axiom),) + self.existing:
                    yield p, o

            def __call__(self, *predicate_objects):
                gen = self.stored  # now runs as many times as we want
                a_p, a_o = next(gen)
                yield from self.outer_self.serialize(self.triple, a_p, a_o, a_s=self.a_s, first=True)
                for a_p, a_o in gen:
                    yield from self.outer_self.serialize(self.triple, a_p, a_o, a_s=self.a_s)
                for a_p, a_o in predicate_objects:
                    yield from self.outer_self.serialize(self.triple, a_p, a_o, a_s=self.a_s)

        return AnnotationCombinator(triple)

    def serialize(self, triple, a_p, a_o, a_s=None, first=False):
        s, p, o = triple
        if a_s is None:
            first = True
            a_s = rdflib.BNode()
            yield a_s, rdf.type, owl.Axiom

        if first:
            yield a_s, owl.annotatedSource, s
            yield a_s, owl.annotatedProperty, p
            yield a_s, owl.annotatedTarget, check_value(o)

        yield a_s, a_p, check_value(a_o)

    def parse(self, *triples, graph=None):
        if graph is None:  # TODO decorator for this
            graph = rdflib.Graph()
            [graph.add(t) for t in triples]

        rspt = rdf.type, owl.annotatedSource, owl.annotatedProperty, owl.annotatedTarget
        for a_s in graph.subjects(rdf.type, owl.Axiom):
            s_s = next(graph.objects(a_s, owl.annotatedSource))
            s_p = next(graph.objects(a_s, owl.annotatedProperty))
            s_o = next(graph.objects(a_s, owl.annotatedTarget))
            triple = s_s, s_p, s_o

            # TODO combinator? or not in this case?
            yield triple, tuple((a_p, a_o)
                                for a_p, a_o in graph.predicate_objects(a_s)
                                if a_p not in rspt)

            # duplicated
            #for a_p, a_o in graph.predicate_objects(a_s):
                #if a_p not in rspt:
                    #yield triple, a_p, a_o


annotation = Annotation()


def _annotation(ap, ao, s, p, o):
    n0 = rdflib.BNode()
    yield n0, rdf.type, owl.Axiom
    yield n0, owl.annotatedSource, s
    yield n0, owl.annotatedProperty, p
    yield n0, owl.annotatedTarget, check_value(o)
    yield n0, ap, check_value(ao)

def annotations(pairs, s, p, o):
    n0 = rdflib.BNode()
    yield n0, rdf.type, owl.Axiom
    yield n0, owl.annotatedSource, s
    yield n0, owl.annotatedProperty, p
    yield n0, owl.annotatedTarget, check_value(o)
    for predicate, object in pairs:
        yield n0, predicate, check_value(object)


class PredicateList(Triple):
    predicate = rdf.List
    typeWhenSubjectIsBlank = owl.Class

    def __init__(self, predicate=None):
        if predicate is not None:
            self.predicate = predicate

        self._list = List({owl.Restriction:Restriction(rdf.first)})
        self.lift_rules = {rdf.first:self._list, rdf.rest:None}

    def __call__(self, *objects_or_combinators):
        class PredicateListCombinator(Combinator):
            outer_self = self
            def __init__(self):
                self.combinators = objects_or_combinators

            def __call__(self, subject, predicate=None):
                # FIXME hrm... there should be a way to regularize this?
                # or is it the case than an PO combinator needs to know
                # what to do when upstream doesn't know what it is
                # but want's to attach to an object which doesn't exist yet
                if predicate is not None:
                    s1 = subject
                    subject = rdflib.BNode()
                    yield s1, predicate, subject
                    yield subject, rdf.type, self.outer_self.typeWhenSubjectIsBlank

                yield from self.outer_self.serialize(subject, self.combinators)

            def debug(self):
                return super().debug(rdflib.BNode())

            def __repr__(self):
                return f'{self.__class__.__name__}{self.combinators!r}'

        return PredicateListCombinator()

    def __repr__(self):
        return f'<PredicateList {self.predicate} {self._list}>'

    def serialize(self, subject, objects_or_combinators):
        if subject is None:
            subject = rdflib.BNode()

        yield from self._list.serialize(subject, self.predicate, *objects_or_combinators)


class IntersectionOf(PredicateList):
    predicate = owl.intersectionOf

intersectionOf = IntersectionOf()


class UnionOf(PredicateList):
    predicate = owl.unionOf

unionOf = UnionOf()


class PropertyChainAxiom(PredicateList):
    predicate = owl.propertyChainAxiom

propertyChainAxiom = PropertyChainAxiom()


class OneOf(PredicateList):
    predicate = owl.oneOf

oneOf = OneOf()


class DisjointUnionOf(PredicateList):
    predicate = owl.disjointUnionOf

disjointUnionOf = DisjointUnionOf()


class Members(PredicateList):
    predicate = owl.members

members = Members()


class DistinctMembers(PredicateList):
    predicate = owl.distinctMembers

distinctMembers = DistinctMembers()


class EquivalentClass(Triple):
    """ That moment when you realize you are reimplementing a crappy version of
        owl functional syntax in python. """
    predicate = owl.equivalentClass
    def __init__(self, operator=owl.intersectionOf):
        self.operator = operator
        self._list = List({owl.Restriction:Restriction(rdf.first)})
        self.lift_rules = {rdf.first:self._list, rdf.rest:None}

    def __call__(self, *objects_or_combinators):
        """ combinator maker """
        class EquivalentClassCombinator(Combinator):
            outer_self = self
            def __init__(self, *combinators):
                self.combinators = combinators

            def __call__(self, subject):
                yield from self.outer_self.serialize(subject, *self.combinators)

            def __repr__(self):
                return f'{self.__class__.__name__}{self.combinators!r}'

        return EquivalentClassCombinator(*objects_or_combinators)

    def serialize(self, subject, *objects_or_combinators):
        """ object_combinators may also be URIRefs or Literals """
        ec_s = rdflib.BNode()
        if self.operator is not None:
            if subject is not None:
                yield subject, self.predicate, ec_s
            yield from oc(ec_s)
            yield from self._list.serialize(ec_s, self.operator, *objects_or_combinators)
        else:
            for thing in objects_or_combinators:
                if isinstance(thing, Combinator):
                    object = rdflib.BNode()
                    #anything = list(thing(object))
                    #if anything:
                        #[print(_) for _ in anything]
                    hasType = False
                    for t in thing(object):
                        if t[1] == rdf.type:
                            hasType = True
                        yield t

                    if not hasType:
                        yield object, rdf.type, owl.Class
                else:
                    object = thing

                yield subject, self.predicate, object

    def parse(self, *triples, graph=None):
        if graph is None:  # TODO decorator for this
            graph = rdflib.Graph()
            [graph.add(t) for t in triples]

        for subject, ec_s in graph.subject_objects(self.predicate):
            #rdftype = next(graph.objects(subject, rdf.type))  # FIXME > 1
            def parts(predicate, object):
                #print('aaaaaaaaaaaaa', predicate, object)
                if predicate == rdf.type:
                    if object != owl.Class:
                        raise TypeError('owl:equivalentClass members need to be owl:Classes not {rdftype}')
                elif predicate == self.operator:
                    #yield subject, tuple((p, o) for p, o in graph.predicate_objects(object))
                    for p, o in graph.predicate_objects(object):
                        typep = self.lift_rules[p]
                        if typep is None:
                            continue
                        print(p, typep)
                        if p == rdf.first:
                            # FIXME should not have to be explicit? or are lists special?
                            # equivalent class does not need explicit list combinatoring at the moment
                            # so we just get the objects in the list for now
                            # it looks weird on repr, but that is ok
                            yield from next(typep.parse(root=object, graph=graph)).objects
                        else:
                            #print('AAAAAAAAAAAAA', typep)
                            triples = ((o, _p, _o) for _p, _o in graph.predicate_objects(o))
                            yield from typep.parse(*triples)
                            #yield from typep.parse((o, _p, _o) for _p, _o in graph.predicate_objects(o))
                else:
                    print(f'failed to parse {subject} owl:equivalentClass {predicate} != {self.operator}')

            # FIXME None to get them all?
            combinators = tuple(t for p, o in graph.predicate_objects(ec_s)
                           #for mt in parts(p, o)  # FIXME somewhere someone is not yielding properly
                           # no actually this is correct, it is just that there is indeed a list in there
                           # that is not property combinatored
                           #for t in mt)
                           for t in parts(p, o))
            yield subject, self(*combinators)


oec = EquivalentClass()


class hasAspectChangeCombinator(_POCombinator):
    def __init__(self, aspect, change):
        """
        0 a Restriction
        0 onProperty hasAspectChange
        0 someValuesFrom 1
        1 a Class
        1 subClassOf aspect
        1 subClassOf 2
        2 a Restriction
        2 onProperty hasChangeOverTechnique
        2 someValuesFrom change
        """
        subClassOf = POCombinator(rdfs.subClassOf, ObjectCombinator)

        #self.pocombinator = restrictionN(ilxtr.hasAspectChange,
                                    #oc_.full_combinator(subClassOf(aspect),
                                                   #subClassOf(restriction(ilxtr.hasChangeOverTechnique,
                                                                          #change))))

        self.pocombinator = restrictionN(ilxtr.hasAspectChange,  # FIXME this is too complex...
                                    oc_.full_combinator(intersectionOf(aspect,
                                                                  restrictionN(ilxtr.hasChangeOverTechnique,
                                                                               change))))
    def __call__(self, subject, *pocombinators):
        # the caller does correctly yield from thing(subject)
        return self.pocombinator(subject, *pocombinators)

    def serialize(self, subject):
        yield from self.pocombinator(subject)


def main():
    import rdflib
    from pyontutils.core import makeGraph, makePrefixes, log
    from pyontutils.config import auth

    ub = auth.get_path('ontology-local-repo') / 'ttl/bridge/uberon-bridge.ttl'
    ncrb = auth.get_path('ontology-local-repo') / 'ttl/NIF-Neuron-Circuit-Role-Bridge.ttl'
    if not ub.exists() or not ncrb.exists():
        # just skip this if we can't file the files
        log.warning(f'missing file {ub} or {ncrb}')
        return

    graph = rdflib.Graph()
    graph.parse(ub.as_posix(), format='turtle')
    graph.parse(ncrb.as_posix(), format='ttl')

    ecgraph = rdflib.Graph()
    oec = EquivalentClass()
    test = tuple(oec.parse(graph=graph))

    ft = oc_.full_combinator(test[0][0], test[0][1])
    ftng = makeGraph('thing3', prefixes=makePrefixes('owl', 'TEMP'))
    *ft.serialize(ftng.g),
    ftng.write()

    _roundtrip = list(test[0][1](test[0][0]))
    roundtrip = oc_(test[0][0], test[0][1])  # FIXME not quite there yet...
    for t in roundtrip:
        ecgraph.add(t)
    ecng = makeGraph('thing2', graph=ecgraph, prefixes=makePrefixes('owl', 'TEMP'))
    ecng.write()
    if __name__ == '__main__':
        breakpoint()
        return
    r = Restriction(rdfs.subClassOf)#, scope=owl.allValuesFrom)#NIFRID.has_proper_part)
    l = tuple(r.parse(graph=graph))
    for t in r.triples:
        graph.remove(t)
    ng = makeGraph('thing', graph=graph)
    ng.write()
    #print(l)
    restriction = Restriction(None)#rdf.first)
    ll = List(lift_rules={owl.Restriction:restriction})
    trips = tuple(ll.parse(graph=graph))
    #subClassOf = PredicateCombinator(rdfs.subClassOf)  # TODO should be able to do POCombinator(rdfs.subClassOf, 0bjectCombinator)
    subClassOf = POCombinator(rdfs.subClassOf, ObjectCombinator)
    superDuperClass = subClassOf(TEMP.superDuperClass)  # has to exist prior to triples
    ec = oec(TEMP.ec1, TEMP.ec2,
             restriction(TEMP.predicate0, TEMP.target1),
             restriction(TEMP.predicate1, TEMP.target2),)
    egraph = rdflib.Graph()
    acombinator = annotation((TEMP.testSubject, rdf.type, owl.Class), (TEMP.hoh, 'FUN'))
    ft = flattenTriples((acombinator((TEMP.annotation, 'annotation value')),
                         acombinator((TEMP.anotherAnnotation, 'annotation value again')),
                         oc_(TEMP.c1, superDuperClass),
                         oc_(TEMP.c2, superDuperClass),
                         oc_(TEMP.c3, superDuperClass),
                         oc_(TEMP.c4, superDuperClass),
                         oc_(TEMP.c5, superDuperClass),
                         oc_(TEMP.wat, subClassOf(TEMP.watParent)),
                         oc_(TEMP.testSubject),
                         ec(TEMP.testSubject),
                         oc_(TEMP.more, oec(TEMP.ec3, restriction(TEMP.predicate10, TEMP.target10))),),)
    [egraph.add(t) for t in ft]
    eng = makeGraph('thing1', graph=egraph, prefixes=makePrefixes('owl', 'TEMP'))
    eng.write()
    if __name__ == '__main__':
        breakpoint()


if __name__ == '__main__':
    main()
