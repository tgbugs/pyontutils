import io
import os
import yaml
import types
import tempfile
import mimetypes
import subprocess
import rdflib
from inspect import getsourcefile
from pathlib import Path, PurePath
from itertools import chain
from collections import namedtuple
from urllib.parse import urlparse
import ontquery as oq
import augpathlib as aug
import requests
import htmlfn as hfn
from joblib import Parallel, delayed
from rdflib.extras import infixowl
from ttlser import CustomTurtleSerializer, natsort
from pyontutils import combinators as cmb
from pyontutils import closed_namespaces as cnses
from pyontutils.utils import (refile,
                              TODAY,
                              UTCNOW,
                              UTCNOWISO,
                              getSourceLine,
                              utcnowtz,
                              Async,
                              deferred,
                              TermColors as tc,
                              log)
from pyontutils.utils_extra import check_value
from pyontutils.config import working_dir, auth
from pyontutils.namespaces import (makePrefixes,
                                   makeNamespaces,
                                   makeURIs,
                                   NIFRID,
                                   ilxtr,
                                   PREFIXES as uPREFIXES,
                                   rdf,
                                   rdfs,
                                   owl,
                                   skos,
                                   dc,
                                   dcterms,
                                   prov,
                                   oboInOwl)
from pyontutils.identity_bnode import IdentityBNode

current_file = Path(__file__).absolute()
oq.utils.log.removeHandler(oq.utils.log.handlers[0])
oq.utils.log.addHandler(log.handlers[0])

# common funcs

def relative_resources(pathstring, failover='nifstd/resources'):
    """ relative paths to resources in this repository
        `failover` matches the location relative to the
        github location (usually for prov purposes) """

    if working_dir is None:
        return Path(failover, pathstring).resolve()
    else:
        return Path(auth.get_path('resources'), pathstring).resolve().relative_to(working_dir.resolve())


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


def build(*onts, fail=False, n_jobs=9, write=True):
    """ Set n_jobs=1 for debug or embed() will crash. """
    tail = lambda:tuple()
    lonts = len(onts)
    if lonts > 1:
        for i, ont in enumerate(onts):
            if ont.__name__ == 'parcBridge':
                onts = onts[:-1]
                def tail(o=ont):
                    return o.setup(),
                if i != lonts - 1:
                    raise ValueError('parcBridge should be built last to avoid weird errors!')
    # ont_setup must be run first on all ontologies
    # or we will get weird import errors
    if n_jobs == 1 or True:
        return tuple(ont.make(fail=fail, write=write) for ont in
                     tuple(ont.setup() for ont in onts) + tail())

    # have to use a listcomp so that all calls to setup()
    # finish before parallel goes to work
    return Parallel(n_jobs=n_jobs)(delayed(o.make)(fail=fail, write=write)
                                   for o in
                                   #[ont_setup(ont) for ont in onts])
                                   (tuple(Async()(deferred(ont.setup)()
                                                  for ont in onts)) + tail()
                                    if n_jobs > 1
                                    else [ont.setup()
                                          for ont in onts]))


def yield_recursive(s, p, o, source_graph):  # FIXME transitive_closure on rdflib.Graph?
    yield s, p, o
    new_s = o
    if isinstance(new_s, rdflib.BNode):
        for p, o in source_graph.predicate_objects(new_s):
            yield from yield_recursive(new_s, p, o, source_graph)


# ontology resource object
from werkzeug.contrib.iterio import IterIO


class Stream:

    @property
    def identifier(self):
        """ Implicitly the unbound identifier that is to be dereferenced. """
        # FIXME interlex naming conventions call this a reference_name
        # in order to give it a bit more lexical distance from identity
        # which implies some hash function
        raise NotImplementedError

    @identifier.setter
    def identifier(self, value):
        raise NotImplementedError

    def checksum(self, cypher=None):  # FIXME default cypher value
        if not hasattr(self, '__checksum'):  # NOTE can set __checksum on the fly
            self.__checksum = self._checksum(cypher)

        return self.__checksum

    identity = checksum  # FIXME the naming here is mathematically incorrect

    def _checksum(self, cypher):
        raise NotImplementedError

    @property
    def progenitor(self):
        """ the lower level stream from which this one is derived """
        # could also, confusingly be called a superstream, but
        # the superstream might have a less differentiated, or simply
        # a different type or structure (e.g. an IP packet -> a byte stream)

        # unfortunately the idea of a tributary, or a stream bed
        # breaks down, though in a pure bytes representation
        # technically the transport headers do come first
        raise NotImplementedError

    superstream = progenitor

    @property
    def headers(self):
        """ Data from the lower level stream from which this stream is
            derived/differentiated """
        # FIXME naming ...
        # sometimes this is related to ...
        #  transport
        #  prior in time
        #  unbound metadata, or metadata that will be unbound in the target
        #  metadata kept by the stream management layer (e.g. file system)
        #  stream type
        #  stream size
        #  operational metadata
        #  summary information

        # if you are sending a file then populate all the info
        # needed by the server to set up the stream (even if that seems a bit low level)
        raise NotImplementedError
        return self.superstream.metadata

    @headers.setter
    def headers(self, value):
        self._headers = value
        raise NotImplementedError('If you override self.headers in the child '
                                  'you need to reimplement this too.')

    @property
    def data(self):
        """ The primary opaque datastream that will be differentiated
            at the next level """
        raise NotImplementedError

    @property
    def metadata(self):
        """ stream metadata, hopefully as a header

            technically this should be called metadata_bound
            since it is part of the same stream, it might
            make sense to invert this to have a variety of
            datasources external to a stream that contain
            additional relevant data using that id
        """
        if not hasattr(self, '_metadata'):
            self._metadata = self._metadata_class(self.identifier)

        return self._metadata

    @property
    def identifier_bound(self):
        raise NotImplementedError
        return self.metadata.identifier_bound

    @property
    def identifier_version(self):
        """ implicitly identifier_bound_version """
        raise NotImplementedError
        return self.metadata.identifier_version


