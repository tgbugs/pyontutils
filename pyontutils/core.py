import os
import yaml
import types
import subprocess
import rdflib
import requests
from pathlib import Path
from collections import namedtuple
from inspect import getsourcelines, getsourcefile
from rdflib.extras import infixowl
from joblib import Parallel, delayed
import ontquery
from pyontutils import closed_namespaces as cnses
from pyontutils.utils import refile, TODAY, UTCNOW, getCommit, Async, deferred, TermColors as tc
from pyontutils.closed_namespaces import *
from IPython import embed

# prefixes

def interlex_namespace(user):
    return 'http://uri.interlex.org/' + user

def _loadPrefixes():
    try:
        with open(refile(__file__, '../scigraph/nifstd_curie_map.yaml'), 'rt') as f:
            curie_map = yaml.load(f)
    except FileNotFoundError:
        curie_map = requests.get('https://github.com/tgbugs/pyontutils/blob/master/scigraph/nifstd_curie_map.yaml?raw=true')
        curie_map = yaml.load(curie_map.text)

    # holding place for values that are not in the curie map
    full = {
        #'':None,  # safety (now managed directly in the curies file)
        #'EHDAA2':'http://purl.obolibrary.org/obo/EHDAA2_',  # FIXME needs to go in curie map?

        'hasRole':'http://purl.obolibrary.org/obo/RO_0000087',
        'inheresIn':'http://purl.obolibrary.org/obo/RO_0000052',
        'bearerOf':'http://purl.obolibrary.org/obo/RO_0000053',
        'participatesIn':'http://purl.obolibrary.org/obo/RO_0000056',
        'hasParticipant':'http://purl.obolibrary.org/obo/RO_0000057',
        'hasInput':'http://purl.obolibrary.org/obo/RO_0002233',
        'hasOutput':'http://purl.obolibrary.org/obo/RO_0002234',
        'adjacentTo':'http://purl.obolibrary.org/obo/RO_0002220',
        'derivesFrom':'http://purl.obolibrary.org/obo/RO_0001000',
        'derivesInto':'http://purl.obolibrary.org/obo/RO_0001001',
        'agentIn':'http://purl.obolibrary.org/obo/RO_0002217',
        'hasAgent':'http://purl.obolibrary.org/obo/RO_0002218',
        'containedIn':'http://purl.obolibrary.org/obo/RO_0001018',
        'contains':'http://purl.obolibrary.org/obo/RO_0001019',
        'locatedIn':'http://purl.obolibrary.org/obo/RO_0001025',
        'locationOf':'http://purl.obolibrary.org/obo/RO_0001015',
        'toward':'http://purl.obolibrary.org/obo/RO_0002503',

        'replacedBy':'http://purl.obolibrary.org/obo/IAO_0100001',
        'hasCurStatus':'http://purl.obolibrary.org/obo/IAO_0000114',
        'definition':'http://purl.obolibrary.org/obo/IAO_0000115',
        'editorNote':'http://purl.obolibrary.org/obo/IAO_0000116',
        'termEditor':'http://purl.obolibrary.org/obo/IAO_0000117',
        'altTerm':'http://purl.obolibrary.org/obo/IAO_0000118',
        'defSource':'http://purl.obolibrary.org/obo/IAO_0000119',
        'termsMerged':'http://purl.obolibrary.org/obo/IAO_0000227',
        'obsReason':'http://purl.obolibrary.org/obo/IAO_0000231',
        'curatorNote':'http://purl.obolibrary.org/obo/IAO_0000232',
        'importedFrom':'http://purl.obolibrary.org/obo/IAO_0000412',

        # realizes the proper way to connect a process to a continuant
        'realizedIn':'http://purl.obolibrary.org/obo/BFO_0000054',
        'realizes':'http://purl.obolibrary.org/obo/BFO_0000055',

        'partOf':'http://purl.obolibrary.org/obo/BFO_0000050',
        'hasPart':'http://purl.obolibrary.org/obo/BFO_0000051',
    }

    normal = {
        'ILX':'http://uri.interlex.org/base/ilx_',
        'ilx':'http://uri.interlex.org/base/',
        'ilxr':'http://uri.interlex.org/base/readable/',
        'ilxtr':'http://uri.interlex.org/tgbugs/uris/readable/',
        # for obo files with 'fake' namespaces, http://uri.interlex.org/fakeobo/uris/ eqiv to purl.obolibrary.org/
        'fobo':'http://uri.interlex.org/fakeobo/uris/obo/',

        'PROTEGE':'http://protege.stanford.edu/plugins/owl/protege#',
        'ILXREPLACE':'http://ILXREPLACE.org/',
        'TEMP': interlex_namespace('temp/uris/'),
        'FIXME':'http://FIXME.org/',
        'NIFTTL':'http://ontology.neuinfo.org/NIF/ttl/',
        'NIFRET':'http://ontology.neuinfo.org/NIF/Retired/NIF-Retired.owl#',
        'NLXWIKI':'http://neurolex.org/wiki/',
        'dc':'http://purl.org/dc/elements/1.1/',
        'dcterms':'http://purl.org/dc/terms/',
        'dctypes':'http://purl.org/dc/dcmitype/',  # FIXME there is no agreement on qnames
        # FIXME a thought: was # intentionally used to increase user privacy? or is this just happenstance?
        'nsu':'http://www.FIXME.org/nsupper#',
        'oboInOwl':'http://www.geneontology.org/formats/oboInOwl#',
        'owl':'http://www.w3.org/2002/07/owl#',
        'ro':'http://www.obofoundry.org/ro/ro.owl#',
        'skos':'http://www.w3.org/2004/02/skos/core#',
        'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
        'prov':'http://www.w3.org/ns/prov#',
    }
    #extras = {**{k:rdflib.URIRef(v) for k, v in full.items()}, **normal}
    extras = {**full, **normal}
    curie_map.update(extras)
    return curie_map

PREFIXES = _loadPrefixes()

def makePrefixes(*prefixes):
    return {k:PREFIXES[k] for k in prefixes}

def makeNamespaces(*prefixes):
    return tuple(rdflib.Namespace(PREFIXES[prefix]) for prefix in prefixes)

def makeURIs(*prefixes):
    return tuple(rdflib.URIRef(PREFIXES[prefix]) for prefix in prefixes)

# namespaces

(HBA, MBA, NCBITaxon, NIFRID, NIFTTL, UBERON, BFO, ilxtr,
 ilxb, TEMP) = makeNamespaces('HBA', 'MBA', 'NCBITaxon', 'NIFRID', 'NIFTTL', 'UBERON',
                       'BFO', 'ilxtr', 'ilx', 'TEMP')

# note that these will cause problems in SciGraph because I've run out of hacks still no https
DHBA = rdflib.Namespace('http://api.brain-map.org/api/v2/data/Structure/')
DMBA = rdflib.Namespace('http://api.brain-map.org/api/v2/data/Structure/')

