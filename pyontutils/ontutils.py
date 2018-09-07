#!/usr/bin/env python3.6
#!/usr/bin/env pypy3
from pyontutils.core import devconfig
__doc__ = f"""Common commands for ontology processes.
Also old ontology refactors to run in the root ttl folder.

Usage:
    ontutils devconfig [--write] [<field> ...]
    ontutils parcellation
    ontutils catalog-extras [options]
    ontutils iri-commit [options] <repo>
    ontutils deadlinks [options] <file> ...
    ontutils scigraph-stress [options]
    ontutils spell [options] <file> ...
    ontutils version-iri [options] <file>...
    ontutils uri-switch [options] <file>...
    ontutils backend-refactor [options] <file>...
    ontutils todo [options] <repo>
    ontutils expand <curie>...

Options:
    -a --scigraph-api=API           SciGraph API endpoint   [default: {devconfig.scigraph_api}]
    -o --output-file=FILE           output file
    -l --git-local=LBASE            local git folder        [default: {devconfig.git_local_base}]
    -u --curies=CURIEFILE           curie definition file   [default: {devconfig.curies}]
    -e --epoch=EPOCH                specify the epoch to use for versionIRI
    -r --rate=Hz                    rate in Hz for requests, zero is no limit  [default: 20]
    -t --timeout=SECONDS            timeout in seconds for deadlinks requests  [default: 5]
    -f --fetch                      fetch catalog extras from their remote location
    -d --debug                      call IPython embed when done
    -v --verbose                    verbose output
    -w --write                      write devconfig file
"""
import os
from glob import glob
from time import time, localtime, strftime
from random import shuffle
from pathlib import Path
import rdflib
import requests
from joblib import Parallel, delayed
from git.repo import Repo
from pyontutils.core import makeGraph, createOntology
from pyontutils.utils import noneMembers, anyMembers, Async, deferred, TermColors as tc
from pyontutils.ontload import loadall, locate_config_file, getCuries
from pyontutils.namespaces import makePrefixes, definition
from pyontutils.closed_namespaces import rdf, rdfs, owl, skos
from IPython import embed

try:
    import hunspell
except ImportError:
    hunspell = None

# common

zoneoffset = strftime('%z', localtime())

def do_file(filename, swap, *args):
    print('START', filename)
    ng = rdflib.Graph()
    ng.parse(filename, format='turtle')
    reps = switchURIs(ng, swap, *args)
    wg = makeGraph('', graph=ng)
    wg.filename = filename
    wg.write()
    print('END', filename)
    return reps

def switchURIs(g, swap, *args):
    if len(args) > 1:  # FIXME hack!
        _, fragment_prefixes = args
    reps = []
    prefs = {None}
    addpg = makeGraph('', graph=g)
    for t in g:
        nt, ireps, iprefs = tuple(zip(*swap(t, *args)))
        if t != nt:
            g.remove(t)
            g.add(nt)

        for rep in ireps:
            if rep is not None:
                reps.append(rep)

        for pref in iprefs:
            if pref not in prefs:
                prefs.add(pref)
                addpg.add_known_namespaces(fragment_prefixes[pref])
    return reps

class ontologySection:
    def __init__(self, filename):
        self.filename = filename
        with open(self.filename, 'rb') as f:
            raw = f.read()
            ontraw, self.rest = raw.split(b'###', 1)
        self.graph = rdflib.Graph().parse(data=ontraw, format='turtle')

    def write(self):
        ontraw_comment = self.graph.serialize(format='nifttl')
        ontraw, comment = ontraw_comment.split(b'###', 1)
        with open(self.filename, 'wb') as f:
            f.write(ontraw)
            f.write(b'###')
            f.write(self.rest)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.write()

#
# utils

def catalog_extras(fetch=False):
    path = Path(devconfig.ontology_local_repo, 'ttl')
    cat = (path / 'catalog-v001.xml').as_posix()
    with open((path / '../catalog-extras').as_posix(), 'rt') as ce, open(cat, 'rt') as c:
        clines = c.readlines()
        celines = ce.readlines()

    if clines[-2] != celines[-1]:
        with open(cat, 'wt') as f:
            f.writelines(clines[:-1] + celines + clines[-1:])
    else:
        print(tc.blue('INFO:'), 'extras already added to catalog doing nothing')

    if fetch:
        print(tc.blue('INFO:'), 'fetching extras')
        def fetch_and_save(url, loc):
            resp = requests.get(url)
            saveloc = (path / loc).as_posix()
            if resp.ok:
                with open(saveloc, 'wb') as f:
                    f.write(resp.content)

                print(tc.blue('INFO:'), f'{url:<60} written to {loc}')
            else:
                print(tc.red('WARNING:'), f'failed to fetch {url}')


        Async()(deferred(fetch_and_save)(url, loc) for line in celines
                    for _, _, _, url, _, loc, _ in (line.split('"'),))


