import os
import yaml
import types
import subprocess
import rdflib
import requests
from pathlib import Path
from collections import namedtuple
from inspect import getsourcefile
from git import Repo
from rdflib.extras import infixowl
from joblib import Parallel, delayed
import ontquery
from pyontutils import closed_namespaces as cnses
from pyontutils.utils import refile, TODAY, UTCNOW, working_dir, getSourceLine
from pyontutils.utils import Async, deferred, TermColors as tc
from pyontutils.config import get_api_key, devconfig
from pyontutils.closed_namespaces import *
from IPython import embed

current_file = Path(__file__).absolute()

# prefixes

def interlex_namespace(user):
    return 'http://uri.interlex.org/' + user

def _loadPrefixes():
    try:
        with open(devconfig.curies, 'rt') as f:
            curie_map = yaml.load(f)
    except FileNotFoundError:
        master_blob = 'https://github.com/tgbugs/pyontutils/blob/master/'
        raw_path = 'scigraph/nifstd_curie_map.yaml?raw=true'
        curie_map = requests.get(master_blob + raw_path)
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
        # defined by chebi.owl, confusingly chebi#2 -> chebi1 maybe an error?
        # better to keep it consistent in case someone tries to copy and paste
        'chebi1':'http://purl.obolibrary.org/obo/chebi#2',
        'chebi2':'http://purl.obolibrary.org/obo/chebi#',
        'chebi3':'http://purl.obolibrary.org/obo/chebi#3',
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
 ilxb, TEMP, ILX) = makeNamespaces('HBA', 'MBA', 'NCBITaxon', 'NIFRID', 'NIFTTL', 'UBERON',
                       'BFO', 'ilxtr', 'ilx', 'TEMP', 'ILX')

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
DKT = rdflib.Namespace(interlex_namespace('mindboggle/uris/dkt/'))
DKTr = rdflib.Namespace(interlex_namespace('mindboggle/uris/dkt/region/labels/'))
DKTs = rdflib.Namespace(interlex_namespace('mindboggle/uris/dkt/sulcus/labels/'))
FSCL = rdflib.Namespace(interlex_namespace('freesurfer/uris/FreeSurferColorLUT/labels/'))
MNDBGL = rdflib.Namespace(interlex_namespace('mindboggle/uris/mndbgl/labels/'))
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
 realizes, partOf, participatesIn, locatedIn,
) = makeURIs('replacedBy', 'definition', 'hasPart', 'hasRole', 'hasParticipant',
             'hasInput', 'hasOutput', 'realizes', 'partOf', 'participatesIn',
             'locatedIn',
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

def standard_checks(graph):
    def cardinality(predicate, card=1):
        for subject in sorted(set(graph.subjects())):
            for i, object in enumerate(graph.objects(subject, predicate)):
                if i == 0:
                    first_error = tc.red('ERROR:'), subject, 'has more than one label!', object
                elif i >= card:
                    print(tc.red('ERROR:'), subject, 'has more than one label!', object)
                    if i == card:
                        print(*first_error)

    cardinality(rdfs.label)

def ont_make(o, fail=False):
    o()
    o.validate()
    failed = standard_checks(o.graph)
    o.failed = failed
    if fail:
        raise BaseException('Ontology validation failed!')
    o.write()
    return o

def build(*onts, fail=False, n_jobs=9):
    """ Set n_jobs=1 for debug or embed() will crash. """
    tail = lambda:tuple()
    lonts = len(onts)
    if lonts > 1:
        for i, ont in enumerate(onts):
            if ont.__name__ == 'parcBridge':
                onts = onts[:-1]
                def tail(o=ont):
                    return ont_setup(o),
                if i != lonts - 1:
                    raise ValueError('parcBridge should be built last to avoid weird errors!')
    # ont_setup must be run first on all ontologies
    # or we will get weird import errors
    if n_jobs == 1:
        return tuple(ont_make(ont, fail=fail) for ont in
                     tuple(ont_setup(ont) for ont in onts) + tail())

    # have to use a listcomp so that all calls to setup()
    # finish before parallel goes to work
    return Parallel(n_jobs=n_jobs)(delayed(ont_make)(o, fail=fail) for o in
                                   #[ont_setup(ont) for ont in onts])
                                   (tuple(Async()(deferred(ont_setup)(ont)
                                                  for ont in onts)) + tail()
                                    if n_jobs > 1
                                    else [ont_setup(ont)
                                          for ont in onts]))

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
        raise NotImplemented

    def __call__(self, subject, predicate, object):
        yield subject, predicate, object

    def debug(self, *args, l=None):
        graph = rdflib.Graph()
        graph.bind('owl', str(owl))
        if l is None:
            l = self.__call__(*args)
        [graph.add(t) for t in l]
        print(graph.serialize(format='nifttl').decode())



class CombinatorIt(Combinator):
    def __init__(self, outer_self, *args, **kwargs):
        self.outer_self = outer_self
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        # FIXME might get two subjects by accident...
        if (isinstance(self.outer_self, Combinator) and args and not isinstance(args[0], str) or
            self.args and self.args[0] is None):
            args = (rdflib.BNode(),) + args
            if self.args[0] is None:
                self.args = self.args[1:]
        elif not args and not self.args:
            args = rdflib.BNode(),

        yield from self.outer_self.__call__(*args, *self.args, **kwargs, **self.kwargs)

    def __repr__(self):
        return f'{self.outer_self.__class__.__name__} {self.args} {self.kwargs}'

    def serialize(self, graph=None):
        for t in self():
            yield t
            if graph is not None:
                graph.add(t)


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
            o = qname(self.object)
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
        tech = rdflib.Namespace(ilxtr[''] + 'technique/')
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
        p = qname(self.predicate)
        if isinstance(self.object, rdflib.URIRef):
            o = qname(self.object)
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


oc_ = POCombinator(rdf.type, owl.Class)


class RestrictionCombinator(_POCombinator):
    def __call__(self, subject, linking_predicate=None):
        if self.outer_self.predicate is not None and linking_predicate is not None:
            if self.outer_self.predicate != linking_predicate:
                raise TypeError(f'Predicates {self.outer_self.predicate} {linking_predicate} do not match on {self!r}')

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
        class AnnotationCombinator(Combinator):
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

        return AnnotationCombinator(triple)

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

            # TODO combinator? or not in this case?
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

class PredicateList(Triple):
    predicate = rdf.List
    typeWhenSubjectIsBlank = owl.Class

    def __init__(self):
        self._list = List({owl.Restriction:Restriction(rdf.first)})
        self.lift_rules = {rdf.first:self._list, rdf.rest:None}

    def __call__(self, *objects_or_combinators):
        class IntersectionOfCombinator(Combinator):
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

            def __repr__(self):
                return f'{self.__class__.__name__}{self.combinators!r}'

        return IntersectionOfCombinator()

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
        prefix, suffix = curie.split(':', 1)
        if prefix not in self.namespaces:
            raise KeyError(f'Namespace prefix {prefix} does exist for {curie}' )
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
            object_ = self.check_thing(object_)

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
        except (KeyError, ValueError) as e:
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
            #print('make_scigraph_json predicate:', repr(pred))
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
def qname(uri, warning=False):
    """ compute qname from defaults """
    if warning:
        print(tc.red('WARNING:'), tc.yellow(f'qname({uri}) is deprecated! please use OntId({uri}).curie'))
    return __helper_graph.qname(uri)

def createOntology(filename=    'temp-graph',
                   name=        'Temp Ontology',
                   prefixes=    None,  # is a dict
                   shortname=   None,  # 'TO'
                   comment=     None,  # 'This is a temporary ontology.'
                   version=     TODAY,
                   path=        'ttl/generated/',
                   local_base=  None,
                   #remote_base= 'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/master/',
                   remote_base= 'http://ontology.neuinfo.org/NIF/',
                   imports=     tuple()):
    if local_base is None:  # get location at runtime
        local_base = devconfig.ontology_local_repo
    writeloc = Path(local_base) / path
    ontid = os.path.join(remote_base, path, filename + '.ttl')
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

OntCuries = ontquery.OntCuries
OntCuries(PREFIXES)
# ontquery.SciGraphRemote.verbose = True

class OntId(ontquery.OntId, rdflib.URIRef):
    #def __eq__(self, other):  # FIXME this makes OntTerm unhashabel!?
        #return rdflib.URIRef.__eq__(rdflib.URIRef(self), other)

    #@property
    #def URIRef(self):  # FIXME stopgap for comparison issues
        #return rdflib.URIRef(self)

    def __str__(self):
        return rdflib.URIRef.__str__(self)

class OntTerm(ontquery.OntTerm, OntId):
    pass


OntTerm.query = ontquery.OntQuery(ontquery.SciGraphRemote(api_key=get_api_key()))
ontquery.QueryResult._OntTerm = OntTerm
query = ontquery.OntQueryCli(query=OntTerm.query)

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
        self._extra_triples = set()  # TODO ?
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
            if kwargs:  # some kwargs did not get popped off
                print(tc.red('WARNING:') + (f' {sorted(kwargs)} are not kwargs '
                      f'for {self.__class__.__name__}. Did you mispell something?'))
        else:
            for kw, arg in kwargs:
                setattr(self, kw, arg)

    def addTo(self, graph):
        [graph.add_trip(*t) for t in self]
        return graph  # enable chaining

    def addSubGraph(self, triples):
        self._extra_triples.update(triples)

    def addPair(self, predicate, object):
        self._extra_triples.add((self.iri, predicate, object))

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
                restriction = Restriction(rdfs.subClassOf, scope=self.lift[key])
            else:
                restriction = None
            if hasattr(self_or_cls, key):
                value = getattr(self_or_cls, key)
                #a, b, c = (qname(key), qname(predicate),
                           #qname(value) if isinstance(value, rdflib.URIRef) else value)
                #print(tc.red('aaaaaaaaaaaaaaaaa'), f'{a:<30}{c}')
                if value is not None:
                    #(f'{key} are not kwargs for {self.__class__.__name__}')
                    def makeTrip(value, iri=iri, predicate=predicate, restriction=restriction):
                        t = iri, predicate, check_value(value)
                        if restriction is not None:
                            yield from restriction.serialize(*t)
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
        if 'class_definition' not in cls.__dict__ and cls.__doc__:  # can't use hasattr due to parents
            cls.class_definition = ' '.join(_.strip() for _ in cls.__doc__.split('\n'))
        yield cls.iri, rdf.type, owl.Class
        mro = cls.mro()
        if len(mro) > 1 and hasattr(mro[1], 'iri'):
            yield cls.iri, rdfs.subClassOf, mro[1].iri
        for arg, predicate in cls.classPropertyMapping.items():
            if hasattr(cls, arg):
                value = check_value(getattr(cls, arg))
                yield cls.iri, predicate, value

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
    sourceFile = None
    # source_original = None  # FIXME this should probably be defined on the artifact not the source?
    artifact = None

    def __new__(cls):
        if not hasattr(cls, '_data'):
            if hasattr(cls, 'runonce'):  # must come first since it can modify how cls.source is defined
                cls.runonce()

            if cls.source.startswith('http'):
                if cls.source.endswith('.git'):
                    cls._type = 'git-remote'
                    cls.sourceRepo = cls.source
                    # TODO look for local, if not fetch, pull latest, get head commit
                    glb = Path(devconfig.git_local_base)
                    cls.repo_path = glb / Path(cls.source).stem
                    rap = cls.repo_path.as_posix()
                    print(rap)
                    # TODO branch and commit as usual
                    if not cls.repo_path.exists():
                        cls.repo = Repo.clone_from(cls.sourceRepo, rap)
                    else:
                        cls.repo = Repo(rap)
                        # cls.repo.remote().pull()  # XXX remove after testing finishes

                    if cls.sourceFile is not None:
                        file = cls.repo_path / cls.sourceFile
                        file_commit = next(cls.repo.iter_commits(paths=file.as_posix(), max_count=1)).hexsha
                        commit_path = os.path.join('blob', file_commit, cls.sourceFile)
                        print(commit_path)
                        if 'github' in cls.source:
                            cls.iri_prefix = cls.source.rstrip('.git') + '/'
                        else:
                            # using github syntax for now since it is possible to convert out
                            cls.iri_prefix = cls.source + '::'
                        cls.iri = rdflib.URIRef(cls.iri_prefix + commit_path)
                        cls.source = file.as_posix()
                    else:
                        # assume the user knows what they are doing
                        #raise ValueError(f'No sourceFile specified for {cls}')
                        cls.iri = rdflib.URIRef(cls.source)
                        pass
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
            cls._data = cls.validate(*cls.processData())
            cls._triples_for_ontology = []
            cls.prov()
        self = super().__new__(cls, cls._data)
        return self

    @classmethod
    def loadData(cls):
        if cls._type == 'local' or cls._type == 'git-local':
            with open(os.path.expanduser(cls.source), 'rt') as f:
                return f.read()
        elif cls._type == 'iri':
            return tuple()
        elif cls._type == 'git-remote':
            if cls.sourceFile is not None:
                with open(cls.source, 'rt') as f:
                    return f.read()
            else:
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

        elif cls._type == 'git-remote':
            if cls.sourceFile is not None:
                origin = next(r for r in cls.repo.remotes if r.name == 'origin')
                origin_branch = next(r.reference.remote_head for r in origin.refs if r.remote_head == 'HEAD')
                default_path = os.path.join('blob', origin_branch, cls.sourceFile)
                object = rdflib.URIRef(cls.iri_prefix + default_path)
                cls.iri_head = object
            else:
                object = None

            if hasattr(cls, 'source_original') and cls.source_original:
                if cls.artifact is not None:
                    cls.artifact.source = cls.iri_head  # do not use cls.iri here # FIXME there may be more than one source
            else:
                if object is None:
                    object = cls.iri

                if hasattr(cls.artifact, 'hadDerivation'):
                    cls.artifact.hadDerivation.append(object)
                else:
                    cls.artifact.hadDerivation = [object]

        elif cls._type == 'iri':
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
    _debug = False
    local_base = devconfig.ontology_local_repo
    remote_base = 'http://ontology.neuinfo.org/NIF/'
    path = 'ttl/generated/'  # sane default
    filename = None
    name = None
    shortname = None
    comment = None  # about how the file was generated, nothing about what it contains
    version = TODAY
    namespace = None
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
            cls.imports = tuple(i()
                                if isinstance(i, type) and issubclass(i, Ont)
                                else i
                                for i in cls.imports)
        if cls.namespace is not None and cls.shortname:
            iri_prefix = str(cls.namespace)
            if iri_prefix not in tuple(cls.prefixes.values()):
                # need the print to keep things sane means maybe
                # this isn't such a good idea after all?
                prefix = cls.shortname.upper()
                print(tc.blue('Adding default namespace '
                              f'{cls.namespace} to {cls} as {prefix}'))
                cls.prefixes[prefix] = iri_prefix  # sane default

    def __init__(self, *args, **kwargs):
        if 'comment' not in kwargs and self.comment is None and self.__doc__:
            self.comment = ' '.join(_.strip() for _ in self.__doc__.split('\n'))

        if hasattr(self, '_repo') and not self._repo:
            commit = 'FAKE-COMMIT'
        else:
            repo = Repo(working_dir.as_posix())
            commit = next(repo.iter_commits()).hexsha

        try:
            line = getSourceLine(self.__class__)
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
                                     local_base=self.local_base,
                                     remote_base=self.remote_base,
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
                if (hasattr(source, 'artifact')
                    and source.artifact is not None
                    and source.artifact.iri not in self.wasDerivedFrom):
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

    def triple_check(self, triple):
        error = ValueError(f'bad triple in {self} {triple!r}')
        try:
            s, p, o = triple
        except ValueError as e:
            raise error from e

        if not isinstance(s, rdflib.URIRef) and not isinstance(s, rdflib.BNode):
            raise error
        elif not isinstance(p, rdflib.URIRef):
            raise error
        elif (not isinstance(o, rdflib.URIRef) and
              not isinstance(o, rdflib.BNode) and
              not isinstance(o, rdflib.Literal)):
            raise error

    def _triple_check(self, triples):
        for triple in triples:
            self.triple_check(triple)
            yield triple

    @property
    def triples(self):
        if self._debug:
            embed()

        if hasattr(self, 'root') and self.root is not None:
            yield from self.root
        elif hasattr(self, 'roots') and self.roots is not None:
            for root in self.roots:
                yield from root

        if hasattr(self, '_triples'):
            yield from self._triple_check(self._triples())

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
              branch='master',
              fail=False,
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

    if branch != 'master':
        Simple.remote_base = f'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/{branch}/'

    built_ont, = build(Simple, fail=fail, n_jobs=1)

    return built_ont

def displayTriples(triples, qname=qname):
    """ triples can also be an rdflib Graph instance """
    [print(*(e[:5]
             if isinstance(e, rdflib.BNode) else
             qname(e)
             for e in t), '.')
             for t in sorted(triples)]

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
    skip = owl.Thing, owl.topObjectProperty, owl.Ontology, ilxtr.topAnnotationProperty, owl.topDataProperty
    byto = {owl.ObjectProperty:(rdfs.subPropertyOf, owl.topObjectProperty),
            owl.DatatypeProperty:(rdfs.subPropertyOf, owl.topDataProperty),
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
        displayTriples(graph, qname=g.qname)

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
    graph = rdflib.Graph().parse(devconfig.ontology_local_repo + '/ttl/bridge/uberon-bridge.ttl', format='turtle')
    graph.parse(devconfig.ontology_local_repo + '/ttl/NIF-Neuron-Circuit-Role-Bridge.ttl', format='ttl')

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
        embed()
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
        embed()

if __name__ == '__main__':
    main()
