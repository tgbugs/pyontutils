#!/usr/bin/env python3.7

# equivalent indexed as default
# equivalent indexed in map only

from urllib.parse import urlparse
import yaml
import idlib
import rdflib
import ontquery as oq
import augpathlib as aug
from ttlser import CustomTurtleSerializer
from pyontutils.core import OntGraph, OntTerm, OntResGit, OntResIri
from pyontutils.utils import Async, deferred, log
from pyontutils.config import auth
from pyontutils.identity_bnode import IdentityBNode
from pyontutils.namespaces import (TEMP,
                                   ILX,
                                   ilx,
                                   rdf,
                                   rdfs,
                                   owl,
                                   ilxtr,
                                   npokb,
                                   OntCuries)

log = log.getChild('sneechenator')

snchn = rdflib.Namespace('https://uilx.org/sneechenator/u/r/')
sncho = rdflib.Namespace('https://uilx.org/sneechenator/o/u/')
# ontology hash resolver w/ filter by group
sghashes = rdflib.Namespace('https://uilx.org/sneechenator/o/h/')
_tc = (snchn.IndexGraph,
       snchn.PartialIndexGraph)
CustomTurtleSerializer.addTopClasses(*_tc)
OntGraph.metadata_type_markers.extend(_tc)  # FIXME naming

IXR = oq.plugin.get('InterLex')
rdfl = oq.plugin.get('rdflib')
ixr = IXR()
ixr.port = None  # FIXME hack
# really need a way to override if this changes things during __init__
# luckily it doesn't right now so we can switch the query endpoint
# at runtime by setting the port to non


class IlxTerm(OntTerm):
    pass


IlxTerm.query_init(ixr)
query = IlxTerm.query