def spell(filenames, debug=False):
    if hunspell is None:
        raise ImportError('hunspell is not installed on your system. If you want '
                          'to run `ontutils spell` please run pipenv install --dev --skip-lock. '
                          'You will need the development libs for hunspell on your system.')
    spell_objects = (u for r in Parallel(n_jobs=9)(delayed(get_spells)(f) for f in filenames) for u in r)
    hobj = hunspell.HunSpell('/usr/share/hunspell/en_US.dic', '/usr/share/hunspell/en_US.aff')
    #nobj = hunspell.HunSpell(os.path.expanduser('~/git/domain_wordlists/neuroscience-en.dic'), '/usr/share/hunspell/en_US.aff')  # segfaults without aff :x
    collect = set()
    for filename, s, p, o in spell_objects:
        missed = False
        no = []
        for line in o.split('\n'):
            nline = []
            for tok in line.split(' '):
                prefix, tok, suffix = tokstrip(tok)
                #print((prefix, tok, suffix))
                if not hobj.spell(tok):# and not nobj.spell(tok):
                    missed = True
                    collect.add(tok)
                    nline.append(prefix + tc.red(tok) + suffix)
                else:
                    nline.append(prefix + tok + suffix)
            line = ' '.join(nline)
            no.append(line)
        o = '\n'.join(no)
        if missed:
            #print(filename, s, o)
            print('>>>', o)

    if debug:
        [print(_) for _ in sorted(collect)]
        embed()

_bads = (',', ';', ':', '"', "'", '(', ')', '[',']','{','}',
         '.', '-', '/',  '\\t', '\\n', '\\', '%', '$', '*',
         '`', '#', '@', '=', '?', '|', '<', '>', '+', '~')
def tokstrip(tok, side=None):
    front = ''
    back = ''
    for bad in _bads:
        if side is None or True:
            ftok = tok[1:] if tok.startswith(bad) else tok
            if ftok != tok:
                front = front + bad
                f, tok = tokstrip(ftok, True)
                front = front + f
        if side is None or False:
            btok = tok[:1] if tok.endswith(bad) else tok
            if btok != tok:
                back = bad + back
                tok, b = tokstrip(btok, False)
                back = b + back
    if side is None:
        return front, tok, back
    elif side:
        return front, tok
    else:
        return tok, back


def get_spells(filename):
    check_spelling = {skos.definition, definition, rdfs.comment}
    return [(filename, s, p, o) for s, p, o in rdflib.Graph().parse(filename, format='turtle') if p in check_spelling]

def scigraph_stress(rate, timeout=5, verbose=False, debug=False, scigraph=devconfig.scigraph_api):
    # TODO use the api classes
    with open((Path(__file__).resolve().absolute().parent / 'resources' / 'chebi-subset-ids.txt').as_posix(), 'rt') as f:
        urls = [os.path.join(scigraph, f'vocabulary/id/{curie.strip()}') for curie in f.readlines()]
    print(urls)
    url_blaster(urls, rate, timeout, verbose, debug)

def deadlinks(filenames, rate, timeout=5, verbose=False, debug=False):
    urls = list(set(u for r in Parallel(n_jobs=9)(delayed(furls)(f) for f in filenames) for u in r))
    url_blaster(urls, rate, timeout, verbose, debug)

