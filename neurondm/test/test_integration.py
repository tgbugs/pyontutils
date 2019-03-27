import unittest
from pathlib import Path
from pyontutils.integration_test_helper import TestScriptsBase
import neurondm

class TestScripts(TestScriptsBase):
    """ woo! """

mains = {}

module_parent = Path(__file__).resolve().parent.parent.as_posix()
working_dir = Path(__file__).resolve().parent.parent.parent.as_posix()
print(module_parent)
print(working_dir)

TestScripts.populate_tests(neurondm, working_dir, mains, module_parent=module_parent, only=[], do_mains=True)
