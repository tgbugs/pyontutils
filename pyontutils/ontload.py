#!/usr/bin/env python3.6
""" ontUse SciGraph to load an ontology from a loacal git repository.
 Remote imports are replaced with local imports.
 NIF -> http://ontology.neuinfo.org/NIF

Usage:
    ontload graph [options] <repo> <remote_base>
    ontload scigraph [options]
    ontload services [options]
    ontload imports [options] <repo> <remote_base> <ontologies>...
    ontload chain [options] <repo> <remote_base> <ontologies>...
    ontload uri-switch [options]
    ontload backend-refactor [options]
    ontload todo [options] <repo>
    ontload extra [options] <repo>

Options:
    -g --git-remote=GBASE           remote git hosting [default: https://github.com/]
    -l --git-local=LBASE            local path to look for ontology <repo> [default: /tmp]
    -z --zip-location=ZIPLOC        local path in which to deposit zipped files [default: /tmp]

    -t --graphload-template=CFG     rel path to graphload.yaml template [default: ../scigraph/graphload-template.yaml]
    -o --org=ORG                    user/org to clone/load ontology from [default: SciCrunch]
    -b --branch=BRANCH              ontology branch to load [default: master]
    -c --commit=COMMIT              ontology commit to load [default: HEAD]
    -d --scp-loc=SCP                where to scp the zipped graph file [default: ${USER}@localhost:/tmp/]

    -e --services-template=SCFG     rel path to services.yaml template [default: ../scigraph/services-template.yaml]
    -r --scigraph-org=SORG          user/org to clone/build scigraph from [default: SciCrunch]
    -a --scigraph-branch=SBRANCH    scigraph branch to build [default: upstream]
    -m --scigraph-commit=SCOMMIT    scigraph commit to build [default: HEAD]
    -p --scigraph-scp-loc=SGSCP     where to scp the zipped graph file [default: ${USER}@localhost:/tmp/]

    -f --graph-folder=DLOC          override config folder where the graph will live [default: from-config]
    -u --curies=CURIEFILE           relative path to curie definition file [default: ../scigraph/nifstd_curie_map.yaml]

    -h --host=HOST                  host where services will run

    -v --debug                      call IPython embed when done
    -i --logfile=LOG                log output here [default: ontload.log]
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
from joblib import Parallel, delayed
from pyontutils.utils import makeGraph, createOntology, makePrefixes, memoryCheck, noneMembers, anyMembers, TODAY, setPS1, refile  # TODO make prefixes needs an all...
from pyontutils.utils import rdf, rdfs, owl, skos, oboInOwl

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
    with open(graphload_template, 'rt') as f:
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

def uri_switch_values(utility_graph):
    NIFSTDBASE = 'http://uri.neuinfo.org/nif/nifstd/'

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

def switchURIs(g, swap, *args):
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

def swapBackend(trip, ureps):
    for spo in trip:
        if spo in ureps:
            new_spo = ureps[spo]
            rep = (new_spo, owl.sameAs, spo)
            yield new_spo, rep, None
        else:
            yield spo, None, None

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

        # other
        #'ro:participates_in'  # above
        #'ro:has_participant'  # above
        #'ro:has_part',  # above
        #'ro:part_of',  # above
        #'ro:precedes'  # unused and only in inferred
        #'ro:preceded_by'  # unused and only in inferred
        #'ro:transformation_of'  # unused and only in inferred
        #'ro:transformed_into'  # unused and only in inferred

        'http://purl.obolibrary.org/obo/pato#inheres_in':'RO:0000052',
        'BIRNLEX:17':'RO:0000053',  # is_bearer_of
        'http://purl.obolibrary.org/obo/pato#towards':'RO:0002502',
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

def backend_refactor(filenames, get_values):
    ureps = get_values()
    print('Start writing')
    trips_lists = Parallel(n_jobs=9)(delayed(do_file)(f, swapBackend, ureps) for f in filenames)
    print('Done writing')
    embed()

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
    if remote_spec == '${USER}@localhost:/tmp/':
        print(f'Default so not scping {local_path}')
    else:
        ssh_target, remote_path = remote_spec.split(':', 1)  # XXX bad things?
        remote_folder = os.path.dirname(remote_path)
        remote_latest = os.path.join(remote_folder, 'LATEST')
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
        os.system(command)

def locate_config_file(location_spec):
    if location_spec.startswith('../scigraph/'):
        location_spec = refile(os.path.realpath(__file__), location_spec)
    elif location_spec.startswith('~'):
        location_spec = os.path.expanduser(location_spec)
    location_spec = os.path.realpath(location_spec)
    #print('Loading config from', location_spec)
    return location_spec

def services(services_template, graph_folder, curies):
    services_path = os.path.join(os.path.dirname(services_template), 'services.yaml')
    with open(services_template, 'rt') as f:
        config = yaml.load(f)
    config['graphConfiguration']['curies'] = curies
    if graph_folder != 'from-config':
        config['graphConfiguration']['location'] = graph_folder
    else:
        graph_folder = config['graphConfiguration']['location']
    with open(services_path, 'wt') as f:
        yaml.dump(config, f, default_flow_style=False)

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
    graphload_template = locate_config_file(graphload_template)
    org = args['--org']
    branch = args['--branch']
    commit = args['--commit']
    scp = args['--scp-loc']

    services_template = args['--services-template']
    services_template = locate_config_file(services_template)
    sorg = args['--scigraph-org']
    sbranch = args['--scigraph-branch']
    scommit = args['--scigraph-commit']
    sscp = args['--scigraph-scp-loc']

    curies_location = args['--curies']
    curies_location = locate_config_file(curies_location)

    host = args['--host']  # TODO
    graph_folder = args['--graph-folder']

    log = args['--logfile']  # TODO
    debug = args['--debug']

    def getCuries():
        with open(curies_location, 'rt') as f:
            curies = yaml.load(f)
        curie_prefixes = set(curies.values())
        return curies, curie_prefixes

    itrips = None

    if repo_name is not None:
        local_base = os.path.join(git_local, repo_name)

    if args['graph']:
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
        deploy_scp(services_zip, sscp)
        deploy_scp(graph_zip, scp)
    elif args['scigraph']:
        scigraph_commit, load_base, services_zip = scigraph_build(zip_location, git_remote, sorg, git_local, sbranch, scommit)
        deploy_scp(services_zip, sscp)
    elif args['services']:
        curies, _ = getCuries()
        services(services_template, graph_folder, curies)
    elif args['imports']:
        # TODO mismatch between import name and file name needs a better fix
        itrips = local_imports(remote_base, local_base, args['<ontologies>'])
    elif args['chain']:
        itrips = local_imports(remote_base, local_base, args['<ontologies>'], readonly=True)
    elif args['extra']:
        graph = loadall(git_local, repo_name)
        curies, _ = getCuries()
        mg, ng_ = normalize_prefixes(graph, curies)
        for_burak(ng_)
        debug = True
    elif args['uri-switch'] or args['backend-refactor']:
        filenames =  glob('*.ttl') + glob('*/*.ttl') + glob('*/*/*.ttl')   # need all for the replacement
        filenames.sort(key=lambda f: os.path.getsize(f), reverse=True)  # make sure the big boys go first
        for n in ('nif.ttl', 'resources.ttl', 'generated/chebislim.ttl',
                  'generated/ncbigeneslim.ttl', 'generated/NIF-NIFSTD-mapping.ttl'):
            if n in filenames:
                filenames.remove(n)
        if args['uri-switch']:
            uri_switch(filenames, uri_switch_values)
        elif args['backend-refactor']:
            backend_refactor(filenames, backend_refactor_values)
    elif args['todo']:
        graph = loadall(git_local, repo_name, local=True)
        _, curie_prefixes = getCuries()
        graph_todo(graph, curie_prefixes, uri_switch_values)
        debug = True
    else:
        raise BaseException('How did we possibly get here docopt?')

    if itrips:
        import_graph = rdflib.Graph()
        [import_graph.add(t) for t in itrips]
        tree, extra = import_tree(import_graph)
        with open(os.path.join(zip_location, '{repo_name}-import-closure.html'.format(repo_name=repo_name)), 'wt') as f:
            f.write(extra.html.replace('NIFTTL:', ''))  # much more readable

    if debug:
        embed()

if __name__ == '__main__':
    main()
