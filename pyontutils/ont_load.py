#!/usr/bin/env python3.6
""" ontUse SciGraph to load an ontology from a loacal git repository.
 Remote imports are replaced with local imports.
 NIF -> http://ontology.neuinfo.org/NIF

Usage:
    ontload services [options] <repo>
    ontload extra [options] <repo>
    ontload imports [options] <repo> <remote_base> <ontologies>...
    ontload chain [options] <repo> <remote_base> <ontologies>...
    ontload uri-switch [options] <repo>
    ontload [options] <repo> <remote_base>

Options:
    -g --git-remote=GBASE           remote git hosting [default: https://github.com/]
    -l --git-local=LBASE            local path to look for ontology <repo> [default: /tmp]
    -z --zip-location=ZIPLOC        local path in which to deposit zipped files [default: /tmp]

    -t --graphload-template=CFG     rel path to graphload.yaml template [default: scigraph/graphload-template.yaml]
    -o --org=ORG                    user/org to clone/load ontology from [default: SciCrunch]
    -b --branch=BRANCH              ontology branch to load [default: master]
    -c --commit=COMMIT              ontology commit to load [default: HEAD]

    -e --services-template=SCFG     rel path to services.yaml template [default: scigraph/services-template.yaml]
    -r --scigraph-org=SORG          user/org to clone/build scigraph from [default: SciCrunch]
    -a --scigraph-branch=SBRANCH    scigraph branch to build [default: upstream]
    -m --scigraph-commit=SCOMMIT    scigraph commit to build [default: HEAD]

    -u --curies=CURIEFILE           relative path to curie definition file [default: scigraph/nifstd_curie_map.yaml]

    -h --host=HOST                  host where services will run
    -d --deploy-location=DLOC       override config folder where the graph will live [default: from-config]

    -f --logfile=LOG                log output here [default: ontload.log]
"""
import os
import shutil
import json
import yaml
from io import BytesIO
from glob import glob
from contextlib import contextmanager
import rdflib
import requests
from lxml import etree
from git.repo import Repo
from pyontutils.utils import makeGraph, makePrefixes, memoryCheck, noneMembers, TODAY, setPS1  # TODO make prefixes needs an all...
from pyontutils.hierarchies import creatTree
from collections import namedtuple
from docopt import docopt
from IPython import embed

setPS1(__file__)

bigleaves = 'go.owl', 'uberon.owl', 'pr.owl', 'doid.owl', 'taxslim.owl', 'chebislim.ttl', 'ero.owl'

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

@contextmanager
def checkout_when_done(original_branch):
    try:
        yield
    finally:
        original_branch.checkout()  # FIXME this fails in the case where we have modified files on the head of another branch instead of a detached head!

def getBranch(repo, branch):
    try:
        return [b for b in repo.branches if b.name == branch][0]
    except IndexError:
        branches = [b.name for b in repo.branches]
        raise ValueError('No branch %s found, options are %s' % (branch, branches))

