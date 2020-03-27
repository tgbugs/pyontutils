#!/usr/bin/env python3.7
import tempfile
from pyontutils.core import auth
__doc__ = f"""Use SciGraph to load an ontology from a loacal git repository.
Remote imports are replaced with local imports.
NIF -> http://ontology.neuinfo.org/NIF

Usage:
    ontload graph [options] <repo> <remote_base>
    ontload config [options] <repo> <remote_base> <graph_path>
    ontload scigraph [options]
    ontload imports [options] <repo> <remote_base> <ontologies>...
    ontload chain [options] <repo> <remote_base> <ontologies>...
    ontload extra [options] <repo>
    ontload patch [options] <repo>
    ontload [options]

Options:
    -g --git-remote=GBASE           remote git hosting          [default: {auth.get('git-remote-base')}]
    -l --git-local=LBASE            local git folder            [default: {auth.get_path('git-local-base')}]
    -z --zip-location=ZIPLOC        local path for build files  [default: {auth.get_path('zip-location')}]

    -t --graphload-config=CFG       graphload.yaml location     [default: {auth.get_path('scigraph-graphload')}]
                                    THIS IS THE LOCATION OF THE BASE TEMPLATE FILE
    -n --graphload-ontologies=YML   ontologies-*.yaml file

    -o --org=ORG                    user/org for ontology       [default: {auth.get('ontology-org')}]
    -b --branch=BRANCH              ontology branch to load     [default: master]
    -c --commit=COMMIT              ontology commit to load     [default: HEAD]
    -s --scp-loc=SCP                scp zipped graph here       [default: user@localhost:{tempfile.tempdir}/graph/]

    -i --path-build-scigraph=PBS    build scigraph at path
    -O --scigraph-org=SORG          user/org for scigraph       [default: SciGraph]
    -B --scigraph-branch=SBRANCH    scigraph branch to build    [default: master]
    -C --scigraph-commit=SCOMMIT    scigraph commit to build    [default: HEAD]
    -S --scigraph-scp-loc=SGSCP     scp zipped services here    [default: user@localhost:{tempfile.tempdir}/scigraph/]
    -Q --scigraph-quiet             silence mvn log output

    -P --patch-config=PATCHLOC      patchs.yaml location        [default: {auth.get_path('patch-config')}]
    -u --curies=CURIEFILE           curie definition file       [default: {auth.get_path('curies')}]
                                    if only the filename is given assued to be in scigraph-config-folder

    -p --patch                      retrieve ontologies to patch and modify import chain accordingly
    -K --check-built                check whether a local copy is present but do not build if it is not

    -d --debug                      call breakpoint when done
    -L --logfile=LOG                log output here             [default: ontload.log]
    -v --view-defaults              print out the currently configured default values
    -f --graph-config-out=GCO       output for graphload.yaml   [default: {auth.get_path('scigraph-graphload')}]
                                    only useful for `ontload config` ignored otherwise
"""
import os
import json
import yaml
import shutil
import subprocess
from io import BytesIO
from glob import glob
from pathlib import Path
from os.path import join as jpth
from contextlib import contextmanager
from collections import namedtuple
import rdflib
import requests
from lxml import etree
from git.repo import Repo
from docopt import parse_defaults
from joblib import Parallel, delayed
from ttlser import CustomTurtleSerializer
from pyontutils.core import OntGraph
from pyontutils.utils import noneMembers, TODAY, setPS1, refile, TermColors as tc
from pyontutils.namespaces import getCuries, OntCuries
from pyontutils.hierarchies import creatTree
from pyontutils.closed_namespaces import rdf, rdfs, owl, skos, oboInOwl, dc
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint

defaults = {o.name:o.value if o.argcount else None for o in parse_defaults(__doc__)}

COMMIT_HASH_HEAD_LEN = 8

bigleaves = 'go.owl', 'uberon.owl', 'pr.owl', 'doid.owl', 'taxslim.owl', 'chebislim.ttl', 'ero.owl'

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

class NotBuiltError(FileNotFoundError):
    pass


def make_catalog(itrips):
    return '\n'.join(("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>""",
                      """<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">""",
                      *[f"""    <uri id="User Entered Import Resolution" name="{s}" uri="{o}"/>""" for s, p, o in itrips
                        if p == owl.sameAs],
                      """</catalog>"""))


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


