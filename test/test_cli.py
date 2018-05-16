""" Tests for the various cli programs """

import os
import unittest
import subprocess
from pathlib import Path
from git import Repo

from pyontutils import scigraph_client

# orig_basepath = scigraph_client.BASEPATH
orig_basepath = 'https://scicrunch.org/api/1/scigraph'

from pyontutils import scigraph
from pyontutils import core
from pyontutils.config import devconfig

if 'SCICRUNCH_API_KEY' in os.environ:
    scigraph.scigraph_client.BASEPATH = orig_basepath
else:
    scigraph.scigraph_client.BASEPATH = 'http://localhost:9000/scigraph'


class Folders(unittest.TestCase):
    _folders =  ('ttl', 'ttl/generated', 'ttl/generated/parcellation', 'ttl/bridge')
    def setUp(self):
        #print('SET UP')
        #print(devconfig.ontology_local_repo)
        if devconfig.ontology_local_repo.isDefault:
            self.fake_local_repo = Path(devconfig.git_local_base, devconfig.ontology_repo)
            if not self.fake_local_repo.exists():  # do not klobber existing
                self.folders = [(self.fake_local_repo / folder)
                                for folder in self._folders]
                self.addCleanup(self._tearDown)
                #print(f'CREATING FOLDERS {self.folders}')
                for folder in self.folders:
                    folder.mkdir(parents=True)
                    # if the parent doesn't exist then there should never
                    # be a case where there is a collision (yes?)

        else:
            self.folders = []

    def recursive_clean(self, d):
        for thing in d.iterdir():
            if thing.is_dir():
                self.recursive_clean(thing)
            else:
                thing.unlink()  # will rm the file

        d.rmdir()

    def _tearDown(self):
        #print('TEAR DOWN')
        if self.folders:
            #print(f'DELETING FOLDERS {self.folders}')
            self.recursive_clean(self.fake_local_repo)


class TestCli(Folders):
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


class TestScripts(Folders):
    """ Import everything and run main() on a subset of those """

    def setUp(self):
        super().setUp()
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
        tests = ('ontree',
        )

        _do_mains = []
        _do_tests = []
        parent = Path(core.__file__).absolute().parent.parent
        repo = Repo(parent.as_posix())
        for path in sorted(repo.git.ls_files('pyontutils/*.py').split('\n')):
            stem = Path(path).stem
            if stem not in skip:
                print('TESTING:', stem)
                module = __import__('pyontutils.' + stem)
                if stem in mains:
                    print('    will main', stem, module)
                    _do_mains.append(getattr(module, stem))
                    #_modules.append(module)  # TODO doens't quite work
                elif stem in tests:
                    print('    will test', stem, module)
                    _do_tests.append(getattr(module, stem))

        print(_do_mains, _do_tests)
        self._do_mains = _do_mains
        self._do_tests = _do_tests

    def test_mains(self):
        failed = []
        for script in self._do_mains:
            try:
                script.main()
            except BaseException as e:
                failed.append((script, e))

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)

    def test_tests(self):
        failed = []
        for script in self._do_tests:
            try:
                script.test()
            except BaseException as e:
                failed.append((script, e))

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)