class OntRes(Stream):
    """ Message manager for serialized ontology resource.
        There are plenty of tools that already deal effectively
        with a triplified store, but we need something that does
        a better job at managing the interchange, esp in and out
        of git. Sort of a better backend for ontquery services back by
        serialized sources. May ultimately move this code there. """

    #def __new__(cls, iri_or_path):
        # TODO return an iri wrapper or a path wrapper
        #pass

    Graph = None  # this is set below after OntGraph is created (derp)

    def __init__(self, identifier, repo=None, Graph=None):  # XXX DO NOT USE THIS IT IS BROKEN
        self.identifier = identifier  # the potential attribute error here is intentional
        self.repo = repo  # I have a repo augmented path in my thesis stats code
        if Graph == None:
            Graph = OntGraph

        self.Graph = Graph

    def _populate(self, graph, gen):
        raise NotImplementedError('too many differences between header/data and xml/all the rest')

    def populate(self, graph):
        # TODO if self.header ...
        self._populate(graph, self.data)

    @property
    def graph(self, cypher=None):
        # FIXME transitions to other streams should be functions
        # and it also allows passing an explicit cypher argument
        # to enable checksumming in one pass, however this will
        # require one more wrapper
        if not hasattr(self, '_graph'):
            kwargs = {}
            if hasattr(self, 'path'):
                kwargs['path'] = self.path

            self._graph = self.Graph(**kwargs)
            self.populate(self._graph)

        return self._graph

    @property
    def identifier_bound(self):
        return next(self.graph[:rdf.type:owl.Ontology])

    @property
    def identifier_version(self):
        """ implicitly identifier_bound_version since we won't maniuplate a
            version iri supplied as the identifi
            the id to get
        """
        return next(self.graph[self.identifier_bound:owl.versionIRI])

    @property
    def imports(self):
        for object in self.graph[self.identifier_bound:owl.imports]:
            # TODO switch this for _res_remote_class to abstract beyond just owl
            yield OntResIri(object)  # this is ok since files will be file:///

    @property
    def import_chain(self):
        yield from self._import_chain({OntResIri(self.identifier_bound)})

    def _import_chain(self, done):
        imps = list(self.imports)
        Async()(deferred(lambda r: r.metadata.graph)(_) for _ in imps)
        for resource in imps:
            if resource in done:
                continue

            done.add(resource)
            yield resource
            yield from resource.metadata._import_chain(done)

    def __eq__(self, other):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError

    def __repr__(self):
        return self.__class__.__name__ + f'({self.identifier!r})'


class OntMeta(OntRes):
    """ only the header of an ontology, e.g. the owl:Ontology section for OWL2 """

    # headers all the way down data -> ontology header -> response header -> iri

    def _graph_sideload(self, data):
        # this will overwrite any existing graph
        self._graph = self.Graph().parse(data=data, format=self.format)

    def _populate(self, graph, gen):
        # we don't pop request headers or file metadata off in here
        # because different loading processes may use that information
        # to dispatch different loading processes

        if self.format == 'application/rdf+xml':
            # rdflib xml parsing uses an incremental parser that
            # constructs its own file object and byte stream
            data = b''.join(gen)
            graph.parse(data=data)

        elif self.format == 'text/owl-functional':  # FIXME TODO
            log.error(f'TODO cannot parse owl functional syntax yet {self}')

        else:
            itio = IterIO(gen)
            itio.name = self.identifier  # some rdflib parses need a name
            graph.parse(file=itio, format=self.format)

    def __eq__(self, other):
        # FIXME this is ... complicated
        return self.identifier_bound == other.identifier_bound

    def __hash__(self):
        return hash((self.__class__, self.identifier_bound))


class OntResOnt(OntRes):
    """ full ontology files """

    _metadata_class = None  # FIXME can we do this by dispatching OntMeta like Path?

    def __eq__(self, other):
        return self.metadata.identifier_bound == other.metadata.identifier_bound

    def __hash__(self):
        return hash((self.__class__, self.metadata.identifier_bound))


class OntIdIri(OntRes):
    def __init__(self, iri):
        self.iri = iri
        # TODO version iris etc.

    def _get(self):
        return requests.get(self.iri, stream=True, headers={'Accept': 'text/turtle'})  # worth a shot ...

    @property
    def identifier(self):
        return self.iri

    @property
    def headers(self):
        """ request headers """
        if not hasattr(self, '_headers'):
            resp = requests.head(self.identifier)  # TODO status handling for all these
            self._headers = resp.headers

        return self._headers

    @headers.setter
    def headers(self, value):
        self._headers = value


class OntMetaIri(OntMeta, OntIdIri):

    @property
    def data(self):
        gen = self._data()
        format = next(gen)  # advance to set self.format in _data
        return gen

    def _data(self, yield_response_gen=False):
        if self.identifier.endswith('.zip'):
            # TODO use Content-Range to retrieve only the central directory
            # after we get the header here
            # https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
            # this could be another way to handle the filesystem issues for bf
            # as well ...
            pass

        resp = self._get()
        self.headers = resp.headers
        # TODO consider yielding headers here as well?
        gen = resp.iter_content(chunk_size=4096)
        first = next(gen)
        # TODO better type detection

        if first.startswith(b'<?xml'):
            start = b'<owl:Ontology'
            stop = b'</owl:Ontology>'
            sentinel = b'TODO'
            self.format = 'application/rdf+xml'

        elif first.startswith(b'@prefix') or first.startswith(b'#lang rdf/turtle'):
            start = b' owl:Ontology'  # FIXME this is not standard
            stop = b' .\n'  # FIXME can be fooled by strings
            sentinel = b'### Annotations'  # FIXME only works for ttlser
            #sentinel = b' a '  # FIXME if a |owl:Ontology has a chunk break on | this is incorrect
            # also needs to be a regex that ends in [^owl:Ontology]
            self.format = 'text/turtle'

        elif first.startswith(b'Prefix(:='):
            start = b'\nOntology'
            stop = b')\n\n'  # FIXME I don't think owl functional syntax actually has a proper header :/
            sentient = b'TODO'
            self.format = 'text/owl-functional'
        else:
            'text/owl-manchester'
            raise ValueError(first.decode())

        yield self.format  # we do this because self.format needs to be accessible before loading the graph

        close_rdf = b'\n</rdf:RDF>\n'
        searching = False
        header_data = b''
        for chunk in chain((first,), gen):
            if start in chunk:
                searching = True
                # yield content prior to start since it may include a stop
                # that we don't actually want to stop at
                start_end_index = chunk.index(start) + len(start)
                header_first_chunk = chunk[:start_end_index]
                if yield_response_gen:
                    header_data += header_first_chunk

                yield header_first_chunk
                chunk = chunk[start_end_index:]

            if searching and stop in chunk:  # or test_chunk_ends_with_start_of_stop(stop, chunk)
                # FIXME edge case where a stop crosses a chunk boundary
                # if stop is short enough it may make sense to do a naieve contains check
                # to start things off ...

                stop_end_index = chunk.index(stop) + len(stop)
                header_last_chunk = chunk[:stop_end_index]
                if yield_response_gen:
                    header_data += header_last_chunk

                yield header_last_chunk
                if yield_response_gen:
                    if self.format == 'application/rdf+xml':
                        header_data += close_rdf

                    self._graph_sideload(header_data)
                    chunk = chunk[stop_end_index:]
                    yield resp, chain((chunk,), gen)

                else:
                    # if we are not continuing then close the xml tags
                    if self.format == 'application/rdf+xml':
                        yield close_rdf

                    resp.close()

                return

            elif not searching and sentinel in chunk:
                sent_end_index = chunk.index(sentinel) + len(sentinel)
                header_last_chunk = chunk[:sent_end_index]
                if yield_response_gen:
                    header_data += header_last_chunk

                yield header_last_chunk
                if yield_response_gen:
                    if self.format == 'application/rdf+xml':
                        header_data += close_rdf

                    self._graph_sideload(header_data)
                    chunk = chunk[sent_end_index:]
                    yield resp, chain((chunk,), gen)

                else:
                    # if we are not continuing then close the xml tags
                    if self.format == 'application/rdf+xml':
                        yield close_rdf

                    resp.close()

                return

            else:
                # FIXME TODO need a sentinel value where there isn't a header
                # so that we can infer that there is no header, or at least
                # no headerish data at the head of the file
                if yield_response_gen:
                    header_data += chunk

                yield chunk


