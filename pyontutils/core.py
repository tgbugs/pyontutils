import io
import os
import re
import json
import yaml
import types
import gzip
import zipfile
import tempfile
import mimetypes
import subprocess
import idlib
import rdflib
from inspect import getsourcefile
from pathlib import Path, PurePath
from itertools import chain
from collections import namedtuple
from urllib.parse import urlparse
import ontquery as oq
import augpathlib as aug
import htmlfn as hfn
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
                                   oboInOwl,
                                   replacedBy,)
from pyontutils.identity_bnode import IdentityBNode

current_file = Path(__file__).absolute()
oq.utils.log.removeHandler(oq.utils.log.handlers[0])
oq.utils.log.addHandler(log.handlers[0])

# common funcs

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
    from joblib import Parallel, delayed  # importing in here saves 150ms
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


def populateFromJsonLd(graph, path_or_blob, pyld=False):
    from pyld import jsonld
    def convert_element(blob,
                        _lu={'literal': rdflib.Literal,
                             'IRI': rdflib.URIRef,
                             'blank node': rdflib.BNode,}):
        kwargs = {}
        if 'datatype' in blob:
            kwargs['datatype'] = blob['datatype']
        elif 'language' in blob:
            kwargs['lang'] = blob['language']

        return _lu[blob['type']](blob['value'], **kwargs)

    fd = None
    try:
        if isinstance(path_or_blob, dict):
            # FIXME this whole branch is so dumb
            close_it = True
            j = path_or_blob
            fd, _path = tempfile.mkstemp()
            path = Path(_path)
            with open(path, 'wt') as f:
                json.dump(j, f)
        else:
            path = path_or_blob
            with open(path, 'rt') as f:
                j = json.load(f)

        if pyld:
            blob = jsonld.to_rdf(j)  # XXX this seems completely broken ???

        def triples():
            for graph_id, dts in blob.items():
                # includes all triples including @default but ignores context
                for dt in dts:
                    yield tuple(convert_element(e) for e in
                                (dt['subject'], dt['predicate'], dt['object']))

        if '@context' in j:
            inctx = j['@context']
        else:
            inctx = {}
        proc = jsonld.JsonLdProcessor()
        ctx = proc.process_context(proc._get_initial_context({}), inctx, {})

        # FIXME how to deal with non prefixed cases like definition
        curies = {k:v['@id'] for k, v in ctx['mappings'].items() if
                  v['_prefix']}
        graph.namespace_manager.populate_from(curies)
        if pyld:
            graph.populate_from_triples(triples())  # pyld broken above
        else:
            graph.parse(path, format='json-ld')
    finally:
        if fd is not None:
            os.close(fd)
            path.unlink()

    return graph


# ontology resource object
from .iterio import IterIO


class OntRes(idlib.Stream):
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

    _imports_class = None  # XXX assigned after OntResIri is defined

    @staticmethod
    def fromStr(string):
        if re.match(r'^(https?)://', string):
            return OntResIri(string)
        else:
            file_uri = re.match(r'^file://(.+)$', string)
            if file_uri:
                path_string = file_uri.group(1)
            else:
                path_string = string

            # TODO other OntResGit identifier options
            rp = aug.RepoPath(path_string)
            if rp.working_dir:
                return OntResGit(rp)
            else:
                return OntResPath(path_string)

    def __init__(self, identifier, repo=None, Graph=None):  # XXX DO NOT USE THIS IT IS BROKEN
        self.identifier = identifier  # the potential attribute error here is intentional
        self.repo = repo  # I have a repo augmented path in my thesis stats code
        if Graph == None:
            Graph = OntGraph

        self.Graph = Graph

    def _import_funowl(self):
        # SIGH python import times for rarely used functionality ...
        if not hasattr(self, '_parse_funowl'):
            try:
                from funowl.converters.functional_converter import to_python as parse_funowl
            except ImportError as e:
                def parse_funowl(*args, __error=e, **kwargs):
                    msg = f'funowl needs >= python3.8'
                    raise ModuleNotFoundError(msg) from __error

            self._parse_funowl = parse_funowl

    def _populate(self, graph, gen):
        raise NotImplementedError('too many differences between header/data and xml/all the rest')

    def populate(self, graph):
        # TODO if self.header ...
        self._populate(graph, self.data)

    #@oq.utils.mimicArgs(data_next)  # TODO
    def populate_next(self, graph, *args, **kwargs):
        gen = self.data_next(**kwargs)
        self._populate(graph, gen)

    @property
    def graph(self, cypher=None):
        return self.graph_next()

    #@oq.utils.mimicArgs(data_next)  # TODO
    def graph_next(self, **kwargs):
        # FIXME this is a successor stream

        # FIXME transitions to other streams should be functions
        # and it also allows passing an explicit cypher argument
        # to enable checksumming in one pass, however this will
        # require one more wrapper
        if not hasattr(self, '_graph'):
            gkwargs = {}
            if hasattr(self, 'path'):
                gkwargs['path'] = self.path

            self._graph = self.Graph(**gkwargs)
            try:
                self.populate_next(self._graph, **kwargs)
            except BaseException as e:
                self._graph = None
                del self._graph
                raise e

        return self._graph

    @property
    def identifier_bound(self):
        try:
            return next(self.graph[:rdf.type:owl.Ontology])
        except StopIteration:
            # TODO maybe warn?
            pass

    @property
    def identifier_version(self):
        """ implicitly identifier_bound_version since we won't maniuplate a
            version iri supplied as the identifi
            the id to get
        """
        try:
            return next(self.graph[self.identifier_bound:owl.versionIRI])
        except StopIteration:
            # TODO maybe warn?
            pass

    @property
    def imports(self):
        for object in self.graph[self.identifier_bound:owl.imports]:
            # TODO switch this for _res_remote_class to abstract beyond just owl
            yield self._imports_class(object)  # this is ok since files will be file:///

    @property
    def import_chain(self):
        yield from self._process_import_chain(
            {self.identifier_bound}, 'imports')

    def _process_import_chain(self, done, imps_attr='imports'):
        # FIXME this has to split local and remote because
        # we need to share done, but we can't share out_cls nor imps_attr
        if not hasattr(self, imps_attr):
            # failover when imports_local hits a non-local import
            # FIXME beware local -> remote -> local issues
            imps_attr = 'imports'

        imps = list(getattr(self, imps_attr))

        def internal(r):
            try:
                log.debug(f'fetching graph for {r}')
                (r.metadata().graph
                 if hasattr(r, '_metadata_class')
                 else r.graph)
            except Exception as e:
                msg = (f'something failed for {r} '
                       f'imported by {self.identifier_bound}')
                raise Exception(msg) from e

        Async()(deferred(internal)(_) for _ in imps)

        for resource in imps:
            _idb = resource.identifier_bound
            rid = _idb if _idb is not None else resource.identifier
            if rid in done:
                continue

            yield resource
            done.add(rid)
            yield from resource._process_import_chain(done, imps_attr)

    def import_closure_graph(
            self, local=False,
            import_ontology_type=ilxtr.Ontology,
            import_ontology_predicate=ilxtr.imports):
        # TODO abstract for local ic case
        if not hasattr(self, '_ic_graph'):
            ic_res = list(self.import_chain)
            all_res = [self] + ic_res  # TODO consider retaining in debug case
            merged = self.Graph()
            _ = [merged.namespace_manager.populate_from(ontres.metadata().graph) for ontres in all_res]
            # swap owl:imports for ilxtr:imports to avoid double import in merged file but still allow tracing the chain
            _ = [merged.add(t)
                 if t[1] != owl.imports
                 else merged.add((t[0], import_ontology_predicate, t[2]))
                 for t in self.graph.metadata()]
            # ensure that there is only a single top level owl:Ontology but retain imported metadata sections
            # also have to swap the owl:imports for ilxtr:imports in this case as well because owlapi will
            # type pun and infer types super hard and thus pull in all the transitive chain >_<
            _ = [(merged.add(t)
                  if t[1] != owl.imports
                  else merged.add((t[0], import_ontology_predicate, t[2])))
                 if t[2] != owl.Ontology
                 else merged.add((t[0], t[1], import_ontology_type))
                 for ontres in ic_res for t in ontres.graph.metadata()]
            _ = [merged.add(t) for ontres in all_res for t in ontres.graph.data]
            self._ic_graph = merged

        return self._ic_graph

    def __eq__(self, other):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError

    def __repr__(self):
        return self.__class__.__name__ + f'({self.identifier!r})'


