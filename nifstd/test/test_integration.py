import unittest
from pathlib import Path
from pyontutils.integration_test_helper import TestScriptsBase, Folders, Repo
import nifstd_tools

class TestScripts(Folders, TestScriptsBase):
    """ woo! """

mains = {'nif_cell':None,
         'hbp_cells':None,
         'nif_neuron':None,
         'chebi_bridge':None,
         'cocomac_uberon':None,
         'gen_nat_models':None,
         'ontree':['ontree', '--test'],
         'scr_sync':['registry-sync', '--test'], }

module_parent = Path(__file__).resolve().parent.parent.as_posix()
working_dir = Path(__file__).resolve().parent.parent.parent.as_posix()

ont_repo = Repo(devconfig.ontology_local_repo)
post_load = lambda : (ont_repo.remove_diff_untracked(), ont_repo.checkout_diff_tracked())
post_main = lambda : (ont_repo.remove_diff_untracked(), ont_repo.checkout_diff_tracked())

TestScripts.populate_tests(nifstd_tools, working_dir, mains, module_parent=module_parent,
                           post_load=post_load, post_main=post_main,
                           only=[], do_mains=True)