class SnchFile:
    @classmethod
    def fromYaml(cls, in_path):
        in_path = aug.RepoPath(in_path).resolve()

        with open(in_path, 'rt') as f:
            blob = yaml.safe_load(f)

        if 'include' in blob:
            orgs = [OntResGit(path=aug.RepoPath(subblob['path']),
                              ref=subblob['ref'])
                    for subblob in blob['include']]
        else:
            orgs = [OntResGit(path=aug.RepoPath(subblob['path']),
                              ref=subblob['ref'])
                    for subblob in blob['paths']]

        if not orgs:
            raise ValueError(f'orgs is epty for {in_path}')

        referenceIndex = blob['referenceIndex']
        namespaces = blob['namespaces']
        if isinstance(namespaces, str):
            namespaces = namespaces.split(' ')

        snchf = cls(orgs=orgs,
                    namespaces=namespaces,
                    referenceIndex=referenceIndex)
        return cls(graph=snchf.populate(OntGraph()))

    @classmethod
    def fromTtl(cls, in_path):
        return cls(graph=OntGraph(path=in_path).parse())

    def __init__(self, *, orgs=tuple(), namespaces=tuple(), referenceIndex=None, graph=None):
        # FIXME ignore the issue of transparently iding git repos right now
        #oris = [OntRestIri(i) for i in input_iris]  # FIXME need commit hashes etc
        # right now we require paths so we can get the granular information and
        # ensure that the ids actually get back into the source ontology
        # rather than having some rando just get a bunch of ilx ids

        # TODO resolve the indirect ref to the direct ref
        #orgs = [OntRestGit(aug.RepoPath(f)) for f in input_paths]
        if graph is not None:
            self._parse_graph(graph)
            # FIXME do we roundtrip this or no this is actually the header
            # for the the status graph we use below ...
        else:
            self.identity_metadata = rdflib.BNode()  # this is removed after a first output
            self.referenceIndex = rdflib.Literal(referenceIndex)
            self.namespaces = [rdflib.URIRef(ns) for ns in namespaces]
            #self.base_path = base_path # FIXME source might be from anywhere an we would have to copy
            #self.path_out = aug.RepoPath(base_path.stem).with_suffix('.deref.yaml')
            # FIXME this is an awful way to do this
            #same_file = self.base_path.resolve() == self.path_out.resolve()
            dereforgs = [org.asDeRef() for org in orgs]
            # TODO change detection
            #if same_file and orgs != dereforgs:
                #raise ValueError('a dereference has changed since you last checked!')

            self._orgs = orgs  # FIXME danger zone?
            self.orgs = dereforgs

        if not self.orgs:
            if graph is not None:
                graph.debug()

            raise TypeError('no orgs, something as gone wrong!')

    def _parse_graph(self, graph):
        # there should be only one of each of these
        graph.debug()
        gen = graph[:rdf.type:snchn.SneechFile]
        s = next(gen)
        try:
            next(gen)
            raise ValueError('MORE THAN ONE SNEECH FILE IN A SINGLE FILE!')
        except StopIteration:
            pass

        self.identity_metadata = graph.subjectIdentity(s)  # FIXME align naming with idlib when we get there
        self.referenceIndex = next(graph[s:snchn.referenceIndex:])
        self.namespaces = list(graph[s:snchn.namespaces:])
        _orgs = []
        orgs = []
        for bn in graph[s:snchn['include']:]:
            try:
                path = aug.RepoPath(next(graph[bn:snchn.path:]))
            except StopIteration:
                iri = next(graph[bn:snchn.iri:])
                for string_path in graph[iri:snchn.hasLocalPath:]:
                    path = aug.RepoPath(string_path).resolve()
                    if path.exists():
                        break

                else:
                    # TODO OntResIri failover ??? probalby not
                    raise ValueError(f'could not find local path for {iri}')

            ref = next(graph[bn:snchn.ref:])
            # TODO if there is a bound name use that and move the raw paths
            # to annotations for local sourcing of that file that can be
            # edited manually if needs be
            org = OntResGit(path, ref)
            dorg = org.asDeRef()
            _orgs.append(org)
            orgs.append(dorg)

        self._orgs = _orgs
        self.orgs = orgs

    def _writeYaml(self, path=None):  #XXX no, yaml is input not output
        # TODO path is really parent path
        # TODO probably also copy base_path if we don't have a record of it?
        # don't both with that?
        path_out = path / self.path_out
        blob = self.asBlob(path_out)
        with open(path_out, 'wt') as f:
            yaml.dump(blob, f)

        return path_out

    def writeTtl(self, path=None):
        g = OntGraph(path=path)
        self.populate(g)
        g.write(format='nifttl')
        return g

    def debug(self):
        g = OntGraph()
        self.populate(g)
        log.debug('printing graph')
        g.debug()

    def populate(self, graph):
        graph.bind('snchn', str(snchn))  # FIXME -> curies probably
        graph.bind('sncho', str(sncho))  # FIXME -> curies probably
        graph.bind('h', str(sghashes))  # FIXME -> curies probably
        for t in self.triples_metadata(graph.path):
            graph.add(t)

        return graph

    @property
    def s(self):
        s = self.identity_metadata
        if isinstance(s, IdentityBNode):
            s = sghashes[s.identity.hex()]

        return s

    def triples_metadata(self, path=None, s=None):
        if s is None:
            s = self.s

        yield s, rdf.type, snchn.SneechFile
        yield s, snchn.referenceIndex, self.referenceIndex
        for ns in self.namespaces:
            yield s, snchn.namespaces, ns

        for org in self.orgs:
            b = rdflib.BNode()
            yield s, snchn.include, b  # FIXME paths, raw-paths, include etc.
            yield b, snchn.ref, rdflib.Literal(str(org.ref))  # FIXME need repo identifiers
            if path is not None:
                iri = org.metadata().identifier_bound
                yield b, snchn.iri, iri
                if org.path.parts[0] == '~':
                    _o = org.path
                else:
                    _o = org.path.relative_path_from(path)

                o = rdflib.Literal(_o.as_posix())
                yield iri, snchn.hasLocalPath, o
            else:
                yield b, snchn.path, rdflib.Literal(org.path.as_posix())

    def asBlob(self, path_this_snch_file=None):
        if path_this_snch_file:
            paths = [{'path': org.path.relative_path_from(path_this_snch_file).as_posix(),
                      'ref': str(org.ref)} for org in self.orgs]
        else:
            paths = [{'path': org.path.as_posix(),
                    'ref': str(org.ref)} for org in self.orgs]

        return {'referenceIndex': self.referenceIndex,
                'namespaces': self.namespaces,
                'paths': paths}

    def COMMENCE(self, sneechenator, path_out=None):
        # FIXME sneechenator needs the whole file ...
        if not self.orgs:
            raise TypeError('no orgs, something as gone wrong!')

        if path_out is None and False:  # TODO the logic for this
            path_out = self

        return sneechenator.COMMENCE(namespaces=self.namespaces,
                                     orgs=self.orgs,
                                     referenceIndex=self.referenceIndex,
                                     sneech_file=self,
                                     path_out=path_out,)


