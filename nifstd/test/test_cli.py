""" Tests for the various cli programs """

import sys
from pyontutils.integration_test_helper import TestCliBase, Folders


class TestCli(Folders, TestCliBase):
    commands = (
        ['ilxcli', '--help'],
        ['ontree', '--help'],
        ['registry-sync', '--test'],
        [sys.executable, 'resolver/make_config.py'],
        # strange that make_config failed in travis in a pipenv as couldn't find pyontutils?
    )
