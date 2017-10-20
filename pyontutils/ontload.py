#!/usr/bin/env python3.6
""" Use SciGraph to load an ontology from a loacal git repository.
 Remote imports are replaced with local imports.
 NIF -> http://ontology.neuinfo.org/NIF

Usage:
    ontload graph [options] <repo> <remote_base>
    ontload scigraph [options]
    ontload imports [options] <repo> <remote_base> <ontologies>...
    ontload chain [options] <repo> <remote_base> <ontologies>...
    ontload extra [options] <repo>
    ontload --view-defaults

Options:
    -g --git-remote=GBASE           remote git hosting [default: https://github.com/]
    -l --git-local=LBASE            local path to look for ontology <repo> [default: /tmp]
    -z --zip-location=ZIPLOC        local path in which to deposit build files [default: /tmp]
    -f --scigraph-config-folder=TP  templates files live here [default: ../scigraph/]

    -t --graphload-config=CFG       graphload.yaml location [default: graphload.yaml]
                                    if only the filename is given assued to be in scigraph-config-folder
                                    will look for *.template version of the file
    -o --org=ORG                    user/org to clone/load ontology from [default: SciCrunch]
    -b --branch=BRANCH              ontology branch to load [default: master]
    -c --commit=COMMIT              ontology commit to load [default: HEAD]
    -s --scp-loc=SCP                where to scp the zipped graph file [default: user@localhost:/tmp/graph/]

    -O --scigraph-org=SORG          user/org to clone/build scigraph from [default: SciCrunch]
    -B --scigraph-branch=SBRANCH    scigraph branch to build [default: upstream]
    -C --scigraph-commit=SCOMMIT    scigraph commit to build [default: HEAD]
    -S --scigraph-scp-loc=SGSCP     where to scp the zipped graph file [default: user@localhost:/tmp/scigraph/]

    -u --curies=CURIEFILE           curie definition file [default: nifstd_curie_map.yaml]
                                    if only the filename is given assued to be in scigraph-config-folder

    -K --check-built                check whether a local copy is present but do not build if it is not

    -d --debug                      call IPython embed when done
    -i --logfile=LOG                log output here [default: ontload.log]
    -v --view-defaults              print out the currently configured default values
"""
import os
import shutil
import json
import yaml
from os.path import join as jpth
from io import BytesIO
from glob import glob
from contextlib import contextmanager
import rdflib
import requests
from lxml import etree
from git.repo import Repo
from docopt import parse_defaults
from joblib import Parallel, delayed
from pyontutils.utils import makeGraph, makePrefixes, memoryCheck, noneMembers, TODAY, setPS1, refile  # TODO make prefixes needs an all...
from pyontutils.utils import rdf, rdfs, owl, skos, oboInOwl
from pyontutils.hierarchies import creatTree
from collections import namedtuple
from IPython import embed

defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}

COMMIT_HASH_HEAD_LEN = 7

setPS1(__file__)

bigleaves = 'go.owl', 'uberon.owl', 'pr.owl', 'doid.owl', 'taxslim.owl', 'chebislim.ttl', 'ero.owl'

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

class NotBuiltError(FileNotFoundError):
    pass

@contextmanager
def execute_regardless(function, only_exception=False):
    try:
        yield
    except BaseException as e:
        if only_exception:
            function()
        raise e
    finally:
        if not only_exception:
            function()

def getBranch(repo, branch):
    try:
        return [b for b in repo.branches if b.name == branch][0]
    except IndexError:
        branches = [b.name for b in repo.branches]
        raise ValueError('No branch %s found, options are %s' % (branch, branches))

