#!/usr/bin/env python3.6
""" ontUse SciGraph to load an ontology from a loacal git repository.
 Remote imports are replaced with local imports.
 NIF -> http://ontology.neuinfo.org/NIF

Usage:
    ontload services [options] <repo>
    ontload extra [options] <repo>
    ontload [options] <repo> <remote_base>

Options:
    -g --git-remote=GBASE           remote git hosting [default: https://github.com/]
    -l --git-local=LBASE            local path to look for ontology <repo> [default: /tmp]
    -z --zip-location=ZIPLOC        local path in which to deposit zipped files [default: /tmp]

    -c --graphload-template=CFG     rel path to graphload.yaml template [default: scigraph/graphload-template.yaml]
    -o --org=ORG                    user/org to clone/load ontology from [default: SciCrunch]
    -b --branch=BRANCH              ontology branch to load [default: master]
    -m --commit=COMMIT              ontology commit to load [default: HEAD]

    -s --services-template=SCFG     rel path to services.yaml template [default: scigraph/services-template.yaml]
    -so --scigraph-org=SORG         user/org to clone/build scigraph from [default: SciCrunch]
    -sb --scigraph-branch=SBRANCH   scigraph branch to build [default: upstream]
    -sm --scigraph-commit=SCOMMIT   scigraph commit to build [default: HEAD]

    -cu --curies=CURIEFILE          relative path to curie definition file [default: scigraph/nifstd_curie_map.yaml]

    -h --host=HOST                  host where services will run
    -f --logfile=LOG                log output here [default: ontload.log]
"""
import os
import shutil
import json
import yaml
from glob import glob
import rdflib
from git.repo import Repo
from pyontutils.utils import makeGraph, makePrefixes, memoryCheck, noneMembers, TODAY, setPS1  # TODO make prefixes needs an all...
from pyontutils.hierarchies import creatTree
from collections import namedtuple
from docopt import docopt
from IPython import embed

setPS1(__file__)

cwd = os.getcwd()

bigleaves = 'go.owl', 'uberon.owl', 'pr.owl', 'doid.owl', 'taxslim.owl', 'chebislim.ttl', 'ero.owl'

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

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
    else:
        repo = Repo(local_base)
    nob = repo.active_branch
    try:
        nab = getBranch(repo, branch)
        nab.checkout()
    except ValueError:  # usually a remote branch
        repo.git.checkout(branch)
        nab = repo.active_branch
    repo.remote().pull()  # make sure we are up to date
    post_clone()

    # TODO consider dumping metadata in a file in the folder too?
    def folder_name(scigraph_commit):
        ontology_commit = repo.head.object.hexsha[:7]
        return (repo_name +
                '-' + branch +
                '-graph' +
                '-' + TODAY +
                '-' + scigraph_commit[:7] +
                '-' + ontology_commit)

    folder = folder_name(scigraph_commit)
    graph_path = os.path.join(zip_location, folder)
    zip_path = graph_path + '.zip'

    zip_name = os.path.basename(zip_path)
    zip_dir = os.path.dirname(zip_path)
    zip_command = ' '.join(('cd', zip_dir, ';', 'zip -r', zip_name, folder))

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

    # main
    import_triples = local_imports(remote_base, local_base, ontologies)  # SciGraph doesn't support catalog.xml
    if not os.path.exists(graph_path):

        failure = os.system(load_command)
        if failure:
            shutil.rmtree(graph_path)
        else:
            os.rename(config_path,  # save the config for eaiser debugging
                      os.path.join(graph_path,
                                   os.path.basename(config_path)))
            failure = os.system(zip_command)
    else:
        print('Graph already loaded at', graph_path)

    # return to original state
    repo.head.reset(index=True, working_tree=True)
    if nab != nob:
        nob.checkout()

    return zip_path, import_triples

def scigraph_build(zip_location, git_remote, org, git_local, branch, commit, clean=False):  # TODO allow exact commit?
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
    except ValueError:  # usually a remote branch
        repo.git.checkout(branch)
        sab = repo.active_branch
    repo.remote().pull()
    commit = repo.head.object.hexsha

    if commit != last_commit or clean:
        print('SciGraph not built at commit', commit, 'last built at', last_commit)
        build_command = ('cd ' + local +
                         '; mvn clean -DskipTests -DskipITs install'
                         '; cd SciGraph-services'
                         '; mvn -DskipTests -DskipITs package')
        out = os.system(build_command)
        print(out)
        if out:
            commit = 'FAILURE'
        with open(commit_log_path, 'wt') as f:
            f.write(commit)
    else:
        print('SciGraph already built at commit', commit)

    zip_filename =  'scigraph-services-*-SNAPSHOT.zip'
    services_zip_temp = glob(os.path.join(local, 'SciGraph-services', 'target', zip_filename))[0]
    def zip_name():
        return (repo_name +
                '-' + branch +
                '-services' +
                '-' + TODAY +
                '-' + commit[:7] +
                '.zip')
    services_zip = os.path.join(zip_location, zip_name())
    shutil.copy(services_zip_temp, services_zip)

    return commit, load_base, services_zip