# interlex namespaces
ilx = rdflib.Namespace(interlex_namespace(''))  # XXX NOTE NOT /base/
AIBS = rdflib.Namespace(interlex_namespace('aibs/uris/'))
ilxHBA = rdflib.Namespace(interlex_namespace('aibs/uris/human/labels/'))
ilxMBA = rdflib.Namespace(interlex_namespace('aibs/uris/mouse/labels/'))
ilxDHBA = rdflib.Namespace(interlex_namespace('aibs/uris/human/devel/labels/'))
ilxDMBA = rdflib.Namespace(interlex_namespace('aibs/uris/mouse/devel/labels/'))
FSLATS = rdflib.Namespace(interlex_namespace('fsl/uris/atlases/'))
HCPMMP = rdflib.Namespace(interlex_namespace('hcp/uris/mmp/labels/'))
PAXMUS = rdflib.Namespace(interlex_namespace('paxinos/uris/mouse/labels/'))
paxmusver = rdflib.Namespace(interlex_namespace('paxinos/uris/mouse/versions/'))
PAXRAT = rdflib.Namespace(interlex_namespace('paxinos/uris/rat/labels/'))
paxratver = rdflib.Namespace(interlex_namespace('paxinos/uris/rat/versions/'))
WHSSD = rdflib.Namespace(interlex_namespace('waxholm/uris/sd/labels/'))

# retired namespaces kept as a record in the even that we need them for some reason
_OLD_HCPMMP = rdflib.Namespace(interlex_namespace('hcpmmp/uris/labels/'))

rdf = rdflib.RDF
rdfs = rdflib.RDFS

(replacedBy, definition, hasPart, hasRole, hasParticipant, hasInput, hasOutput,
 realizes,
) = makeURIs('replacedBy', 'definition', 'hasPart', 'hasRole', 'hasParticipant',
             'hasInput', 'hasOutput', 'realizes'
            )

# common funcs

def nsExact(namespace, slash=True):
    uri = str(namespace)
    if not slash:
        uri = uri[:-1]
    return rdflib.URIRef(uri)

def check_value(v):
    if isinstance(v, rdflib.Literal) or isinstance(v, rdflib.URIRef):
        return v
    elif isinstance(v, str) and v.startswith('http'):
        return rdflib.URIRef(v)
    else:
        return rdflib.Literal(v)

def ont_setup(ont):
    ont.prepare()
    o = ont()
    return o

def ont_make(o):
    o()
    o.validate()
    o.write()
    return o

def ont_doit(ont):
    return make(ont_setup(ont))

def build(*onts, n_jobs=9):
    """ Set n_jobs=1 for debug or embed() will crash. """
    # have to use a listcomp so that all calls to setup()
    # finish before parallel goes to work
    return Parallel(n_jobs=n_jobs)(delayed(ont_make)(o) for o in
                                   #[ont_setup(ont) for ont in onts])
                                   (Async()(deferred(ont_setup)(ont)
                                           for ont in onts
                                           if ont.__name__ != 'parcBridge')
                                    if n_jobs > 1
                                    else [ont_setup(ont)
                                          for ont in onts
                                          if ont.__name__ != 'parcBridge']))

def make_predicate_object_thunk(function, p, o):
    """ Thunk to hold predicate object pairs until a subject is supplied and then
        call a function that accepts a subject, predicate, and object.

        Create a thunk to defer production of a triple until the missing pieces are supplied.
        Note that the naming here tells you what is stored IN the thunk. The argument to the
        thunk is the piece that is missing. """
    def predicate_object_thunk(subject):
        return function(subject, p, o)
    return predicate_object_thunk

def make_object_thunk(function, o):
    def object_thunk(subject, predicate):
        return function(subject, predicate, o)
    return object_thunk

def make_subject_object_thunk(s, function, o):
    def subject_object_thunk(predicate):
        return function(s, predicate, o)
    return subject_object_thunk

def oc(iri, subClassOf=None):
    yield iri, rdf.type, owl.Class
    if subClassOf is not None:
        yield iri, rdfs.subClassOf, subClassOf

def oop(iri, subPropertyOf=None):
    yield iri, rdf.type, owl.ObjectProperty
    if subPropertyOf is not None:
        yield iri, rdfs.subPropertyOf, subPropertyOf

def olit(subject, predicate, *objects):
    if not objects:
        raise ValueError(f'{subject} {predicate} Objects is empty?')
    for object in objects:
        if object not in (None, ''):
            yield subject, predicate, rdflib.Literal(object)

class Thunk:
    def __init__(self, *present):
        raise NotImplemented

    def __call__(self, subject, predicate, object):
        yield subject, predicate, object


class ObjectThunk(Thunk):
    def __init__(self, object):
        self.object = object

    def __call__(self, subject, predicate):
        yield subject, predicate, self.object

    def __repr__(self):
        if isinstance(self.object, rdflib.URIRef):
            o = qname(self.object)
        elif isinstance(self.object, rdflib.Literal):
            o = self.object.value
        else:
            o = self.object
        return f"{self.__class__.__name__}({o!r})"


class _POThunk(Thunk):
    def __init__(self, predicate, object):
        self.predicate = predicate
        self.object = object

    def __call__(self, subject, *pothunks):
        """ Overwrite this function for more complex expansions. """
        # seems unlikely that same object multiple predicates would occur, will impl if needed
        yield subject, self.predicate, self.object
        for thunk in pothunks:
            #if isinstance(thunk, types.GeneratorType):
                #thunk = next(thunk)  # return the trapped thunk ;_;
            #else:
            yield from thunk(subject)

    def __repr__(self):
        p = qname(self.predicate)
        if isinstance(self.object, rdflib.URIRef):
            o = qname(self.object)
        elif isinstance(self.object, rdflib.Literal):
            o = self.object.value
        else:
            o = self.object
        return f"{self.__class__.__name__}({p!r}, {o!r})"


class POThunk(_POThunk):
    def __new__(cls, predicate, object):
        if isinstance(object, type) and issubclass(object, ObjectThunk):
            class InnerThunk(object):
                _predicate = predicate
                def __call__(self, subject):
                    return super().__call__(subject, self._predicate)

            return InnerThunk
        else:
            self = super().__new__(cls)
            self.__init__(predicate, object)
            return self


oc_ = POThunk(rdf.type, owl.Class)


class RestrictionThunk(_POThunk):
    def __call__(self, subject, predicate=None):
        print(self.predicate, self.object)
        generator = self.outer_self.serialize(subject, self.predicate, self.object)
        if self.outer_self.predicate is None and predicate is None:
            raise TypeError(f'No predicate defined for {self!r}')
        elif self.outer_self.predicate is not None and predicate is not None:
            if self.outer_self.predicate != predicate:
                raise TypeError(f'Predicates {self.outer_self.predicate} {predicate} do not match on {self!r}')
        elif self.outer_self.predicate is None:
            self.outer_self.predicate = predicate
            yield from generator
            self.outer_self.predicate = None
        else:
            yield from generator


