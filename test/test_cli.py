""" Tests for the various cli programs """

from IPython import embed
import os
import sys
import unittest
import subprocess
from pathlib import Path
from git import Repo

from pyontutils.config import devconfig
p1 = Path(__file__).resolve().absolute().parent.parent.parent
p2 = Path(devconfig.git_local_base).resolve().absolute()
print(p1, p2)
if p1 != p2:
    devconfig.git_local_base = p1

from pyontutils import scigraph
from pyontutils import core
from pyontutils import scigraph_client

# orig_basepath = scigraph_client.BASEPATH
orig_basepath = 'https://scicrunch.org/api/1/scigraph'

if 'SCICRUNCH_API_KEY' in os.environ:
    devconfig.scigraph_api = orig_basepath
    scigraph.scigraph_client.BASEPATH = orig_basepath
else:
    local_basepath = 'http://localhost:9000/scigraph'
    devconfig.scigraph_api = local_basepath
    scigraph.scigraph_client.BASEPATH = local_basepath

checkout_ok = 'NIFSTD_CHECKOUT_OK' in os.environ

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

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)


class TestScripts(Folders):
    """ Import everything and run main() on a subset of those """
    # NOTE printing issues here have to do with nose not suppressing printing during coverage tests

    def setUp(self, checkout_ok=checkout_ok):
        super().setUp()
        if not hasattr(self, '_do_mains'):
            self.__class__._do_mains = []
            self.__class__._do_tests = []

    def test_import(self):
        skip = ('cocomac_uberon',  # known broken
                'neuron_ma2015',  # still needs work
                'old_neuron_example',  # known broken
               )
        lasts = tuple()
        neurons = ('neurons',
                   'neuron_lang',
                   'neuron_example',
                   'phenotype_namespaces',)
        if not checkout_ok:
            skip += neurons
        else:
            lasts += tuple(f'pyontutils/{s}.py' for s in neurons)

        ban = Path(devconfig.ontology_local_repo, 'ttl/BIRNLex_annotation_properties.ttl').as_posix()
        zap = 'git checkout $(git ls-files {*,*/*,*/*/*}.ttl)'
        mains = {'nif_cell':None,
                 'methods':None,
                 'core':None,
                 'scigraph':None,
                 'graphml_to_ttl':['graphml-to-ttl', 'development/methods/methods_isa.graphml'],
        #['ilxcli', '--help'],
        'ttlfmt':[['ttlfmt', ban],
                  #[zap]
                 ],
        'qnamefix':[['qnamefix', ban],
                    #[zap]
                   ],
        'necromancy':['necromancy', ban],
        'ontload':[['ontload', '--help'],
                   ['ontload', 'imports', 'NIF-Ontology', 'NIF', ban],
                   ['cd', devconfig.ontology_local_repo + '/ttl', '&&', 'git', 'checkout', ban]],
        'ontutils':[['ontutils', '--help'],
                    #['ontutils', 'diff', 'test/diff-before.ttl', 'test/diff-after.ttl', 'definition:', 'skos:definition'],
                   ],
        'ontree':['ontree', '--test'],
        'overlaps':['overlaps', '--help'],
        'scr_sync':['registry-sync', '--test'],
        'scigraph_codegen':['scigraph-codegen'],
        'scigraph_deploy':[
            ['scigraph-deploy', '--help'],
            ['scigraph-deploy', 'all', 'NIF-Ontology', 'NIF', 'localhost', 'localhost'],
            ['scigraph-deploy', 'graph', 'NIF-Ontology', 'NIF', 'localhost', 'localhost'],
            ['scigraph-deploy', 'config', 'localhost', 'localhost', '-L'],
            ['scigraph-deploy', 'config', 'localhost', 'localhost'],
            ['scigraph-deploy', 'services', 'localhost', 'localhost'],
            ['scigraph-deploy', '--view-defaults']],
        'scig':['scig', 't', '-v', 'brain'],

        }
        tests = tuple()  # moved to mains --test

        _do_mains = []
        _do_tests = []
        parent = Path(core.__file__).absolute().parent.parent
        repo = Repo(parent.as_posix())
        paths = sorted(repo.git.ls_files('pyontutils/*.py').split('\n'))
        for last in lasts:
            # FIXME hack to go last
            if last in paths:
                paths.remove(last)
                paths.append(last)

        for path in paths:
            stem = Path(path).stem
            if stem not in skip:
                print('TESTING:', stem)
                module = __import__('pyontutils.' + stem)
                submod = getattr(module, stem)
                if hasattr(submod, '_CHECKOUT_OK'):
                    print(submod, submod._CHECKOUT_OK)
                    setattr(submod, '_CHECKOUT_OK', True)

                if stem in mains:
                    print('    will main', stem, module)
                    argv = mains[stem]
                    if argv and type(argv[0]) == list:
                        argvs = argv
                    else:
                        argvs = argv,

                    for argv in argvs:
                        _do_mains.append((getattr(module, stem), argv))
                    #_modules.append(module)  # TODO doens't quite work
                elif stem in tests:
                    print('    will test', stem, module)
                    _do_tests.append(getattr(module, stem))

        print(_do_mains, _do_tests)
        self._do_mains.extend(_do_mains)
        self._do_tests.extend(_do_tests)
        if not hasattr(self.__class__, 'argv_orig'):
            self.__class__.argv_orig = sys.argv

    def test_mains(self):
        failed = []
        if not self._do_mains:
            raise ValueError('test_imports did not complete successfully')
        for script, argv in self._do_mains:
            if argv and argv[0] != script:
                os.system(' '.join(argv))

            try:
                if argv is not None:
                    sys.argv = argv
                else:
                    sys.argv = self.argv_orig

                script.main()
            except BaseException as e:
                if isinstance(e, SystemExit):
                    continue  # --help
                failed.append((script, e, argv))

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)

    def test_tests(self):
        failed = []
        for script in self._do_tests:
            try:
                script.test()
            except BaseException as e:
                failed.append((script, e))

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)