def repro_loader(zip_location, git_remote, org, git_local, repo_name, branch, commit, remote_base, load_base, graphload_template, scigraph_commit, post_clone=lambda: None):
    local_base = os.path.join(git_local, repo_name)
    git_base = os.path.join(git_remote, org, repo_name)
    if not os.path.exists(local_base):
        repo = Repo.clone_from(git_base + '.git', local_base)
        post_clone()  # FIXME if this does not complete we need to warn or something, it causes errors
    else:
        repo = Repo(local_base)
    nob = repo.active_branch
    try:
        nab = getBranch(repo, branch)
        nab.checkout()
    except ValueError:  # usually indicates a remote branch
        repo.git.checkout(branch)
        nab = repo.active_branch
    repo.remote().pull()  # make sure we are up to date
    if commit != 'HEAD':
        repo.git.checkout(commit)

    # TODO consider dumping metadata in a file in the folder too?
    def folder_name(scigraph_commit, wild=False):
        ontology_commit = repo.head.object.hexsha[:7]
        return (repo_name +
                '-' + branch +
                '-graph' +
                '-' + ('*' if wild else TODAY) +
                '-' + scigraph_commit[:7] +
                '-' + ontology_commit)

    def make_folder_zip(wild=False):
        folder = folder_name(scigraph_commit, wild)
        graph_path = os.path.join(zip_location, folder)
        zip_path = graph_path + '.zip'
        if wild:
            return graph_path, zip_path
        zip_name = os.path.basename(zip_path)
        zip_dir = os.path.dirname(zip_path)
        zip_command = ' '.join(('cd', zip_dir, ';', 'zip -r', zip_name, folder))
        return graph_path, zip_path, zip_command
    
    graph_path, zip_path, zip_command = make_folder_zip()
    wild_graph_path, wild_zip_path = make_folder_zip(wild=True)

    # config graphload.yaml from template
    with open(os.path.join(local_base, graphload_template), 'rt') as f:
        config = yaml.load(f)

    config['graphConfiguration']['location'] = graph_path
    config['ontologies'] = [{k:v.replace(remote_base, local_base)
                             if k == 'url'
                             else v
                             for k, v in ont.items()}
                            for ont in config['ontologies']]

    config_path = os.path.join(zip_location, 'graphload-' + TODAY + '.yaml')
    with open(config_path, 'wt') as f:
        yaml.dump(config, f, default_flow_style=False)
    ontologies = [ont['url'] for ont in config['ontologies']]
    load_command = load_base.format(config_path=config_path)
    print(load_command)

    with checkout_when_done(nob):  # FIXME start this immediately after we obtain nob?
        # main
        itrips = local_imports(remote_base, local_base, ontologies)  # SciGraph doesn't support catalog.xml
        if not glob(wild_zip_path):
            failure = os.system(load_command)
            if failure:
                if os.path.exists(graph_path):
                    shutil.rmtree(graph_path)
            else:
                os.rename(config_path,  # save the config for eaiser debugging
                          os.path.join(graph_path,
                                       os.path.basename(config_path)))
                failure = os.system(zip_command)  # graphload zip
        else:
            print('Graph already loaded at', graph_path)

    # return to original state (reset --hard)
    repo.head.reset(index=True, working_tree=True)

    return zip_path, itrips

def scigraph_build(zip_location, git_remote, org, git_local, branch, commit, clean=False):
    COMMIT_LOG = 'last-built-commit.log'
    repo_name = 'SciGraph'
    remote = os.path.join(git_remote, org, repo_name)
    local = os.path.join(git_local, repo_name)
    commit_log_path = os.path.join(local, COMMIT_LOG)

    load_base = (
        'cd {}; '.format(os.path.join(local, 'SciGraph-core')) + 
        'mvn exec:java '
        '-Dexec.mainClass="io.scigraph.owlapi.loader.BatchOwlLoader" '
        '-Dexec.args="-c {config_path}"')

    if not os.path.exists(local):
        repo = Repo.clone_from(remote + '.git', local)
    else:
        repo = Repo(local)

    if not os.path.exists(commit_log_path):
        last_commit = None
    else:
        with open(commit_log_path, 'rt') as f:
            last_commit = f.read().strip()

    sob = repo.active_branch
    try:
        sab = getBranch(repo, branch)
        sab.checkout()
    except ValueError:  # usually indicates a remote branch
        repo.git.checkout(branch)
        sab = repo.active_branch
    repo.remote().pull()
    if commit != 'HEAD':
        repo.git.checkout(commit)
    scigraph_commit = repo.head.object.hexsha

    def zip_name(wild=False):
        return (repo_name +
                '-' + branch +
                '-services' +
                '-' + ('*' if wild else TODAY) +
                '-' + scigraph_commit[:7] +
                '.zip')

    with checkout_when_done(sob):  # FIXME this fails when we need to load the graph if we start on master :/
        # main
        if scigraph_commit != last_commit or clean:
            print('SciGraph not built at commit', commit, 'last built at', last_commit)
            build_command = ('cd ' + local +
                             '; mvn clean -DskipTests -DskipITs install'
                             '; cd SciGraph-services'
                             '; mvn -DskipTests -DskipITs package')
            out = os.system(build_command)
            print(out)
            if out:
                scigraph_commit = 'FAILURE'
            with open(commit_log_path, 'wt') as f:
                f.write(scigraph_commit)
        else:
            print('SciGraph already built at commit', scigraph_commit)
            wildcard = os.path.join(zip_location, zip_name(wild=True))
            try:
                services_zip = glob(wildcard)[0]  # this will error if the zip was moved
                return scigraph_commit, load_base, services_zip
            except IndexError:
                pass  # we need to copy the zip out again

        # services zip
        zip_filename =  'scigraph-services-*-SNAPSHOT.zip'
        services_zip_temp = glob(os.path.join(local, 'SciGraph-services', 'target', zip_filename))[0]
        services_zip = os.path.join(zip_location, zip_name())
        shutil.copy(services_zip_temp, services_zip)

    return scigraph_commit, load_base, services_zip