class OntMeta(OntRes):
    """ only the header of an ontology, e.g. the owl:Ontology section for OWL2 """

    _imports_class = None  # XXX assigned after OntMetaIri is defined

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
            graph.parse(data=data, format=self.format)

        elif self.format == 'text/owl-functional':
            self._import_funowl()
            # FIXME funowl could work with iterio I think?
            data = b''.join(gen)
            fo = self._parse_funowl(data)
            fo.to_rdf(graph)

        else:
            itio = IterIO(gen)
            itio.name = self.identifier  # some rdflib parses need a name
            graph.parse(source=itio, format=self.format)

    def _populate_next(self, graph, *args, yield_response_gen=False, **kwargs):
        """ Use when you want to populate a graph with the header
            and then populate another graph with everything, will probably
            become useful when we get conjuctive graph working as expected """

        if yield_response_gen:
            kwargs['yield_response_gen'] = yield_response_gen
            format, *header_chunks, (resp, gen) = self.data_next(**kwargs)
            self._populate(graph, header_chunks)
            yield format
            yield from header_chunks
            yield resp, gen
        else:
            generator = self.data_next(**kwargs)
            format = next(generator)
            self._populate(graph, generator)

    def populate_next(self, graph, *args, **kwargs):
        if 'yield_response_gen' in kwargs:
            raise TypeError('if you need yield_response_gen use _populate_next')

        generator = self._populate_next(graph, *args, **kwargs)
        list(generator)  # express the generator without causing a StopIteration

    def __lt__(self, other):
        # FIXME this is ... complicated and currently incorrectly/incomplete/confusing
        # FIXME this is also super confusing beause it sorts on the invisible id bound
        # instead of on identifier
        sib = self.identifier_bound
        oib = other.identifier_bound
        if sib and oib:
            return sib < oib

        # compare only matched id types
        si = self.identifier
        oi = other.identifier
        if si and oi:
            return si < oi

        return False

    def __eq__(self, other):
        # FIXME this is ... complicated and currently incorrectly/incomplete/confusing
        # the current behavior results in cases where you can have two files with
        # different local names but that have the same bound id and they will be
        # considered to be "equal" which is ... not helpful, and possibly confusing
        # because there are so many ways you could compare these
        sib = self.identifier_bound
        oib = other.identifier_bound
        if sib and oib:
            return sib == oib

        # compare only matched id types
        si = self.identifier
        oi = other.identifier
        if si and oi:
            return si == oi

        return False

    def __hash__(self):
        # use identity bnode for these, the metadata is small enough
        idbn = self.graph.identity()
        return hash((self.__class__, idbn))


class OntResOnt(OntRes):
    """ full ontology files """

    _metadata_class = None  # FIXME can we do this by dispatching OntMeta like Path?

    def __eq__(self, other):
        return self.metadata().identifier_bound == other.metadata().identifier_bound

    def __hash__(self):
        # assumes that people are good citizens and change their
        # metadata when they change the data section
        return hash((self.__class__, self.metadata()))


class OntIdIri(OntRes):
    def __init__(self, iri):
        self.iri = iri
        # TODO version iris etc.

    def _get(self, *, send_data=None, send_successor={'Accept': 'text/turtle'}):
        if self.iri.startswith('file://'):  # requests transport adapters seem overly complex?
            parsed = urlparse(self.iri)
            return OntIdPath(parsed.path)._get()
        else:
            if send_data is None:
                return self._requests.get(self.iri, stream=True, headers=send_successor)  # worth a shot ...
            else:
                return self._requests.post(self.iri, stream=True,
                                    headers=send_successor,
                                    data=send_data)

    @property
    def identifier(self):
        return self.iri

    @property
    def headers(self):  # FIXME vs get vs post
        """ request headers """
        if not hasattr(self, '_headers'):
            resp = self._requests.head(self.identifier)  # TODO status handling for all these
            self._headers = resp.headers

        return self._headers

    @headers.setter
    def headers(self, value):
        self._headers = value


