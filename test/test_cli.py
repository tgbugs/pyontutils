""" Tests for the various cli programs """

import sys
import unittest
import subprocess
from test.common import Folders


class TestCli(Folders, unittest.TestCase):
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

    def test_cli(self):
        # we still run these tests to make sure that the install process works as expected
        failed = []
        for command in self.commands:
            try:
                output = subprocess.check_output(command,
                                                 stderr=subprocess.STDOUT).decode().rstrip()
            except BaseException as e:
                failed.append((command, e, e.stdout if hasattr(e, 'stdout') else '', ''))

        msg = '\n'.join('\n'.join(str(e) for e in f) for f in failed)
        assert not failed, msg