def url_blaster(urls, rate, timeout=5, verbose=False, debug=False, method='head', fail=False, negative=False):
    shuffle(urls)  # try to distribute timeout events evenly across workers
    if verbose:
        [print(u) for u in sorted(urls)]

    class Timedout:
        ok = False
        def __init__(self, url):
            self.url = url

    r_method = getattr(requests, method)
    def method_timeout(url, _method=r_method):
        try:
            return _method(url, timeout=timeout)
        except (requests.ConnectTimeout, requests.ReadTimeout) as e:
            print('Timedout:', url, e)
            return Timedout(url)
    s = time()
    collector = [] if debug else None
    all_ = Async(rate=rate, debug=verbose, collector=collector)(deferred(method_timeout)(url) for url in urls)
    o = time()
    not_ok = [_.url for _ in all_ if not _.ok]
    d = o - s
    print(f'Actual time: {d}    Effective rate: {len(urls) / d}Hz    diff: {(len(urls) / d) / rate if rate else 1}')
    print('Failed:')
    if not_ok:
        for nok in not_ok:
            print(nok)
        ln = len(not_ok)
        lt = len(urls)
        lo = lt - ln
        msg = f'{ln} urls out of {lt} ({ln / lt * 100:2.2f}%) are not ok. D:'
        print(msg)  # always print to get around joblib issues
        if negative and fail:
            if len(not_ok) == len(all_):
                raise AssertionError('Everything failed!')
        elif fail:
            raise AssertionError(f'{msg}\n' + '\n'.join(sorted(not_ok)))

    else:
        print(f'OK. All {len(urls)} urls passed! :D')
    if debug:
        from matplotlib.pyplot import plot, savefig, figure, show, legend, title
        from collections import defaultdict
        def asyncVis(collector):
            by_thread = defaultdict(lambda: [[], [], [], [], [], [], [], []])
            min_ = 0
            for thread, job, start, target_stop, stop, time_per_job, p, i, d in sorted(collector):
                if not min_:
                    min_ = stop
                by_thread[thread][0].append(job)
                #by_thread[thread][1].append(start - min_)
                by_thread[thread][2].append(target_stop - stop)
                by_thread[thread][3].append(stop - min_)
                by_thread[thread][4].append(time_per_job)
                by_thread[thread][5].append(p)
                by_thread[thread][6].append(i)
                by_thread[thread][7].append(d)

            for thread, (job, y1, y2, y3, y4, y5, y6, y7) in by_thread.items():
                figure()
                title(str(thread))
                plot(job, [0] * len(job), 'r-')
                #plot(job, y1, label=f'stop')
                plot(job, y2, label=f'early by')
                #plot(job, y3, label=f'stop')
                #plot(job, y4, label=f'time per job')  # now constant...
                plot(job, y5, label='P')
                plot(job, y6, label='I')
                plot(job, y7, label='D')
                legend()
            show()
        asyncVis(collector)
        embed()


def furls(filename):
    return set(url for t in rdflib.Graph().parse(filename, format='turtle')
               for url in t if isinstance(url, rdflib.URIRef) and not url.startswith('file://'))

def version_iris(*filenames, epoch=None):
    # TODO make sure that when we add versionIRIs the files we are adding them to are either unmodified or in the index
    if epoch is None:
        epoch = int(time())
    Parallel(n_jobs=9)(delayed(version_iri)(f, epoch) for f in filenames)

def version_iri(filename, epoch):
    with ontologySection(filename) as ont:
        add_version_iri(ont.graph, epoch)

def make_version_iri_from_iri(iri, epoch):
    base = os.path.dirname(iri)
    basename = os.path.basename(iri)
    name, ext = os.path.splitext(basename)
    newiri = f'{base}/{name}/version/{epoch}/{basename}'
    print(newiri)
    return rdflib.URIRef(newiri)

def add_version_iri(graph, epoch):
    """ Also remove the previous versionIRI if there was one."""
    for ont in graph.subjects(rdf.type, owl.Ontology):
        for versionIRI in graph.objects(ont, owl.versionIRI):
            graph.remove((ont, owl.versionIRI, versionIRI))
        t = ont, owl.versionIRI, make_version_iri_from_iri(ont, epoch)
        graph.add(t)

def validate_new_version_iris(diffs):  # TODO
    for diff in diffs:
        diff.diff.split('\n')

def make_git_commit_command(git_local, repo_name):
    # TODO also need to get the epochs for all unchanged files and make sure that the max of those is less than commit_epoch...
    repo_path = os.path.join(git_local, repo_name)
    print(repo_path)
    repo = Repo(repo_path)
    diffs = repo.index.diff(None) + repo.index.diff(repo.head.commit)  # not staged + staged; cant use create_patch=True...
    filenames = [d.a_path for d in diffs if d.change_type == 'M']
    print(filenames)
    #validate_new_version_iris(something)  # TODO
    min_epoch = get_epoch(*filenames)
    other_filenames = [f for f in repo.git.ls_files().split('\n') if f not in filenames and f.endswith('.ttl')]
    max_old_epoch = get_epoch(*other_filenames, min_=False)
    print(min_epoch, max_old_epoch)
    assert min_epoch - max_old_epoch >= 2, "NOPE"
    commit_epoch = min_epoch
    print(f'git commit --date {commit_epoch}{zoneoffset}')