class RestrictionsThunk(RestrictionThunk):
    def __init__(self, *predicate_objects):
        self.predicate_objects = predicate_objects

    def __call__(self, subject, predicate=None):
        call = super().__call__
        for self.predicate, self.object in self.predicate_objects:
            yield from call(subject, predicate)

        if hasattr(self, 'predicate'):
            del self.predicate
        if hasattr(self, 'object'):
            del self.object


class Triple:
    """ All the BNodes should remain hidden. """
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


class Restriction(Triple):
    def __init__(self, predicate, scope=owl.someValuesFrom):
        """ You may explicitly pass None to predicate if the call to the thunk
            will recieve the predicate. """
        self.predicate = predicate
        self.scope = scope

    def __call__(self, predicate=None, object=None):
        """ thunk maker """
        if object is not None:
            p = predicate
            o = object
        else:
            _, p, o = predicate

        rt = type('RestrictionThunk', (RestrictionThunk,), dict(outer_self=self))
        return rt(p, o)

    def serialize(self, s, p, o):  # lift, serialize, expand
        subject = rdflib.BNode()
        yield s, self.predicate, subject
        yield subject, rdf.type, owl.Restriction
        yield subject, owl.onProperty, p
        yield subject, self.scope, o

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
            yield s, p, o  # , self.__class__.__name__

restriction = Restriction(rdfs.subClassOf)

class Restrictions(Restriction):
    def __call__(self, *predicate_objects):
        rt = type('RestrictionsThunk', (RestrictionsThunk,), dict(outer_self=self))
        return rt(*predicate_objects)

restrictions = Restrictions(None)

def __restrictions(*rests):
    for rest in rests:
        yield from restriction(*rest)


def _restrictions(*predicate_objects, scope=owl.someValuesFrom):
    """ restriction_object_thunk """
    for p, o in predicate_objects:
        def function(subject, predicate, object, p=p):
            # note that in this case object = o
            r = Restriction(predicate, scope)
            yield from r.serialize(subject, p, object)
        yield make_object_thunk(function, o)

class List(Triple):
    def __init__(self, lift_rules=None):
        if lift_rules is not None:
            self.lift_rules = lift_rules
        else:
            self.lift_rules = {}

    def _old__call__(self, s, p, *objects_or_thunks):
        """ Normal objects are accepted as well as object thunks.
            But if you have to deal with BNodes, use an object thunk. """
        yield from self.serialize(s, p, *objects_or_thunks)

    def __call__(self, *objects_or_thunks):
        """ thunk maker """
        class ListThunk(Thunk):
            outer_self = self
            def __init__(self, *objects_or_thunk):
                self.predicate = rdf.first
                self.objects = objects_or_thunk

            def __call__(self, subject, predicate):
                yield from self.outer_self.serialize(subject, predicate, *self.objects)

            def __repr__(self):
                return f'{self.objects!r}'

        return ListThunk(*objects_or_thunks)

    def serialize(self, s, p, *objects_or_thunks):
        # FIXME for restrictions we can't pass the restriction in, we have to know the bnode in advance
        # OR list has to deal with restrictions which is NOT what we want at all...
        subject = rdflib.BNode()
        yield s, p, subject
        stop = len(objects_or_thunks) - 1
        for i, object_thunk in enumerate(objects_or_thunks):
            if isinstance(object_thunk, types.FunctionType) or isinstance(object_thunk, Thunk):
                #if isinstance(object_thunk, POThunk):
                    #yield from object_thunk(subject)  # in cases where rdf.first already specified
                #elif isinstance(object_thunk, ObjectThunk): 
                yield from object_thunk(subject, rdf.first)  # thunk call must accept a predicate
                #else:
                    #raise TypeError('Unknown Thunk type {object_thunk}')
            else:
                # assume that it is a URIRef or Literal
                yield subject, rdf.first, object_thunk

            if i < stop:  # why would you design a list this way >_<
                next_subject = rdflib.BNode()
            else:
                next_subject = rdf.nil

            yield subject, rdf.rest, next_subject
            subject = next_subject

    def parse(self, *triples, graph=None):
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

        # find heads of lists
        for subject in graph.subjects(rdf.first, None):
            try:  # subject should not be the member of a rdf.rest
                next(graph.subjects(rdf.rest, subject))
            except StopIteration:
                print(subject)
                yield tuple(firsts(subject))

olist = List()

def oec(subject, *object_thunks, relation=owl.intersectionOf):
    n0 = rdflib.BNode()
    yield subject, owl.equivalentClass, n0
    yield from oc(n0)
    yield from olist.serialize(n0, relation, *object_thunks)

def _restriction(lift, s, p, o):
    n0 = rdflib.BNode()
    yield s, rdfs.subClassOf, n0
    yield n0, rdf.type, owl.Restriction
    yield n0, owl.onProperty, p
    yield n0, lift, o


class Annotation(Triple):
    def __call__(self, triple, *predicate_objects):
        class AnnotationThunk(Thunk):
            a_s = rdflib.BNode()
            outer_self = self
            existing = predicate_objects
            def __init__(self, triple):
                self.triple = triple
                self.stored = ((p, o) for p, o in ((rdf.type, owl.Axiom),) + self.existing)

            def __call__(self, *predicate_objects):
                for a_p, a_o in predicate_objects:
                    yield from self.outer_self.serialize(self.triple, a_p, a_o, a_s=self.a_s)
                for a_p, a_o in self.stored:  # since it is a generator it will only run once
                    yield from self.outer_self.serialize(self.triple, a_p, a_o, a_s=self.a_s)

        return AnnotationThunk(triple)

    def serialize(self, triple, a_p, a_o, a_s=None):
        s, p, o = triple
        if a_s is None:
            a_s = rdflib.BNode()
            yield a_s, rdf.type, owl.Axiom

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

            # TODO thunk? or not in this case?
            yield triple, tuple((a_p, a_o) for a_p, a_o in graph.predicate_objects(a_s) if a_p not in rspt)

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

class EquivalentClass(Triple):
    def __init__(self, operator=owl.intersectionOf):
        self.operator = operator
        self._list = List({owl.Restriction:Restriction(rdf.first)})

    def __call__(self, *objects_or_thunks):
        """ thunk maker """
        class EquivalentClassThunk(Thunk):
            outer_self = self
            def __init__(self, *thunks):
                self.thunks = thunks

            def __call__(self, subject):
                yield from self.outer_self.serialize(subject, *self.thunks)

            def __repr__(self):
                return f'{self.thunks!r}'
        return EquivalentClassThunk(*objects_or_thunks)

    def _old__call__(self, subject, *objects_or_thunks):
        yield from self.serialize(subject, *objects_or_thunks)

    def serialize(self, subject, *objects_or_thunks):
        """ object_thunks may also be URIRefs or Literals """
        ec_s = rdflib.BNode()
        yield subject, owl.equivalentClass, ec_s
        yield from oc(ec_s)
        yield from self._list.serialize(ec_s, self.operator, *objects_or_thunks)

    def parse(self, *triples, graph=None):
        return subject, members 

oec = EquivalentClass()