class ReproLoader:
    def __init__(self, zip_location, git_remote, org, git_local, repo_name, branch, commit,
                 remote_base, load_base, graphload_config_template, graphload_ontologies,
                 patch_config, patch, scigraph_commit, post_clone=lambda: None, check_built=False):

        load_from_repo=True
        local_base = jpth(git_local, repo_name)
        if load_from_repo:
            repo, nob = self._set_up_repo_state(local_base,
                                                git_remote,
                                                org,
                                                git_local,
                                                repo_name,
                                                branch,
                                                commit,
                                                post_clone)
            ontology_commit = repo.head.object.hexsha[:COMMIT_HASH_HEAD_LEN]
        else:
            ontology_commit = 'NONE'

        (graph_path, zip_path, zip_command,
         wild_zip_path) = self._set_up_paths(zip_location, repo_name, branch,
                                             scigraph_commit, ontology_commit)

        (config, config_path,
         ontologies) = self.make_graphload_config(graphload_config_template, graphload_ontologies,
                                                  graph_path, remote_base, local_base, zip_location)

        load_command = load_base.format(config_path=config_path)  # 'exit 1' to test
        print(load_command)

        if load_from_repo:
            # replace raw github imports with ontology.neuinfor iris to simplify import chain
            # FIXME this is hardcoded and will not generalize ...
            fix_imports = ("find " + local_base +
                        (" -name '*.ttl' -exec sed -i"
                            " 's/<http.\+\/ttl\//<http:\/\/ontology.neuinfo.org\/NIF\/ttl\//' {} \;"))
            os.system(fix_imports)

        if load_from_repo:
            def reset_state(original_branch=nob):
                repo.git.checkout('--', local_base)
                original_branch.checkout()
        else:
            reset_state = lambda x:x

        with execute_regardless(reset_state):  # FIXME start this immediately after we obtain nob?
            # main
            if load_from_repo:
                if patch:
                    # FIXME TODO XXX does scigraph load from the catalog!??!??
                    # because it seems like doid loads correctly without using local_versions
                    # which would be cool, if confusing
                    local_versions = tuple(do_patch(patch_config, local_base))
                else:
                    local_versions = tuple()
                itrips = local_imports(remote_base, local_base, ontologies,
                                       local_versions=local_versions, dobig=True)  # SciGraph doesn't support catalog.xml
                catalog = make_catalog(itrips)
                with open(Path(local_base, 'catalog.xml'), 'wt') as f:
                    f.write(catalog)
            else:
                itrips = []
                pass

            maybe_zip_path = glob(wild_zip_path)
            if not maybe_zip_path:
                if check_built:
                    print('The graph has not been loaded.')
                    raise NotBuiltError('The graph has not been loaded.')

                #breakpoint()
                failure = os.system(load_command)
                if failure:
                    if os.path.exists(graph_path):
                        shutil.rmtree(graph_path)
                else:
                    os.rename(config_path,  # save the config for eaiser debugging
                              graph_path / config_path.name)
                    cpr = config_path.with_suffix(config_path.suffix + '.raw')
                    os.rename(cpr, graph_path / cpr.name)
                    failure = os.system(zip_command)  # graphload zip
            else:
                zip_path = maybe_zip_path[0]  # this way we get the actual date
                print('Graph already loaded at', zip_path)

            # this needs to be run when the branch is checked out
            # FIXME might be worth adding this to the load config?
            self.ontologies = [get_iri(load_header(rec['url'])) for rec in config['ontologies']]

        self.zip_path = zip_path
        self.itrips = itrips
        self.config = config

    @staticmethod
    def _set_up_repo_state(local_base, git_remote, org, git_local,
                           repo_name, branch, commit, post_clone):
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

        return repo, nob

    @staticmethod
    def _set_up_paths(zip_location, repo_name, branch, scigraph_commit, ontology_commit):
        # TODO consider dumping metadata in a file in the folder too?
        def folder_name(scigraph_commit, wild=False):
            return (repo_name +
                    '-' + branch +
                    '-graph' +
                    '-' + ('*' if wild else TODAY()) +
                    '-' + scigraph_commit[:COMMIT_HASH_HEAD_LEN] +
                    '-' + ontology_commit)

        def make_folder_zip(wild=False):
            folder = folder_name(scigraph_commit, wild)
            graph_path = zip_location / folder
            zip_path = graph_path.with_suffix('.zip')
            if wild:
                return graph_path, zip_path.as_posix()
            zip_name = zip_path.name
            zip_dir = os.path.dirname(zip_path)
            zip_command = ' '.join(('cd', zip_dir, ';', 'zip -r', zip_name, folder))
            return graph_path, zip_path, zip_command

        graph_path, zip_path, zip_command = make_folder_zip()
        wild_graph_path, wild_zip_path = make_folder_zip(wild=True)
        return graph_path, zip_path, zip_command, wild_zip_path

    @staticmethod
    def make_graphload_config(graphload_config_template, graphload_ontologies,
                              graph_path, remote_base, local_base, zip_location,
                              config_path=None):
        config_n = 'graphload-' + TODAY() + '.yaml'
        config_raw = config_n + '.raw'
        if graphload_ontologies is not None:
            with open(graphload_config_template, 'rt') as f1, open(graphload_ontologies, 'rt') as f2, open(zip_location / config_raw, 'wt') as out:  # LOL PYTHON
                out.write(f1.read())
                out.write(f2.read())
        else:  # nothing will load, but that's ok
            with open(graphload_config_template, 'rt') as f1, open(zip_location / config_raw, 'wt') as out:  # LOL PYTHON
                out.write(f1.read())

        # config graphload.yaml from template
        with open(zip_location / config_raw, 'rt') as f:
            config = yaml.safe_load(f)

        if 'ontologies' not in config:
            # FIXME log a warning?
            config['ontologies'] = []

        config['graphConfiguration']['location'] = graph_path.as_posix()
        if isinstance(local_base, Path):
            lbasposix = local_base.as_posix()
        else:
            lbasposix = local_base

        config['ontologies'] = [{k:v.replace(remote_base, lbasposix)
                                if k == 'url'
                                else v
                                for k, v in ont.items()}
                                for ont in config['ontologies']]

        if config_path is None:
            config_path = zip_location / config_n

        with open(config_path, 'wt') as f:
            yaml.dump(config, f, default_flow_style=False)

        ontologies = [ont['url'] for ont in config['ontologies']]
        return config, config_path, ontologies


