import os
import sys
import unittest
from pathlib import Path
from importlib import import_module
import git
import pyontutils
from pyontutils.utils import TermColors as tc, get_working_dir
from pyontutils.config import devconfig
from pyontutils.integration_test_helper import _TestScriptsBase, Repo, Folders


class TestOntQuery(unittest.TestCase):
    """ ITs for ontquery """

    def setUp(self):
        from pyontutils.core import OntTerm
        self.OntTerm = OntTerm
        self.query = OntTerm.query

    def test_term(self):
        self.OntTerm('UBERON:0000955')

    def test_query(self):
        self.query('brain')


class TestScripts(Folders, _TestScriptsBase):
    """ woo ! """


only = tuple()
skip = tuple()
ci_skip = tuple()

if devconfig.scigraph_services is None:
    skip += ('scigraph_deploy',)  # this will fail # FIXME this should really only skip main not both main and import?

working_dir = get_working_dir(__file__)
if working_dir is None:
    # python setup.py test will run from the module_parent folder
    # I'm pretty the split was only implemented because I was trying
    # to run all tests from the working_dir in one shot, but that has
    # a number of problems with references to local vs installed packages
    working_dir = Path(__file__).parent.parent

devconfig._check_ontology_local_repo()  # FIXME maybe we can be a bit less blunt about it?
ont_repo = Repo(devconfig.ontology_local_repo)
post_load = lambda : (ont_repo.remove_diff_untracked(), ont_repo.checkout_diff_tracked())
post_main = lambda : (ont_repo.remove_diff_untracked(), ont_repo.checkout_diff_tracked())

### build mains

ban = Path(devconfig.ontology_local_repo, 'ttl/BIRNLex_annotation_properties.ttl').as_posix()
mba = Path(devconfig.ontology_local_repo, 'ttl/generated/parcellation/mbaslim.ttl').as_posix()
nifttl = Path(devconfig.ontology_local_repo, 'ttl/nif.ttl').as_posix()
nsmethodsobo = Path(devconfig.git_local_base, 'methodsOntology/source-material/ns_methods.obo').as_posix()
zap = 'git checkout $(git ls-files {*,*/*,*/*/*}.ttl)'
mains = {'scigraph':None,
         'combinators':None,
         'hierarchies':None,
         'closed_namespaces':None,
         #'docs':['ont-docs'],  # can't seem to get this to work correctly on travis so leaving it out for now
         'make_catalog':['ont-catalog', '--jobs', '1'],
         'graphml_to_ttl':['graphml-to-ttl', 'development/methods/methods_isa.graphml'],
#['ilxcli', '--help'],
         'obo_io':['obo-io', '--ttl', nsmethodsobo],
'ttlfmt':[['ttlfmt', ban],
          ['ttlfmt', '--version'],
          #[zap]
         ],
'qnamefix':[['qnamefix', ban],
            ['qnamefix', mba],
            #[zap]
           ],
'necromancy':['necromancy', ban],
'ontload':[['ontload', '--help'],
           ['ontload', 'imports', 'NIF-Ontology', 'NIF', ban],
           ['ontload', 'chain', 'NIF-Ontology', 'NIF', nifttl],  # this hits the network
           ['cd', devconfig.ontology_local_repo + '/ttl', '&&', 'git', 'checkout', ban]],
'ontutils':[['ontutils', '--help'],
            ['ontutils', 'deadlinks', nifttl],
            ['ontutils', 'version-iri', nifttl],
            #['ontutils', 'spell', ban],  #  FIXME skipping for now due to huspell dependency
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
        ['scig', 'e', '-v', 'IAO:0100001' 'BIRNLEX:796' 'UBERON:0000955'],
        ['scig', 'cy', '"MATCH (n) RETURN n"'],
        ['scig', 'onts'],
],

}

if 'CI' not in os.environ:
    mains['mapnlxilx'] = None  # requires db connection

print(skip)
TestScripts.populate_tests(pyontutils, working_dir, mains, skip=skip,
                           post_load=post_load, post_main=post_main,
                           only=only, do_mains=True)