def yield_recursive(s, p, o, source_graph):  # FIXME transitive_closure on rdflib.Graph?
    yield s, p, o
    new_s = o
    if isinstance(new_s, rdflib.BNode):
        for p, o in source_graph.predicate_objects(new_s):
            yield from yield_recursive(new_s, p, o, source_graph)

#
# old impl

OntMeta = namedtuple('OntMeta',
                     ['path',
                      'filename',
                      'name',
                      'shortname',
                      'comment',
                      'version'])
OntMeta('http://ontology.neuinfo.org/NIF/ttl/',
        'swallows',
        'Python Ontology',
        'PO',
        'Tis a silly place.',
        '-1')

def getNamespace(prefix, namespace):
    if prefix in cnses.__all__:
        return getattr(cnses, prefix)
    elif prefix == 'rdf':
        return rdf
    elif prefix == 'rdfs':
        return rdfs
    else:
        return rdflib.Namespace(namespace)

class makeGraph:
    SYNONYM = 'NIFRID:synonym'  # dangerous with prefixes

    def __init__(self, name, prefixes=None, graph=None, writeloc='/tmp/'):
        self.name = name
        self.writeloc = writeloc
        self.namespaces = {}
        if prefixes:
            self.namespaces.update({p:getNamespace(p, ns) for p, ns in prefixes.items()})
        if graph:  # graph takes precidence
            self.namespaces.update({p:getNamespace(p, ns) for p, ns in graph.namespaces()})
        if graph is None and not prefixes:
            raise ValueError('No prefixes or graph specified.')

        if graph is not None:
            self.g = graph
        else:
            self.g = rdflib.Graph()  # default args issue

        for p, ns in self.namespaces.items():
            self.add_namespace(p, ns)
        self.namespaces.update({p:getNamespace(p, ns)
                                for p, ns in self.g.namespaces()})  # catchall for namespaces in self.g

    def add_known_namespaces(self, *prefixes):
        for prefix in prefixes:
            if prefix not in self.namespaces:
                self.add_namespace(prefix, PREFIXES[prefix])

    def add_namespace(self, prefix, namespace):
        self.namespaces[prefix] = getNamespace(prefix, namespace)
        self.g.bind(prefix, namespace)

    def del_namespace(self, prefix):
        try:
            self.namespaces.pop(prefix)
            self.g.store._IOMemory__namespace.pop(prefix)
        except KeyError:
            print('Namespace (%s) does not exist!' % prefix)
            pass

    @property
    def filename(self):
        return str(Path(self.writeloc) / (self.name + '.ttl'))

    @filename.setter
    def filename(self, filepath):
        dirname = Path(filepath).parent
        self.writeloc = dirname
        self.name = Path(filepath).stem

    @property
    def ontid(self):
        ontids = list(self.g.subjects(rdf.type, owl.Ontology))
        if len(ontids) > 1:
            raise TypeError('There is more than one ontid in this graph!'
                            ' The graph is not isomorphic to a single ontology!')
        return ontids[0]

    def write(self):
        """ Serialize self.g and write to self.filename"""
        ser = self.g.serialize(format='nifttl')
        with open(self.filename, 'wb') as f:
            f.write(ser)
            #print('yes we wrote the first version...', self.name)

    def expand(self, curie):
        prefix, suffix = curie.split(':',1)
        if prefix not in self.namespaces:
            raise KeyError('Namespace prefix does exist:', prefix)
        return self.namespaces[prefix][suffix]

    def check_thing(self, thing):
        if type(thing) == rdflib.Literal:
            return thing
        elif not isinstance(thing, rdflib.term.URIRef) and not isinstance(thing, rdflib.term.BNode):
            try:
                return self.expand(thing)
            except (KeyError, ValueError) as e:
                if thing.startswith('http') and ' ' not in thing:  # so apparently some values start with http :/
                    return rdflib.URIRef(thing)
                else:
                    raise e
        else:
            return thing

    def add_ont(self, ontid, label, shortName=None, comment=None, version=None):
        self.add_trip(ontid, rdf.type, owl.Ontology)
        self.add_trip(ontid, rdfs.label, label)
        if comment:
            self.add_trip(ontid, rdfs.comment, comment)
        if version:
            self.add_trip(ontid, owl.versionInfo, version)
        if shortName:
            self.add_trip(ontid, skos.altLabel, shortName)

    def add_class(self, id_, subClassOf=None, synonyms=tuple(), label=None, autogen=False):
        self.add_trip(id_, rdf.type, owl.Class)
        if autogen:
            label = ' '.join(re.findall(r'[A-Z][a-z]*', id_.split(':')[1]))
        if label:
            self.add_trip(id_, rdfs.label, label)
        if subClassOf:
            self.add_trip(id_, rdfs.subClassOf, subClassOf)

        [self.add_trip(id_, self.SYNONYM, s) for s in synonyms]

    def del_class(self, id_):
        id_ = self.check_thing(id_)
        for p, o in self.g.predicate_objects(id_):
            self.g.remove((id_, p, o))
            if type(o) == rdflib.BNode():
                self.del_class(o)

    def add_ap(self, id_, label=None, addPrefix=True):
        """ Add id_ as an owl:AnnotationProperty"""
        self.add_trip(id_, rdf.type, owl.AnnotationProperty)
        if label:
            self.add_trip(id_, rdfs.label, label)
            if addPrefix:
                prefix = ''.join([s.capitalize() for s in label.split()])
                namespace = self.expand(id_)
                self.add_namespace(prefix, namespace)

    def add_op(self, id_, label=None, subPropertyOf=None, inverse=None, transitive=False, addPrefix=True):
        """ Add id_ as an owl:ObjectProperty"""
        self.add_trip(id_, rdf.type, owl.ObjectProperty)
        if inverse:
            self.add_trip(id_, owl.inverseOf, inverse)
        if subPropertyOf:
            self.add_trip(id_, rdfs.subPropertyOf, subPropertyOf)
        if label:
            self.add_trip(id_, rdfs.label, label)
            if addPrefix:
                prefix = ''.join([s.capitalize() for s in label.split()])
                namespace = self.expand(id_)
                self.add_namespace(prefix, namespace)
        if transitive:
            self.add_trip(id_, rdf.type, owl.TransitiveProperty)

    def add_trip(self, subject, predicate, object_):
        if not object_:  # no empty object_s!
            return
        subject = self.check_thing(subject)
        predicate = self.check_thing(predicate)
        try:
            if object_.startswith(':') and ' ' in object_:  # not a compact repr AND starts with a : because humans are insane
                object_ = ' ' + object_
            object_ = self.check_thing(object_)
        except (AttributeError, KeyError, ValueError) as e:
            object_ = rdflib.Literal(object_)  # trust autoconv
        self.g.add( (subject, predicate, object_) )

    def del_trip(self, s, p, o):
        self.g.remove(tuple(self.check_thing(_) for _ in (s, p, o)))

    def add_hierarchy(self, parent, edge, child):  # XXX DEPRECATED
        """ Helper function to simplify the addition of part_of style
            objectProperties to graphs. FIXME make a method of makeGraph?
        """
        if type(parent) != rdflib.URIRef:
            parent = self.check_thing(parent)

        if type(edge) != rdflib.URIRef:
            edge = self.check_thing(edge)

        if type(child) != infixowl.Class:
            if type(child) != rdflib.URIRef:
                child = self.check_thing(child)
            child = infixowl.Class(child, graph=self.g)

        restriction = infixowl.Restriction(edge, graph=self.g, someValuesFrom=parent)
        child.subClassOf = [restriction] + [c for c in child.subClassOf]

    def add_restriction(self, subject, predicate, object_):
        """ Lift normal triples into restrictions using someValuesFrom. """
        if type(object_) != rdflib.URIRef:
            object = self.check_thing(object_)

        if type(predicate) != rdflib.URIRef:
            predicate = self.check_thing(predicate)

        if type(subject) != infixowl.Class:
            if type(subject) != rdflib.URIRef:
                subject = self.check_thing(subject)
            subject = infixowl.Class(subject, graph=self.g)

        restriction = infixowl.Restriction(predicate, graph=self.g, someValuesFrom=object_)
        subject.subClassOf = [restriction] + [c for c in subject.subClassOf]

    def add_recursive(self, triple, source_graph):
        self.g.add(triple)
        s = triple[-1]
        if isinstance(s, rdflib.BNode):
            for p, o in source_graph.predicate_objects(s):
                self.add_recursive((s, p, o), source_graph)

    def replace_uriref(self, find, replace):  # find and replace on the parsed graph
        # XXX warning this does not update cases where an iri is in an annotation property!
        #  if you need that just use sed
        # XXX WARNING if you are doing multiple replaces you need to replace the ENTIRE
        #  set first, and THEN transfer those, otherwise you will insert half replaced
        #  triples into a graph!

        find = self.check_thing(find)

        for i in range(3):
            trip = [find if i == _ else None for _ in range(3)]
            for s, p, o in self.g.triples(trip):
                rep = [s, p, o]
                rep[i] = replace
                self.add_trip(*rep)
                self.g.remove((s, p, o))

    def replace_subject_object(self, p, s, o, rs, ro):  # useful for porting edges to equivalent classes
        self.add_trip(rs, p, ro)
        self.g.remove((s, p, o))

    def get_equiv_inter(self, curie):
        """ get equivelant classes where curie is in an intersection """
        start = self.qname(self.expand(curie))  # in case something is misaligned
        qstring = """
        SELECT DISTINCT ?match WHERE {
        ?match owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first %s .
        }""" % start
        return [_ for (_,) in self.g.query(qstring)]  # unpack...

    def qname(self, uri, generate=False):
        """ Given a uri return the qname if it exists, otherwise return the uri. """
        try:
            prefix, namespace, name = self.g.namespace_manager.compute_qname(uri, generate=generate)
            qname = ':'.join((prefix, name))
            return qname
        except (KeyError, ValueError) as e :
            return uri.toPython() if isinstance(uri, rdflib.URIRef) else uri

    def make_scigraph_json(self, edge, label_edge=None, direct=False):  # for checking trees
        if label_edge is None:
            label_edge = rdfs.label
        else:
            label_edge = self.expand(label_edge)
        json_ = {'nodes':[], 'edges':[]}
        if isinstance(edge, rdflib.URIRef):
            restriction = edge
        elif edge == 'isDefinedBy':
            restriction = self.expand('rdfs:isDefinedBy')
        else:
            restriction = self.expand(edge)
        if direct:
            #trips = list(self.g.triples((None, restriction, None)))
            pred = restriction
            done = []
            print(repr(pred))
            #for obj, sub in self.g.subject_objects(pred):  # yes these are supposed to be flipped?
            for sub, obj in self.g.subject_objects(pred):  # or maybe they aren't?? which would explain some of my confusion
                try:
                    olab = list(self.g.objects(obj, label_edge))[0].toPython()
                except IndexError:  # no label
                    olab = obj.toPython()
                try:
                    slab = list(self.g.objects(sub, label_edge))[0].toPython()
                except IndexError:  # no label
                    slab = sub.toPython()

                obj = self.qname(obj)
                sub = self.qname(sub)
                json_['edges'].append({'sub':sub,'pred':edge,'obj':obj})
                if sub not in done:
                    node = {'lbl':slab,'id':sub, 'meta':{}}
                    #if sdep: node['meta'][owl.deprecated.toPython()] = True
                    json_['nodes'].append(node)
                    done.append(sub)
                if obj not in done:
                    node = {'lbl':olab,'id':obj, 'meta':{}}
                    #if odep: node['meta'][owl.deprecated.toPython()] = True
                    json_['nodes'].append(node)
                    done.append(obj)
            return json_

        #linkers = list(self.g.subjects(owl.onProperty, restriction))
        done = []
        for linker in self.g.subjects(owl.onProperty, restriction):
            try:
                obj = list(self.g.objects(linker, owl.someValuesFrom))[0]
            except IndexError:
                obj = list(self.g.objects(linker, owl.allValuesFrom))[0]
            if type(obj) != rdflib.term.URIRef:
                continue  # probably encountere a unionOf or something and don't want
            try:
                olab = list(self.g.objects(obj, label_edge))[0].toPython()
            except IndexError:  # no label
                olab = obj.toPython()
            odep = True if list(self.g.objects(obj, owl.deprecated)) else False
            obj = self.qname(obj)
            sub = list(self.g.subjects(rdfs.subClassOf, linker))[0]
            try:
                slab = list(self.g.objects(sub, label_edge))[0].toPython()
            except IndexError:  # no label
                slab = sub.toPython()
            sdep = True if list(self.g.objects(sub, owl.deprecated)) else False
            try:
                sub = self.qname(sub)
            except:  # rdflib has iffy error handling here so need to catch unsplitables
                print('Could not split the following uri:', sub)

            json_['edges'].append({'sub':sub,'pred':edge,'obj':obj})
            if sub not in done:
                node = {'lbl':slab,'id':sub, 'meta':{}}
                if sdep: node['meta'][owl.deprecated.toPython()] = True
                json_['nodes'].append(node)
                done.append(sub)
            if obj not in done:
                node = {'lbl':olab,'id':obj, 'meta':{}}
                if odep: node['meta'][owl.deprecated.toPython()] = True
                json_['nodes'].append(node)
                done.append(obj)

        return json_