class OntResIri(OntIdIri, OntResOnt):

    _metadata_class = OntMetaIri

    @property
    def data(self):
        format, *header_chunks, (resp, gen) = self.metadata._data(yield_response_gen=True)
        self.headers = resp.headers
        self.format = format
        # TODO populate header graph? not sure this is actually possible
        # maybe need to double wrap so that the header chunks always get
        # consumbed by the header object ?
        if self.format == 'application/rdf+xml':
            resp.close()
            return None

        return chain(header_chunks, gen)

    def _populate(self, graph, gen):
        # we don't pop request headers or file metadata off in here
        # because different loading processes may use that information
        # to dispatch different loading processes

        if self.format == 'application/rdf+xml':
            # rdflib xml parsing uses and incremental parser that
            # constructs its own file object and byte stream
            graph.parse(self.identifier, format=self.format)

        elif self.format == 'text/owl-functional':  # FIXME TODO
            log.error(f'TODO cannot parse owl functional syntax yet {self}')

        else:
            itio = IterIO(gen)
            itio.name = self.identifier
            graph.parse(file=itio, format=self.format)


class OntIdPath(OntRes):
    # FIXME should this be an instrumented path?
    # should OntResIri be an instrumented iri?
    def __init__(self, path):
        # FIXME type caste?
        self.path = path

    @property
    def identifier(self):
        return self.path.as_posix()

    def _get(self):
        resp = requests.Response()
        with open(self.path, 'rb') as f:
            resp.raw = io.BytesIO(f.read())  # FIXME streaming file read should be possible ...

        # TODO set headers here
        #resp.headers = {'Content-Length': self.path.meta_no_checksum.size}
        resp.status_code = 200
        return resp

    headers = OntIdIri.headers


class OntMetaPath(OntIdPath, OntMeta):
    data = OntMetaIri.data
    _data = OntMetaIri._data


class OntResPath(OntIdPath, OntResOnt):
    """ ontology resource coming from a file """

    _metadata_class = OntMetaPath
    data = OntResIri.data

    _populate = OntResIri._populate  # FIXME application/rdf+xml is a mess ... cant parse streams :/


class OntIdGit(OntIdPath):
    def __init__(self, path, ref='HEAD'):
        """ ref can be HEAD, branch, commit hash, etc.

            if ref = None, the working copy of the file is used
            if ref = '',   the index   copy of the file is used """

        self.path = path
        self.ref = ref

    @property
    def identifier(self):
        # FIXME this doesn't quite conform because it is a local identifier
        # which neglects the repo portion of the id ...
        if type(self.path) == str:
            breakpoint()

        if self.ref is None:
            return self.path.as_posix()

        return self.ref + ':' + self.path.repo_relative_path.as_posix()

    @property
    def metadata(self):
        if not hasattr(self, '_metadata'):
            self._metadata = self._metadata_class(self.path, ref=self.ref)

        return self._metadata

    def _get(self):
        resp = requests.Response()
        if self.ref is None:
            with open(self.path, 'rb') as f:
                resp.raw = io.BytesIO(f.read())  # FIXME can't we stream/seek these?
        else:
            resp.raw = io.BytesIO(self.path.repo.git.show(self.identifier).encode())

        resp.status_code = 200
        return resp

    headers = OntIdIri.headers


class OntMetaGit(OntIdGit, OntMeta):
    data = OntMetaIri.data
    _data = OntMetaIri._data


class OntResGit(OntIdGit, OntResOnt):
    _metadata_class = OntMetaGit
    data = OntResIri.data

    _populate = OntResIri._populate  # FIXME application/rdf+xml is a mess ... cant parse streams :/


class OntResAny:
    def __new__(cls, path, ref=None, ref_failover=None):
        # it really is better if people statically know so we don't have to guess
        """
        if isinstance(path_or_iri, Path):
            iri = None
            path = path_or_iri
        elif isinstance(path_or_iri, str):
            if path_or_iri.startswith('http://') or path_or_iri.startswith('https://'):
                iri = path_or_iri
                # TODO try to find the local version?
                path = None
            else:
                iri = None
                path = path_or_iri
        else:
            raise TypeError(f'what is a {type(path_or_iri)} {path_or_iri!r}')

        """
        try:
            org = OntResGit(path, ref=ref)
            org._get()  # yes this is slow, but it is the safest way ...
            return org
        except BaseException as e:
            #log.exception(e)
            repo = path.repo
            remote = repo.remote()
            rnprefix = remote.name + '/'
            url_base = next(remote.urls)
            pu = urlparse(url_base)
            if pu.netloc == 'github.com':
                if not ref or ref == 'HEAD':
                    ref = repo.active_branch.name
                elif ref not in [r.name.replace(rnprefix, '') for r in repo.refs]:
                    log.warning(f'unknown ref {ref}')

                rpath = Path(pu.path).with_suffix('') / ref / path.repo_relative_path
                iri = 'https://raw.githubusercontent.com' + rpath.as_posix()
                return OntResIri(iri)

            breakpoint()


