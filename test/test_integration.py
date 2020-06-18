import os
import sys
import unittest
from pathlib import Path
from importlib import import_module
import pytest
import augpathlib as aug
import pyontutils
from pyontutils.utils import get_working_dir
from pyontutils.config import auth
from pyontutils.integration_test_helper import _TestScriptsBase, Repo, Folders, skipif_no_net
from .common import temp_path_ap, temp_path


@skipif_no_net
class TestOntQuery(unittest.TestCase):
    """ ITs for ontquery """

    def setUp(self):
        from pyontutils.core import OntTerm
        self.OntTerm = OntTerm
        self.query = OntTerm.query

    def test_term(self):
        self.OntTerm('UBERON:0000955')

    def test_query(self):
        list(self.query('brain'))


class TestScripts(Folders, _TestScriptsBase):
    """ woo ! """

    def setUp(self):
        super().setUp()
        _temp_git.init()
        _test_ttl.copy_outto(_temp_git)
        _test_owl.copy_outto(_temp_git)


TestScripts.temp_path = temp_path


only = tuple()
skip = tuple()
ci_skip = tuple()
network_tests = (  # reminder that these only skip mains
    'closed_namespaces',
    'hierarchies',
    'make_catalog',
    'scig',
    'scigraph_codegen',
    ['ontload', 'graph'],
    ['ontutils', 'deadlinks'],
    ['ontutils', 'version-iri'],
)
#requests.exceptions.SSLError

if auth.get_path('scigraph-services') is None:
    skip += ('scigraph_deploy',)  # this will fail # FIXME this should really only skip main not both main and import?

working_dir = get_working_dir(__file__)
if working_dir is None:
    # python setup.py test will run from the module_parent folder
    # I'm pretty the split was only implemented because I was trying
    # to run all tests from the working_dir in one shot, but that has
    # a number of problems with references to local vs installed packages
    import inspect
    sf = inspect.getsourcefile(pyontutils)
    working_dir = Path(sf).parent.parent
else:
    class RP(aug.RepoPath):
        """ can't just change RepoPath._repo_class due to
            fail in the no commit case """
        _repo_class = Repo

    RP._bind_flavours()
    working_dir = RP(working_dir)

glb = auth.get_path('git-local-base')
olr = auth.get_path('ontology-local-repo')  # TODO clone to a safe testing repo
if olr.exists():
    ont_repo = Repo(olr)
    if isinstance(working_dir, aug.RepoPath):
        this_repo = working_dir.repo
        post_load = lambda : (ont_repo.remove_diff_untracked(),
                              ont_repo.checkout_diff_tracked(),
                              this_repo.remove_diff_untracked(),
                              this_repo.checkout_diff_tracked(),)
        post_main = lambda : (ont_repo.remove_diff_untracked(),
                              ont_repo.checkout_diff_tracked(),
                              this_repo.remove_diff_untracked(),
                              this_repo.checkout_diff_tracked(),)
    else:
        post_load = lambda : (ont_repo.remove_diff_untracked(),
                              ont_repo.checkout_diff_tracked())
        post_main = lambda : (ont_repo.remove_diff_untracked(),
                              ont_repo.checkout_diff_tracked())
else:
    if isinstance(working_dir, aug.RepoPath):
        this_repo = working_dir.repo
        post_load = lambda : (this_repo.remove_diff_untracked(),
                              this_repo.checkout_diff_tracked(),)
        post_main = lambda : (this_repo.remove_diff_untracked(),
                              this_repo.checkout_diff_tracked(),)

    else:
        post_load = lambda : None
        post_main = lambda : None


do_mains = True


default_dir = aug.AugmentedPath(__file__).parent

_test_ttl = (default_dir / 'graphload-test.ttl')
test_ttl = _test_ttl.as_posix()
_test_owl = (default_dir / 'owl-test.ttl')
test_owl = _test_owl.as_posix()
_temp_git = aug.RepoPath(temp_path) / 'git-test'
temp_git = _temp_git.as_posix()