def get_epoch(*filenames, min_=True):
    comp_epoch = None
    for f in filenames:
        graph = ontologySection(f).graph
        for ont in graph.subjects(rdf.type, owl.Ontology):
            for versionIRI in graph.objects(ont, owl.versionIRI):
                base, epoch, filename = versionIRI.rsplit('/', 2)
                epoch = int(epoch)
                print(epoch)
                if comp_epoch is None:
                    comp_epoch = epoch
                elif min_ and epoch < comp_epoch:
                    comp_epoch = epoch
                elif not min_ and epoch > comp_epoch:
                    comp_epoch = epoch
    print('min' if min_ else 'max', comp_epoch)
    if comp_epoch is None:
        if min_:
            return 0
        else:
            return 0  # XXX this may cause errors down the line

    return comp_epoch

#
# refactors

#
# uri switch

NIFSTDBASE = 'http://uri.neuinfo.org/nif/nifstd/'
def uri_switch_values(utility_graph):

    fragment_prefixes = {
        'NIFRID':'NIFRID',
        'NIFSTD':'NIFSTD',  # no known collisions, mostly for handling ureps
        'birnlex_':'BIRNLEX',
        'sao':'SAO',
        'sao-':'FIXME_SAO',  # FIXME
        'nif_organ_':'FIXME_NIFORGAN',  # single and seems like a mistake for nlx_organ_
        'nifext_':'NIFEXT',
        #'nifext_5007_',  # not a prefix
        'nlx_':'NLX',
        #'nlx_0906_MP_',  # not a prefix, sourced from mamalian phenotype ontology and prefixed TODO
        #'nlx_200905_',  # not a prefix
        'nlx_anat_':'NLXANAT',
        'nlx_cell_':'NLXCELL',
        'nlx_chem_':'NLXCHEM',
        'nlx_dys_':'NLXDYS',
        'nlx_func_':'NLXFUNC',
        'nlx_inv_':'NLXINV',
        'nlx_mol_':'NLXMOL',
        'nlx_neuron_nt_':'NLXNEURNT',
        'nlx_organ_':'NLXORG',
        'nlx_qual_':'NLXQUAL',
        'nlx_res_':'NLXRES',
        'nlx_sub_':'FIXME_NLXSUBCELL',  # FIXME one off mistake for nlx_subcell?
        'nlx_subcell_':'NLXSUB',   # NLXSUB??
        'nlx_ubo_':'NLXUBO',
        'nlx_uncl_':'NLXUNCL',
    }

    uri_replacements = {
        # Classes
        'NIFCELL:Class_6':'NIFSTD:Class_6',
        'NIFCHEM:CHEBI_18248':'NIFSTD:CHEBI_18248',
        'NIFCHEM:CHEBI_26020':'NIFSTD:CHEBI_26020',
        'NIFCHEM:CHEBI_27958':'NIFSTD:CHEBI_27958',
        'NIFCHEM:CHEBI_35469':'NIFSTD:CHEBI_35469',
        'NIFCHEM:CHEBI_35476':'NIFSTD:CHEBI_35476',
        'NIFCHEM:CHEBI_3611':'NIFSTD:CHEBI_3611',
        'NIFCHEM:CHEBI_49575':'NIFSTD:CHEBI_49575',
        'NIFCHEM:DB00813':'NIFSTD:DB00813',
        'NIFCHEM:DB01221':'NIFSTD:DB01221',
        'NIFCHEM:DB01544':'NIFSTD:DB01544',
        'NIFGA:Class_12':'NIFSTD:Class_12',
        'NIFGA:Class_2':'NIFSTD:Class_2',  # FIXME this record is not in neurolex
        'NIFGA:Class_4':'NIFSTD:Class_4',
        'NIFGA:FMAID_7191':'NIFSTD:FMA_7191',  # FIXME http://neurolex.org/wiki/FMA:7191
        'NIFGA:UBERON_0000349':'NIFSTD:UBERON_0000349',
        'NIFGA:UBERON_0001833':'NIFSTD:UBERON_0001833',
        'NIFGA:UBERON_0001886':'NIFSTD:UBERON_0001886',
        'NIFGA:UBERON_0002102':'NIFSTD:UBERON_0002102',
        'NIFINV:OBI_0000470':'NIFSTD:OBI_0000470',
        'NIFINV:OBI_0000690':'NIFSTD:OBI_0000690',
        'NIFINV:OBI_0000716':'NIFSTD:OBI_0000716',
        'NIFMOL:137140':'NIFSTD:137140',
        'NIFMOL:137160':'NIFSTD:137160',
        'NIFMOL:D002394':'NIFSTD:D002394',
        'NIFMOL:D008995':'NIFSTD:D008995',
        'NIFMOL:DB00668':'NIFSTD:DB00668',
        'NIFMOL:GO_0043256':'NIFSTD:GO_0043256',  # FIXME http://neurolex.org/wiki/GO:0043256
        'NIFMOL:IMR_0000512':'NIFSTD:IMR_0000512',
        'NIFRES:Class_2':'NLX:293',  # FIXME note that neurolex still thinks Class_2 goes here... not to NIFGA:Class_2
        'NIFSUB:FMA_83604':'NIFSTD:FMA_83604',  # FIXME http://neurolex.org/wiki/FMA:83604
        'NIFSUB:FMA_83605':'NIFSTD:FMA_83605',  # FIXME http://neurolex.org/wiki/FMA:83605
        'NIFSUB:FMA_83606':'NIFSTD:FMA_83606',  # FIXME http://neurolex.org/wiki/FMA:83606
        'NIFUNCL:CHEBI_24848':'NIFSTD:CHEBI_24848',  # FIXME not in interlex and not in neurolex_full.csv but in neurolex (joy)
        'NIFUNCL:GO_0006954':'NIFSTD:GO_0006954',  # FIXME http://neurolex.org/wiki/GO:0006954
    }
    uri_reps_nonstandard = {
        # nonstandards XXX none of these collide with any other namespace
        # that we might like to use in the future under NIFSTD:namespace/
        # therefore they are being placed directly into NIFSTD and we will
        # work out the details and redirects later (some intlerlex classes
        # may need to be created) maybe when we do the backend refactor.

        # Classes (from backend)
        'BIRNANN:_birnlex_limbo_class':'NIFRID:birnlexLimboClass',
        'BIRNANN:_birnlex_retired_class':'NIFRID:birnlexRetiredClass',
        rdflib.URIRef('http://ontology.neuinfo.org/NIF/Backend/DC_Term'):'NIFRID:dctermsClass',
        rdflib.URIRef('http://ontology.neuinfo.org/NIF/Backend/SKOS_Entity'):'NIFRID:skosClass',
        rdflib.URIRef('http://ontology.neuinfo.org/NIF/Backend/_backend_class'):'NIFRID:BackendClass',
        rdflib.URIRef('http://ontology.neuinfo.org/NIF/Backend/oboInOwlClass'):'NIFRID:oboInOwlClass',

        # NamedIndividuals
        'NIFORG:Infraclass':'NIFRID:Infraclass',  # only used in annotaiton but all other similar cases show up as named individuals
        'NIFORG:first_trimester':'NIFRID:first_trimester',
        'NIFORG:second_trimester':'NIFRID:second_trimester',
        'NIFORG:third_trimester':'NIFRID:third_trimester',

        # ObjectProperties not in OBOANN or BIRNANN
        'NIFGA:has_lacking_of':'NIFRID:has_lacking_of',
        'NIFNEURNT:has_molecular_constituent':'NIFRID:has_molecular_constituent',
        'NIFNEURNT:has_neurotransmitter':'NIFRID:has_neurotransmitter',
        'NIFNEURNT:molecular_constituent_of':'NIFRID:molecular_constituent_of',
        'NIFNEURNT:neurotransmitter_of':'NIFRID:neurotransmitter_of',
        'NIFNEURNT:soma_located_in':'NIFRID:soma_located_in',
        'NIFNEURNT:soma_location_of':'NIFRID:soma_location_of',

        # AnnotationProperties not in OBOANN or BIRNANN
        'NIFCHEM:hasStreetName':'NIFRID:hasStreetName',
        'NIFMOL:hasGenbankAccessionNumber':'NIFRID:hasGenbankAccessionNumber',
        'NIFMOL:hasLocusMapPosition':'NIFRID:hasLocusMapPosition',
        'NIFMOL:hasSequence':'NIFRID:hasSequence',
        'NIFORG:hasCoveringOrganism':'NIFRID:hasCoveringOrganism',
        'NIFORG:hasMutationType':'NIFRID:hasMutationType',
        'NIFORG:hasTaxonRank':'NIFRID:hasTaxonRank',
    }

    utility_graph.add_known_namespaces(*(c for c in fragment_prefixes.values() if 'FIXME' not in c))
    ureps = {utility_graph.expand(k):utility_graph.expand(v)
                        for k, v in uri_replacements.items()}
    ureps.update({utility_graph.check_thing(k):utility_graph.expand(v)
                  for k, v in uri_reps_nonstandard.items()})

    return fragment_prefixes, ureps