class OntMetaIri(OntMeta, OntIdIri):

    @property
    def data(self):  # FIXME design flaw
                     # .data() should always be a function to allow post style communication
        gen = self._data()
        format = next(gen)  # advance to set self.format in _data
        return gen

    def _data(self, yield_response_gen=False):
        yield from self.data_next(yield_response_gen=yield_response_gen)

    def _process_resp_zip(self, resp, file):
        # FIXME since the resp is already closed here
        # need to prevent double close issuse below
        self._progenitors['stream-http-response'] = resp
        self.headers = resp.headers  # XXX I think this is right ?
        # FIXME obvious issue here is if the content length is the
        # same but the checksum differs, e.g. due to single char fixes
        # though for zipped content that seems unlikely given all the
        # metadata that a zipfile embeds
        # some sources do provide an etag might help?
        if 'Content-Length' in resp.headers:  # WHY U DO DIS!??!!
            content_length = int(resp.headers['Content-Length'])
        else:
            # apparently the chebi server doesn't returen content length on some requests !?
            content_length = object()

        if not file.exists() or file.size != content_length:
            file.data = resp.iter_content(chunk_size=file.chunksize)

    def data_next(self, *, send_type=None, send_head=None, send_meta=None, send_data=None,
                  conventions_type=None,  # expect header detection conventions
                  # FIXME probably all we need are
                  # the inversion of the streams
                  # data meta local_conventions stuff_successor_stream_needs
                  # or something like that
                  yield_response_gen=False):

        # reset progenitors each call to prevent stale state
        # it is ok to fail halfway through and not restore
        # the whole point of progenitors is to give you access
        # to the exact state that failed so you can debug
        self._progenitors = {}

        _gz = self.identifier.endswith('.gz')
        _zip = self.identifier.endswith('.zip')
        if _zip or _gz:
            id_hash = IdentityBNode(self.identifier).identity.hex()
            cache_root = idlib.config.auth.get_path('cache-path') / 'streams'
            cache_dir = cache_root / id_hash[:2]
            cache_dir.mkdir(exist_ok=True, parents=True)
            file = aug.LocalPath(cache_dir / id_hash)
            with self._get(send_data=send_data) as resp:
                self._process_resp_zip(resp, file)

            self._progenitors['path'] = file

            if _gz:
                # check also Etag and Last-Modified
                # but will need to use xattrs to store
                raise NotImplementedError('TODO')
            elif _zip:
                zp = aug.ZipPath(file)
                # TODO so many progenitors
                id_path = PurePath(self.identifier)
                id_stem = id_path.stem
                matching_members = [
                    z for z in zp.rchildren if not z.is_dir() and z.stem == id_stem
                ]

                if len(matching_members) != 1:
                    # TODO
                    raise ValueError(matching_members)

                member = matching_members[0]
                self._progenitors['path-compressed'] = member  # ok to include a tuple here I think ...
                filelike = member.open()
                self._progenitors['stream-file'] = filelike  # NOTE reproductible progenitors only
                # unfortunately the ZipInfo objects don't hold a pointer back to the ZipFile
                def filelike_to_generator(filelike, chunksize=file.chunksize):
                    """ NOTE: closes at the end """
                    with filelike:  # will close at the end
                        while True:
                            try:
                                data = filelike.read(chunksize)  # TODO hinting
                            except AttributeError as e:
                                raise ValueError('I/O operation on closed zip stream') from e

                            if not data:
                                break

                            yield data

                # FIXME the rdf+xml won't work on a generator
                # it would be nice to be able to return/work directly from
                # the filelike instead of from the generator in cases where
                # it really is a file like instead of the resp.iter_content
                # case that we deal with here
                gen = filelike_to_generator(filelike)
                self._progenitors['stream-generator'] = gen  # NOTE reproducible progenitors only

            else:
                raise BaseException('WHAT HATH THOU PROSECUTED SIR!?')

        else:
            resp = self._get(send_data=send_data)
            self._progenitors['stream-http-response'] = resp
            self.headers = resp.headers
            # TODO consider yielding headers here as well?
            filelike = None
            gen = resp.iter_content(chunk_size=4096)

        yield from self._data_from_generator(
            resp,
            filelike,
            gen,
            conventions_type,
            yield_response_gen,
        )

    def _data_from_generator(self,
                             resp,
                             filelike,
                             gen,
                             conventions_type,
                             yield_response_gen,
                             ):
        if not resp.ok:
            resp.raise_for_status()

        first = next(gen)
        # TODO better type detection

        if conventions_type is not None:
            # in the case where the type is known/assumed in advance
            # failure to match conventions is a good thing because
            # it signals that something unexpected has happened
            self.format = conventions_type.format
            start = conventions_type.start
            stop = conventions_type.stop
            sentinel = conventions_type.sentinel
            # FIXME TODO another way around this would be to use
            # local conventions in a _standard_ way to allow multiple
            # different values to have the same _surface_ representation
            # making it easier to parse ... HRM this seems like it might
            # be a more robust approach ... though annoying for the greppers

        elif first.startswith(b'<?xml'):  # FIXME owl xml
            # FIXME overlapping start and end patterns
            start = b'<owl:Ontology'
            stop = b'</owl:Ontology>|<owl:Ontology rdf:about=".+"/>'
            #stop = b'</owl:Ontology>'  # use with uberon-bridge-to-nifstd.owl to test sent before stop
            sentinel = b'<!--|<owl:Class'
            self.format = 'application/rdf+xml'

        elif first.startswith(b'@prefix') or first.startswith(b'#lang rdf/turtle'):
            start = b' owl:Ontology'  # FIXME this is not standard
            # FIXME snchn.IndexGraph etc ... need a more extensible way to mark the header ...
            stop = b'\ \.\n'  # FIXME can be fooled by strings
            sentinel = b'^###\ '  # FIXME only works for ttlser
            #sentinel = b' a '  # FIXME if a |owl:Ontology has a chunk break on | this is incorrect
            # also needs to be a regex that ends in [^owl:Ontology]
            self.format = 'text/turtle'

        elif first.startswith(b'Prefix(:='):
            # FIXME regex will likely cause issues here
            start = b'\nOntology\('
            stop = b'\n[^OA]'  # XXX owl functional syntax actually has a proper header :/
            # so for now we use a hueristic matching the first line that doesn't start with Annotation?
            sentinel = b'\n#'
            self.format = 'text/owl-functional'
        else:
            'text/owl-manchester'
            raise ValueError(first.decode())

        if conventions_type is None:
            conventions_type = idlib.conventions.type.ConvTypeBytesHeader(format, start, stop, sentinel)

        yield self.format  # we do this because self.format needs to be accessible before loading the graph

        close_rdf = b'\n</rdf:RDF>\n'
        close_fun = b'\n)'
        searching = False
        header_data = b''
        for chunk in chain((first,), gen):
            if not searching:
                start_start_index, start_end_index = conventions_type.findStart(chunk)
                if start_start_index is not None:
                    searching = True
                    # yield content prior to start since it may include a stop
                    # that we don't actually want to stop at
                    header_first_chunk = chunk[:start_start_index]
                    if yield_response_gen:
                        header_data += header_first_chunk

                    yield header_first_chunk
                    chunk = chunk[start_start_index:]

            if searching: #and stop in chunk:  # or test_chunk_ends_with_start_of_stop(stop, chunk)
                stop_start_index, stop_end_index = conventions_type.findStop(chunk)
                # FIXME need to handle the case where we hit the sentinel before we hit stop
                if stop_end_index is not None:
                    # FIXME edge case where a stop crosses a chunk boundary
                    # if stop is short enough it may make sense to do a naieve contains check
                    # to start things off ...

                    #stop_end_index = chunk.index(stop) + len(stop)
                    header_last_chunk = chunk[:stop_end_index]
                    if yield_response_gen:
                        header_data += header_last_chunk

                    yield header_last_chunk
                    if yield_response_gen:
                        if self.format == 'application/rdf+xml':
                            header_data += close_rdf
                        elif self.format == 'text/owl-functional':
                            header_data += close_fun

                        self._graph_sideload(header_data)
                        chunk = chunk[stop_end_index:]
                        yield resp, chain((chunk,), gen)

                    else:
                        # if we are not continuing then close the xml tags
                        if self.format == 'application/rdf+xml':
                            yield close_rdf
                        elif self.format == 'text/owl-functional':
                            yield close_fun

                        resp.close()
                        if filelike is not None:
                            filelike.close()

                    return

                else:  # I LOVE CODE DUPLICATION DON'T YOU?
                    # FIXME TODO need a sentinel value where there isn't a header
                    # so that we can infer that there is no header, or at least
                    # no headerish data at the head of the file
                    if yield_response_gen:
                        header_data += chunk

                    yield chunk

            # FIXME sentinel could be in the same chunk as stop
            else:  # and this is why you need the walrus operator :/ but then no < 3.8 >_<
                sent_start_index, sent_end_index = conventions_type.findSentinel(chunk)
                if sent_start_index is not None:
                    #sent_end_index = chunk.index(sentinel) + len(sentinel)
                    header_last_chunk = chunk[:sent_start_index]
                    if yield_response_gen:
                        header_data += header_last_chunk

                    yield header_last_chunk
                    if yield_response_gen:
                        if self.format == 'application/rdf+xml':
                            header_data += close_rdf
                        elif self.format == 'text/owl-functional':
                            header_data += close_fun

                        self._graph_sideload(header_data)
                        chunk = chunk[sent_start_index:]
                        yield resp, chain((chunk,), gen)

                    else:
                        # if we are not continuing then close the xml tags
                        if self.format == 'application/rdf+xml':
                            yield close_rdf
                        elif self.format == 'text/owl-functional':
                            yield close_fun

                        resp.close()
                        if filelike is not None:
                            filelike.close()

                    return

                else:  # I LOVE CODE DUPLICATION DON'T YOU?
                    # FIXME TODO need a sentinel value where there isn't a header
                    # so that we can infer that there is no header, or at least
                    # no headerish data at the head of the file
                    if yield_response_gen:
                        header_data += chunk

                    # we yield here because pre-header chunks count as header chunks
                    # this is because any information prior to the header stop pattern
                    # is either header or local conventions that will be needed to
                    # parse the header stream ... and thus count as 'header chunks'
                    yield chunk

        else:
            # the case where there is no header so we don't return inside the loop
            log.warning('missed sentinel')
            if yield_response_gen:
                yield resp, gen
            else:
                resp.close()
                if filelike is not None:
                    filelike.close()

            return