nsmethodsobo = (glb / 'methodsOntology/source-material/ns_methods.obo').as_posix()


### build mains

mains = {'scigraph':None,
         'combinators':None,
         'hierarchies':None,
         'closed_namespaces':None,
         'clifun': [['clifun'],
                    ['clifun', 'sub-command-1', 'arg1', 'arg2'],
                    ['clifun', 'sub-command-2', 'sub-command-1', 'arg3'],],
         'googapis': ['googapis', '--help'],
         'make_catalog':['ont-catalog',
                         '-l', temp_git,
                         '--jobs', '1'],  # hits the network
         'graphml_to_ttl':['graphml-to-ttl', 'development/methods/methods_isa.graphml'],
#['ilxcli', '--help'],
         'obo_io':['obo-io', '-t', 'ttl', nsmethodsobo],
'ttlfmt':[['ttlfmt', test_ttl],
          ['ttlfmt', '--version'],
         ],
'qnamefix':[['qnamefix', test_ttl],
            ['qnamefix', test_ttl],
            ['qnamefix', '-x', 'skos', test_ttl],
           ],
'necromancy':['necromancy', '-l', temp_path_ap, '--mkdir', test_ttl],
'ontload':[['ontload', '--help'],
           ['ontload', 'chain', 'NIF-Ontology', 'NIF', test_owl,
            '--zip-location', temp_path_ap],  # this hits the network, so why doesn't it fail in sandbox?
           ['ontload', 'config', 'NIF-Ontology', 'NIF', temp_path_ap,
            '--zip-location', temp_path_ap,],
           ['ontload', 'graph', 'NIF-Ontology', 'NIF',
            '--zip-location', temp_path_ap,
            '--git-local', temp_path_ap,
            '--graphload-ontologies', (default_dir / 'ontologies-test.yaml').resolve().as_posix()],  # FIXME cleanup
           ['ontload', 'imports', 'NIF-Ontology', 'NIF', test_ttl]],
'ontutils':[['ontutils', '--help'],
            ['ontutils', 'deadlinks', test_owl],
            ['ontutils', 'version-iri', test_owl],
            #['ontutils', 'spell', test_ttl],  #  FIXME skipping for now due to huspell dependency
            #['ontutils', 'diff', 'test/diff-before.ttl', 'test/diff-after.ttl', 'definition:', 'skos:definition'],
           ],
'overlaps':['overlaps', '--help'],
'scigraph_codegen':['scigraph-codegen', '--api', 'https://scicrunch.org/api/1/scigraph'],
'scigraph_deploy':[
    ['scigraph-deploy', '--help'],
    ['scigraph-deploy', 'all', 'NIF-Ontology', 'NIF', 'localhost', 'localhost'],
    ['scigraph-deploy', 'graph', 'NIF-Ontology', 'NIF', 'localhost', 'localhost'],
    ['scigraph-deploy', 'config', 'localhost', 'localhost', '-L'],
    ['scigraph-deploy', 'config', 'localhost', 'localhost'],
    ['scigraph-deploy', 'services', 'localhost', 'localhost'],
    ['scigraph-deploy', '--view-defaults']],
'scig':[['scig', 'c', '-v'],
        ['scig', 'v', '-v', 'BIRNLEX:796'],
        ['scig', 't', '-v', 'brain'],
        ['scig', 's', '-v', 'fat'],
        ['scig', 'g', '-v', 'BIRNLEX:796'],
        ['scig', 'g', '-v', 'BIRNLEX:796', '--rt', 'subClassOf'],
        ['scig', 'e', '-v', 'IAO:0100001', 'BIRNLEX:796', 'UBERON:0000955'],
        ['scig', 'cy', '"MATCH (n) RETURN n"'],
        ['scig', 'onts'],
],

}

if 'CI' not in os.environ:
    mains['mapnlxilx'] = None  # requires db connection

print(skip)
TestScripts.populate_tests(pyontutils, working_dir, mains,
                           skip=skip, network_tests=network_tests,
                           post_load=post_load, post_main=post_main,
                           only=only, do_mains=do_mains)