def scigraph_build(zip_location, git_remote, org, git_local, branch, commit,
                   clean=False, check_built=False, cleanup_later=False, quiet=False):
    COMMIT_LOG = 'last-built-commit.log'
    repo_name = 'SciGraph'
    remote = jpth(git_remote, org, repo_name)
    local = jpth(git_local, repo_name)
    commit_log_path = jpth(local, COMMIT_LOG)

    if not os.path.exists(local):
        repo = Repo.clone_from(remote + '.git', local)
    elif not Path(local, '.git').exists():
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
    scigraph_commit_short = scigraph_commit[:COMMIT_HASH_HEAD_LEN]

    bin_location = zip_location / 'bin'
    os.environ['PATH'] = bin_location.as_posix() + ':' + os.environ.get('PATH', '')
    if not bin_location.exists():
        bin_location.mkdir()
        # hack to make the scigraph-load we are about to create available as a command
        # so that it matches the usual scigraph-load behavior

    def zip_name(wild=False):
        return (repo_name +
                '-' + branch +
                '-services' +
                '-' + ('*' if wild else TODAY()) +
                '-' + scigraph_commit_short +
                '.zip')

    def reset_state(original_branch=sob):
        original_branch.checkout()

    with execute_regardless(reset_state, only_exception=cleanup_later):  # FIXME this fails when we need to load the graph if we start on master :/
        # main
        if scigraph_commit != last_commit or clean:
            print('SciGraph not built at commit', commit, 'last built at', last_commit)
            quiet = '--quiet ' if quiet else ''
            build_command = ('cd ' + local +
	                     f';export HASH={scigraph_commit_short}'
	                     ';sed -i "/<name>SciGraph<\/name>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" pom.xml'
	                     ';sed -i "/<artifactId>scigraph<\/artifactId>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" SciGraph-analysis/pom.xml'
	                     ';sed -i "/<groupId>io.scigraph<\/groupId>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" SciGraph-core/pom.xml'
	                     ';sed -i "/<artifactId>scigraph<\/artifactId>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" SciGraph-entity/pom.xml'
	                     ';sed -i "/<groupId>io.scigraph<\/groupId>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" SciGraph-services/pom.xml'
                             f'; mvn {quiet}clean -DskipTests -DskipITs install'
                             '; cd SciGraph-services'
                             f'; mvn {quiet}-DskipTests -DskipITs package')

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
                return scigraph_commit, services_zip, reset_state
            except IndexError:
                pass  # we need to copy the zip out again

        # services zip
        zip_filename =  f'scigraph-services-{scigraph_commit_short}.zip'
        services_zip_temp = Path(local, 'SciGraph-services', 'target', zip_filename)
        services_zip = jpth(zip_location, zip_name())
        shutil.copy(services_zip_temp, services_zip)

        core_jar = Path(local, 'SciGraph-core', 'target', f'scigraph-core-{scigraph_commit_short}-jar-with-dependencies.jar')
        scigraph_load = f'''#!/usr/bin/env sh
/usr/bin/java \\
-cp "{core_jar.as_posix()}" \\
io.scigraph.owlapi.loader.BatchOwlLoader $@'''
        slf = bin_location / 'scigraph-load'
        with open(slf, 'wt') as f:
            f.write(scigraph_load)

        os.chmod(slf, 0o0755)

    return scigraph_commit, services_zip, reset_state