class OntMetaInterLex(OntMeta):
    pass


class OntResInterLex(OntResOnt):
    """ ontology resource backed by interlex """

    _metadata_class = OntMetaInterLex


class BetterNamespaceManager(rdflib.namespace.NamespaceManager):
    def __call__(self, **kwargs):
        """ set prefixes """
        raise NotImplementedError

    def __iter__(self):
        yield from self.namespaces()

    def qname(self, iri):
        prefix, namespace, name = self.compute_qname(iri, generate=False)
        if prefix == "":
            return name
        else:
            return ":".join((prefix, name))

    def populate(self, graph):
        [graph.bind(k, v) for k, v in self.namespaces()]

    def populate_from(self, *graphs):
        [self.bind(k, v) for g in graphs for k, v in g.namespaces()]


class OntGraph(rdflib.Graph):
    """ A 5th try at making one of these. ConjunctiveGraph version? """

    metadata_type_markers = [owl.Ontology]  # FIXME naming

    def __init__(self, *args, path=None, existing=None, namespace_manager=None, **kwargs):
        if existing:
            self.__dict__ == existing.__dict__
            if not hasattr(existing, '_namespace_manager'):
                self._namespace_manager = BetterNamespaceManager(self)
                self.namespace_manager.populate_from(existing)
        else:
            super().__init__(*args, **kwargs)
            # FIXME the way this is implemented in rdflib makes it impossible to
            # change the namespace manager type in subclasses which is _really_ annoying
            # we shortcircuit this here
            self._namespace_manager = namespace_manager

        self.bind('owl', owl)
        self.path = path

    @property
    def path(self):
        return self.__path

    @path.setter
    def path(self, path):
        if path is not None and not isinstance(path, Path):
            log.warning(f'Not a pathlib.Path! {path}')
        self.__path = path

    # TODO id for graphs like this ... use InterLex IdentityBNode?

    # TODO local_conventions aka curies
    # NOTE you actually just use it the other way by passing this
    # to OntCuries.populate

    @oq.utils.mimicArgs(rdflib.Graph.parse)
    def parse(self, *args, **kwargs):
        if not args and not kwargs and self.path is not None:
            # FIXME augpathlib.Path ;_;
            mimetype, _ = mimetypes.guess_type(self.path.as_uri())
            return super().parse(self.path.as_posix(), format=mimetype)
        else:
            args = [a.as_posix() if isinstance(a, Path) else a for a in args]
            return super().parse(*args, **kwargs)

    def _get_namespace_manager(self):
        if self._namespace_manager is None:
            self._namespace_manager = BetterNamespaceManager(self)
        return self._namespace_manager

    def _set_namespace_manager(self, nm):
        self._namespace_manager = nm

    namespace_manager = property(_get_namespace_manager,
                                 _set_namespace_manager,
                                 doc="this graph's namespace-manager")

    @property
    def prefixes(self):
        """ the prefix/curie/qname section of an rdf file """
        # a new OntCuries-like object that wraps NamespaceManager
        # and can leverage its trie
        self.namespace_manager
        raise NotImplementedError('yet')

    @property
    def metadata(self):
        """ the header/metadata/ontology section of an rdf file """
        raise NotImplementedError('yet')
        return OntGraphMetadata(self)

    @property
    def data(self):
        """ everything else """
        # FIXME this is actually metadata + homogenous data
        # question: should data sections automatically checksum
        # their contents as it streams through?
        # answer: no, if someone needs a checksum, they should ask
        # for it explicitly when they transition to some other stream
        # whether that is a file or a graph etc.

        raise NotImplementedError('yet')

    def write(self, path=None, format='nifttl'):
        if path is None:
            path = self.path

        with open(path, 'wb') as f:
            self.serialize(f, format=format)

    @property
    def ttl(self):
        out = self.serialize(format='nifttl').decode()
        return out

    @property
    def ttl_html(self):
        out = self.serialize(format='htmlttl').decode()
        return out

    def debug(self):
        print(self.ttl)

    def matchNamespace(self, namespace, *, ignore_predicates=tuple()):
        # FIXME can't we hit the cache for these?
        sns = str(namespace)
        for s, p, o in self:
            if p not in ignore_predicates:
                for e in (s, p, o):
                    if isinstance(e, rdflib.URIRef):
                        try:
                            pre, ns, suff = self.compute_qname(e, generate=False)
                            if str(ns) == sns:
                                yield e
                        except KeyError:
                            pass

    def couldMapEntities(self, *temp_namespaces, ignore_predicates=tuple()):
        yield from (e for ns in temp_namespaces
                    for e in self.matchNamespace(ns, ignore_predicates=ignore_predicates))

    def diffFromReplace(self, replace_graph, *, new_replaces_old=True):
        """ compute add, remove, same graphs based on a graph
            the contains triples of the form `new replaces old`
            where replaces can be any predicate set new_replaces_old=False
            if the add_and_replace graph is of the form `old replacedBy new`
        """
        if new_replaces_old:
            replace = {old:new for new, _, old in replace_graph}
        else:
            replace = {old:new for old, _, new in replace_graph}

        def iri_replace(t):
            return tuple(replace[e] if e in replace else e for e in t)

        add, rem, same = [self.__class__() for _ in range(3)]
        for t in self:
            nt = iri_replace(t)
            if nt != t:
                add.add(nt), rem.add(t)
            else:
                same.add(t)

        return add, rem, same

    def subjectGraph(self, subject):
        # some days I am smart, as in years ago when working on neuron stuff
        # TODO do we need to check for duplicates and cycels?
        def f(triple, graph):
            subject, predicate, object = triple
            for p, o in graph[object]:
                yield object, p, o

        yield from self.transitiveClosure(f, (None, None, subject))

    def _subjectGraph(self, subject, *, done=None):
        # some days I am dumb
        first = False
        if done is None:
            first = True
            done = set()

        done.add(subject)

        for p, o in self[subject::]:
            if first:  # subject free subject graph
                yield p, o
            else:
                yield subject, p, o

            if isinstance(o, rdflib.BNode):
                yield from self.subjectGraph(o, done=done)
            elif isinstance(o, rdflib.URIRef):
                # TODO if we want closed world identified subgraphs
                # then we would compute the identity of the named
                # here as well, however, that is a rare case and
                # would cause identities to change at a distance
                # which is bad, so probably should never do it
                pass

    def subjectIdentity(self, subject, *, debug=False):
        """ calculate the identity of a subgraph for a particular subject
            useful for determining whether individual records have changed
            not quite
        """

        pairs_triples = list(self.subjectGraph(subject))
        ibn = IdentityBNode(pairs_triples, debug=False)
        if debug:
            triples = [(subject, *pos) if len(pos) == 2 else pos for pos in pairs_triples]
            g = self.__class__()

            _replaced = {}
            def replace(e):
                if isinstance(e, rdflib.BNode):
                    if e not in _replaced:
                        _replaced[e] = rdflib.BNode()

                    e = _replaced[e]

                return e

            def rebnode(t):
                return tuple(replace(e) for e in t)

            # switch out all the bnodes to double check
            [g.add(rebnode(t)) for t in triples]
            self.namespace_manager.populate(g)
            dibn = g.subjectIdentity(subject, debug=False)
            gibn = IdentityBNode(g, debug=True)
            print(g.ttl)
            print(ibn, dibn)
            assert ibn == dibn
            assert ibn != gibn
            breakpoint()

        return ibn

    def named_subjects(self):
        for s in self.subjects():
            if isinstance(s, rdflib.URIRef):
                yield s

    def subjectsChanged(self, other_graph):
        """ in order to detect this the mapped id must be persisted
            by the process that is making the change

            NOTE: To avoid the hashing chicken and egg problem here
            one would have to explicitly exclude triples with the
            predicate used to store the identity, which adds quite a
            bit of complexity. To avoid this, simply keeping and old
            version of the graph around might be easier. TODO explore
            tradeoffs.
        """

        # the case where an external process (e.g. editing in protege)
        # has caused a change in the elements used to calculate the id
        # of the class

        # FIXME mapped but a change to the structure of the class has
        # cause a change in the identity of the class
        # in which case the old hasTemporaryId should still be attached

        #temporary_id_changed = [e for e in self[:ilxtr.hasTemporaryId:] not_mapped ]
        #changed_classes = [(s,
                            #ilxtr.hasTemporaryId,
                            #o) for s, o in self[:ilxtr.hasTemporaryId:]]

        sid = {s:self.subjectIdentity(s) for s in set(self.named_subjects())}
        osid = {s:other_graph.subjectIdentity(s) for s in set(other_graph.named_subjects())}
        ssid = set(sid)
        sosid = set(osid)
        added = not_in_other = ssid - sosid
        removed = not_in_self = sosid - ssid
        changed = [(s, osid[s], i) for s, i in sid.items() if s in osid and i != osid[s]]
        return added, removed, changed

    def addReplaceGraph(self, index_graph, index_namespace, *temp_namespaces):
        """ Given an index of existing ids that map to ids in temporary namespaces
            return a graph of `new replaces old` triples. Currently this works on
            temp_namespaces, but in theory it could operate on any namespace.

            Note that this does attempt to detect changes to classes that
            have already been mapped and have a new temporary id. That
            functionality is implemented elsewhere. """

        existing_indexes  = list(set(index_graph.matchNamespace(index_namespace)))  # target prefix?
        lp = len(index_namespace)
        suffixes = [int(u[lp:]) for u in existing_indexes]
        start = max(suffixes) + 1 if suffixes else 1

        # FIXME ignore predicates is more complex than this
        # we want to filter out only cases that have already been mapped to
        # the current index namespace
        could_map = list(set(self.couldMapEntities(*temp_namespaces,
                                                   ignore_predicates=(ilxtr.hasTemporaryId,))))
        mapped_triples = [(s,
                           ilxtr.hasTemporaryId,
                           o) for s, o in index_graph[:ilxtr.hasTemporaryId:]]
        # FIXME could be mapped into another namespace ? what to do in that case?
        already_mapped = [o for _, _, o in mapped_triples]
        not_mapped = [e for e in could_map if e not in already_mapped]

        # the iri replace operation is common enough that it probably
        # deserves its own semantics since when combined with a known
        # input qualifier the output graph is well defined and it provides
        # much stronger and clearer semantics for what was going on
        # allowing multiple different predicates is fine since different
        # processes may have different use cases for the predicate
        # in the case where the mapping is simply stored and added
        # as an equivalent class along with hasInterLexId, then the new
        # mappings are simply add rather than addAndReplaceUsingMapping
        iri_replace_map = [(index_namespace[str(i + start)],
                            ilxtr.hasTemporaryId,
                            temp_id)
                           for i, temp_id in enumerate(sorted(not_mapped, key=natsort))]

        # FIXME
        # iris that have been mapped but not replaced
        # this will probably be a bug in the future?
        # the issue is that those triples shouldn't be added to add_replace_graph
        # because they are already in the index_graph
        # this is the more efficient place to obtain this list
        # but it could also be obtained by comparing index_graph
        # with add_replace_graph ... maybe ...
        not_replaced = [(s, p, o) for s, p, o in mapped_triples if o in could_map]

        # need to compute the id of the graph/triples opaque data section
        # this is the pure add graph, in this case it is also used to
        # compute the replace graph as well
        add_replace_graph = self.__class__()
        [add_replace_graph.add(t) for t in iri_replace_map]

        return add_replace_graph, not_replaced

    def mapTempToIndex(self, index_graph, index_namespace, *temp_namespaces):
        """ In theory index_graph could be self if the namespace in use
            is only relevant for a single file, otherwise there needs to be
            a single shared reference file that maintains the the index for all
            files

            NOTE: either the current graph or the index_graph needs to have the
                  curie mapping for the namespaces defined prior to calling this
                  otherwise you will have to cross populate namespaces again
        """
        if not isinstance(index_graph, self.__class__):
            index_graph = self.__class__(existing=index_graph)

        add_replace_graph, not_replaced = self.addReplaceGraph(index_graph,
                                                               index_namespace,
                                                               *temp_namespaces)

        # TODO also want the transitions here if we
        # want to record the record in InterLex
        index_graph.namespace_manager.populate_from(self)
        [index_graph.add(t) for t in add_replace_graph]
        # FIXME for some reason I had a thought that the index
        # graph should include labels as a semi-orthogonal check
        # to make sure that everything lines up as expected

        # if an identifier is used in multiple serialized graphs
        # then we want to make sure that we can do a replacement
        # if we find that temporary identifier somewhere else
        # even if it has already been added to the index
        # NOTE that this behavior is undesireable if the temp ids
        # were originally minted per file, in which case this
        # requires a two step process where the graph is run with itself
        # as the index at which point it can safely be run again
        # against a global index
        # TODO detect use of likely non-unique suffixes in temp namespaces
        [add_replace_graph.add(t) for t in not_replaced]
        add_only_graph, remove_graph, same_graph = self.diffFromReplace(add_replace_graph)

        # the other semantics that could be used here
        # would be to do an in place modification of self
        # to remove the remove graph and add the add_only_graph

        # NOTE the BNodes need to retain their identity across the 3 graphs
        # so that they reassemble correctly
        new_self = self.__class__(path=self.path)
        [new_self.add(t) for t in add_replace_graph]
        [new_self.add(t) for t in add_only_graph]
        [new_self.add(t) for t in same_graph]

        new_self.namespace_manager.populate_from(index_graph)
        return new_self

    # variously named/connected subsets

    @property
    def boundIdentifiers(self):
        """ There should only be one but ... """
        for type in self.metadata_type_markers:
            yield from self[:rdf.type:type]

    @property
    def boundIdentifier(self):
        return next(self.boundIdentifiers)

    @property
    def versionIdentifiers(self):
        """ There should only be one but ... """
        for bid in self.boundIdentifiers:
            yield from self[bid:owl.versionIRI]

    @property
    def versionIdentifier(self):
        return next(self.versionIdentifiers)

    @property
    def metadata(self):
        for bi in self.boundIdentifiers:
            yield from self.subjectGraph(bi)

    @property
    def metadata_unnamed(self):
        yield from ((s, p, o) for s, p, o in self.metadata
                    if isinstance(s, rdflib.BNode))

    @property
    def data(self):
        bis = tuple(self.boundIdentifiers)
        meta_bnodes = tuple(e for t in metadata_unnamed for e in t
                            if isinstance(e, rdflib.BNode))
        meta_skip_subject = bis + meta_bnodes
        for s, p, o in self:
            if s not in meta_skip_subject:
                yield (s, p, o)

    @property
    def data_named(self):
        # FIXME process_graph is more efficient that this ...
        bis = tuple(self.boundIdentifiers)
        for s in self.subjects():
            if not isinstance(s, rdflib.BNode) and s not in bis:
                yield from self.subjectGraph(s)

    @property
    def data_unnamed(self):
        # there is no metadata unnamed
        # FIXME connected unnamed vs named ...
        # why is this so darned complex

        # have to know which bnodes are attached to meta
        #bi = self.boundIdentifier
        #connected_bnodes = tuple(e for t in self.data_named for e in t
                                 #if isinstance(e, rdflib.BNode))
        object_bnodes = tuple(o for o in self.objects() if isinstance(o, rdflib.BNode))
        for s in self.subjects():  # FIXME some non-bnode fellows seem to be sneeking in here
            if isinstance(s, rdflib.BNode) and s not in object_bnodes:
                yield from self.subjectGraph(s)

    def asConjunctive(self, debug=False):
        # TODO a version of this that can populate
        # from OntRes directly if conjunctive graph is requested or similar
        # since the individual graphs are already separate (though possibly incorrect)
        id = self.boundIdentifier
        #curies = rdflib.URIRef(id + '?section=localConventions')
        meta_id = rdflib.URIRef(id + '?section=metadata')
        data_id = rdflib.URIRef(id + '?section=data')
        datan_id = rdflib.URIRef(id + '?section=data_named')
        datau_id = rdflib.URIRef(id + '?section=data_unnamed')
        c = OntConjunctiveGraph(identifier=id)
        [c.addN((*t, meta_id) for t in self.metadata)]
        #[c.addN((*t, data_id)) for t in self.data]
        [c.addN((*t, datan_id) for t in self.data_named)]
        [c.addN((*t, datau_id) for t in self.data_unnamed)]
        if debug:
            c.bind('ilxtr', ilxtr)
            tc = CustomTurtleSerializer.topClasses
            if ilxtr.StreamSection not in tc:
                sec = CustomTurtleSerializer.SECTIONS
                CustomTurtleSerializer.topClasses = [ilxtr.StreamSection] + tc
                CustomTurtleSerializer.SECTIONS = ('',) + sec
            c.add((meta_id, rdf.type, ilxtr.StreamSection, meta_id))
            c.add((datan_id, rdf.type, ilxtr.StreamSection, datan_id))
            c.add((datau_id, rdf.type, ilxtr.StreamSection, datau_id))
        return c