def local_imports(remote_base, local_base, ontologies, dobig=False):
    """ Read the import closure and use the local versions of the files. """
    done = []
    triples = set()
    p = rdflib.OWL.imports
    oi = b'owl:imports'
    def inner(local_filepath):
        if noneMembers(local_filepath, *bigleaves) or dobig:
            ext = os.path.splitext(local_filepath)[-1]
            if ext == '.ttl':
                infmt = 'turtle'
            else:
                print(ext, local_filepath)
                infmt = None
            scratch = rdflib.Graph()
            try:
                with open(local_filepath, 'rb') as f:
                    raw = f.read()
            except FileNotFoundError as e:
                if local_filepath.startswith('file://'):
                    raise ValueError('local_imports has already been run') from e
            if oi in raw:  # we only care if there are imports
                start, ont_rest = raw.split(oi, 1)
                ont, rest = ont_rest.split(b'###', 1)
                data = start + oi + ont
                scratch.parse(data=data, format=infmt)
                for s, o in sorted(scratch.subject_objects(p)):
                    nlfp = o.replace(remote_base, local_base)
                    triples.add((s, p, o))
                    if local_base in nlfp:
                        scratch.add((s, p, rdflib.URIRef('file://' + nlfp)))
                        scratch.remove((s, p, o))
                    if nlfp not in done:
                        done.append(nlfp)
                        if local_base in nlfp and 'external' not in nlfp:  # skip externals
                            inner(nlfp)
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

def loadall(git_local, repo_name):
    local_base = os.path.join(git_local, repo_name)
    lb_ttl = os.path.join(local_base, 'ttl')

    if cwd == lb_ttl:
        print("WOOOOWOW")
        memoryCheck(2665488384)
    else:
        raise FileNotFoundError('Please run this in %s' % lb_ttl) 

    graph = rdflib.Graph()

    done = []
    for f in glob('*/*/*.ttl') + glob('*/*.ttl') + glob('*.ttl'):
        print(f)
        done.append(os.path.basename(f))
        graph.parse(f, format='turtle')

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

    for i in range(4):
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

def import_tree(graph, curie_prefixes):
    mg = makeGraph('', graph=graph)
    mg.add_known_namespace('owl')
    mg.add_known_namespace('NIFTTL')
    j = mg.make_scigraph_json('owl:imports', direct=True)
    #asdf = sorted(set(_ for t in graph for _ in t if type(_) == rdflib.URIRef))  # this snags a bunch of other URIs
    #asdf = sorted(set(_ for _ in graph.subjects() if type(_) != rdflib.BNode))
    asdf = set(_ for t in graph.subject_predicates() for _ in t if type(_) == rdflib.URIRef)
    prefs = set(_.rsplit('#', 1)[0] + '#' if '#' in _
                       else (_.rsplit('_',1)[0] + '_' if '_' in _
                             else _.rsplit('/',1)[0] + '/') for _ in asdf)
    nots = set(_ for _ in prefs if _ not in curie_prefixes)  # TODO
    sos = set(prefs) - set(nots)

    print(len(prefs))
    t, te = creatTree(*Query('NIFTTL:nif.ttl', 'owl:imports', 'OUTGOING', 30), json=j)
    #print(t)
    return t, te

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

    curies = args['--curies']

    host = args['--host']

    with open(os.path.join(git_local, repo_name, curies), 'rt') as f:
        curies = yaml.load(f)
    curie_prefixes = set(curies.values())

    if args['services']:
        services_template_path = os.path.join(git_local, repo_name, services_template)
        services_path = os.path.join(git_local, repo_name, 'scigraph/services.yaml')
        with open(services_template_path, 'rt') as f:
            config = yaml.load(f)
        config['graphConfiguration']['curies'] = curies
        with open(services_path, 'wt') as f:
            yaml.dump(config, f, default_flow_style=False)

    elif args['extra']:
        graph = loadall(git_local, repo_name)
        mg, ng_ = normalize_prefixes(graph, curies)
        for_burak(ng_)

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
            tree, extra = import_tree(import_graph, curie_prefixes)
            with open(os.path.join(zip_location, '{repo_name}-import-closure.html'.format(repo_name=repo_name)), 'wt') as f:
                f.write(extra.html)
    embed()

if __name__ == '__main__':
    main()