class SneechWrangler:
    """ A git based backend for local wranging that can
        also work in concert with a remote. """

    def __init__(self, path_repo):
        # TODO make sneech path configurable and passable via command line etc.
        rpath = aug.RepoPath(path_repo)
        if not rpath.exists():
            self.rp_sneech = rpath
            self.rp_sneech.init()
            readme = self.rp_sneech / 'README.org'
            with open(readme, 'wt') as f:
                f.write('#+title: Sneechenator\n\nTrack the stars for your sneeches!')

            readme.commit_from_working_tree('first commit')

            self.dir_index.mkdir()
            self.dir_process.mkdir()
        else:
            self.rp_sneech = rpath.working_dir

    def index_graph(self, referenceIndex, *, _gc=OntGraph):
        path = self.path_index(referenceIndex)
        # TODO check for uncommitted?
        return _gc(path=path).parse()

    def path_index(self, referenceIndex):
        #uri_path_sandbox = uri_path_sandbox.strip('/')  # insurace
        # uri_path_sandbox is needless complication here
        path = self.dir_index / referenceIndex / 'index.ttl'
        return path

    def new_index(self, referenceIndex, *, commit=True):
        """ reference hosts have a single incrementing primary key index
            to which everything is mapped

            in theory these indexes could also be per 'prefix' aka
            the sandboxed uri path or external uri path to which
            something is mapped I don't see any reason not to do this
            for this kind of implementation since a regular pattern
            can be develop
        """

        '''
            QUESTION: do we force a remapping of external id sequences
            into uris/ first? this seems like a bad idea? or rather,
            it is actually a good idea, but it will have to be done with
            a pattern based redirect instead of an actual materialization
            the alternative is to do what ontobee does and pass the external
            iri as a query parameter ... hrm tradoffs, well we certainly
            can't make a nice /uberon/uris/obo/{UBERON_} folder if we include
            the whole uri ... so this seems a reasonable tradeoff
            http://purl.obolibrary.org/obo/ can wind up being mapped into
            multiple uri spaces ... /obo/uris/obo/ would seem to make more sense
            but how to indicate that other organizations/projects map there ...
            /uberon/uris/obo/UBERON_ could indicate the latest sequence
            ah, and of course in theory this gets us out of the very annoying
            situation where /uberon/uris/obo/UBERON_ really IS different than
            /doid/uris/obo/UBERON_ for some identifiers (sigh) and if they are
            all mapped and masking based on presence then we can detect the issues
            HOWEVER how do we enforce that in reality the _mapping_ is all to
            /obo/uris/obo/ ??
        '''

        path = self.path_index(referenceIndex)

        rrp = path.repo_relative_path
        s = sncho[rrp.with_suffix('').as_posix()]  # TODO check ownership

        if path.exists():
            raise FileExistsError(path)

        g = OntGraph(path=path)
        OntCuries.populate(g)
        # TODO these are really identified by the follow:
        # base/readable/
        # {group}/uris/
        # base/ontologies/
        # {group}/ontologies/uris/
        pos = ((rdf.type, snchn.IndexGraph),
               (rdfs.label, rdflib.Literal(f'IndexGraph for {referenceIndex}')),
               (snchn.referenceIndex, rdflib.Literal(referenceIndex)),  # TODO HRM
               #(snchn.indexRemote, )
        )

        for po in pos:
            g.add((s, *po))  # FIXME

        g.path.parent.mkdir(parents=True)
        g.write()

        if commit:
            path.commit(f'add new index for {referenceIndex}')

        return path

    def get_dir_process(self, in_process_folder=None):
        ipf = self.in_process_folder
        if not ipf and in_process_folder:
            in_process_folder.chdir()
            ipf = self.in_process_folder
            if not ipf:
                raise ValueError(f'{in_process_folder} is not in the process of sneechenating!')

        elif ipf and in_process_folder and ipf != in_process_folder:
            raise ValueError(f'already in process at {ipf} cannot also sneech '
                             f'in {in_process_folder} at the same time')

        elif not ipf and not in_process_folder:
            # SNEEECH!
            # TODO should be able to automate? no not really, we need the snch file
            raise ValueError(f'please creat and chdir to a new folder in {self.dir_process}'
                             'and add the snch file to start work on a new sneechening')
        else:
            raise BaseException('how did we get here?')

    @property
    def dir_index(self):
        return self.rp_sneech / 'indexes'

    @property
    def dir_process(self):
        return self.rp_sneech / 'sneechenings'

    @property
    def in_process_folder(self):
        """ There may be multiple in process folders """
        cwd = aug.RepoPath.cwd()
        if cwd.working_dir == self.rp_sneech.working_dir and self.logic_for_in_process:
            existing = cwd

    def existing_indexes(self, referenceIndex, *index_namespaces):
        index_graph = self.index_graph(referenceIndex)
        if not index_namespaces:
            index_namespaces = [n for p, n in index_graph
                                if p not in ('owl', 'rdf', 'rdfs', 'xml')]

        {index_namespace:set(index_graph.matchNamespace(index_namespace))
         for index_namespace in index_namespaces}