__helper_graph = makeGraph('', prefixes=PREFIXES)
def qname(uri):
    """ compute qname from defaults """
    return __helper_graph.qname(uri)

def createOntology(filename=    'temp-graph',
                   name=        'Temp Ontology',
                   prefixes=    None,  # is a dict
                   shortname=   None,  # 'TO'
                   comment=     None,  # 'This is a temporary ontology.'
                   version=     TODAY,
                   path=        'ttl/generated/',
                   local_base=  os.path.expanduser('~/git/NIF-Ontology/'),
                   #remote_base= 'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/master/',
                   remote_base= 'http://ontology.neuinfo.org/NIF/',
                   imports=     tuple()):
    writeloc = local_base + path
    ontid = remote_base + path + filename + '.ttl'
    prefixes.update(makePrefixes('', 'owl'))
    if shortname is not None and prefixes is not None and 'skos' not in prefixes:
        prefixes.update(makePrefixes('skos'))
    graph = makeGraph(filename, prefixes=prefixes, writeloc=writeloc)
    graph.add_ont(ontid, name, shortname, comment, version)
    for import_ in imports:
        graph.add_trip(ontid, owl.imports, import_)
    return graph

#
# query

ontquery.OntCuries(PREFIXES)
# ontquery.SciGraphRemote.verbose = True
ontquery.OntTerm.query = ontquery.OntQuery(ontquery.SciGraphRemote())