class OntConjunctiveGraph(rdflib.ConjunctiveGraph, OntGraph):
    def __init__(self, *args, store='default', identifier=None, **kwargs):
        super().__init__(*args, **kwargs)
        # overwrite default context with our subclass
        self.default_context = OntGraph(store=self.store,
                                        identifier=identifier or rdflib.BNode())

    def get_context(self, identifier, quoted=False):
        """Return a context graph for the given identifier

        identifier must be a URIRef or BNode.
        """
        return OntGraph(store=self.store, identifier=identifier,
                        namespace_manager=self.namespace_manager)

    def debugAll(self):
        for g in sorted(self.contexts(), key=lambda g: g.identifier):
            print('-' * 80)
            print('-' * 80)
            g.debug()


OntRes.Graph = OntGraph


class OntGraphMetadata(OntGraph):
    """ header """
    # TODO given some OntGraphData that doesn't already have some meta
    # attache this meta to that data in prep to run all the hashing etc.


class OntGraphData(OntGraph):
    """ the homogenous everything else """


# TODO bind _ont_class for headers


def nif_import_chain():
    test = OntResIri('http://ontology.neuinfo.org/NIF/ttl/nif.ttl')
    return list(test.import_chain)


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


mGraph = OntGraph


class makeGraph:
    SYNONYM = 'NIFRID:synonym'  # dangerous with prefixes

    def __init__(self, name, prefixes=None, graph=None, writeloc=tempfile.tempdir):
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
            self.g = OntGraph()  # default args issue

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

    def write(self, cull=False):
        """ Serialize self.g and write to self.filename, set cull to true to remove unwanted prefixes """
        if cull:
            cull_prefixes(self).write()
        else:
            ser = self.g.serialize(format='nifttl')
            with open(self.filename, 'wb') as f:
                f.write(ser)
                #print('yes we wrote the first version...', self.name)

    def expand(self, curie):
        if isinstance(curie, rdflib.URIRef):
            return curie

        prefix, suffix = curie.split(':', 1)
        if ' ' in prefix:
            raise ValueError(f'Namespace prefix {prefix!r} is not a valid curie prefix!')
        if prefix not in self.namespaces:
            raise KeyError(f'Namespace prefix {prefix} does not exist for {curie}')
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