def repro_loader(zip_location, git_remote, org, git_local, repo_name, branch, commit,
                 remote_base, load_base, graphload_config, scigraph_commit,
                 post_clone=lambda: None, check_built=False):
    local_base = jpth(git_local, repo_name)
    git_base = jpth(git_remote, org, repo_name)
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
        ontology_commit = repo.head.object.hexsha[:COMMIT_HASH_HEAD_LEN]
        return (repo_name +
                '-' + branch +
                '-graph' +
                '-' + ('*' if wild else TODAY) +
                '-' + scigraph_commit[:COMMIT_HASH_HEAD_LEN] +
                '-' + ontology_commit)

    def make_folder_zip(wild=False):
        folder = folder_name(scigraph_commit, wild)
        graph_path = jpth(zip_location, folder)
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
    graphload_config_template = graphload_config + '.template'
    with open(graphload_config_template, 'rt') as f:
        config = yaml.load(f)

    config['graphConfiguration']['location'] = graph_path
    config['ontologies'] = [{k:v.replace(remote_base, local_base)
                             if k == 'url'
                             else v
                             for k, v in ont.items()}
                            for ont in config['ontologies']]

    config_path = jpth(zip_location, 'graphload-' + TODAY + '.yaml')
    with open(config_path, 'wt') as f:
        yaml.dump(config, f, default_flow_style=False)
    ontologies = [ont['url'] for ont in config['ontologies']]
    load_command = load_base.format(config_path=config_path)
    print(load_command)


    def reset_state(original_branch=nob):
        original_branch.checkout()
        # return to original state (reset --hard)
        repo.head.reset(index=True, working_tree=True)  # FIXME we need to not run anything if there are files added to staging

    with execute_regardless(reset_state):  # FIXME start this immediately after we obtain nob?
        # main
        itrips = local_imports(remote_base, local_base, ontologies)  # SciGraph doesn't support catalog.xml
        maybe_zip_path = glob(wild_zip_path)
        if not maybe_zip_path:
            if check_built:
                print('The graph has not been loaded.')
                raise NotBuiltError('The graph has not been loaded.')
            failure = os.system(load_command)
            if failure:
                if os.path.exists(graph_path):
                    shutil.rmtree(graph_path)
            else:
                os.rename(config_path,  # save the config for eaiser debugging
                          jpth(graph_path,
                                       os.path.basename(config_path)))
                failure = os.system(zip_command)  # graphload zip
        else:
            zip_path = maybe_zip_path[0]  # this way we get the actual date
            print('Graph already loaded at', zip_path)


    return zip_path, itrips

def scigraph_build(zip_location, git_remote, org, git_local, branch, commit,
                   clean=False, check_built=False, cleanup_later=False):
    COMMIT_LOG = 'last-built-commit.log'
    repo_name = 'SciGraph'
    remote = jpth(git_remote, org, repo_name)
    local = jpth(git_local, repo_name)
    commit_log_path = jpth(local, COMMIT_LOG)

    load_base = (
        'cd {}; '.format(jpth(local, 'SciGraph-core')) + 
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
                '-' + scigraph_commit[:COMMIT_HASH_HEAD_LEN] +
                '.zip')

    def reset_state(original_branch=sob):
        original_branch.checkout()

    with execute_regardless(reset_state, only_exception=cleanup_later):  # FIXME this fails when we need to load the graph if we start on master :/
        # main
        if scigraph_commit != last_commit or clean:
            print('SciGraph not built at commit', commit, 'last built at', last_commit)
            build_command = ('cd ' + local +
                             '; mvn clean -DskipTests -DskipITs install'
                             '; cd SciGraph-services'
                             '; mvn -DskipTests -DskipITs package')
            if check_built:
                print('SciGraph has not been built.')
                raise NotBuiltError('SciGraph has not been built.')
            out = os.system(build_command)
            print(out)
            if out:
                scigraph_commit = 'FAILURE'
            with open(commit_log_path, 'wt') as f:
                f.write(scigraph_commit)
        else:
            print('SciGraph already built at commit', scigraph_commit)
            wildcard = jpth(zip_location, zip_name(wild=True))
            try:
                services_zip = glob(wildcard)[0]  # this will error if the zip was moved
                return scigraph_commit, load_base, services_zip, reset_state
            except IndexError:
                pass  # we need to copy the zip out again

        # services zip
        zip_filename =  'scigraph-services-*-SNAPSHOT.zip'
        services_zip_temp = glob(jpth(local, 'SciGraph-services', 'target', zip_filename))[0]
        services_zip = jpth(zip_location, zip_name())
        shutil.copy(services_zip_temp, services_zip)

    return scigraph_commit, load_base, services_zip, reset_state