def local_imports(remote_base, local_base, ontologies, readonly=False, dobig=False):
    """ Read the import closure and use the local versions of the files. """
    done = []
    triples = set()
    imported_iri_vs_ontology_iri = {}
    p = rdflib.OWL.imports
    oi = b'owl:imports'
    def inner(local_filepath, remote=False):
        if noneMembers(local_filepath, *bigleaves) or dobig:
            ext = os.path.splitext(local_filepath)[-1]
            if ext == '.ttl':
                infmt = 'turtle'
            else:
                print(ext, local_filepath)
                infmt = None
            if remote:
                resp = requests.get(local_filepath)  # TODO nonblocking pull these out, fetch, run inner again until done
                raw = resp.text.encode()
            else:
                try:
                    with open(local_filepath, 'rb') as f:
                        raw = f.read()
                except FileNotFoundError as e:
                    if local_filepath.startswith('file://'):
                        print('local_imports has already been run, skipping', local_filepath)
                        return
                        #raise ValueError('local_imports has already been run') from e
                    else:
                        print(e)
                        raw = b''
            if oi in raw:  # we only care if there are imports
                scratch = rdflib.Graph()
                if infmt == 'turtle':
                    start, ont_rest = raw.split(oi, 1)
                    ont, rest = ont_rest.split(b'###', 1)
                    data = start + oi + ont
                elif infmt == None:  # assume xml
                    xml_tree = etree.parse(BytesIO(raw))
                    xml_root = xml_tree.getroot()
                    xml_ontology = xml_tree.xpath("/*[local-name()='RDF']/*[local-name()='Ontology']")
                    xml_root.clear()
                    xml_root.append(xml_ontology[0])
                    data = etree.tostring(xml_root)
                scratch.parse(data=data, format=infmt)
                for s, o in sorted(scratch.subject_objects(p)):
                    nlfp = o.replace(remote_base, local_base)
                    triples.add((s, p, o))
                    if 'http://' in local_filepath or 'external' in local_filepath:  # FIXME what to do about https used inconsistently :/
                        if 'external' in local_filepath:
                            imported_iri = rdflib.URIRef(local_filepath.replace(local_base, remote_base))  # inefficient
                        else:
                            imported_iri = rdflib.URIRef(local_filepath)
                        if s != imported_iri:
                            imported_iri_vs_ontology_iri[imported_iri] = s  # kept for the record
                            triples.add((imported_iri, p, s))  # bridge imported != ontology iri
                    if local_base in nlfp and 'file://' not in o:  # FIXME file:// should not be slipping through here...
                        scratch.add((s, p, rdflib.URIRef('file://' + nlfp)))
                        scratch.remove((s, p, o))
                    if nlfp not in done:
                        done.append(nlfp)
                        if local_base in nlfp and 'external' not in nlfp:  # skip externals TODO
                            inner(nlfp)
                        elif readonly:  # read external imports
                            if 'external' in nlfp:
                                inner(nlfp)
                            else:
                                inner(nlfp, remote=True)
                if not readonly:
                    ttl = scratch.serialize(format='nifttl')
                    ndata, comment = ttl.split(b'###', 1)
                    out = ndata + b'###' + rest
                    with open(local_filepath, 'wb') as f:
                        f.write(out)

    for start in ontologies:
        print('START', start)
        done.append(start)
        inner(start)
    return sorted(triples)

