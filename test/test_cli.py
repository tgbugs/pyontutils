""" Tests for the various cli programs """

import unittest
import subprocess
from glob import glob
from pathlib import Path
from pyontutils import core

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
                failed.append((command, e, e.stdout if hasattr(e, 'stdout') else '', ''))

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)

class TestScripts(unittest.TestCase):
    """ Test other random python scripts that are not run frequently """

    for path in sorted(Path(core.__file__).parent.glob('*.py')):
        __import__('pyontutils.' + path.stem)

    scripts = []

    def test_scripts(self):
        failed = []
        for script in scripts:
            try:
                script.main()
            except BaseException as e:
                failed.append((script, e))

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)

