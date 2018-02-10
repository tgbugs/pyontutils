import os
import yaml
import subprocess
import rdflib
import requests
from pathlib import Path
from collections import namedtuple
from rdflib.extras import infixowl
from inspect import getsourcelines, getsourcefile
from pyontutils import closed_namespaces as cnses
from pyontutils.utils import refile, TODAY, getCommit
from pyontutils.closed_namespaces import *

# prefixes

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
    return tuple(PREFIXES[prefix] for prefix in prefixes)

def interlex_namespace(user):
    return 'http://uri.interlex.org/' + user + '/'

# namespaces

(HBA, MBA, NCBITaxon, NIFRID, NIFTTL, UBERON, ilxtr,
 ilx) = makeNamespaces('HBA', 'MBA', 'NCBITaxon', 'NIFRID', 'NIFTTL', 'UBERON',
                       'ilxtr', 'ilx')
HCPMMP = rdflib.Namespace(interlex_namespace('hcpmmp/uris/labels'))
PAXMUS = rdflib.Namespace(interlex_namespace('paxinos/uris/mouse/labels'))
PAXRAT = rdflib.Namespace(interlex_namespace('paxinos/uris/rat/labels'))
TEMP = rdflib.Namespace(interlex_namespace('temp/uris'))
WHSSD = rdflib.Namespace(interlex_namespace('waxholm/uris/sd/labels'))

rdf = rdflib.RDF
rdfs = rdflib.RDFS

replacedBy = makeURIs('replacedBy')

# common funcs

def check_value(v):
    if isinstance(v, rdflib.Literal) or isinstance(v, rdflib.URIRef):
        return v
    elif isinstance(v, str) and v.startswith('http'):
        return rdflib.URIRef(v)
    else:
        return rdflib.Literal(v)

def restriction(lift, s, p, o):
    n0 = rdflib.BNode()
    yield s, rdfs.subClassOf, n0
    yield n0, rdf.type, owl.Restriction
    yield n0, owl.onProperty, p
    yield n0, lift, o

def annotation(ap, ao, s, p, o):
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

def yield_recursive(s, p, o, source_graph):
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
        if edge == 'isDefinedBy':
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
        definingArtifactsS=ilxtr.isDefinedBy,
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
                    setattr(self, kw, arg)
            if kwargs:
                #print(f'WARNING: {sorted(kwargs)} are not kwargs for {self.__class__.__name__}')  # XXX
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
            if hasattr(cls, 'runonce'):
                cls.runonce()
            cls.raw = cls.loadData()
            cls.data = cls.validate(*cls.processData())
            cls._triples_for_ontology = []
            if os.path.exists(cls.source):  # TODO no expanded stuff
                file_commit = subprocess.check_output(['git', 'log', '-n', '1',
                                                       '--pretty=format:%H', '--',
                                                       cls.source]).decode().rstrip()

                cls.iri = rdflib.URIRef(cls.iri_prefix_wdf.format(file_commit=file_commit) + cls.source)
            elif cls.source.startswith('http'):
                cls.iri = rdflib.URIRef(cls.source)
            else:
                print('Unknown source', cls.source)
            cls.prov()
        self = super().__new__(cls, cls.data)
        return self

    @classmethod
    def loadData(cls):
        with open(os.path.expanduser(cls.source), 'rt') as f:
            return f.read()

    @classmethod
    def processData(cls):
        return cls.raw,

    @classmethod
    def validate(cls, data):
        return data

    @classmethod
    def prov(cls):
        object = rdflib.URIRef(cls.iri_prefix_hd + cls.source)
        if os.path.exists(cls.source) and not hasattr(cls, 'source_original'):
            cls.iri_head = object
            if hasattr(cls.artifact, 'hadDerivation'):
                cls.artifact.hadDerivation.append(object)
            else:
                cls.artifact.hadDerivation = [object]
        elif hasattr(cls, 'source_original') and cls.source_original:
            cls.iri_head = object
            if cls.artifact is not None:
                cls.artifact.source = cls.iri
        elif cls.source.startswith('http'):
            print('Source is url and assumed to have no intermediate', cls.source)
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
    )

    def __init__(self, *args, **kwargs):
        if 'comment' not in kwargs and self.comment is None and self.__doc__:
            self.comment = ' '.join(_.strip() for _ in self.__doc__.split('\n'))

        commit = getCommit()
        line = getsourcelines(self.__class__)[-1]
        file = getsourcefile(self.__class__)
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
        if hasattr(self, 'sources'):  # FIXME move this to the RegionBase/LabelBase
            self.wasDerivedFrom = tuple(_ for _ in (i.iri if isinstance(i, Source) else i
                                                    for i in self.sources)
                                        if _ is not None)
            print(self.wasDerivedFrom)

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
        if hasattr(self, 'root'):
            yield from self.root
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
            self.graph.add(t)
        return self

    def validate(self):
        # implement per class
        pass

    @property
    def iri(self):
        return self._graph.ontid

    def write(self):
        # TODO warn in ttl file when run when __file__ has not been committed
        self._graph.write()