def uri_switch(filenames, get_values):
    replacement_graph = createOntology('NIF-NIFSTD-mapping',
                                       'NIF* to NIFSTD equivalents',
                                       makePrefixes(
                                           'BIRNANN', 'BIRNOBI', 'BIRNOBO', 'NIFANN',
                                           'NIFCELL', 'NIFCHEM', 'NIFDYS', 'NIFFUN',
                                           'NIFGA', 'NIFGG', 'NIFINV', 'NIFMOL',
                                           'NIFMOLINF', 'NIFMOLROLE', 'NIFNCBISLIM',
                                           'NIFNEURBR', 'NIFNEURBR2', 'NIFNEURCIR',
                                           'NIFNEURMC', 'NIFNEURMOR', 'NIFNEURNT',
                                           'NIFORG', 'NIFQUAL', 'NIFRES', 'NIFRET',
                                           'NIFSCID', 'NIFSUB', 'NIFUNCL', 'OBOANN',
                                           'SAOCORE')
                                      )
    fragment_prefixes, ureps = get_values(replacement_graph)
    print('Start writing')
    trips_lists = Parallel(n_jobs=9)(delayed(do_file)(f, swapUriSwitch, ureps, fragment_prefixes) for f in filenames)
    print('Done writing')
    [replacement_graph.g.add(t) for trips in trips_lists for t in trips]
    replacement_graph.write()

