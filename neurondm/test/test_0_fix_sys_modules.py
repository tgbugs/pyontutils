# pytest module discovery somehow adds the nested compiled module
# and models module to sys.modules which breaks tests, so we run
# this file as the first test after test collection
# I'm sure there is a non-hacked sanctioned way to actually do this
# but for now let's not worry about that
import sys


def test_fix_sys_modules():
    sys.modules.pop('compiled', None)
    sys.modules.pop('models', None)