OntMeta._imports_class = OntMetaIri


class OntResIri(OntIdIri, OntResOnt):

    _metadata_class = OntMetaIri

    def _data_next(self, *, send_type=None, send_head=None, send_meta=None, send_data=None):
        raise NotImplementedError('this is a template')

    @oq.utils.mimicArgs(_data_next)
    def data_next(self, *args, **kwargs):
        """ an alternate implementation of data """
        # there is this nasty tradeoff where if you implement this in this way
        # where data can take arguments, then _any_ downstream artifact that you
        # want also has to take those arguments as well, clearly undesireable
        # in cases where you would like to be able to do the transformation
        # without having to haul a bunch of stuff around with you
        # what this means is that either you have to accept a set of defaults that
        # are sane and will get you what you want, you identifier is incomplete and
        # thus you add arguments to your function to flesh it out, or
        # you have to drop down a level, configure your argument ahead of time
        # and then make the request again with slightly differen types

        # allowing the underlying abstraction to bubble up into optional kwarsg
        # frankly seems like a pretty good option, if it werent for the fact that
        # it is an absolute pain to maintain in the absense of mimicArgs
        # I feel like cl generics could make this much easier ...

        # OR OR OR the graph is successor stream of the actual instantiation of this stream
        # which means that ... the extra args would go in at init time??? no
        # that doesn't seem like the right tradeoff, any successor streams
        # basically have to present kwargs for any variables that cannot be
        # set to a sane default within the scope of the identifier system (sigh)
        # or at least in cases where it hasn't been demostrated that the variables
        # are simply a matter of representaiton, not differences in information
        # (i.e. that there isn't a function that can 1:1 interconvert)

        generator = self.metadata().data_next(yield_response_gen=True, **kwargs)
        format, *header_chunks, (resp, gen) = generator
        self.headers = resp.headers
        self.format = format
        # TODO populate header graph? not sure this is actually possible
        # maybe need to double wrap so that the header chunks always get
        # consumbed by the header object ?
        if self.format == 'application/rdf+xml':
            resp.close()
            return None

        return chain(header_chunks, gen)

    @property
    def data(self):
        format, *header_chunks, (resp, gen) = self.metadata()._data(yield_response_gen=True)
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
            self._import_funowl()
            data = b''.join(gen)
            fo = self._parse_funowl(data)
            fo.to_rdf(graph)

        else:
            itio = IterIO(gen)
            itio.name = self.identifier
            graph.parse(source=itio, format=self.format)