def swapUriSwitch(trip, ureps, fragment_prefixes):
    for spo in trip:
        if not isinstance(spo, rdflib.URIRef):
            yield spo, None, None
            continue
        elif spo in ureps:
            new_spo = ureps[spo]
            rep = (new_spo, owl.sameAs, spo)
            if 'nlx_' in new_spo:
                pref = 'nlx_'
            elif '/readable/' in new_spo:
                pref = 'NIFRID'
            else:
                pref = 'NIFSTD'
            yield new_spo, rep, pref
            continue
        elif anyMembers(spo,  # backend refactor
                        'BIRNLex_annotation_properties.owl#',
                        'OBO_annotation_properties.owl#'):
            _, suffix = spo.rsplit('#', 1)
            new_spo = rdflib.URIRef(os.path.join(NIFSTDBASE, 'readable', suffix))
            rep = (new_spo, owl.sameAs, spo)
            pref = 'NIFRID'
            yield new_spo, rep, pref
            continue

        try:
            uri_pref, fragment = spo.rsplit('#', 1)
            if '_' in fragment:
                frag_pref, p_suffix = fragment.split('_', 1)
                if not p_suffix[0].isdigit():
                    p, suffix = p_suffix.split('_', 1)
                    frag_pref = frag_pref + '_' + p
                else:
                    suffix = p_suffix
                frag_pref_ = frag_pref + '_'
                if frag_pref_ in fragment_prefixes:
                    if frag_pref_ == 'nlx_sub_': pref = 'nlx_subcell_'
                    elif frag_pref_ == 'nif_organ_': pref = 'nlx_organ_'
                    else: pref = frag_pref_  # come on branch predictor you can do it!
                elif frag_pref_ == 'nlx_neuron_':  # special case
                    rest = 'nt_'
                    suffix = suffix[len(rest):]
                    pref = frag_pref_ + rest
                else:
                    yield spo, None, None
                    continue
            elif 'sao' in fragment:
                suffix = fragment[3:].strip('-')
                pref = 'sao'
            else:
                yield spo, None, None
                continue
            new_spo = rdflib.URIRef(NIFSTDBASE + pref + suffix)
            if new_spo != spo:
                rep = (new_spo, owl.sameAs, spo)
            else:
                rep = None
                print('Already converted', spo)
            yield new_spo, rep, pref
        except ValueError:  # there was no # so do not split
            yield spo, None, None
            continue

#
# backend