class Sneechenator:
    """
    The sneechenator works as follows.
    0. create the OntResGit instances for the files to be sneeched
    0. specify the namespaces/prefixes to be sneeched
    0. those files/namespaces are logged in the repo by reference
    0. from the seed spec 5 files are generated,
       cannot sneech,
       already sneeched,
       maybe already sneeched,
       to sneech,
       maybe sneeched report
    0. the previous steps may be repeated until cannot sneech matches the the desired set
    0. commit
    0. the maybe sneeched report can now be used to determine which if any of the maybe sneeched
       have actually been sneeched
    0. the maybe already sneeched file is updated to remove incorrect/undesired matches
       or terms with all incorrect matches, ids with no matches should be move to sneech
    0. commit
    0. at this point run maybeHasIlxId -> index
    0. commit
    0. update already sneeched, maybe already sneeched and repeat until satisfied
    0. commit + push
    0. use to sneech + the input graphs to submit each square to interlex to get the sneech star
       and update the index
    0. commit + push
"""

    referenceIndex = 'uilx.org/temp/u'
    mapping_predicate = snchn.hasIndexedId
    #type_index = None

    def __init__(self, *args, path_wrangler=None, **kwargs):
        if path_wrangler is None:
            path_wrangler = auth.get_path('git-local-base') / 'sneechenator'

        self.wrangler = SneechWrangler(path_wrangler)
        #super().__init__(*args, **kwargs)

        #if org_index.path.stem != self.type_index:  # FIXME bad ... use embedded metadata?
            #raise TypeError('type mismatch {self.type_index} != {org_index.path.stem}')

        #self.index_graph = org_index.graph

        # FIXME or do the namespaces and orgs come later ?
        # and need to be passed in making the sneechenator identical with the index ?

    def COMMENCE(self, *, namespaces=tuple(), orgs=tuple(), sneech_file=None, path_out=None, **kwargs):
        if sneech_file is not None and not orgs:
            return sneech_file.COMMENCE(self, path_out)

        if not orgs:
            raise TypeError('orgs cannot be empty!')

        source_graph = OntGraph()
        for org in orgs:
            org.populate(source_graph)

        #derp = g.namespace_manager.store.namespace
        #namespaces = [derp(p) for p in prefixes]  # FIXME prefix vs namespace
        rg, maybe_sneeches = self.sneechReviewGraph(source_graph, namespaces,  sneech_file, path_out)
        # TODO I think we commit here ?
        #breakpoint()

    def CONTINUE(self, path_sneech_file):
        pass

    def alreadyMapped(self, could_map, namespace=None):
        """ alreadyMapped is the most efficient way to allow multiple different
            implementations to return the set of terms that have already been
            identified in a way that is network transparent """

        # some files might even have that relation in the source graph already ...
        # if the index is the source of truth then it could be local or remote
        # in the git implementation it is local, also we have to assume that
        # the number of things to be mapped in any one instance will be smaller
        # than the index of everything that has been mapped

        # FIXME TODO allow namespace could_map pairings?
        # or what? should we assume anything about the
        # criteria used to select could map?
        index_graph = self.wrangler.index_graph(self.referenceIndex)
        g = index_graph.__class__()
        s = index_graph.boundIdentifier + '#ArbitrarySubset'
        title = rdflib.Literal(f'Subset of mapped IRIs for {self.referenceIndex}')
        triples_header = (
            (s, p, o) for p, o in
            ((rdf.type, snchn.PartialIndexGraph),
             (rdfs.label, title),
             (snchn.referenceIndex, rdflib.Literal(self.referenceIndex)),
            ))
        [g.add(t) for t in triples_header]
        [g.add((s, self.mapping_predicate, o))
         for s in could_map
         for o in index_graph[s:self.mapping_predicate:]]
        return g



    def preSquare(self, source_graph, namespaces):
        # TODO remove use of self where possible
        already = []
        maybe = []
        for namespace in namespaces:
            could_map = list(set(
                source_graph.couldMapEntities(namespace,
                                              ignore_predicates=(self.mapping_predicate,))))

            # yes we are trading off more network roundtrips as
            # a function of namespaces right now, internally we can
            # rework this as needed since it is an implementation detail
            # FIXME already_mapped in this case is actually the
            # remote index graph and should probably be passed along ??
            already_mapped = self.alreadyMapped(could_map, namespace)
            already += [s for s, p, o in already_mapped]
            maybe += [e for e in could_map if e not in already]

        return already, maybe

    def preSneech(self, source_graph, namespaces):
        already, maybe_maybe = self.preSquare(source_graph, namespaces)

        rdll = rdfl(source_graph)
        rdll.setup(instrumented=OntTerm)
        maybe_squares = [self.makeSquare(rdll, m) for m in maybe_maybe]

        cannot = [m for s, m in zip(maybe_squares, maybe_maybe) if not s or not s.label]
        squares = sorted(s for s in maybe_squares if s and s.label)
        circles = self.searchSquares(squares)  # not quite right
        maybe_sneeches = {term:candidates for term, candidates in circles.items()
                          if candidates}  # maybe into the machine
        maybe = list(maybe_sneeches)
        sneeches = [term for term, candidates in circles.items() if not candidates]  # INTO THE MACHINE
        return already, cannot, maybe, sneeches, maybe_sneeches

    def reView(self, graph, maybe_sneeches):
        if maybe_sneeches:
            ml = max(len(t.label) for t in maybe_sneeches)
            mlm = max(len(m.label) for ms in maybe_sneeches.values() for m in ms)
            for ms, matches in maybe_sneeches.items():
                for match in matches:
                    mp = self.mapping_predicate.n3(graph.namespace_manager)
                    print(f'{ms.label:<{ml + 2}}{match.label:<{mlm + 2}}{ms.curie} {mp} {match.curie}')

    @staticmethod
    def makeSquare(rdll, e):
        square = [r.OntTerm for r in rdll.query(iri=e)]
        if len(square) > 1:
            raise TypeError(f'too many results for {e}\n{square}')
        elif square:
            return square[0]

    @staticmethod
    def searchSquares(squares):
        raise NotImplementedError('implement in subclasses')

    def submitSquares(self, squares):
        # label
        # synonyms
        raise NotImplementedError('implement in subclasses')

    def sneechReviewGraph(self, source_graph, namespaces, sneech_file=None, path_out=None):
        # TODO cache
        (already, cannot, maybe, sneeches, maybe_sneeches
        )= self.preSneech(source_graph, namespaces)
        # TODO not entirely sure about the best place to put this ...
        self.reView(source_graph, maybe_sneeches)  # FIXME dump and commit

        review_graph = OntGraph(path=path_out)
        oq.OntCuries.populate(review_graph)
        review_graph.bind('snchn', str(snchn))  # FIXME -> curies probably
        review_graph.bind('sncho', str(sncho))  # FIXME -> curies probably
        review_graph.bind('h', str(sghashes))  # FIXME -> curies probably
        if sneech_file:
            sneech_file.populate(review_graph)

        gen = self.triples_review(already, cannot, maybe, sneeches, sneech_file)
        [review_graph.add(t) for t in gen]
        # TODO hasReport -> maybe_sneeches report / reView
        # TODO snchn predicate ordering
        return review_graph, maybe_sneeches

    def triples_review(self, already, cannot, maybe, sneeches, sneech_file):
        pairs = (
            (snchn.alreadyMapped, already),
            (snchn.cannotMap, cannot),
            (snchn.maybeMapped, maybe),
            (snchn.toMap, sneeches),
        )
        pos = [(p, o) for p, os in pairs for o in os]
        # TODO populate header from sneech file

        s = sghashes[IdentityBNode(pos).identity.hex()]
        yield s, rdf.type, snchn.Review
        for p, o in pos:
            yield s, p, o

        if sneech_file is not None:
            yield s, snchn.isReviewOf, sneech_file.s

            # FIXME the review graph IS the sneech file ...
            # maybe with
            # review_graph.path = sneech_file.path