def do_patch(patch_config, local_base):
    repo_base = Path(local_base)
    config_path = Path(patch_config)
    with open(patch_config, 'rt') as f:
        config = yaml.safe_load(f)

    for patchset, patches in config.items():
        for patch, target_remote in patches.items():
            patchfile = config_path.parent / patch
            if not patchfile.exists():
                raise FileNotFoundError(f'Cannot find {patchfile} specified in {config_path}')
            target = target_remote['target']
            targetfile = repo_base / target
            if 'remote' in target_remote and not targetfile.exists():
                remote = target_remote['remote']
                resp = requests.get(remote)
                with open(targetfile, 'wb') as f:
                    f.write(resp.content)

            print(tc.blue('INFO: patching'), patchset, patchfile, targetfile)
            try:
                out = subprocess.check_output(['patch', '-p1', '-N', '-i', patchfile.as_posix()],
                                              cwd=repo_base.as_posix(),
                                              stderr=subprocess.STDOUT).decode().rstrip()
                print(out)
                yield targetfile.as_posix()
            except subprocess.CalledProcessError as e:
                # FIXME this is not failing on other types of patching errors!
                if e.returncode > 1:  # 1 means already applied
                    print(e.stdout.decode())
                    raise e

def load_header(filepath, remote=False):
    oo = b'owl:Ontology'
    path = Path(filepath)
    if path.suffix == '.ttl':
        infmt = 'turtle'
    else:
        infmt = 'xml'  # FIXME assumption

    if remote:
        resp = requests.get(filepath)  # TODO nonblocking pull these out, fetch, run inner again until done
        raw = resp.text.encode()
    else:
        with open(filepath, 'rb') as f:  # do not catch FileNotFoundErrors
            raw = f.read()

    if oo in raw:  # we only care if there are imports or an ontology iri
        scratch = OntGraph()
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

    return scratch

def get_iri(graph):
    gen = graph[:rdf.type:owl.Ontology]
    return next(gen)  # XXX WARNING does not check for > 1 bound name per file

def get_imports(graph):
    yield from (p for p in graph[get_iri(graph):owl.imports:])

def local_imports(remote_base, local_base, ontologies, local_versions=tuple(), readonly=False, dobig=False, revert=False):
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
                        print(e)  # TODO raise a warning if the file cannot be matched
                        # seems like good practice to have any imported ontology under
                        # version control so all imports are guaranteed to have good
                        # provenance and not split the prior informaiton between the
                        # scigraph config and the repository, the repository remains
                        # the source of truth, load.yaml files can then pick a subset
                        # of the properly tracked files to load as they see fit, but
                        # not add to them (at least in pyontutils land)
                        raw = b''
            if oo in raw:  # we only care if there are imports or an ontology iri
                scratch = OntGraph()
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
                    # somehow this breaks computing the chain
                    #for p in (rdfs.comment, skos.definition, definition, dc.title, rdfs.label):
                        #for o in scratch[s:p]:
                            #triples.add((s, p, o))
                for s, o in sorted(scratch.subject_objects(p)):
                    if revert:
                        raise NotImplementedError('TODO')
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
                    _orp = CustomTurtleSerializer.roundtrip_prefixes  # FIXME awful hack :/
                    CustomTurtleSerializer.roundtrip_prefixes = True
                    ttl = scratch.serialize(format='nifttl')
                    CustomTurtleSerializer.roundtrip_prefixes = _orp
                    ndata, comment = ttl.split(b'###', 1)
                    out = ndata + b'###' + rest
                    with open(local_filepath, 'wb') as f:
                        f.write(out)

    for start in ontologies:
        print('START', start)
        done.append(start)
        inner(start)
    return sorted(triples)