null_prefix = uPREFIXES['']
def cull_prefixes(graph, prefixes={k:v for k, v in uPREFIXES.items() if k != 'NIFTTL'},
                  cleanup=lambda ps, graph: None, keep=False):
    """ Remove unused curie prefixes and normalize to a standard set. """
    prefs = ['']
    if keep:
        prefixes.update({p:str(n) for p, n in graph.namespaces()})

    if '' not in prefixes:
        prefixes[''] = null_prefix  # null prefix

    pi = {v:k for k, v in prefixes.items()}
    asdf = {} #{v:k for k, v in ps.items()}
    asdf.update(pi)
    # determine which prefixes we need
    for uri in set((e for t in graph for e in t)):
        if uri.endswith('.owl') or uri.endswith('.ttl') or uri.endswith('$$ID$$'):
            continue  # don't prefix imports or templates
        for rn, rp in sorted(asdf.items(), key=lambda a: -len(a[0])):  # make sure we get longest first
            lrn = len(rn)
            if type(uri) == rdflib.BNode:
                continue
            elif uri.startswith(rn) and '#' not in uri[lrn:] and '/' not in uri[lrn:]:  # prevent prefixing when there is another sep
                prefs.append(rp)
                break

    ps = {p:prefixes[p] for p in prefs}

    cleanup(ps, graph)

    ng = makeGraph('', prefixes=ps)
    [ng.g.add(t) for t in graph]
    return ng


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
        local_base = auth.get_path('ontology-local-repo')
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