def loadall(git_local, repo_name, local=False):
    cwd = os.getcwd()
    local_base = os.path.join(git_local, repo_name)
    lb_ttl = os.path.realpath(os.path.join(local_base, 'ttl'))

    if cwd == lb_ttl:
        print("WOOOOWOW")
        memoryCheck(2665488384)
    else:
        raise FileNotFoundError('Please run this in %s. You are in %s.' % (lb_ttl, cwd))

    graph = rdflib.Graph()

    #match = (rdflib.term.URIRef('http://purl.org/dc/elements/1.1/member'),  # iao.owl
             #rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
             #rdflib.term.URIRef('http://www.w3.org/2002/07/owl#AnnotationProperty'))
    done = []
    for f in glob('*/*/*.ttl') + glob('*/*.ttl') + glob('*.ttl'):
        print(f)
        done.append(os.path.basename(f))
        graph.parse(f, format='turtle')
        #if match in graph:
            #raise BaseException('Evil file found %s' % f)

    def repeat(dobig=False):  # we don't really know when to stop, so just adjust
        for s, o in graph.subject_objects(rdflib.OWL.imports):
            if os.path.basename(o) not in done and o not in done:
            #if (o, rdflib.RDF.type, rdflib.OWL.Ontology) not in graph:
                print(o)
                done.append(o)
                ext = os.path.splitext(o)[1]
                fmt = 'turtle' if ext == '.ttl' else 'xml'
                if noneMembers(o, *bigleaves) or dobig:
                    graph.parse(o, format=fmt)
                    #if match in graph:
                        #raise BaseException('Evil file found %s' % o)

    #if local:
        #repeat(False)
    #else:
    if not local:
        for i in range(10):
            repeat(True)

    return graph

def normalize_prefixes(graph, curies):
    mg = makeGraph('nifall', makePrefixes('owl', 'skos', 'oboInOwl'), graph=graph)
    mg.del_namespace('')

    old_namespaces = list(graph.namespaces())
    ng_ = makeGraph('', prefixes=makePrefixes('oboInOwl', 'skos'))
    [ng_.g.add(t) for t in mg.g]
    [ng_.add_namespace(n, p) for n, p in curies.items() if n != '']
    #[mg.add_namespace(n, p) for n, p in old_namespaces if n.startswith('ns') or n.startswith('default')]
    #[mg.del_namespace(n) for n in list(mg.namespaces)]
    #graph.namespace_manager.reset()
    #[mg.add_namespace(n, p) for n, p in wat.items() if n != '']
    return mg, ng_

def import_tree(graph):
    mg = makeGraph('', graph=graph)
    mg.add_known_namespace('owl')
    mg.add_known_namespace('obo')
    mg.add_known_namespace('dc')
    mg.add_known_namespace('dcterms')
    mg.add_known_namespace('dctypes')
    mg.add_known_namespace('skos')
    mg.add_known_namespace('NIFTTL')
    j = mg.make_scigraph_json('owl:imports', direct=True)
    t, te = creatTree(*Query('NIFTTL:nif.ttl', 'owl:imports', 'OUTGOING', 30), json=j, prefixes=mg.namespaces)
    #print(t)
    return t, te