def loadall(git_local, repo_name, local=False, dobig=False):
    local_base = jpth(git_local, repo_name)
    lb_ttl = os.path.realpath(jpth(local_base, 'ttl'))

    #match = (rdflib.term.URIRef('http://purl.org/dc/elements/1.1/member'),  # iao.owl
             #rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
             #rdflib.term.URIRef('http://www.w3.org/2002/07/owl#AnnotationProperty'))

    done = []
    filenames = [f for g in ('*', '*/*', '*/*/*') for f in glob(lb_ttl + '/' + g + '.ttl')]
    graph = OntGraph()
    for f in filenames:
        print(f)
        done.append(os.path.basename(f))
        graph.parse(f, format='turtle')
        #if match in graph:
            #raise BaseException('Evil file found %s' % f)

    def repeat(dobig=dobig):  # we don't really know when to stop, so just adjust
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
    new_graph = OntGraph()
    oc = OntCuries.new()
    curies.pop('', None)
    curies['rdf'] = str(rdf)
    curies['rdfs'] = str(rdfs)
    oc(curies)
    oc.populate(new_graph)
    [new_graph.add(t) for t in graph]
    return new_graph

def import_tree(graph, ontologies, **kwargs):
    for ontology in ontologies:
        thisfile = Path(ontology).name
        print(thisfile)
        OntCuries.populate(graph)
        j = graph.asOboGraph('owl:imports', restriction=False)
        try:
            t, te = creatTree(*Query(f'NIFTTL:{thisfile}', 'owl:imports', 'OUTGOING', 30), json=j, prefixes=dict(graph.namespace_manager), **kwargs)
            #print(t)
            yield t, te
        except KeyError:
            print(tc.red('WARNING:'), 'could not find', ontology, 'in import chain')  # TODO zap onts w/o imports

