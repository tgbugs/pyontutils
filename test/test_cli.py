""" Tests for the various cli programs """

import sys
import unittest
import subprocess
from pyontutils.integration_test_helper import TestCliBase, Folders


class TestCli(Folders, TestCliBase):
    commands = (
        ['graphml-to-ttl', '--help'],
        ['ilxcli', '--help'],
        ['necromancy', '--help'],
        ['ontload', '--help'],
        ['ontree', '--help'],
        ['overlaps', '--help'],
        ['qnamefix', '--help'],
        ['registry-sync', '--test'],
        ['scigraph-codegen', '--help'],
        ['scigraph-deploy', '--help'],
        ['scig', '--help'],
        ['ttlfmt', '--help'],
        [sys.executable, 'resolver/make_config.py'],
        # strange that make_config failed in travis in a pipenv as couldn't find pyontutils?
    )