def backend_refactor_values():
    uri_reps_lit = {
        # from https://github.com/information-artifact-ontology/IAO/blob/master/docs/BFO%201.1%20to%202.0%20conversion/mapping.txt
        'http://www.ifomis.org/bfo/1.1#Entity':'BFO:0000001',
        'BFO1SNAP:Continuant':'BFO:0000002',
        'BFO1SNAP:Disposition':'BFO:0000016',
        'BFO1SNAP:Function':'BFO:0000034',
        'BFO1SNAP:GenericallyDependentContinuant':'BFO:0000031',
        'BFO1SNAP:IndependentContinuant':'BFO:0000004',
        'BFO1SNAP:MaterialEntity':'BFO:0000040',
        'BFO1SNAP:Quality':'BFO:0000019',
        'BFO1SNAP:RealizableEntity':'BFO:0000017',
        'BFO1SNAP:Role':'BFO:0000023',
        'BFO1SNAP:Site':'BFO:0000029',
        'BFO1SNAP:SpecificallyDependentContinuant':'BFO:0000020',
        'BFO1SPAN:Occurrent':'BFO:0000003',
        'BFO1SPAN:ProcessualEntity':'BFO:0000015',
        'BFO1SPAN:Process':'BFO:0000015',
        'BFO1SNAP:ZeroDimensionalRegion':'BFO:0000018',
        'BFO1SNAP:OneDimensionalRegion':'BFO:0000026',
        'BFO1SNAP:TwoDimensionalRegion':'BFO:0000009',
        'BFO1SNAP:ThreeDimensionalRegion':'BFO:0000028',
        'http://purl.org/obo/owl/OBO_REL#bearer_of':'RO:0000053',
        'http://purl.org/obo/owl/OBO_REL#inheres_in':'RO:0000052',
        'ro:has_part':'BFO:0000051',
        'ro:part_of':'BFO:0000050',
        'ro:has_participant':'RO:0000057',
        'ro:participates_in':'RO:0000056',
        'http://purl.obolibrary.org/obo/OBI_0000294':'RO:0000059',
        'http://purl.obolibrary.org/obo/OBI_0000297':'RO:0000058',
        'http://purl.obolibrary.org/obo/OBI_0000300':'BFO:0000054',
        'http://purl.obolibrary.org/obo/OBI_0000308':'BFO:0000055',

        # more bfo
        'BFO1SNAP:SpatialRegion':'BFO:0000006',
        'BFO1SNAP:FiatObjectPart':'BFO:0000024',
        'BFO1SNAP:ObjectAggregate':'BFO:0000027',
        'BFO1SNAP:Object':'BFO:0000030',
        #'BFO1SNAP:ObjectBoundary'  # no direct replacement, only occurs in unused
        #'BFO1SPAN:ProcessAggregate'  # was not replaced, could simply be a process itself??
        #'BFO1SNAP:DependentContinuant'  # was not replaced

        # other
        #'ro:participates_in'  # above
        #'ro:has_participant'  # above
        #'ro:has_part',  # above
        #'ro:part_of',  # above
        #'ro:precedes'  # unused and only in inferred
        #'ro:preceded_by'  # unused and only in inferred
        #'ro:transformation_of'  # unused and only in inferred
        #'ro:transformed_into'  # unused and only in inferred

        'http://purl.org/obo/owl/obo#inheres_in':'RO:0000052',
        'http://purl.obolibrary.org/obo/obo#towards':'RO:0002503',
        'http://purl.org/obo/owl/pato#towards':'RO:0002503',

        'http://purl.obolibrary.org/obo/pato#inheres_in':'RO:0000052',
        'BIRNLEX:17':'RO:0000053',  # is_bearer_of
        'http://purl.obolibrary.org/obo/pato#towards':'RO:0002503',
        'ro:adjacent_to':'RO:0002220',

        'ro:derives_from':'RO:0001000',
        'ro:derives_into':'RO:0001001',

        'ro:agent_in':'RO:0002217',
        'ro:has_agent':'RO:0002218',

        'ro:contained_in':'RO:0001018',
        'ro:contains':'RO:0001019',

        'ro:located_in':'RO:0001025',
        'ro:location_of':'RO:0001015',

        'ro:has_proper_part':'NIFRID:has_proper_part',
        'ro:proper_part_of':'NIFRID:proper_part_of',  # part of where things are not part of themsevles need to review
    }
    ug = makeGraph('', prefixes=makePrefixes('ro', 'RO', 'BIRNLEX', 'NIFRID',
                                             'BFO', 'BFO1SNAP', 'BFO1SPAN'))
    ureps = {ug.check_thing(k):ug.check_thing(v)
             for k, v in uri_reps_lit.items()}

    return ureps

def swapBackend(trip, ureps):
    print(ureps)
    for spo in trip:
        if spo in ureps:
            new_spo = ureps[spo]
            rep = (new_spo, owl.sameAs, spo)
            yield new_spo, rep, None
        else:
            yield spo, None, None

def backend_refactor(filenames, get_values):
    ureps = get_values()
    print('Start writing')
    if len(filenames) == 1:
        trips_lists = [do_file(f, swapBackend, ureps) for f in filenames]
    else:
        trips_lists = Parallel(n_jobs=9)(delayed(do_file)(f, swapBackend, ureps) for f in filenames)
    print('Done writing')
    embed()

#
# graph todo

