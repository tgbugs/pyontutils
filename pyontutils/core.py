import os
import yaml
import types
import subprocess
import rdflib
import requests
from pathlib import Path
from collections import namedtuple
from inspect import getsourcefile
from rdflib.extras import infixowl
from joblib import Parallel, delayed
import ontquery
from pyontutils import closed_namespaces as cnses
from pyontutils.utils import refile, TODAY, UTCNOW, working_dir, getSourceLine
from pyontutils.utils import Async, deferred, TermColors as tc, check_value
from pyontutils.config import get_api_key, devconfig
from pyontutils.namespaces import makePrefixes, makeNamespaces, makeURIs
from pyontutils.namespaces import NIFRID, ilxtr, PREFIXES as uPREFIXES
from pyontutils.combinators import Restriction, flattenTriples
from pyontutils.closed_namespaces import rdf, rdfs, owl, skos, dc, dcterms, prov
from IPython import embed

current_file = Path(__file__).absolute()

# common funcs

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

def ont_make(o, fail=False, write=True):
    o()
    o.validate()
    failed = standard_checks(o.graph)
    o.failed = failed
    if fail:
        raise BaseException('Ontology validation failed!')
    if write:
        o.write()
    return o

def build(*onts, fail=False, n_jobs=9, write=True):
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
        return tuple(ont_make(ont, fail=fail, write=write) for ont in
                     tuple(ont_setup(ont) for ont in onts) + tail())

    # have to use a listcomp so that all calls to setup()
    # finish before parallel goes to work
    return Parallel(n_jobs=n_jobs)(delayed(ont_make)(o, fail=fail, write=write)
                                   for o in
                                   #[ont_setup(ont) for ont in onts])
                                   (tuple(Async()(deferred(ont_setup)(ont)
                                                  for ont in onts)) + tail()
                                    if n_jobs > 1
                                    else [ont_setup(ont)
                                          for ont in onts]))


def yield_recursive(s, p, o, source_graph):  # FIXME transitive_closure on rdflib.Graph?
    yield s, p, o
    new_s = o
    if isinstance(new_s, rdflib.BNode):
        for p, o in source_graph.predicate_objects(new_s):
            yield from yield_recursive(new_s, p, o, source_graph)

#
# old impl

def getNamespace(prefix, namespace):
    if prefix in cnses.__all__:
        return getattr(cnses, prefix)
    elif prefix == 'rdf':
        return rdf
    elif prefix == 'rdfs':
        return rdfs
    else:
        return rdflib.Namespace(namespace)


class mGraph(rdflib.Graph):
    def __init__(self, *args, filename='/tmp/test.ttl', **kwargs):
        super().__init__(*args, **kwargs)
        self.bind('owl', owl)
        self.filename = filename

    def write(self, filename=None):
        if filename is None:
            filename = self.filename
        with open(filename, 'wb') as f:
            f.write(self.serialize(format='nifttl'))


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
                self.add_namespace(prefix, uPREFIXES[prefix])

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


__helper_graph = makeGraph('', prefixes=uPREFIXES)
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
                   version=     TODAY(),
                   path=        'ttl/generated/',
                   local_base=  None,
                   #remote_base= 'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/master/',
                   remote_base= 'http://ontology.neuinfo.org/NIF/',
                   imports=     tuple()):
    if local_base is None:  # get location at runtime
        local_base = devconfig.ontology_local_repo
    writeloc = Path(local_base) / path
    ontid = os.path.join(remote_base, path, filename + '.ttl') if filename else None
    prefixes.update(makePrefixes('', 'owl'))
    if shortname is not None and prefixes is not None and 'skos' not in prefixes:
        prefixes.update(makePrefixes('skos'))
    graph = makeGraph(filename, prefixes=prefixes, writeloc=writeloc)
    if ontid is not None:
        graph.add_ont(ontid, name, shortname, comment, version)
        for import_ in imports:
            graph.add_trip(ontid, owl.imports, import_)
    return graph

#
# query

OntCuries = ontquery.OntCuries
OntCuries(uPREFIXES)
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
        from git import Repo
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
                elif cls.artifact is None:
                    raise TypeError('If artifact = None and you have a source set source_original = True')
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


class resSource(Source):
    source = 'https://github.com/tgbugs/pyontutils.git'


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
    version = TODAY()
    namespace = None
    prefixes = makePrefixes('NIFRID', 'ilxtr', 'prov', 'dc', 'dcterms')
    imports = tuple()
    source_file = None  # override for cases where __class__ is used internally
    wasGeneratedBy = ('https://github.com/tgbugs/pyontutils/blob/'  # TODO predicate ordering
                      '{commit}/pyontutils/'  # FIXME prefer {filepath} to assuming pyontutils...
                      '{file}'
                      '{hash_L_line}')

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
            from git import Repo
            repo = Repo(working_dir.as_posix())
            commit = next(repo.iter_commits()).hexsha

        try:
            if self.source_file:
                file = self.source_file
                line = ''
            else:
                line = '#L' + str(getSourceLine(self.__class__))
                _file = getsourcefile(self.__class__)
                file = Path(_file).name
        except TypeError:  # emacs is silly
            line = '#Lnoline'
            _file = 'nofile'
            file = Path(_file).name

        self.wasGeneratedBy = self.wasGeneratedBy.format(commit=commit,
                                                         hash_L_line=line,
                                                         file=file)
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


class ParcOnt(Ont):
    """ Parent class for parcellation related ontologies.
        Used to isolate parcellation related subclasses at build time."""


class LabelsBase(ParcOnt):  # this replaces genericPScheme
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


def simpleOnt(filename=f'temp-{UTCNOW()}',
              prefixes=tuple(),  # dict or list
              imports=tuple(),
              triples=tuple(),
              comment=None,
              path='ttl/',
              branch='master',
              fail=False,
              _repo=True,
              write=False):

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
    Simple.imports = imports
    if isinstance(prefixes, dict):
        Simple.prefixes = {k:str(v) for k, v in prefixes.items()}
    else:
        Simple.prefixes = makePrefixes(*prefixes)

    if branch != 'master':
        Simple.remote_base = f'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/{branch}/'

    built_ont, = build(Simple, fail=fail, n_jobs=1, write=write)

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