OntRes._imports_class = OntResIri


class OntIdPath(OntRes):

    # FIXME should this be an instrumented path?
    # should OntResIri be an instrumented iri?
    def __init__(self, path):
        # FIXME type caste?
        if not isinstance(path, Path):
            path = aug.AugmentedPath(path)

        self.path = path

    @property
    def identifier(self):
        return self.path.as_posix()

    def _get(self, *args, **kwargs):  # some functions that go back the other way can't use more info
        resp = self._requests.Response()
        with open(self.path, 'rb') as f:
            resp.raw = io.BytesIO(f.read())  # FIXME streaming file read should be possible ...

        # TODO set headers here
        #resp.headers = {'Content-Length': self.path.meta_no_checksum.size}
        resp.status_code = 200
        return resp

    headers = OntIdIri.headers

    def imports_catalog(self):
        raise NotImplementedError('TODO')

    @property
    def imports_local(self):
        url = urlparse(self.identifier_bound)
        url_path = Path(url.path)
        path = self.path.resolve()
        matched = [part for upart, part in
                   zip(reversed(url_path.parts), reversed(path.parts))
                   if upart == part]
        lm = len(matched)
        remote_base = Path(*url_path.parts[:-lm])
        local_base = Path(*path.parts[:-lm])
        remote_prefix = url._replace(path=remote_base.as_posix()).geturl()
        local_prefix = local_base.as_posix()
        replace = remote_prefix, local_prefix
        for ori in self.imports:
            id = str(ori.identifier)
            lp = id.replace(*replace)
            if id == lp:
                # no obvious local path, TODO use the catalog
                yield ori
            else:
                yield self.__class__(Path(lp))

    @property
    def import_chain_local(self):
        yield from self._process_import_chain({self.identifier_bound}, 'imports_local')


class OntMetaPath(OntIdPath, OntMeta):
    data = OntMetaIri.data
    _data = OntMetaIri._data
    _data_from_generator = OntMetaIri._data_from_generator

    def data_next(self, *, send_type=None, send_head=None, send_meta=None,
                  send_data=None, conventions_type=None, yield_response_gen=False):
        self._progenitors = {}
        self._progenitors['path'] = self.path
        resp = self._get()
        filelike = None
        gen = resp.iter_content(chunk_size=4096)
        yield from self._data_from_generator(
            resp,
            filelike,
            gen,
            conventions_type,
            yield_response_gen,
        )


class OntResPath(OntIdPath, OntResOnt):
    """ ontology resource coming from a file """

    _metadata_class = OntMetaPath
    data = OntResIri.data
    data_next = OntResIri.data_next

    _populate = OntResIri._populate  # FIXME application/rdf+xml is a mess ... cant parse streams :/


class OntIdGit(OntIdPath):

    def __init__(self, path, ref='HEAD'):
        """ ref can be HEAD, branch, commit hash, etc.

            if ref = None, the working copy of the file is used
            if ref = '',   the index   copy of the file is used """

        if not isinstance(path, aug.RepoPath):
            path = aug.RepoPath(path)

        self.path = path
        self.ref = ref

    @classmethod
    def fromRepoAndId(cls, repo_path, id):
        ref, rel_path = id.split(':', 1)  # FIXME ref handling
        path = repo_path / rel_path

        return cls(path, ref)

    def asDeRef(self):
        """ return the dereferenced form of this resource """
        return self.__class__(self.path, self.path.latest_commit(self.ref))

    @property
    def identifier(self):
        # FIXME this doesn't quite conform because it is a local identifier
        # which neglects the repo portion of the id ...
        if type(self.path) == str:
            breakpoint()

        if self.ref is None:
            return self.path.as_posix()

        return str(self.ref) + ':' + self.path.repo_relative_path.as_posix()

    @property
    def repo(self):
        return self.path.repo

    def metadata(self):
        if not hasattr(self, '_metadata'):
            self._metadata = self._metadata_class(self.path, ref=self.ref)

        return self._metadata

    def _get(self, *args, **kwargs):  # TODO mimicArgs
        resp = self._requests.Response()
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
    data_next = OntMetaIri.data_next
    _data_from_generator = OntMetaIri._data_from_generator


class OntResGit(OntIdGit, OntResOnt):
    _metadata_class = OntMetaGit
    data = OntResIri.data
    data_next = OntResIri.data_next

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


class Edge(tuple):
    """ Expansion of curies must happen before construction if it is going to
        happen at all. The expansion rule must be known beforehand. """

    @classmethod
    def fromNx(cls, edge, namespace_manager=None):
        s, o, p = [e.toPython() if isinstance(e, rdflib.URIRef) else e
                   for e in edge]  # FIXME need to curie here or elsewhere?

        t = (s, p, o)
        if namespace_manager is not None:  # FIXME I think we store the string format natively here? or no? what do we do ...
            t = [namespace_manager.expand(e) for e in t]  # FIXME sigh OntId OntCuries etc etc local conventions etc ...

        self = cls(t)
        if namespace_manager is not None:
            self._namespace_manager = namespace_manager

        return self

    @classmethod
    def fromOboGraph(cls, blob, namespace_manager=None):
        t = blob['sub'], blob['pred'], blob['obj']
        if namespace_manager is not None:  # FIXME I think we store the string format natively here? or no? what do we do ...
            t = [namespace_manager.expand(e) for e in t]  # FIXME sigh OntId OntCuries etc etc local conventions etc ...

        self = cls(t)
        self._blob = blob
        if namespace_manager is not None:
            self._namespace_manager = namespace_manager

        return self

    @property
    def s(self): return self[0]
    @property
    def p(self): return self[1]
    @property
    def o(self): return self[2]
    subject = s
    predicate = p
    object = o

    def asTuple(self):
        return (*self,)
        #return self.s, self.p, self.o

    def asRdf(self):
        """ Note that no expansion may be done at this time. """
        t = tuple(e if isinstance(e, rdflib.URIRef) else rdflib.URIRef(e) for e in self)
        return t

    def asOboGraph(self, namespace_manager=None):
        """ namespace manager here is provided only for compaction """

        nm = namespace_manager
        if nm is None and hasattr(self, '_namespace_manager'):
            nm = self._namespace_manager

        if namespace_manager is not None:
            return {k:e for k, e in zip(('sub', 'pred', 'obj'),
                                        [nm._qhrm(e) for e in self])}

        elif not hasattr(self, '_blob'):
            self._blob = {k:e for k, e in
                          zip(('sub', 'pred', 'obj'),
                              [nm._qhrm(e) for e in self]
                              if nm is not None else
                              self)}

        return self._blob


