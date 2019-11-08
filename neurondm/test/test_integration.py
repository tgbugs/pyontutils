import unittest
from pathlib import Path
import pytest
from pyontutils.utils import get_working_dir
from pyontutils.config import auth
from pyontutils.integration_test_helper import _TestScriptsBase, Folders, Repo
import neurondm


class TestScripts(Folders, _TestScriptsBase):
    """ woo! """


only = tuple()

lasts = tuple()

neurons = ('neurondm/example',
           'neurondm/phenotype_namespaces',
           'neurondm/models/allen_cell_types',
           'neurondm/models/phenotype_direct',
           'neurondm/models/basic_neurons',
           'neurondm/models/huang2017',
           'neurondm/models/ma2015',
           'neurondm/models/cuts',
           'neurondm/build',
           'neurondm/sheets',)

skip = tuple()
olr = auth.get_path('ontology-local-repo')
if olr.exists():
    ont_repo = Repo(olr)
    # FIXME these aren't called?
    post_load = lambda : (ont_repo.remove_diff_untracked(), ont_repo.checkout_diff_tracked())
    post_main = lambda : (ont_repo.remove_diff_untracked(), ont_repo.checkout_diff_tracked())

    ### handle ontology branch behavior
    checkout_ok = neurondm.core.ont_checkout_ok
    print('checkout ok:', checkout_ok)
    ont_branch = ont_repo.active_branch.name
    if not checkout_ok and ont_branch != 'neurons':
        neurons += ('neurondm/core', 'neurondm/lang',)  # FIXME these two are ok for no repo but not wrong branch?!
        skip += tuple(n.split('/')[-1] for n in neurons)
    else:
        lasts += tuple(f'neurondm/{s}.py' for s in neurons)

else:
    skip += tuple(n.split('/')[-1] for n in neurons)


### build mains
mains = {}  # NOTE mains run even if this is empty ? is this desired?

module_parent = Path(__file__).resolve().parent.parent.as_posix()
working_dir = get_working_dir(__file__)
if working_dir is None:
    # python setup.py test will run from the module_parent folder
    # I'm pretty the split was only implemented because I was trying
    # to run all tests from the working_dir in one shot, but that has
    # a number of problems with references to local vs installed packages
    working_dir = module_parent

print(module_parent)
print(working_dir)

TestScripts.populate_tests(neurondm, working_dir, mains, skip=skip, lasts=lasts,
                           module_parent=module_parent, only=only, do_mains=True)
