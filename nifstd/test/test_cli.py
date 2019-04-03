""" Tests for the various cli programs """

import sys
from pyontutils.utils import get_working_dir
from pyontutils.integration_test_helper import _TestCliBase, Folders

extras = tuple()
if get_working_dir(__file__):
    # strange that make_config failed in travis in a pipenv as couldn't find pyontutils?
    extras += ([sys.executable, 'resolver/make_config.py'],)


class TestCli(Folders, _TestCliBase):
    commands = (
        ['ontree', '--help'],
        ['registry-sync', '--test'],
        *extras)
