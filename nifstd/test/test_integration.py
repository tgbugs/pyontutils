import unittest
from pathlib import Path
from pyontutils.utils import get_working_dir
from pyontutils.config import auth
from pyontutils.integration_test_helper import _TestScriptsBase, Folders, Repo
import nifstd_tools


class TestScripts(Folders, _TestScriptsBase):
    """ woo! """


skip = tuple()
ci_skip = (
    'cocomac_uberon',  # lookups too slow when using remote scigraph
    'chebi_bridge',  # too slow generally
)
network_tests = (  # reminder that these only skip mains
    'methods',
    'ontree',
    'parcellation',
)

mains = {'methods': None,
         'nif_cell': None,
         'hbp_cells': None,  # needs methodsOntology
         'nif_neuron': None,
         'chebi_bridge': None,
         'gen_nat_models': None,
         'cocomac_uberon': None,  # needs entity_mapping
         'ontree': ['ontree', '--test'],
         'parcellation': ['parcellation', '--jobs', '1'],
         'scr_sync': ['registry-sync', '--test'],
        }

module_parent = Path(__file__).resolve().parent.parent
working_dir = get_working_dir(__file__)
if working_dir is None:
    # python setup.py test will run from the module_parent folder
    # I'm pretty the split was only implemented because I was trying
    # to run all tests from the working_dir in one shot, but that has
    # a number of problems with references to local vs installed packages
    working_dir = module_parent

olr = auth.get_path('ontology-local-repo')
do_mains = olr.exists()
if olr.exists():
    ont_repo = Repo(olr)
    post_load = lambda : (ont_repo.remove_diff_untracked(), ont_repo.checkout_diff_tracked())
    post_main = lambda : (ont_repo.remove_diff_untracked(), ont_repo.checkout_diff_tracked())
else:
    post_load = lambda : None
    post_main = lambda : None

TestScripts.populate_tests(nifstd_tools, working_dir, mains,
                           skip=skip, ci_skip=ci_skip,
                           network_tests=network_tests,
                           module_parent=module_parent,
                           post_load=post_load, post_main=post_main,
                           only=[], do_mains=do_mains)
