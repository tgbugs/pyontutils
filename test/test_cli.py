""" Tests for the various cli programs """

import os
import unittest
import subprocess
from glob import glob
from pathlib import Path

from pyontutils import scigraph_client

orig_basepath = scigraph_client.BASEPATH

from pyontutils import scigraph
from pyontutils import core

if 'SCICRUNCH_API_KEY' in os.environ:
    scigraph.scigraph_client.BASEPATH = orig_basepath
else:
    scigraph.scigraph_client.BASEPATH = 'http://localhost:9000/scigraph'

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
    """ Import everything and run main() on a subset of those """

    skip = ('neurons',
            'neuron_lang',
            'neuron_example',
            'neuron_ma2015',
            'phenotype_namespaces',  # FIXME clearly we know what the problem project is :/
            'old_neuron_example',
            'cocomac_uberon'
           )

    mains = ('nif_cell',
            )

    _modules = []
    for path in sorted(Path(core.__file__).parent.glob('*.py')):
        stem = path.stem
        if stem not in skip:
            print('TESTING:', stem)
            module = __import__('pyontutils.' + stem)
            if stem in mains:
                print('    will test', stem, module)
                #_modules.append(module)  # TODO doens't quite work

    print(_modules)

    def test_scripts(self):
        failed = []
        for script in self._modules:
            try:
                script.main()
            except BaseException as e:
                failed.append((script, e))

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)