def uri_switch(graph, curie_prefixes):
    #asdf = sorted(set(_ for t in graph for _ in t if type(_) == rdflib.URIRef))  # this snags a bunch of other URIs
    #asdf = sorted(set(_ for _ in graph.subjects() if type(_) != rdflib.BNode))
    asdf = set(_ for t in graph.subject_predicates() for _ in t if type(_) == rdflib.URIRef)
    prefs = set(_.rsplit('#', 1)[0] + '#' if '#' in _
                       else (_.rsplit('_',1)[0] + '_' if '_' in _
                             else _.rsplit('/',1)[0] + '/') for _ in asdf)
    nots = set(_ for _ in prefs if _ not in curie_prefixes)  # TODO
    sos = set(prefs) - set(nots)

    fragment_prefixes = {
        'birlex_':'FIXME_BIRLEX',  # FIXME
        'birnlex_':'BIRNLEX',
        'sao':'SAO',
        'sao-':'FIXME_SAO',  # FIXME
        #'nif_organ_',  # single and seems like a mistake for nlx_organ_
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
        'nlx_organ_':'NLXORGAN',
        'nlx_qual_':'NLXQUAL',
        'nlx_res_':'NLXRES',
        'nlx_sub_':'FIXME_NLXSUBCELL',  # FIXME one off mistake for nlx_subcell?
        'nlx_subcell_':'NLXSUBCELL', 
        'nlx_ubo_':'NLXUBO',
        'nlx_uncl_':'NLXUNCL',
    }
    existing = {}
    NIFSTDBASE = 'http://uri.neuinfo.org/nif/nifstd/' 
    repacement_graph = createOntology('NIF*-NIFSTD-mapping',
                                      'NIF* to NIFSTD equivalents',
                                      makePrefixes('NIFMOL',
                                                   'NIFCELL',
                                                   'NIFDYS',
                                                  )
                                     )

    skip_namespaces = ('BIRNLex_annotation_properties.owl#',
                       'OBO_annotation_properties.owl#',
                      )
    def prefixFixes(pref):
        if pref == 'birlex_': return 'birnlex_'
        elif pref == 'sao-': return 'sao'
        elif pref == 'nlx_sub_': return 'nlx_subcell_'
        else: return pref

    def add_namespace(pref, g):
        makeGraph('', graph=g).add_namespace(fragment_prefixes[pref], NIFSTDBASE + pref)
        replacement_graph.add_namespace(fragment_prefixes[pref], NIFSTDBASE + pref)

    def swapPrefs(trip, g):  # TODO one last collision check for old times sake
        for spo in trip:
            done = False
            if not isinstance(spo, rdflib.URIRef):
                yield spo
                continue
            for pref in sorted(fragment_prefixes, key=lambda x:-len(x)):  # make sure we find the longest (even though the swap will still work as expected we would get bad data on suffixes)
                if noneMembers(spo, *skip_namespaces) and pref in spo:
                    prefix, suffix = spo.split(pref)
                    if pref + suffix in existing:
                        if prefix != existing[pref + suffix]:
                            print('WARNING multiple prefixes for', pref + suffix, prefix, existing[pref + suffix])
                    else:
                        existing[suffix] = prefix
                    pref = prefixFixes(pref)
                    new_spo = rdflib.URIRef(NIFSTDBASE + pref + suffix)
                    replacement_graph.g.add(spo, rdflib.OWL.sameAs, new_spo)
                    add_namespace(pref, g)
                    yield new_spo
                    done = True
                    break
            if not done:
                yield spo

    def switchURIs(g):
        for t in g:
            nt = tuple(swapPrefs(t, g))
            if t != nt:
                g.remove(t)
                g.add(nt)


    #to_rep = set(_.rsplit('#', 1)[-1].split('_', 1)[0] for _ in asdf if 'ontology.neuinfo.org' in _)
    to_rep = set(_.rsplit('#', 1)[-1] for _ in asdf if 'ontology.neuinfo.org' in _)
    things_that_need_interlex_ids = sorted(u for u in asdf if 'ontology.neuinfo.org' in u and noneMembers(u, *fragment_prefixes) and not u.endswith('.ttl'))

    filenames = glob('*/*/*.ttl') + glob('*/*.ttl') + glob('*.ttl')

    for filename in filenames:
        ng = rdflib.Graph()
        ng.parse(filename, format='turtle')
        switchURIs(ng)
        wg = makeGraph('', graph=ng)
        wg.filename = filename
        wg.write()

    replacement_graph.write()

    print(len(prefs))
    embed()


def for_burak(ng_):
    syn_predicates = (ng_.expand('OBOANN:synonym'),
                      ng_.expand('OBOANN:acronym'),
                      ng_.expand('OBOANN:abbrev'),
                      ng_.expand('oboInOwl:hasExactSynonym'),
                      ng_.expand('oboInOwl:hasNarrowSynonym'),
                      ng_.expand('oboInOwl:hasBroadSynonym'),
                      ng_.expand('oboInOwl:hasRelatedSynonym'),
                      ng_.expand('skos:prefLabel'),
                      rdflib.URIRef('http://purl.obolibrary.org/obo/go#systematic_synonym'),
                     )
    lab_predicates = rdflib.RDFS.label,
    def inner(ng):
        graph = ng.g
        for s in graph.subjects(rdflib.RDF.type, rdflib.OWL.Class):
            if not isinstance(s, rdflib.BNode):
                curie = ng.qname(s)
                labels = [o for p in lab_predicates for o in graph.objects(s, p)
                          if not isinstance(o, rdflib.BNode)]
                synonyms = [o for p in syn_predicates for o in graph.objects(s, p)
                            if not isinstance(o, rdflib.BNode)]
                parents = [ng.qname(o) for o in graph.objects(s, rdflib.RDFS.subClassOf)
                           if not isinstance(o, rdflib.BNode)]
                yield [curie, labels, synonyms, parents]

    records = {c:[l, s, p] for c, l, s, p in inner(ng_) if l or s}
    with open(os.path.expanduser('~/files/ontology-classes-with-labels-synonyms-parents.json'), 'wt') as f:
              json.dump(records, f, sort_keys=True, indent=2)