def local_imports(remote_base, local_base, ontologies, readonly=False, dobig=False):
    """ Read the import closure and use the local versions of the files. """
    done = []
    triples = set()
    imported_iri_vs_ontology_iri = {}
    p = owl.imports
    oi = b'owl:imports'
    oo = b'owl:Ontology'
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
            if oo in raw:  # we only care if there are imports or an ontology iri
                scratch = rdflib.Graph()
                if infmt == 'turtle':
                    data, rest = raw.split(b'###', 1)
                elif infmt == None:  # assume xml
                    xml_tree = etree.parse(BytesIO(raw))
                    xml_root = xml_tree.getroot()
                    xml_ontology = xml_tree.xpath("/*[local-name()='RDF']/*[local-name()='Ontology']")
                    xml_root.clear()
                    xml_root.append(xml_ontology[0])
                    data = etree.tostring(xml_root)
                scratch.parse(data=data, format=infmt)
                for s in scratch.subjects(rdf.type, owl.Ontology):
                    triples.add((s, owl.sameAs, rdflib.URIRef(local_filepath)))
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
    memoryCheck(2665488384)
    local_base = jpth(git_local, repo_name)
    lb_ttl = os.path.realpath(jpth(local_base, 'ttl'))

    #match = (rdflib.term.URIRef('http://purl.org/dc/elements/1.1/member'),  # iao.owl
             #rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
             #rdflib.term.URIRef('http://www.w3.org/2002/07/owl#AnnotationProperty'))

    done = []
    filenames = [f for g in ('*', '*/*', '*/*/*') for f in glob(lb_ttl + '/' + g + '.ttl')]
    graph = rdflib.Graph()
    for f in filenames:
        print(f)
        done.append(os.path.basename(f))
        graph.parse(f, format='turtle')
        #if match in graph:
            #raise BaseException('Evil file found %s' % f)

    def repeat(dobig=False):  # we don't really know when to stop, so just adjust
        for s, o in graph.subject_objects(owl.imports):
            if os.path.basename(o) not in done and o not in done:
            #if (o, rdf.type, owl.Ontology) not in graph:
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
    mg.add_known_namespaces('owl', 'obo', 'dc', 'dcterms', 'dctypes', 'skos', 'NIFTTL')
    j = mg.make_scigraph_json('owl:imports', direct=True)
    t, te = creatTree(*Query('NIFTTL:nif.ttl', 'owl:imports', 'OUTGOING', 30), json=j, prefixes=mg.namespaces)
    #print(t)
    return t, te

def for_burak(ng_):
    syn_predicates = (ng_.expand('OBOANN:synonym'),
                      ng_.expand('OBOANN:acronym'),
                      ng_.expand('OBOANN:abbrev'),
                      ng_.expand('NIFRID:synonym'),
                      ng_.expand('NIFRID:acronym'),
                      ng_.expand('NIFRID:abbrev'),
                      oboInOwl.hasExactSynonym,
                      oboInOwl.hasNarrowSynonym,
                      oboInOwl.hasBroadSynonym,
                      oboInOwl.hasRelatedSynonym,
                      skos.prefLabel,
                      rdflib.URIRef('http://purl.obolibrary.org/obo/go#systematic_synonym'),
                     )
    lab_predicates = rdfs.label,
    def inner(ng):
        graph = ng.g
        for s in graph.subjects(rdf.type, owl.Class):
            if not isinstance(s, rdflib.BNode):
                curie = ng.qname(s)
                labels = [o for p in lab_predicates for o in graph.objects(s, p)
                          if not isinstance(o, rdflib.BNode)]
                synonyms = [o for p in syn_predicates for o in graph.objects(s, p)
                            if not isinstance(o, rdflib.BNode)]
                parents = [ng.qname(o) for o in graph.objects(s, rdfs.subClassOf)
                           if not isinstance(o, rdflib.BNode)]
                yield [curie, labels, synonyms, parents]

    records = {c:[l, s, p] for c, l, s, p in inner(ng_) if l or s}
    with open(os.path.expanduser('~/files/ontology-classes-with-labels-synonyms-parents.json'), 'wt') as f:
              json.dump(records, f, sort_keys=True, indent=2)

def deploy_scp(local_path, remote_spec):
    basename = os.path.basename(local_path)
    if remote_spec == 'user@localhost:/tmp/':
        print(f'Default so not scping {local_path}')
    else:
        ssh_target, remote_path = remote_spec.split(':', 1)  # XXX bad things?
        remote_folder = os.path.dirname(remote_path)
        remote_latest = jpth(remote_folder, 'LATEST')
        if 'localhost' in remote_spec:
            if '~' in remote_path:
                remote_path = os.path.expanduser(remote_path)
                remote_latest = os.path.expanduser(remote_latest)
            remote_spec = remote_path
            copy_command = 'cp'
            update_latest = f'echo {basename} > {remote_latest}'
        else:
            copy_command = 'scp'
            update_latest = f'ssh {ssh_target} "echo {basename} > {remote_latest}"'
        command = f'{copy_command} {local_path} {remote_spec}'
        print(command)
        print(update_latest)
        #os.system(command)
        #os.system(update_latest)

def locate_config_file(location_spec, git_local):
    dflt = defaults['--scigraph-config-folder']
    if location_spec.startswith(dflt):
        this_path = os.path.realpath(__file__)
        #print(this_path)
        test = jpth(os.path.dirname(this_path), '..', '.git')
        if not os.path.exists(test):
            base = jpth(git_local, 'pyontutils', 'pyontutils','some_file.wat')
        else:
            base = this_path
        location_spec = refile(base, location_spec)
    elif location_spec.startswith('~'):
        location_spec = os.path.expanduser(location_spec)
    location_spec = os.path.realpath(location_spec)
    #print('Loading config from', location_spec)
    return location_spec