class BetterNamespaceManager(rdflib.namespace.NamespaceManager):

    def __init__(self, *args, bind_namespaces='core', **kwargs):
        try:
            super().__init__(*args, bind_namespaces=bind_namespaces, **kwargs)
        except TypeError as e:
            super().__init__(*args, **kwargs)

    def __call__(self, **kwargs):
        """ set prefixes """
        raise NotImplementedError

    def __iter__(self):
        yield from self.namespaces()

    def expand(self, curie):
        # I'm still not sure that this is the right way to do it
        # but there are SO many cases where we need this that
        # can't use OntId as a drop in replacement
        if ':' not in curie:
            raise ValueError(f'{curie} is not a curie!')

        prefix, suffix = curie.split(':', 1)
        namespace = self.store.namespace(prefix)
        if namespace is None:
            return  # TODO do we want to raise an error here? probably?

        return namespace + suffix

    def _qhrm(self, node):  # FIXME what the heck is this thing ... asPython????
        """ WARNING experimental """
        if isinstance(node, rdflib.BNode):
            return node.n3()

        elif isinstance(node, rdflib.URIRef):
            try:
                return self.qname(node)
            except (KeyError, ValueError):
                return node.toPython()

        else:
            raise TypeError(f'unhandled type {type(node)} for {node}')

    def qname(self, iri):
        # a version of normalizeUri that fails if no prefix is available
        prefix, namespace, name = self.compute_qname(iri, generate=False)
        if prefix == "":
            return name
        else:
            return ":".join((prefix, name))

    def normalizeUri(self, iri):
        # FIXME the core rdflib normalizeUri implementation is incorrect now ...
        try:
            return self.qname(iri)
        except KeyError:
            if isinstance(iri, rdflib.term.Variable):
                return f'?{iri}'
            else:
                return f'<{iri}>'

    def populate(self, graph):
        [graph.bind(k, v) for k, v in self.namespaces()]
        return graph  # make it possible to write g = BNM.populate(OntGraph())

    def populate_from(self, *graph_nsm_dict):
        """ populate namespace manager from graphs,
            namespace managers, or dicts """

        [self.bind(k, v) for gnd in graph_nsm_dict
         for k, v in
         (gnd.namespaces()
          if (isinstance(gnd, rdflib.Graph) or
              isinstance(gnd, rdflib.namespace.NamespaceManager)) else
          gnd.items())]

        return self  # allow chaining


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
            if namespace_manager and not isinstance(namespace_manager, BetterNamespaceManager):
                namespace_manager = BetterNamespaceManager(self).populate_from(namespace_manager)

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

    def compute_qname(self, uri, generate=False):
        # XXX need to flip to generate=False so that things like
        # infixowl can't silently insert madness into namespaces
        return super().compute_qname(uri, generate=generate)

    @property
    def prefixes(self):
        """ the prefix/curie/qname section of an rdf file """
        # a new OntCuries-like object that wraps NamespaceManager
        # and can leverage its trie
        self.namespace_manager
        raise NotImplementedError('yet')

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

    def serialize(self, *args, encoding='utf-8', **kwargs):  # FIXME XXX eventually remove this
        # compatibility layer for transition from 5.0 to 6.0 behavior
        # where the default switched from string to bytes
        return super().serialize(*args, encoding=encoding, **kwargs)

    def write(self, path=None, format='nifttl'):
        if path is None:
            path = self.path

        with open(path, 'wb') as f:
            self.serialize(f, format=format)

        return self  # allow chaining of parse and write

    def asMimetype(self, mimetype):
        if mimetype in ('text/turtle+html', 'text/html'):
            return self.serialize(format='htmlttl')
        elif mimetype == 'text/turtle':
            return self.serialize(format='nifttl')
        else:
            return self.serialize(format=mimetype)

    @property
    def ttl(self):
        #breakpoint()  # infinite loop inside somehow
        out = self.serialize(format='nifttl').decode()
        return out

    @property
    def ttl_html(self):
        out = self.serialize(format='htmlttl').decode()
        return out

    def debug(self):
        """ don't call this from other code
            you won't be able to find the call site """
        #breakpoint()  # infinite loop
        print(self.ttl)

    def debug_editor(self, command=None):
        fd = None
        try:
            fd, _path = tempfile.mkstemp(suffix='.ttl')
            path = Path(_path)
            self.write(path)
            aug.XopenPath(path).xopen(command=command)
        finally:
            if fd is not None:
                os.close(fd)

    def matchNamespace(self, namespace, *, ignore_predicates=tuple()):
        """ find all uris that have namespace as their prefix """
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
            that contains triples of the form `new replaces old`
            where `replaces` can be any predicate, set new_replaces_old=False
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

    def diffFromGraph(self, graph):
        # FIXME extremely inefficient
        add, rem, same = [self.__class__() for _ in range(3)]
        for t in self:
            if t in graph:
                same.add(t)
            else:
                rem.add(t)

        for t in graph:
            if t not in self:
                add.add(t)

        return add, rem, same

    def subjectGraphClosure(self, subject, seen=None):
        if seen is None:
            seen = set()

        def f (triple, graph):
            s, predicate, object = triple
            if s in seen:
                return
            else:
                seen.add(s)

            yield from self.subjectGraphClosure(s, seen=seen)

        for s, p, o in self.subjectGraph(subject):
            yield s, p, o
            yield from self.transitiveClosure(f, (o, None, None))

    def subjectGraph(self, subject):
        # some days I am smart, as in years ago when working on neuron stuff
        # TODO do we need to check for duplicates and cycels?
        # some days I am dumb, and didn't cut at bnodes, but do now
        seen = set()
        def f(triple, graph):
            _, predicate, object = triple
            if object in seen:
                return
            else:
                seen.add(object)

            if object != subject and isinstance(object, rdflib.URIRef) or isinstance(object, rdflib.Literal):
                # cut the graph when we run out of bnodes
                return

            for p, o in graph[object]:
                yield object, p, o

        yield from self.transitiveClosure(f, (None, None, subject))

    def subjectIdentity(self, subject, *, debug=False):
        """ calculate the identity of a subgraph for a particular subject
            useful for determining whether individual records have changed
            not quite
        """

        triples = list(self.subjectGraph(subject))  # subjective
        pairs_triples = [tuple(None if e == subject else e for e in t) for t in triples]  # objective
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

    def mapStableIdentifiers(self, other_graph, predicate):
        """ returns a new graph the is the result of mapping
            idenitifers between graphs using a predicate that points to
            objects that are known to be stable independent of changes to
            automatically generated identifiers

            the other graph is taken as the source of the identifiers that
            will be used in the new graph """

        gen = ((s, ilxtr.hasTemporaryId, temp_s)
               for s, o in other_graph[:predicate:]
               for temp_s in self[:predicate:o])


        add_replace_graph = self.__class__()
        add_replace_graph.populate_from_triples(gen)
        new_self = self._do_add_replace(add_replace_graph)
        new_self.namespace_manager.populate_from(self).populate_from(other_graph)
        return new_self

    def subjectsRenamed(self, other_graph):
        """ find subjects where only the id has changed """
        # FIXME dispatch on OntRes ?

        # TODO consider adding this to subjectsChanged?
        # probably not because the ability to reliably detect
        # renaming vs changing using this code requires that
        # renames and changes be two separate operations

        # FIXME cases where we have :a a owl:Class . :b a owl:Class .
        # in a single graph
        sid = {self.subjectIdentity(s):s for s in set(self.named_subjects())}
        oid = {other_graph.subjectIdentity(s):s for s in set(other_graph.named_subjects())}
        # FIXME triples output vs map?
        mapping = {s:oid[identity] for identity, s in sid.items()
                   if identity in oid and oid[identity] != s}
        return mapping

    def subjectsRenamedTriples(self, renamed_subjects_graph, predicate=replacedBy):
        for name, renamed in self.subjectsRenamed(renamed_subjects_graph).items():
            yield name, predicate, renamed

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
        # FIXME dispatch on OntRes ?

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
        new_self = self._do_add_replace(add_replace_graph)
        new_self.namespace_manager.populate_from(index_graph)
        return new_self

    def replaceIdentifiers(self, replace_pairs, new_replaces_old=True):
        "given a list of new, old pairs, replace old with new"
        replace_graph = [(s, new_replaces_old, o) for s, o in replace_pairs]
        return self._do_add_replace(
            replace_graph, include_input_triples=False,
            new_replaces_old=new_replaces_old)

    def _do_add_replace(self, add_replace_graph, include_input_triples=True,
                        new_replaces_old=True):
        add_only_graph, remove_graph, same_graph = self.diffFromReplace(
            add_replace_graph, new_replaces_old=new_replaces_old)

        # the other semantics that could be used here
        # would be to do an in place modification of self
        # to remove the remove graph and add the add_only_graph

        # NOTE the BNodes need to retain their identity across the 3 graphs
        # so that they reassemble correctly
        new_self = self.__class__(path=self.path)
        if include_input_triples:
            [new_self.add(t) for t in add_replace_graph]

        [new_self.add(t) for t in add_only_graph]
        [new_self.add(t) for t in same_graph]
        return new_self

    def identity(self, cypher=None):
        # TODO cypher ?
        return IdentityBNode(self)

    # variously named/connected subsets

    @property
    def boundIdentifiers(self):
        """ There should only be one but ... """
        for type in self.metadata_type_markers:
            yield from self[:rdf.type:type]

    @property
    def boundIdentifier(self):  # FIXME regularize naming ...
        return next(self.boundIdentifiers)

    @property
    def versionIdentifiers(self):
        """ There should only be one but ... """
        for bid in self.boundIdentifiers:
            yield from self[bid:owl.versionIRI]

    @property
    def versionIdentifier(self):
        return next(self.versionIdentifiers)

    def metadata(self):
        for bi in self.boundIdentifiers:
            yield from self.subjectGraph(bi)

    def metadata_unnamed(self):
        yield from ((s, p, o) for s, p, o in self.metadata()
                    if isinstance(s, rdflib.BNode))

    @property
    def data(self):
        bis = tuple(self.boundIdentifiers)
        meta_bnodes = tuple(e for t in self.metadata_unnamed() for e in t
                            if isinstance(e, rdflib.BNode))
        meta_skip_subject = bis + meta_bnodes
        for s, p, o in self:
            if s not in meta_skip_subject:  # FIXME conjunctive for performance
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
        # TODO assert len() triples match
        id = self.boundIdentifier
        #curies = rdflib.URIRef(id + '?section=localConventions')
        meta_id = rdflib.URIRef(id + '?section=metadata')
        data_id = rdflib.URIRef(id + '?section=data')
        datan_id = rdflib.URIRef(id + '?section=data_named')
        datau_id = rdflib.URIRef(id + '?section=data_unnamed')
        c = OntConjunctiveGraph(identifier=id)
        [c.addN((*t, meta_id) for t in self.metadata())]
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

    def populate(self, graph):
        for t in self:
            graph.add(t)

        return graph

    def populate_from(self, graph):
        for t in graph:
            self.add(t)

        return self

    def populate_from_triples(self, generator):
        for t in generator:
            self.add(t)

        return self

    def _genNodesEdges(self, triples_gen, label_predicate):
        nodes = []
        edges = []
        done = set()
        for t in triples_gen:
            edge = Edge(t)
            edges.append(edge.asOboGraph(self.namespace_manager))
            for e in t:
                if e in done:
                    continue

                done.add(e)

                try:
                    lbl = next(self[e:label_predicate]).toPython()
                except StopIteration:
                    lbl = e.toPython()

                meta = {owl.deprecated.toPython():o.toPython() for o in self[e:owl.deprecated]}
                node = {'id': self.namespace_manager._qhrm(e),
                        'lbl': lbl, 'meta': meta}
                nodes.append(node)

        return nodes, edges

    def asOboGraph(self, predicate=None, label_predicate=None, restriction=True):
        """ supply a predicate to restrict the exported graph """
        if label_predicate is None:
            label_predicate = rdfs.label
        else:
            label_predicate = self.namespace_manager.expand(label_predicate)  # FIXME oh boy this will break stuff

        restriction = predicate is not None and restriction

        if isinstance(predicate, rdflib.URIRef):
            pass
        elif predicate == 'isDefinedBy':
            predicate = self.namespace_manager.expand('rdfs:isDefinedBy')
        else:
            predicate = self.namespace_manager.expand(predicate)

        if not restriction:
            if predicate is None:
                # FIXME this needs to implement the full conversion rules
                # otherwise the bnodes flood everything, this is probably
                # the real use case for the combinators
                gen = (t for t in self
                       if not isinstance(t[-1], rdflib.Literal))
            else:
                gen = ((s, predicate, o) for s, o in self[:predicate:]
                       if not [e for e in (s, o) if isinstance(e, rdflib.BNode)])
        else:
            # TODO consider using the combinators here ?
            gen = ((s, predicate, o)
                   for s_bnode in self[:owl.onProperty:predicate]
                   for s in self[:rdfs.subClassOf:s_bnode]
                   for p in (owl.someValuesFrom,)  # I don't think we would want all values from?
                   for o in self[s_bnode:p])

        nodes, edges = self._genNodesEdges(gen, label_predicate)
        return {'nodes': nodes, 'edges': edges}

    def fromTabular(self, rows, lifting_rule=None):
        pass

    def asTabular(self, lifting_rule=None, mimetype='text/tsv'):
        pass