def main():
    args = docopt(__doc__, version='nif_load 0')
    print(args)

    repo_name = args['<repo>']
    remote_base = args['<remote_base>']
    if remote_base == 'NIF':
        remote_base = 'http://ontology.neuinfo.org/NIF'

    git_remote = args['--git-remote']
    git_local = args['--git-local']
    if '~' in git_local:
        git_local = os.path.expanduser(git_local)
    zip_location = args['--zip-location']

    graphload_template = args['--graphload-template']
    org = args['--org']
    branch = args['--branch']
    commit = args['--commit']

    services_template = args['--services-template']
    sorg = args['--scigraph-org']
    sbranch = args['--scigraph-branch']
    scommit = args['--scigraph-commit']

    curies_location = args['--curies']

    host = args['--host']  # TODO
    deploy_location = args['--deploy-location']

    log = args['--logfile']  # TODO

    def getCuries():
        with open(os.path.join(git_local, repo_name, curies_location), 'rt') as f:
            curies = yaml.load(f)
        curie_prefixes = set(curies.values())
        return curies, curie_prefixes

    itrips = None

    local_base = os.path.join(git_local, repo_name)

    if args['services']:  # TODO this could run when no specific is called as well?
        services_template_path = os.path.join(git_local, repo_name, services_template)
        services_path = os.path.join(git_local, repo_name, 'scigraph/services.yaml')
        with open(services_template_path, 'rt') as f:
            config = yaml.load(f)
        curies, _ = getCuries()
        config['graphConfiguration']['curies'] = curies
        if deploy_location != 'from-config':
            config['graphConfiguration']['location'] = deploy_location
        else:
            deploy_location = config['graphConfiguration']['location']
        with open(services_path, 'wt') as f:
            yaml.dump(config, f, default_flow_style=False)
    elif args['imports']:
        itrips = local_imports(remote_base, local_base, args['<ontologies>'])
        # TODO mismatch between import name and file name needs a better fix
    elif args['chain']:
        itrips = local_imports(remote_base, local_base, args['<ontologies>'], readonly=True)
    elif args['extra']:
        graph = loadall(git_local, repo_name)
        curies, _ = getCuries()
        mg, ng_ = normalize_prefixes(graph, curies)
        for_burak(ng_)
    elif args['uri-switch']:
        graph = loadall(git_local, repo_name, local=True)
        _, curie_prefixes = getCuries()
        uri_switch(graph, curie_prefixes)
    else:
        local_go = os.path.join(git_local, repo_name, 'ttl/external/go.owl')
        if repo_name == 'NIF-Ontology' and not os.path.exists(local_go):
            remote_go = os.path.join(remote_base, 'ttl/external/go.owl')
            def post_clone():
                print('Retrieving go.owl since it is not in the repo.')
                os.system('wget -O' + local_go + ' ' + remote_go)
        else:
            post_clone = lambda: None

        scigraph_commit, load_base, services_zip = scigraph_build(zip_location, git_remote, sorg, git_local, sbranch, scommit)
        graph_zip, itrips = repro_loader(zip_location, git_remote, org,
                                        git_local, repo_name, branch, commit,
                                        remote_base, load_base,
                                        graphload_template, scigraph_commit,
                                        post_clone=post_clone)
        print(graph_zip, services_zip, sep='\n')

    if itrips:
        import_graph = rdflib.Graph()
        [import_graph.add(t) for t in itrips]
        tree, extra = import_tree(import_graph)
        with open(os.path.join(zip_location, '{repo_name}-import-closure.html'.format(repo_name=repo_name)), 'wt') as f:
            f.write(extra.html)

    embed()

if __name__ == '__main__':
    main()