# oq.SciGraphRemote.verbose = True

class OntId(oq.OntId, rdflib.URIRef):
    #def __eq__(self, other):  # FIXME this makes OntTerm unhashabel!?
        #return rdflib.URIRef.__eq__(rdflib.URIRef(self), other)

    @property
    def URIRef(self):  # FIXME stopgap for comparison issues
        return rdflib.URIRef(self)

    @property
    def u(self):
        return self.URIRef

    def __str__(self):
        return rdflib.URIRef.__str__(self)

    def atag(self, **kwargs):
        if 'curie' in kwargs:
            kwargs.pop('curie')
        return hfn.atag(self.iri, self.curie, **kwargs)


class OntTerm(oq.OntTerm, OntId):
    def atag(self, curie=False, **kwargs):
        return hfn.atag(self.iri, self.curie if curie else self.label, **kwargs)  # TODO schema.org ...


SGR = oq.plugin.get('SciGraph')
IXR = oq.plugin.get('InterLex')
#sgr.verbose = True
for rc in (SGR, IXR):
    rc.known_inverses += ('hasPart:', 'partOf:'), ('NIFRID:has_proper_part', 'NIFRID:proper_part_of')

sgr = SGR(apiEndpoint=auth.get('scigraph-api'))
ixr = IXR(apiEndpoint=None, readonly=True)
ixr.Graph = OntGraph
OntTerm.query_init(sgr, ixr)  # = oq.OntQuery(sgr, ixr, instrumented=OntTerm)
[OntTerm.repr_level(verbose=False) for _ in range(2)]
query = oq.OntQueryCli(query=OntTerm.query)


class IlxTerm(OntTerm):
    skip_for_instrumentation = True


IlxTerm.query = oq.OntQuery(ixr, instrumented=OntTerm)  # This init pattern still works if you want to mix and match
ilxquery = oq.OntQueryCli(query=IlxTerm.query)