def for_burak(graph):
    nm = graph.namespace_manager
    syn_predicates = (nm.expand('OBOANN:synonym'),
                      nm.expand('OBOANN:acronym'),
                      nm.expand('OBOANN:abbrev'),
                      nm.expand('NIFRID:synonym'),
                      nm.expand('NIFRID:acronym'),
                      nm.expand('NIFRID:abbrev'),
                      oboInOwl.hasExactSynonym,
                      oboInOwl.hasNarrowSynonym,
                      oboInOwl.hasBroadSynonym,
                      oboInOwl.hasRelatedSynonym,
                      skos.prefLabel,
                      rdflib.URIRef('http://purl.obolibrary.org/obo/go#systematic_synonym'),
                     )
    lab_predicates = rdfs.label,
    def inner(graph):
        for s in graph[:rdf.type:owl.Class]:
            if not isinstance(s, rdflib.BNode):
                curie = nm._qhrm(s)  # FIXME
                labels = [o for p in lab_predicates for o in graph[s:p]
                          if not isinstance(o, rdflib.BNode)]
                synonyms = [o for p in syn_predicates for o in graph[s:p]
                            if not isinstance(o, rdflib.BNode)]
                parents = [nm._qhrm(o) for o in graph[s:rdfs.subClassOf]  # FIXME
                           if not isinstance(o, rdflib.BNode)]
                yield [curie, labels, synonyms, parents]

    records = {c:[l, s, p] for c, l, s, p in inner(graph) if l or s}
    with open(os.path.expanduser('~/files/ontology-classes-with-labels-synonyms-parents.json'), 'wt') as f:
              json.dump(records, f, sort_keys=True, indent=2)


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
    config = args['config']
    imports = args['imports']
    chain = args['chain']
    extra = args['extra']

    # required
    repo_name = args['<repo>']
    remote_base = args['<remote_base>']
    ontologies = args['<ontologies>']

    # options
    git_remote = args['--git-remote']
    git_local = Path(args['--git-local']).resolve()
    zip_location = Path(args['--zip-location']).resolve()
    graphload_config = Path(args['--graphload-config']).resolve()
    graphload_config_template = graphload_config  # NOTE XXX
    if args['--graphload-ontologies'] is not None:
        graphload_ontologies = Path(args['--graphload-ontologies']).resolve()
    else:
        graphload_ontologies = None

    org = args['--org']
    branch = args['--branch']
    commit = args['--commit']
    scp = args['--scp-loc']
    sorg = args['--scigraph-org']
    sbranch = args['--scigraph-branch']
    scommit = args['--scigraph-commit']
    sscp = args['--scigraph-scp-loc']
    scigraph_quiet = args['--scigraph-quiet']
    patch_config = args['--patch-config']
    curies_location = args['--curies']
    patch = args['--patch']
    check_built = args['--check-built']
    debug = args['--debug']
    log = args['--logfile']  # TODO

    load_base = 'scigraph-load -c {config_path}'  # now _this_ is easier

    if args['--view-defaults']:
        for k, v in defaults.items():
            print(f'{k:<22} {v}')
        return

    # post parse mods
    if remote_base == 'NIF':
        remote_base = 'http://ontology.neuinfo.org/NIF'

    itrips = None

    if repo_name is not None:
        local_base = jpth(git_local, repo_name)

    if graph:
        if args['--path-build-scigraph']:  # path-build-scigraph
            path_build_scigraph = Path(args['--path-build-scigraph'])
            (scigraph_commit, services_zip,
             scigraph_reset_state) = scigraph_build(path_build_scigraph, git_remote, sorg,
                                                    path_build_scigraph, sbranch, scommit,
                                                    check_built=check_built,
                                                    cleanup_later=True, quiet=scigraph_quiet)
        else:
            scigraph_commit = 'dev-9999'
            services_zip = 'None'
            scigraph_reset_state = lambda : None

        with execute_regardless(scigraph_reset_state):
            rl = ReproLoader(zip_location, git_remote, org,
                             git_local, repo_name, branch,
                             commit, remote_base, load_base,
                             graphload_config_template, graphload_ontologies,
                             patch_config, patch, scigraph_commit,
                             check_built=check_built)

        FILE_NAME_ZIP = Path(rl.zip_path).name
        LATEST = Path(zip_location) / 'LATEST'
        if LATEST.exists() and LATEST.is_symlink():
            LATEST.unlink()

        LATEST.symlink_to(FILE_NAME_ZIP)

        itrips, config = rl.itrips, rl.config

        if not ontologies:
            ontologies = rl.ontologies

        print(services_zip)
        print(rl.zip_path)
        if '--local' in args:
            return

    elif scigraph:
        (scigraph_commit, services_zip,
         _) = scigraph_build(zip_location, git_remote, sorg, git_local,
                             sbranch, scommit, check_built=check_built,
                             quiet=scigraph_quiet)
        print(services_zip)
        if '--local' in args:
            return

    elif config:
        graph_path = Path(args['<graph_path>']).resolve()
        config_path = Path(args['--graph-config-out']).resolve()
        local_base = Path(git_local, repo_name).resolve()
        ReproLoader.make_graphload_config(graphload_config_template, graphload_ontologies,
                                          graph_path, remote_base, local_base,
                                          zip_location, config_path)

    elif imports:
        # TODO mismatch between import name and file name needs a better fix
        itrips = local_imports(remote_base, local_base, ontologies)
    elif chain:
        itrips = local_imports(remote_base, local_base, ontologies, readonly=True)
    elif extra:
        from nifstd_tools.utils import memoryCheck
        curies = getCuries(curies_location)
        curie_prefixes = set(curies.values())
        memoryCheck(2665488384)
        graph = loadall(git_local, repo_name)
        new_graph = normalize_prefixes(graph, curies)
        for_burak(new_graph)
        debug = True
    elif patch:
        local_base = jpth(git_local, repo_name)
        local_versions = tuple(do_patch(patch_config, local_base))
    else:
        raise BaseException('How did we possibly get here docopt?')

    if itrips:
        import_graph = OntGraph()
        [import_graph.add(t) for t in itrips]
        for tree, extra in import_tree(import_graph, ontologies):
            name = Path(next(iter(tree.keys()))).name
            with open(jpth(zip_location, f'{name}-import-closure.html'), 'wt') as f:
                f.write(extra.html.replace('NIFTTL:', ''))  # much more readable

    if debug:
        breakpoint()


def main():
    from docopt import docopt
    args = docopt(__doc__, version='ontload .5')
    args = {k: None if v == 'None' else v for k, v in args.items()}
    setPS1(__file__)
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
