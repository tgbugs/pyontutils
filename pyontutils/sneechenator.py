#!/usr/bin/env python3.7

# equivalent indexed as default
# equivalent indexed in map only

import yaml
import rdflib
import ontquery as oq
import augpathlib as aug
from pyontutils.core import OntGraph, OntTerm, OntResGit
from pyontutils.utils import Async, deferred
from pyontutils.config import auth
from pyontutils.namespaces import TEMP, ILX, ilx, rdf, owl, ilxtr, npokb, OntCuries

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

        if 'raw-paths' in blob:
            orgs = [OntResGit(path=aug.RepoPath(subblob['path']).expanduser(),
                                ref=subblob['ref'])
                    for subblob in blob['raw-paths']]
        else:
            orgs = [OntResGit(path=aug.RepoPath(subblob['path']).expanduser(),
                                ref=subblob['ref'])
                    for subblob in blob['paths']]

        index = blob['index']
        namespaces = blob['namespaces']
        if isinstance(namespaces, str):
            namespaces = namespaces.split(' ')

        return cls(in_path, orgs, namespaces, index)

    def __init__(self, base_path, orgs=tuple(), namespaces=tuple(), index=None):
        # FIXME ignore the issue of transparently iding git repos right now
        #oris = [OntRestIri(i) for i in input_iris]  # FIXME need commit hashes etc
        # right now we require paths so we can get the granular information and
        # ensure that the ids actually get back into the source ontology
        # rather than having some rando just get a bunch of ilx ids

        # TODO resolve the indirect ref to the direct ref
        #orgs = [OntRestGit(aug.RepoPath(f)) for f in input_paths]
        self.index = index
        self.namespaces = namespaces
        self.base_path = base_path # FIXME source might be from anywhere an we would have to copy
        self.out_path = aug.RepoPath(base_path.stem).with_suffix('.deref.yaml')
        # FIXME this is an awful way to do this
        same_file = self.base_path.resolve() == self.out_path.resolve()
        dereforgs = [org.asDeRef() for org in orgs]
        if same_file and orgs != dereforgs:
            # TODO
            raise ValueError('a dereference has changed since you last checked!')

        # whether to write or not is not decided in here
        self.orgs = dereforgs

    def write(self, path=None):
        # TODO path is really parent path
        # TODO probably also copy base_path if we don't have a record of it?
        # don't both with that?
        out_path = path / self.out_path
        blob = self.asBlob(out_path)
        with open(out_path, 'wt') as f:
            yaml.dump(blob, f)

        return out_path

    def asBlob(self, path_this_snch_file=None):
        if path_this_snch_file:
            paths = [{'path': org.path.relative_path_from(path_this_snch_file).as_posix(),
                      'ref': str(org.ref)} for org in self.orgs]
        else:
            paths = [{'path': org.path.as_posix(),
                    'ref': str(org.ref)} for org in self.orgs]

        return {'index': self.index,
                'namespaces': self.namespaces,
                'paths': paths}



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

    def __init__(self, org_index, prefixes, orgs):
        self.index_graph = org_index.graph

        # FIXME or do the namespaces and orgs come later ?
        # and need to be passed in making the sneechenator identical with the index ?
        g = OntGraph()
        for org in orgs:
            org.populate(g)

        self.source_graph = g
        derp = g.namespace_manager.store.namespace
        self.namespaces = [derp(p) for p in prefixes]  # FIXME prefix vs namespace

    def preSquare(self, index_graph=None, namespaces=None, source_graph=None):
        # TODO remove use of self where possible
        could_map = list(set(self.source_graph.couldMapEntities(*self.namespaces,
                                                                ignore_predicates=(ilxtr.hasIlxId,))))

        mapped_subjects = set(s for s, o in self.index_graph[:ilxtr.hasIlxId:])
        already = []
        maybe = []
        for e in could_map:
            if e in mapped_subjects:
                already.append(e)
            else:
                maybe.append(e)

        return already, maybe

    def preSneech(self, index_graph=None, namespaces=None, source_graph=None):
        already, maybe_maybe = self.preSquare(index_graph, namespaces, source_graph)

        rdll = rdfl(self.source_graph)
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

    @staticmethod
    def reView(maybe_sneeches):
        ml = max(len(t.label) for t in maybe_sneeches)
        mlm = max(len(m.label) for ms in maybe_sneeches.values() for m in ms)
        for ms, matches in maybe_sneeches.items():
            for match in matches:
                print(f'{ms.label:<{ml + 2}}{match.label:<{mlm + 2}}{ms.curie} ilxtr:hasIlxId {match.curie}')

    @staticmethod
    def makeSquare(rdll, e):
        square = [r.OntTerm for r in rdll.query(iri=e)]
        if len(square) > 1:
            raise TypeError(f'too many results for {e}\n{square}')
        elif square:
            return square[0]

    @staticmethod
    def searchSquares(squares):
        def fetch(s):
            return s, list(query(label=s.label))

        return {s:match for s, match in Async(rate=10)(deferred(fetch)(s) for s in squares)}

    def submitSquares(self, squares):
        # label
        # synonyms
        pass

    def sneechReviewGraph(self, index_graph=None, namespaces=None, source_graph=None):
        # TODO cache
        (already, cannot, maybe, sneeches, maybe_sneeches
        )= self.preSneech(index_graph, namespaces, source_graph)
        # TODO not entirely sure about the best place to put this ...
        self.reView(maybe_sneeches)  # FIXME dump and commit
        pairs = (
            (already, ilxtr.AlreadyMapped),
            (cannot, ilxtr.CannotMap),
            (maybe, ilxtr.MaybeMapped),
            (sneeches, ilxtr.ToMap),
        )
        review_graph = OntGraph()
        oq.OntCuries.populate(review_graph)
        for lst, s in pairs:
            for e in lst:
                review_graph.add((s, ilxtr.hasMember, e))

        return review_graph, maybe_sneeches

    def preSneechUpon(self, path):
        """ dump in process files at path """

    def sneechUpon(self, path):
        """ dump output at path """