class OntConjunctiveGraph(rdflib.ConjunctiveGraph, OntGraph):
    def __init__(self, *args, store='default', identifier=None, **kwargs):
        super().__init__(*args, store=store, identifier=identifier, **kwargs)
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
            attr = f'_{self.g.store.__class__.__name__}__namespace'
            internal_dict = getattr(self.g.store, attr)
            internal_dict.pop(prefix)
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
            ser = self.g.serialize(format='nifttl', encoding='utf-8')
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

    @classmethod
    def _sinit(cls):
        """ set up services for a particular OntTerm class or subclass
        calling this more than once may produce unexpected results """
        SGR = oq.plugin.get('SciGraph')
        IXR = oq.plugin.get('InterLex')
        #sgr.verbose = True
        for rc in (SGR, IXR):
            rc.known_inverses += (
                ('hasPart:', 'partOf:'),
                ('NIFRID:has_proper_part', 'NIFRID:proper_part_of'))

        sgr = SGR(apiEndpoint=auth.get('scigraph-api'))
        ixr = IXR(readonly=True)
        ixr.Graph = OntGraph
        cls.query_init(sgr, ixr)  # = oq.OntQuery(sgr, ixr, instrumented=OntTerm)
        [cls.repr_level(verbose=False) for _ in range(2)]