class InterLexSneechenator(Sneechenator):
    referenceIndex = 'uri.interlex.org'
    mapping_predicate = ilxtr.hasIlxId

    def COMMENCE(self, *, namespaces=tuple(), orgs=tuple(),
                 sneech_file=None, path_out=None,
                 referenceIndex=None):
        # TODO set up index and stuff
        if sneech_file is not None and not orgs:
            return sneech_file.COMMENCE(self, path_out=path_out)

        if self.referenceIndex != str(referenceIndex):
            raise TypeError(f'{self.referenceIndex} != {referenceIndex}')

        if not orgs:
            raise TypeError('orgs cannot be empty!')

        return super().COMMENCE(namespaces=namespaces,
                                orgs=orgs,
                                sneech_file=sneech_file,
                                path_out=path_out)

    def CONTINUE(self, path_sneech_file):
        raise NotImplementedError('TODO')

    @staticmethod
    def searchSquares(squares):
        def fetch(s):
            return s, list(query(label=s.label))

        return {s:match for s, match in Async(rate=10)(deferred(fetch)(s) for s in squares)}

    def _alreadyMapped(self, could_map):
        # TODO should be able to check existing ids without using a local index
        # this definitely has to implemented efficiently for {group}/uris/ mappings
        # iirc the spec is already such that it will be since it is a single check
        # against the names index
        '''
        SELECT t.s, t.p, t.o FROM triples as t WHERE t.p = {self.mapping_predicate} AND t.s IN {could_map}
        '''
        index_graph = self.wrangler.index_graph(self.referenceIndex)
        return set((s, self.mapping_predicate, o)
                   for s in could_map
                   for o in index_graph[s:self.mapping_predicate:])

    def alreadyMapped(self, could_map, namespace=None):
        arg_ns = f'?iri={namespace}' if namespace is not None else ''
        ori = OntResIri(f'http://localhost:8515/base/external/mapped{arg_ns}')  # FIXME
        ct = idlib.conventions.type.ConvTypeBytesHeader(
            format='text/turtle',
            start=b'\ (?:snchn)?:(PartialIndexGraph)',
            stop=b'\ \.$',
            sentinel=b'^###\ ')
        g = ori.graph_next(send_data='\n'.join(str(m) for m in could_map), conventions_type=ct)
        return g