class SneechWrangler:
    def __init__(self, path=None):
        # TODO make sneech path configurable and passable via command line etc.
        if path is None:
            self.rp_sneech = aug.RepoPath(auth.get_path('git-local-base') / 'sneechenator')
            if not self.rp_sneech.exists():
                self.rp_sneech.init()
                readme = self.rp_sneech / 'README.org'
                with open(readme, 'wt') as f:
                    f.write('#+title: Sneechenator\n\nTrack the stars for your sneeches!')

                readme.commit_from_working_tree('first commit')

                self.dir_index.mkdir()
                self.dir_process.mkdir()
        else:
            raise NotImplementedError('TODO')

    def new_index(self, name):
        path = self.path_index(name)
        if path.exists():
            raise FileExistsError(path)

        g = OntGraph(path=path)
        OntCuries.populate(g)
        s = ilx[f'tgbugs/ontologies/uris/sneechenator/indexes/{name}']
        g.add((s, rdf.type, ilxtr.SneechenatorIndexGraph))  # FIXME
        g.write()
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

    def path_index(self, index):
        return (self.dir_index / index).with_suffix('.ttl')

    @property
    def in_process_folder(self):
        """ There may be multiple in process folders """
        cwd = aug.RepoPath.cwd()
        if cwd.working_dir == self.rp_sneech.working_dir and self.logic_for_in_process:
            existing = cwd

    @property
    def existing_indexes(self):
        return list(set(index_graph.matchNamespace(index_namespace)))


class InterLexSneechenator(Sneechenator):
    file_index = 'interlex.ttl'

    def mappingReport(self, input_graph, *namespaces_to_square):
        squares, could_square, could_not_square = makeSquares(input_graph, *namespaces_to_square)
        circles, has_matches, no_matches = self.searchSquares(squares)

    def makeSquares(self, input_graph, *namespaces_to_square):
        """ input graph can and probably should be a conjuctive graph
            we will loudly announce if an identifier in the target graph
            cannot be squared due to missing information """
        if not namespaces_to_square:
            raise TypeError('at least on namespaces_to_square is required')

        could_square = []
        could_not_square = []
        for e in could_map:
            ps = self.makeSquare(rdll, e)
            breakpoint()
            return

        return squares, could_square, could_not_square

    def manuallyMapSquaresThatHaveCircles(self):
        # TODO
        pass

    def submitSquares(self, squares):
        pass


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