OntTerm._sinit()
query = oq.OntQueryCli(query=OntTerm.query)


class IlxTerm(OntTerm):
    skip_for_instrumentation = True


ixr = query.services[-1]  # FIXME this whole approach seems bad and wrong
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
                            file_commit = next(cls.repo.iter_commits(max_count=1)).hexsha
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

            elif cls.source and os.path.exists(cls.source):  # TODO no expanded stuff
                cls.source = aug.RepoPath(cls.source)
                try:
                    cls.source.repo
                    try:
                        file_commit = next(cls.source.repo.iter_commits(max_count=1)).hexsha
                    except StopIteration:
                        file_commit = None

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
                except BaseException as e:
                    raise BaseException('I can\'t believe you\'ve done this.') from e

            else:
                cls._type = None
                log.warning(f'Unknown source {cls.source}')

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
                .resolve()
                .working_dir)

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
            wgb = None
            if self.source_file:
                filepath = self.source_file
                line = ''
                if isinstance(self.source_file, aug.RepoPath):
                    working_dir = self.source_file.working_dir
                    if working_dir is not None:
                        # this can fail on new repo
                        commit = next(self.source_file.repo.iter_commits(max_count=1)).hexsha
                        #str(self.source_file.latest_commit())
                        uri = self.source_file.remote_uri_human(ref=commit)
                        # we always want the latest commit for the repo
                        # but when checking if a file should be marked as
                        # dirty/uncommitted we only check the file itself
                        # because there can be other files that linger in
                        # uncommitted states that are completely unrelated
                        # the _right_ thing to do would be to trace the
                        # import chain, but that is a major TODO not quick
                        #t = self.source_file.repo.head.commit.tree
                        #diff = self.source_file.repo.git.diff(t)
                        diff = self.source_file.has_uncommitted_changes()
                        if diff:
                            uri = uri.replace(commit, f'uncommitted@{commit[:8]}')

                        wgb = self.wasGeneratedBy = uri

            else:
                line = '#L' + str(getSourceLine(self.__class__))
                file_string = getsourcefile(self.__class__)
                file = aug.RepoPath(file_string)
                file = file.resolve().resolve()
                working_dir = file.working_dir
                if working_dir is not None:
                    # this can fail on new repo
                    commit = next(file.repo.iter_commits(max_count=1)).hexsha
                    #str(file.latest_commit())
                    uri = file.remote_uri_human(ref=commit) + line
                    #t = file.repo.head.commit.tree
                    #diff = file.repo.git.diff(t)
                    diff = file.has_uncommitted_changes()
                    if diff:
                        uri = uri.replace(commit, f'uncommitted@{commit[:8]}')

                    wgb = self.wasGeneratedBy = uri
                else:
                    filepath = file.name

        except TypeError:  # emacs is silly
            line = '#Lnoline'
            _file = 'nofile'
            filepath = Path(_file).name

        if wgb is None:
            self.wasGeneratedBy = (self.wasGeneratedBy
                                   .format(commit=commit,
                                           hash_L_line=line,
                                           filepath=filepath))

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
              prefixes=tuple(),  # dict
              imports=tuple(),
              triples=tuple(),
              comment=None,
              path='ttl/',
              branch='master',
              local_base=None,
              fail=False,
              _repo=True,
              write=False,
              calling__file__=None):

    for i in imports:
        if not isinstance(i, rdflib.URIRef):
            raise TypeError(f'Import {i} is not a URIRef!')

    class Simple(Ont):  # TODO make a Simple(Ont) that works like this?

        source_file = aug.RepoPath(calling__file__)
        # FIXME TODO get the line by inspecting the stack ?

        def _triples(self):
            yield from cmb.flattenTriples(triples)

    Simple._repo = _repo
    Simple.path = path
    Simple.filename = filename
    Simple.comment = comment
    Simple.imports = imports
    Simple.prefixes = dict(uPREFIXES)
    if local_base is not None:
        Simple.local_base = local_base

    if prefixes:
        Simple.prefixes.update({k:str(v) for k, v in prefixes.items()})

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

        j = g.g.asOboGraph(pred, restriction=False)
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