def test():
    snchf = SnchFile.fromYaml('../test/sneech-file.yaml')
    snchf.write(aug.RepoPath('../test/').resolve())
    rp = aug.RepoPath(auth.get_path('ontology-local-repo'))
    wrangler = SneechWrangler()
    dir_snchn = wrangler.dir_process / 'test-sneechening'
    if not dir_snchn.exists():  # FIXME bad workflow
        dir_snchn.mkdir()

    path_index = wrangler.path_index(snchf.index)
    if not path_index.exists():
        path_index = wrangler.new_index(snchf.index)  # FIXME move inside Sneechenator? or no
        path_index.commit_from_working_tree(f'new index {snchf.index}')

    org_index = OntResGit(path_index)
    expanded = snchf.write(dir_snchn)  # TODO commit
    expanded.commit_from_working_tree(f'expanded snch file')
    sncher = Sneechenator(org_index, snchf.namespaces, snchf.orgs)
    #sncher.preSneechUpon(dir_snchn)
    rg, maybe_sneeches = sncher.sneechReviewGraph()
    # commit here I think ?
    # consider using ilxtr.maybeHasIlxId ?
    # TODO modified maybe_sneeches file + maybe list -> update list
    breakpoint()


def main():

    #InterLexSneechenator()
    test()

    return
    # testing
    index_graph.bind('ILX', ILX)
    #[index_graph.add((npokb[str(i)], rdf.type, owl.Class)) for i in range(1, 11)]
    #[index_graph.add((npokb[str(i)], ilxtr.hasTemporaryId, TEMP[str(i)])) for i in range(1, 11)]

    ios = []
    for eff in ('phenotype-core.ttl', 'phenotypes.ttl'):
        path = auth.get_path('ontology-local-repo') / eff
        input_graph = OntGraph(path=path)
        input_graph.parse()
        output_graph = input_graph.mapTempToIndex(index_graph, ILX, ilxtr)
        ios.append((input_graph, output_graph))

    input_graph, output_graph = ios[0]
    a, r, c = output_graph.subjectsChanged(input_graph)
    index_graph.write()
    # [o.write() for i, o, in ios]  # when ready
    #from sparcur.paths import Path
    #Path(index_graph.path).xopen()
    breakpoint()

if __name__ == '__main__':
    main()