class OntTerm(ontquery.OntTerm, rdflib.URIRef):
    def __str__(self):
        return rdflib.URIRef.__str__(self)

#
# classes

class Class:
    rdf_type = owl.Class
    propertyMapping = dict(  # NOTE ONLY theese properties are serialized
        rdfs_label=rdfs.label,
        label=skos.prefLabel,
        altLabel=skos.altLabel,
        synonyms=NIFRID.synonym,
        abbrevs=NIFRID.abbrev,
        rdfs_subClassOf=rdfs.subClassOf,
        definition=skos.definition,
        version=None,
        shortname=NIFRID.abbrev,  # FIXME used NIFRID:acronym originally probably need something better
        species=ilxtr.isDefinedInTaxon,  # FIXME was defined in much clearer in intent and scope
        devstage=ilxtr.isDefinedInDevelopmentalStage,  # FIXME
        definingArtifacts=ilxtr.isDefinedBy,  # FIXME used in... also lifting to owl:allMembersOf
        definingArtifactsS=ilxtr.isDefinedBy,  # FIXME type check here...
        definingCitations=NIFRID.definingCitation,
        citation=dcterms.bibliographicCitation,
        source=dc.source,  # replaces NIFRID.externalSourceURI?
        comment=rdfs.comment,
        docUri=ilxtr.isDocumentedBy,
        # things that go on classes namely artifacts
        # documentation of where the exact information came from
        # documentation from the source about how the provenance was generated
        #NIFRID.definingCitation
    )
    classPropertyMapping = dict(
        class_label=rdfs.label,
        class_definition=skos.definition,
    )
    lift = dict(
        species=owl.allValuesFrom,  # FIXME really for all rats? check if reasoner makes r6 and r4 the same, see if they are disjoint
        devstage=owl.allValuesFrom,  # protege says only but fact, and hermit which manage disjointness don't complain...
        definingArtifacts=owl.allValuesFrom,
        definingArtifactsS=owl.someValuesFrom,  # HRM
    )
    _kwargs = tuple()  # but really a dict
    def __init__(self, *args, **kwargs):

        if self.parentClass:
            self.rdfs_subClassOf = self._rdfs_subClassOf

        self.args = args
        self._extra_triples = []  # TODO ?
        if self._kwargs:
            for kw, arg in self._kwargs.items():
                if kw in kwargs:
                    arg = kwargs.pop(kw)
                    if (kw == 'label' and
                        'rdfs_label' not in kwargs and
                        not hasattr(self, 'rdfs_label')):
                        kw = 'rdfs_label'  # if nothing else defines rdfs_label for this class fail over

                    #try:
                        #print(self.rdfs_label)
                    #except AttributeError as e :
                        #print(e)
                    #if self.__class__ == Terminology:
                        #print(self.__class__, kw, arg)

                    # TODO type check and fail or try to caste? eg when iri is string not uriref?
                    def typeCheck(thing):
                        print('ARE WE CHECKING?', type(thing))
                        types_ = rdflib.URIRef, str
                        conts = tuple, list, set
                        if type(thing) in conts:
                            for t in thing:
                                typeCheck(t)
                        elif type(thing) in types_:
                            return
                        else:
                            raise ValueError(f'Type of {kw} incorrect. '
                                             f'Is {type(arg)}. '
                                             f'Should be one of {types_}')

                    if isinstance(arg, types.GeneratorType):
                        arg = tuple(arg)  # avoid draining generators
                    #typeCheck(arg)
                    setattr(self, kw, arg)
            if kwargs:
                print(tc.red('WARNING:') + (f' {sorted(kwargs)} are not kwargs '
                      f'for {self.__class__.__name__}. Did you mispell something?'))
                pass
        else:
            for kw, arg in kwargs:
                setattr(self, kw, arg)

    def addTo(self, graph):
        [graph.add_trip(*t) for t in self]
        return graph  # enable chaining

    def addSubGraph(self, triples):
        self._extra_triples.extend(triples)

    def addPair(self, predicate, object):
        self._extra_triples.append((self.iri, predicate, object))

    def __iter__(self):
        yield from self.triples

    @property
    def triples(self):
        return self._triples(self)

    def _triples(self, self_or_cls):
        iri = self_or_cls.iri
        yield iri, rdf.type, self.rdf_type
        for key, predicate in self_or_cls.propertyMapping.items():
            if key in self.lift:
                lift = self.lift[key]
            else:
                lift = None
            if hasattr(self_or_cls, key):
                value = getattr(self_or_cls, key)
                #print(key, predicate, value)
                if value is not None:
                    #(f'{key} are not kwargs for {self.__class__.__name__}')
                    def makeTrip(value, iri=iri, predicate=predicate, lift=lift):
                        t = iri, predicate, check_value(value)
                        if lift is not None:
                            yield from restriction(lift, *t)
                        else:
                            yield t
                    if not isinstance(value, str) and hasattr(self._kwargs[key], '__iter__'):  # FIXME do generators have __iter__?
                        for v in value:
                            yield from makeTrip(v)
                    else:
                        yield from makeTrip(value)
        for s, p, o in self._extra_triples:
            yield s, p, o

    @property
    def parentClass(self):
        if hasattr(self.__class__, 'iri'):
            return self.__class__.iri

    @property
    def parentClass_triples(self):
        if self.parentClass:
            yield from self._triples(self.__class__)

    @classmethod
    def class_triples(cls):
        if not hasattr(cls, 'class_definition') and cls.__doc__:
            cls.class_definition = ' '.join(_.strip() for _ in cls.__doc__.split('\n'))
        yield cls.iri, rdf.type, owl.Class
        mro = cls.mro()
        if len(mro) > 1 and hasattr(mro[1], 'iri'):
            yield cls.iri, rdfs.subClassOf, mro[1].iri
        for arg, predicate in cls.classPropertyMapping.items():
            if hasattr(cls, arg):
                yield cls.iri, predicate, check_value(getattr(cls, arg))

    @property
    def _rdfs_subClassOf(self):
        return self.parentClass

    def __repr__(self):
        return repr(self.__dict__)