def map_term(subject, label, prefix=tuple()):
    def gn(t):
        try:
            return next(OntTerm.query(term=t, prefix=prefix))
        except StopIteration:
            return None

    def term_source(t, test):
        tl = t.lower()
        if tl == test.label:
            return 'label'
        elif tl in test.synonyms:
            return 'synonym'
        else:
            return 'WAT'

    ot = gn(label)
    if ot is not None:
        source = term_source(label, ot)
        t = subject, oboInOwl.hasDbXref, ot.URIRef
        pairs = (ilxtr.termMatchType, rdflib.Literal(source)),
        yield t
        yield from cmb.annotations(pairs, *t)


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
        region=ilxtr.isDefinedInRegion,  # FIXME isAbout? For vs In?
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
        species=owl.someValuesFrom,  # FIXME really for all rats? check if reasoner makes r6 and r4 the same, see if they are disjoint
        devstage=owl.someValuesFrom,  # protege says only but fact, and hermit which manage disjointness don't complain...
        definingArtifacts=owl.someValuesFrom,  # TODO we do need the closure axioms
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

        self.validate()

    def validate(self):
        """ Put checks here. They will save you. """
        if hasattr(self, 'iri'):
            assert self.iri != self.parentClass, f'{self} iri and subClassOf match! {self.iri}'
        else:
            pass  # TODO do we the class_label?

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
                restriction = cmb.Restriction(rdfs.subClassOf, scope=self.lift[key])
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
    iri_prefix_working_dir = 'https://github.com/tgbugs/pyontutils/blob/{file_commit}/'
    iri_prefix_wdf = iri_prefix_working_dir + 'pyontutils/'
    iri_prefix_hd = f'https://github.com/tgbugs/pyontutils/blob/master/pyontutils/'
    iri = None
    source = None
    sourceFile = None
    # source_original = None  # FIXME this should probably be defined on the artifact not the source?
    artifact = None

    def __new__(cls, dry_run=False):
        from git import Repo
        if not hasattr(cls, '_data'):
            if hasattr(cls, 'runonce'):  # must come first since it can modify how cls.source is defined
                cls.runonce()

            if isinstance(cls.source, str) and cls.source.startswith('http'):
                if cls.source.endswith('.git'):
                    cls._type = 'git-remote'
                    cls.sourceRepo = cls.source
                    # TODO look for local, if not fetch, pull latest, get head commit
                    glb = aug.RepoPath(auth.get_path('git-local-base'))
                    cls.repo_path = glb.clone_path(cls.sourceRepo)
                    print(cls.repo_path)
                    # TODO branch and commit as usual
                    if not cls.repo_path.exists():
                        cls.repo = cls.repo_path.init(cls.sourceRepo)
                    else:
                        cls.repo = cls.repo_path.repo
                        # cls.repo.remote().pull()  # XXX remove after testing finishes

                    if cls.sourceFile is not None:
                        file = cls.repo_path / cls.sourceFile
                        if not dry_run:  # dry_run means data may not be present
                            file_commit = cls.repo_path.latest_commit.hexsha
                            #file_commit = next(cls.repo.iter_commits(paths=file.as_posix(), max_count=1)).hexsha
                            commit_path = os.path.join('blob', file_commit, cls.sourceFile)
                            print(commit_path)
                            if 'github' in cls.source:
                                cls.iri_prefix = cls.source.rstrip('.git') + '/'
                            else:
                                # using github syntax for now since it is possible to convert out
                                cls.iri_prefix = cls.source + '::'
                            cls.iri = rdflib.URIRef(cls.iri_prefix + commit_path)

                        cls.source = file
                    else:
                        # assume the user knows what they are doing
                        #raise ValueError(f'No sourceFile specified for {cls}')
                        cls.iri = rdflib.URIRef(cls.source)
                        pass
                else:
                    cls._type = 'iri'
                    cls.iri = rdflib.URIRef(cls.source)

            elif os.path.exists(cls.source):  # TODO no expanded stuff
                cls.source = aug.RepoPath(cls.source)
                try:
                    cls.source.repo
                    file_commit = cls.source.latest_commit
                    if file_commit is not None:
                        cls.iri = rdflib.URIRef(cls.iri_prefix_wdf.format(file_commit=file_commit)
                                                + cls.source.repo_relative_path.as_posix())
                        cls._type = 'git-local'
                    else:
                        raise aug.exceptions.NotInRepoError('oops no commit?')
                except aug.exceptions.NotInRepoError:
                    cls._type = 'local'
                    if not hasattr(cls, 'iri'):
                        cls.iri = rdflib.URIRef(cls.source.as_uri())
                    #else:
                        #print(cls, 'already has an iri', cls.iri)
                else:
                    raise BaseException('I can\'t believe you\'ve done this.')

            else:
                cls._type = None
                log.warning('Unknown source {cls.source}')

            cls.raw = cls.loadData()
            cls._data = cls.validate(*cls.processData())
            cls._triples_for_ontology = []
            if not dry_run:
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
                object = rdflib.URIRef(cls.iri_prefix_hd + cls.source.as_posix())
            else:
                object = rdflib.URIRef(cls.source.as_posix())
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
    local_base = auth.get_path('ontology-local-repo')
    remote_base = 'http://ontology.neuinfo.org/NIF/'
    path = 'ttl/generated/'  # sane default
    filename = None
    name = None
    shortname = None
    comment = None  # about how the file was generated, nothing about what it contains
    version = TODAY()
    start_time = UTCNOWISO(timespec='seconds')
    namespace = None
    prefixes = makePrefixes('NIFRID', 'ilxtr', 'prov', 'dc', 'dcterms')
    imports = tuple()
    source_file = None  # override for cases where __class__ is used internally
    wasGeneratedBy = ('https://github.com/tgbugs/pyontutils/blob/'  # TODO predicate ordering
                      '{commit}/'  # FIXME prefer {filepath} to assuming pyontutils...
                      '{filepath}'
                      '{hash_L_line}')

    propertyMapping = dict(
        wasDerivedFrom=prov.wasDerivedFrom,  # the direct source file(s)  FIXME semantics have changed
        wasGeneratedBy=prov.wasGeneratedBy,  # FIXME technically wgb range is Activity
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

    @property
    def working_dir(self):
        return (aug.RepoPath(getsourcefile(self.__class__))
                .resolve()
                .resolve())

    def __init__(self, *args, **kwargs):
        if 'comment' not in kwargs and self.comment is None and self.__doc__:
            self.comment = ' '.join(_.strip() for _ in self.__doc__.split('\n'))

        working_dir = self.working_dir

        if hasattr(self, '_repo') and not self._repo or working_dir is None:
            commit = 'FAKE-COMMIT'
        else:
            try:
                repo = working_dir.repo
                commit = next(repo.iter_commits()).hexsha
            except aug.exceptions.NotInRepoError:
                commit = 'FAKE-COMMIT'

        try:
            if self.source_file:
                filepath = self.source_file
                line = ''
            else:
                line = '#L' + str(getSourceLine(self.__class__))
                _file = getsourcefile(self.__class__)
                file = Path(_file)
                file = file.resolve().resolve()
                filepath = file.relative_to(working_dir).as_posix()
        except TypeError:  # emacs is silly
            line = '#Lnoline'
            _file = 'nofile'
            filepath = Path(_file).name

        self.wasGeneratedBy = self.wasGeneratedBy.format(commit=commit,
                                                         hash_L_line=line,
                                                         filepath=filepath)
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
            breakpoint()

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

    @classmethod
    def setup(cls):
        cls.prepare()
        o = cls()
        return o

    def make(self, fail=False, write=True):
        self()
        self.validate()
        failed = standard_checks(self.graph)
        self.failed = failed
        if fail:
            raise BaseException('Ontology validation failed!')
        if write:
            self.write()
        return self

    def validate(self):
        # implement per class
        return self

    @property
    def iri(self):
        return self.graph.boundIdentifier

    @property
    def versionIRI(self):
        return self.graph.versionIdentifier

    def write(self, cull=False):
        # TODO warn in ttl file when run when __file__ has not been committed
        self._graph.write(cull=cull)


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
            yield from cmb.flattenTriples(triples)

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
                 temp_path=tempfile.tempdir,
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
     for t in cmb.flattenTriples((oc(owl.Thing),
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