def getCuries(curies_location):
    with open(curies_location, 'rt') as f:
        curies = yaml.load(f)
    curie_prefixes = set(curies.values())
    return curies, curie_prefixes

def make_post_clone(git_local, repo_name, remote_base):
    local_go = jpth(git_local, repo_name, 'ttl/external/go.owl')
    if repo_name == 'NIF-Ontology' and not os.path.exists(local_go):
        remote_go = jpth(remote_base, 'ttl/external/go.owl')
        def post_clone():
            print('Retrieving go.owl since it is not in the repo.')
            os.system('wget -O' + local_go + ' ' + remote_go)
    else:
        post_clone = lambda: None
    return post_clone

def run(args):
    # modes
    graph = args['graph']
    scigraph = args['scigraph']
    imports = args['imports']
    chain = args['chain']
    extra = args['extra']

    # required
    repo_name = args['<repo>']
    remote_base = args['<remote_base>']
    ontologies = args['<ontologies>']

    # options
    git_remote = args['--git-remote']
    git_local = args['--git-local']
    zip_location = args['--zip-location']
    scigraph_config_folder = args['--scigraph-config-folder']
    graphload_config = args['--graphload-config']
    org = args['--org']
    branch = args['--branch']
    commit = args['--commit']
    scp = args['--scp-loc']
    sorg = args['--scigraph-org']
    sbranch = args['--scigraph-branch']
    scommit = args['--scigraph-commit']
    sscp = args['--scigraph-scp-loc']
    curies_location = args['--curies']
    check_built = args['--check-built']
    debug = args['--debug']
    log = args['--logfile']  # TODO

    # post parse mods
    if remote_base == 'NIF':
        remote_base = 'http://ontology.neuinfo.org/NIF'
    if '~' in git_local:
        git_local = os.path.expanduser(git_local)
    if '/' not in graphload_config:
        graphload_config = jpth(scigraph_config_folder, graphload_config)
    if '/' not in curies_location:
        curies_location = jpth(scigraph_config_folder, curies_location)
    graphload_config = locate_config_file(graphload_config, git_local)
    curies_location = locate_config_file(curies_location, git_local)
    curies, curie_prefixes = getCuries(curies_location)

    itrips = None

    if repo_name is not None:
        local_base = jpth(git_local, repo_name)

    if graph:
        (scigraph_commit, load_base, services_zip,
         scigraph_reset_state) = scigraph_build(zip_location, git_remote, sorg,
                                                git_local, sbranch, scommit,
                                                check_built=check_built,
                                                cleanup_later=True)
        with execute_regardless(scigraph_reset_state):
            graph_zip, itrips = repro_loader(zip_location, git_remote, org,
                                             git_local, repo_name, branch,
                                             commit, remote_base, load_base,
                                             graphload_config, scigraph_commit,
                                             check_built=check_built)
        if not check_built:
            deploy_scp(services_zip, sscp)
            deploy_scp(graph_zip, scp)
        print(services_zip)
        print(graph_zip)
        if '--local' in args:
            return
    elif scigraph:
        (scigraph_commit, load_base, services_zip,
         _) = scigraph_build(zip_location, git_remote, sorg, git_local,
                             sbranch, scommit, check_built=check_built)
        if not check_built:
            deploy_scp(services_zip, sscp)
        print(services_zip)
        if '--local' in args:
            return
    elif imports:
        # TODO mismatch between import name and file name needs a better fix
        itrips = local_imports(remote_base, local_base, ontologies)
    elif chain:
        itrips = local_imports(remote_base, local_base, ontologies, readonly=True)
    elif extra:
        graph = loadall(git_local, repo_name)
        mg, ng_ = normalize_prefixes(graph, curies)
        ng_.add_known_namespaces('NIFRID')  # not officially in the curies yet...
        for_burak(ng_)
        debug = True
    else:
        raise BaseException('How did we possibly get here docopt?')

    if itrips:
        import_graph = rdflib.Graph()
        [import_graph.add(t) for t in itrips]
        tree, extra = import_tree(import_graph)
        with open(jpth(zip_location, '{repo_name}-import-closure.html'.format(repo_name=repo_name)), 'wt') as f:
            f.write(extra.html.replace('NIFTTL:', ''))  # much more readable

    if debug:
        embed()

def main():
    from docopt import docopt
    args = docopt(__doc__, version='ontload .5')
    if args['--debug']:
        print(args)
    try:
        run(args)
    except NotBuiltError:
        if args['--check-built']:
            print('Not built')
        os.sys.exit(1)

if __name__ == '__main__':
    main()