class Source(tuple):
    """ Manages loading and converting source files into ontology representations """ 
    iri_prefix_wdf = 'https://github.com/tgbugs/pyontutils/blob/{file_commit}/pyontutils/'
    iri_prefix_hd = f'https://github.com/tgbugs/pyontutils/blob/master/pyontutils/'
    iri = None
    source = None
    artifact = None

    def __new__(cls):
        if not hasattr(cls, 'data'):
            if hasattr(cls, 'runonce'):  # must come first since it can modify how cls.source is defined
                cls.runonce()

            if cls.source.startswith('http'):
                if cls.source.endswith('.git'):
                    cls._type = 'git-remote'
                    # TODO look for local, if not fetch, pull latest, get head commit
                else:
                    cls._type = 'iri'
                cls.iri = rdflib.URIRef(cls.source)
            elif os.path.exists(cls.source):  # TODO no expanded stuff
                try:
                    file_commit = subprocess.check_output(['git', 'log', '-n', '1',
                                                           '--pretty=format:%H', '--',
                                                           cls.source],
                                                          stderr=subprocess.DEVNULL).decode().rstrip()
                    cls.iri = rdflib.URIRef(cls.iri_prefix_wdf.format(file_commit=file_commit) + cls.source)
                    cls._type = 'git-local'
                except subprocess.CalledProcessError as e:
                    cls._type = 'local'
                    if e.args[0] == 128:  # hopefully this is the git status code for not a get repo...
                        if not hasattr(cls, 'iri'):
                            cls.iri = rdflib.URIRef('file://' + cls.source)
                        #else:
                            #print(cls, 'already has an iri', cls.iri)
                    else:
                        raise e
            else:
                cls._type = None
                print('Unknown source', cls.source)

            cls.raw = cls.loadData()
            cls.data = cls.validate(*cls.processData())
            cls._triples_for_ontology = []
            cls.prov()
        self = super().__new__(cls, cls.data)
        return self

    @classmethod
    def loadData(cls):
        if cls._type == 'local' or cls._type == 'git-local':
            with open(os.path.expanduser(cls.source), 'rt') as f:
                return f.read()
        elif cls._type == 'iri':
            return tuple()
        elif cls._type == 'git-remote':
            return tuple()
        else:
            return tuple()

    @classmethod
    def processData(cls):
        return cls.raw,

    @classmethod
    def validate(cls, data):
        return data

    @classmethod
    def prov(cls):
        if cls._type == 'local' or cls._type == 'git-local':
            if cls._type == 'git-local':
                object = rdflib.URIRef(cls.iri_prefix_hd + cls.source)
            else:
                object = rdflib.URIRef(cls.source)
            if os.path.exists(cls.source) and not hasattr(cls, 'source_original'):  # FIXME no help on mispelling
                cls.iri_head = object
                if hasattr(cls.artifact, 'hadDerivation'):
                    cls.artifact.hadDerivation.append(object)
                else:
                    cls.artifact.hadDerivation = [object]
            elif hasattr(cls, 'source_original') and cls.source_original:
                cls.iri_head = object
                if cls.artifact is not None:
                    cls.artifact.source = cls.iri
        elif cls._type == 'git-remote' or cls._type == 'iri':
            #print('Source is url and assumed to have no intermediate', cls.source)
            if hasattr(cls, 'source_original') and cls.source_original:
                cls.artifact = cls  # make the artifact and the source equivalent for prov
        else:
            print('Unknown source', cls.source)

    @property
    def isVersionOf(self):
        if hasattr(self, 'iri_head'):
            yield self.iri, dcterms.isVersionOf, self.iri_head


class Ont:
    #rdf_type = owl.Ontology

    path = 'ttl/generated/'  # sane default
    filename = None
    name = None
    shortname = None
    comment = None  # about how the file was generated, nothing about what it contains
    version = TODAY
    prefixes = makePrefixes('NIFRID', 'ilxtr', 'prov', 'dc', 'dcterms')
    imports = tuple()
    wasGeneratedBy = ('https://github.com/tgbugs/pyontutils/blob/'  # TODO predicate ordering
                      '{commit}/pyontutils/'
                      '{file}'
                      '#L{line}')

    propertyMapping = dict(
        wasDerivedFrom=prov.wasDerivedFrom,  # the direct source file(s)  FIXME semantics have changed
        wasGeneratedBy=prov.wasGeneratedBy,
        hasSourceArtifact=ilxtr.hasSourceArtifact,  # the owl:Class it was derived from
    )

    @classmethod
    def prepare(cls):
        if hasattr(cls, 'sources'):
            cls.sources = tuple(s() for s in cls.sources)
        if hasattr(cls, 'imports'):# and not isinstance(cls.imports, property):
            cls.imports = tuple(i() if isinstance(i, type) and issubclass(i, Ont) else i
                                for i in cls.imports)

    def __init__(self, *args, **kwargs):
        if 'comment' not in kwargs and self.comment is None and self.__doc__:
            self.comment = ' '.join(_.strip() for _ in self.__doc__.split('\n'))

        if hasattr(self, '_repo') and not self._repo:
            commit = 'FAKE-COMMIT'
        else:
            commit = getCommit()

        try:
            line = getsourcelines(self.__class__)[-1]
            file = getsourcefile(self.__class__)
        except TypeError:  # emacs is silly
            line = 'noline'
            file = 'nofile'

        self.wasGeneratedBy = self.wasGeneratedBy.format(commit=commit,
                                                         line=line,
                                                         file=Path(file).name)
        imports = tuple(i.iri if isinstance(i, Ont) else i for i in self.imports)
        self._graph = createOntology(filename=self.filename,
                                     name=self.name,
                                     prefixes={**self.prefixes, **makePrefixes('prov')},
                                     comment=self.comment,
                                     shortname=self.shortname,
                                     path=self.path,
                                     version=self.version,
                                     imports=imports)
        self.graph = self._graph.g
        self._extra_triples = set()
        if hasattr(self, 'sources'):  # FIXME also support source = ?
            for source in self.sources:
                if not isinstance(source, Source):
                    raise TypeError(f'{source} is not an instance of Source '
                                    'did you remember to call prepare?')
            self.wasDerivedFrom = tuple(_ for _ in (i.iri if isinstance(i, Source) else i
                                                    for i in self.sources)
                                        if _ is not None)
            self.hasSourceArtifact = tuple()
            for source in self.sources:
                if hasattr(source, 'artifact') and source.artifact is not None and source.artifact.iri not in self.wasDerivedFrom:
                    self.hasSourceArtifact += source.artifact.iri,
                    source.artifact.addPair(ilxtr.hasDerivedArtifact, self.iri)
            #print(self.wasDerivedFrom)

    def addTrip(self, subject, predicate, object):
        # TODO erro if object not an rdflib term to prevent
        # non-local error issues at serilization time
        self._extra_triples.add((subject, predicate, object))

    def _mapProps(self):
        for key, predicate in self.propertyMapping.items():
            if hasattr(self, key):
                value = getattr(self, key)
                if value is not None:
                    if not isinstance(value, str) and hasattr(value, '__iter__'):
                        for v in value:
                            yield self.iri, predicate, check_value(v)
                    else:
                        yield self.iri, predicate, check_value(value)

    @property
    def triples(self):
        if hasattr(self, 'root') and self.root is not None:
            yield from self.root
        elif hasattr(self, 'roots') and self.roots is not None:
            for root in self.roots:
                yield from root
        if hasattr(self, '_triples'):
            yield from self._triples()
        else:
            raise StopIteration
        for t in self._extra_triples:  # last so _triples can populate
            yield t

    def __iter__(self):
        yield from self._mapProps()
        yield from self.triples

    def __call__(self):  # FIXME __iter__ and __call__ ala Class?
        for t in self:
            try:
                self.graph.add(t)
            except ValueError as e:
                print(tc.red('AAAAAAAAAAA'), t)
                raise e
        return self

    def validate(self):
        # implement per class
        return self

    @property
    def iri(self):
        return self._graph.ontid

    def write(self):
        # TODO warn in ttl file when run when __file__ has not been committed
        self._graph.write()


