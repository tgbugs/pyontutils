""" Tests for the various cli programs """

import unittest
import subprocess

class TestCli(unittest.TestCase):
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
    )
    
    def test_cli(self):
        failed = []
        for command in self.commands:
            try:
                output = subprocess.check_output(command,
                                                 stderr=subprocess.STDOUT).decode().rstrip()
            except BaseException as e:
                failed.append([command, e, e.stdout if hasattr(e, 'stdout') else '', ''])

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)