def graph_todo(graph, curie_prefixes, get_values):
    ug = makeGraph('big-graph', graph=graph)
    ug.add_known_namespaces('NIFRID')
    fragment_prefixes, ureps = get_values(ug)
    #all_uris = sorted(set(_ for t in graph for _ in t if type(_) == rdflib.URIRef))  # this snags a bunch of other URIs
    #all_uris = sorted(set(_ for _ in graph.subjects() if type(_) != rdflib.BNode))
    #all_uris = set(spo for t in graph.subject_predicates() for spo in t if isinstance(spo, rdflib.URIRef))
    all_uris = set(spo for t in graph for spo in t if isinstance(spo, rdflib.URIRef))
    prefs = set(_.rsplit('#', 1)[0] + '#' if '#' in _
                       else (_.rsplit('_',1)[0] + '_' if '_' in _
                             else _.rsplit('/',1)[0] + '/') for _ in all_uris)
    nots = set(_ for _ in prefs if _ not in curie_prefixes)  # TODO
    sos = set(prefs) - set(nots)
    all_uris = [u if u not in ureps
                else ureps[u]
                for u in all_uris]
    #to_rep = set(_.rsplit('#', 1)[-1].split('_', 1)[0] for _ in all_uris if 'ontology.neuinfo.org' in _)
    #to_rep = set(_.rsplit('#', 1)[-1] for _ in all_uris if 'ontology.neuinfo.org' in _)

    ignore = (
        # deprecated and only in as annotations
        'NIFGA:birnAnatomy_011',
        'NIFGA:birnAnatomy_249',
        'NIFORG:birnOrganismTaxon_19',
        'NIFORG:birnOrganismTaxon_20',
        'NIFORG:birnOrganismTaxon_21',
        'NIFORG:birnOrganismTaxon_390',
        'NIFORG:birnOrganismTaxon_391',
        'NIFORG:birnOrganismTaxon_56',
        'NIFORG:birnOrganismTaxon_68',
        'NIFINV:birnlexInvestigation_174',
        'NIFINV:birnlexInvestigation_199',
        'NIFINV:birnlexInvestigation_202',
        'NIFINV:birnlexInvestigation_204',
    )
    ignore = tuple(ug.expand(i) for i in ignore)


    non_normal_identifiers = sorted(u for u in all_uris
                                    if 'ontology.neuinfo.org' in u
                                    and noneMembers(u, *fragment_prefixes)
                                    and not u.endswith('.ttl')
                                    and not u.endswith('.owl')
                                    and u not in ignore)
    print(len(prefs))
    embed()

def main():
    from docopt import docopt
    args = docopt(__doc__, version='ontutils 0.0.1')

    verbose = args['--verbose']
    debug = args['--debug']

    repo_name = args['<repo>']

    git_local = os.path.expanduser(args['--git-local'])

    epoch = args['--epoch']

    curies_location = args['--curies']
    #curies_location = locate_config_file(curies_location, git_local)
    curies, curie_prefixes = getCuries(curies_location)

    filenames = args['<file>']
    filenames.sort(key=lambda f: os.path.getsize(f), reverse=True)  # make sure the big boys go first
    refactor_skip = ('nif.ttl',
                     'resources.ttl',
                     'generated/chebislim.ttl',
                     'unused/ro_bfo_bridge.ttl',
                     'generated/ncbigeneslim.ttl',
                     'generated/NIF-NIFSTD-mapping.ttl')
    rfilenames = [f for f in filenames if f not in refactor_skip]

    if args['devconfig']:
        if args['--write']:
            file = devconfig.write(args['--output-file'])
            print(f'config written to {file}')
        elif args['<field>']:
            for f in args['<field>']:
                print(getattr(devconfig, f, ''))
        else:
            print(devconfig)
    elif args['catalog-extras']:
        catalog_extras(args['--fetch'])
    elif args['version-iri']:
        version_iris(*filenames, epoch=epoch)
    elif args['scigraph-stress']:
        scigraph_stress(int(args['--rate']), int(args['--timeout']), verbose, debug)
    elif args['deadlinks']:
        deadlinks(filenames, int(args['--rate']), int(args['--timeout']), verbose, debug)
    elif args['spell']:
        spell(filenames, debug)
    elif args['iri-commit']:
        make_git_commit_command(git_local, repo_name)
    elif args['uri-switch']:
        uri_switch(rfilenames, uri_switch_values)
    elif args['backend-refactor']:
        backend_refactor(rfilenames, backend_refactor_values)
    elif args['todo']:
        graph = loadall(git_local, repo_name, local=True)
        graph_todo(graph, curie_prefixes, uri_switch_values)
        embed()
    elif args['expand']:
        curies['NLXWIKI'] = 'http://legacy.neurolex.org/wiki/'
        for curie in args['<curie>']:
            prefix, suffix = curie.split(':')
            print(curies[prefix] + suffix)

if __name__ == '__main__':
    main()