class LabelsBase(Ont):  # this replaces genericPScheme
    """ An ontology file containing parcellation labels from a common source. """

    __pythonOnly = True
    path = 'ttl/generated/parcellation/'  # XXX warning just a demo...
    imports = tuple()  # set parcCore manually...
    sources = tuple()
    root = None  # : LabelRoot
    roots = None  # : (LabelRoot, ...)
    filename = None
    name = None
    prefixes = {}
    comment = None

    @property
    def triples(self):
        if self.root is not None:
            yield self.iri, ilxtr.rootClass, self.root.iri
        elif self.roots is not None:
            for root in self.roots:
                yield self.iri, ilxtr.rootClass, root.iri
        yield from super().triples


class Collector:
    @classmethod
    def arts(cls):
        for k, v in cls.__dict__.items():
            if v is not None and isinstance(v, cls.collects):
                yield v


def flattenTriples(triples):
    for triple_or_generator in triples:
        if isinstance(triple_or_generator, tuple):
            yield triple_or_generator
        else:
            yield from triple_or_generator

def simpleOnt(filename=f'temp-{UTCNOW()}',
              prefixes=tuple(),
              imports=tuple(),
              triples=tuple(),
              comment=None,
              path='ttl/',
              _repo=True):

    for i in imports:
        if not isinstance(i, rdflib.URIRef):
            raise TypeError(f'Import {i} is not a URIRef!')

    class Simple(Ont):  # TODO make a Simple(Ont) that works like this?

        def _triples(self):
            yield from flattenTriples(triples)

    Simple._repo = _repo
    Simple.path = path
    Simple.filename = filename
    Simple.comment = comment
    Simple.prefixes = makePrefixes(*prefixes)
    Simple.imports = imports

    built_ont, = build(Simple, n_jobs=1)

    return built_ont

def displayGraph(graph_,
                 temp_path='/tmp',
                 debug=False):
    from pyontutils.hierarchies import creatTree, Query, dematerialize
    graph = rdflib.Graph()
    # load prefixes here so that makeGraph will get them automatically
    # and so that rdflib doesn't try to generate its own prefixes
    [graph.bind(k, v) for k, v in graph_.namespaces()]
    [graph.add(t) for t in graph_]
    g = makeGraph('', graph=graph)
    skip = owl.Thing, owl.topObjectProperty, owl.Ontology, ilxtr.topAnnotationProperty
    byto = {owl.ObjectProperty:(rdfs.subPropertyOf, owl.topObjectProperty),
            owl.AnnotationProperty:(rdfs.subPropertyOf, ilxtr.topAnnotationProperty),
            owl.Class:(rdfs.subClassOf, owl.Thing),}

    def add_supers(s, ito=None):
        #print(s)
        if s in skip or isinstance(s, rdflib.BNode):
            return
        try: next(graph.objects(s, rdfs.label))
        except StopIteration: graph.add((s, rdfs.label, rdflib.Literal(g.qname(s))))
        tos = graph.objects(s, rdf.type)
        to = None
        for to in tos:
            _super = False
            if to in skip:
                continue
            else:
                p, bo = byto[to]
                for o in graph.objects(s, p):
                    _super = o
                    if _super == s:
                        print(tc.red('WARNING:'), f'{s} subClassOf itself!')
                    else:
                        add_supers(_super, ito=to)

                if not _super:
                    graph.add((s, p, bo))

        if to is None and ito is not None:
            p, bo = byto[ito]
            #print('FAILED ADDING', (s, p, bo))
            graph.add((s, p, bo))
            #if (bo, p, bo) not in graph:
                #graph.add((bo, p, bo))

    [graph.add(t)
     for t in flattenTriples((oc(owl.Thing),
                              olit(owl.Thing, rdfs.label, 'Thing'),
                              oop(owl.topObjectProperty),
                              olit(owl.topObjectProperty, rdfs.label, 'TOP'),))]

    for s in set(graph.subjects(None, None)):
        add_supers(s)

    if debug:
        _ = [print(*(e[:5]
                     if isinstance(e, rdflib.BNode) else
                     g.qname(e)
                     for e in t), '.')
             for t in sorted(graph)]

    for pred, root in ((rdfs.subClassOf, owl.Thing), (rdfs.subPropertyOf, owl.topObjectProperty)):
        try: next(graph.subjects(pred, root))
        except StopIteration: continue

        j = g.make_scigraph_json(pred, direct=True)
        if debug: print(j)
        prefixes = {k:str(v) for k, v in g.namespaces.items()}
        start = g.qname(root)
        tree, extras = creatTree(*Query(start, pred, 'INCOMING', 10), prefixes=prefixes, json=j)
        dematerialize(next(iter(tree.keys())), tree)
        print(f'\n{tree}\n')
        # 3.5 behavior forces str here
        with open(str(Path(temp_path) / (g.qname(root) + '.txt')), 'wt') as f:
            f.write(str(tree))
        with open(str(Path(temp_path) / (g.qname(root) + '.html')), 'wt') as f:
            f.write(extras.html)

    return graph

def main():
    graph = rdflib.Graph().parse('/home/tom/git/NIF-Ontology/ttl/bridge/uberon-bridge.ttl', format='turtle')
    graph.parse('/home/tom/git/NIF-Ontology/ttl/NIF-Neuron-Circuit-Role-Bridge.ttl', format='ttl')
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
    oec = EquivalentClass()
    #subClassOf = PredicateThunk(rdfs.subClassOf)  # TODO should be able to do POThunk(rdfs.subClassOf, 0bjectThunk)
    subClassOf = POThunk(rdfs.subClassOf, ObjectThunk)
    superDuperClass = subClassOf(TEMP.superDuperClass)  # has to exist prior to triples
    ec = oec(TEMP.ec1, TEMP.ec2,
             restriction(TEMP.predicate0, TEMP.target1),
             restriction(TEMP.predicate1, TEMP.target2),)
    egraph = rdflib.Graph()
    athunk = annotation((TEMP.testSubject, rdf.type, owl.Class), (TEMP.hoh, 'FUN'))
    ft = flattenTriples((athunk((TEMP.annotation, 'annotation value')),
                         athunk((TEMP.anotherAnnotation, 'annotation value again')),
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
    embed()

if __name__ == '__main__':
    main()
