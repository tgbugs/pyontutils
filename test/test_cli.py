""" Tests for the various cli programs """

import os
import sys
import unittest
import subprocess
from importlib import import_module
from pathlib import Path
import git
from git import Repo as baseRepo
from pyontutils.utils import working_dir, TermColors as tc
from pyontutils.config import devconfig, checkout_ok


class Repo(baseRepo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._untracked_start = self.untracked()

    def untracked(self):
        return set(self.git.ls_files('--others', '--exclude-standard').split('\n'))

    def diff_untracked(self):
        new_untracked = self.untracked()
        diff = new_untracked - self._untracked_start
        return diff

    def remove_diff_untracked(self):
        wd = Path(self.working_dir)
        for tail in self.diff_untracked():
            path = wd / tail
            print('removing file', path)
            path.unlink()


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

        msg = '\n'.join('\n'.join(str(e) for e in f) for f in failed)
        assert not failed, msg


class TestScripts(Folders):
    """ Import everything and run main() on a subset of those
        NOTE If you are debugging this. Most of the functions in this
        class are defined dynamically by populate_tests, and you will not
        find their code here. """
    # NOTE printing issues here have to do with nose not suppressing printing during coverage tests

    def setUp(self):
        super().setUp()
        if not hasattr(self, '_modules'):
            self.__class__._modules = {}

        if not hasattr(self, '_do_mains'):
            self.__class__._do_mains = []
            self.__class__._do_tests = []

    def notest_mains(self):
        failed = []
        if not self._do_mains:
            raise ValueError('test_imports did not complete successfully')
        for script, argv in self._do_mains:
            pass
        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)

    def notest_tests(self):
        failed = []
        for script in self._do_tests:
            try:
                script.test()
            except BaseException as e:
                failed.append((script, e))

        assert not failed, '\n'.join('\n'.join(str(e) for e in f) for f in failed)


def populate_tests():
    skip = ('cocomac_uberon',  # known broken
            'old_neuron_example',  # known broken
            'cuts',  # issues with neuron_models.compiled vs load from ontology
    )
    if 'TRAVIS' in os.environ:
        skip += ('librdf',  # getting python3-librdf installed is too much of a pain atm
        )

    lasts = tuple()
    neurons = ('neurons/core',
               'neurons/lang',
               'neurons/example',
               'phenotype_namespaces',
               'neurons/models/allen_cell_types',
               'neurons/models/phenotype_direct',
               'neurons/models/basic_neurons',
               'neurons/models/huang2017',
               'neurons/models/ma2015',
               'neurons/models/cuts',
               'neurons/build',
              )
    print('checkout ok:', checkout_ok)

    ont_branch = Repo(devconfig.ontology_local_repo).active_branch.name
    if not checkout_ok and ont_branch != 'neurons':
        skip += tuple(n.split('/')[-1] for n in neurons)  # FIXME don't use stem below
    else:
        lasts += tuple(f'pyontutils/{s}.py' for s in neurons)

    ban = Path(devconfig.ontology_local_repo, 'ttl/BIRNLex_annotation_properties.ttl').as_posix()
    mba = Path(devconfig.ontology_local_repo, 'ttl/generated/parcellation/mbaslim.ttl').as_posix()
    nifttl = Path(devconfig.ontology_local_repo, 'ttl/nif.ttl').as_posix()
    nsmethodsobo = Path(devconfig.git_local_base, 'methodsOntology/source-material/ns_methods.obo').as_posix()
    zap = 'git checkout $(git ls-files {*,*/*,*/*/*}.ttl)'
    mains = {'methods':None,
             'nif_cell':None,
             'scigraph':None,
             'hbp_cells':None,
             'nif_neuron':None,
             'combinators':None,
             'hierarchies':None,
             'chebi_bridge':None,
             'cocomac_uberon':None,
             'gen_nat_models':None,
             'closed_namespaces':None,
             #'docs':['ont-docs'],  # can't seem to get this to work correctly on travis so leaving it out for now
             'make_catalog':['ont-catalog', '--jobs', '1'],
             'parcellation':['parcellation', '--jobs', '1'],
             'graphml_to_ttl':['graphml-to-ttl', 'development/methods/methods_isa.graphml'],
    #['ilxcli', '--help'],
             'obo_io':['obo-io', '--ttl', nsmethodsobo],
    'ttlfmt':[['ttlfmt', ban],
              ['ttlfmt', '--version'],
              #[zap]
             ],
    'qnamefix':[['qnamefix', ban],
                ['qnamefix', mba],
                #[zap]
               ],
    'necromancy':['necromancy', ban],
    'ontload':[['ontload', '--help'],
               ['ontload', 'imports', 'NIF-Ontology', 'NIF', ban],
               ['ontload', 'chain', 'NIF-Ontology', 'NIF', nifttl],  # this hits the network
               ['cd', devconfig.ontology_local_repo + '/ttl', '&&', 'git', 'checkout', ban]],
    'ontutils':[['ontutils', '--help'],
                ['ontutils', 'deadlinks', nifttl],
                ['ontutils', 'version-iri', nifttl],
                ['ontutils', 'spell', ban],
                #['ontutils', 'diff', 'test/diff-before.ttl', 'test/diff-after.ttl', 'definition:', 'skos:definition'],
               ],
    'ontree':['ontree', '--test'],
    'overlaps':['overlaps', '--help'],
    'scr_sync':['registry-sync', '--test'],
    'scigraph_codegen':['scigraph-codegen', '--api', 'https://scicrunch.org/api/1/scigraph'],
    'scigraph_deploy':[
        ['scigraph-deploy', '--help'],
        ['scigraph-deploy', 'all', 'NIF-Ontology', 'NIF', 'localhost', 'localhost'],
        ['scigraph-deploy', 'graph', 'NIF-Ontology', 'NIF', 'localhost', 'localhost'],
        ['scigraph-deploy', 'config', 'localhost', 'localhost', '-L'],
        ['scigraph-deploy', 'config', 'localhost', 'localhost'],
        ['scigraph-deploy', 'services', 'localhost', 'localhost'],
        ['scigraph-deploy', '--view-defaults']],
    'scig':[['scig', 'c', '-v'],
            ['scig', 'v', '-v', 'BIRNLEX:796'],
            ['scig', 't', '-v', 'brain'],
            ['scig', 's', '-v', 'fat'],
            ['scig', 'g', '-v', 'BIRNLEX:796'],
            ['scig', 'g', '-v', 'BIRNLEX:796', '--rt', 'subClassOf'],
            ['scig', 'e', '-v', 'IAO:0100001' 'BIRNLEX:796' 'UBERON:0000955'],
            ['scig', 'cy', '"MATCH (n) RETURN n"'],
            ['scig', 'onts'],
    ],

    }
    if 'CI' not in os.environ:
        mains['mapnlxilx'] = None  # requires db connection

    tests = tuple()  # moved to mains --test

    _do_mains = []
    _do_tests = []
    try:
        ont_repo = Repo(devconfig.ontology_local_repo)
        repo = Repo(working_dir.as_posix())
        paths = sorted(f.rsplit('/', 1)[0] if '__main__' in f else f
                       for f in repo.git.ls_files().split('\n')
                       if f.endswith('.py') and
                       f.startswith('pyontutils') and
                       '__init__' not in f)

        for last in lasts:
            # FIXME hack to go last
            if last in paths:
                paths.remove(last)
                paths.append(last)

        npaths = len(paths)
        for i, path in enumerate(paths):
            ppath = Path(path).absolute()
            #print('PPATH:  ', ppath)
            pex = ppath.as_posix().replace('/', '_').replace('.', '_')
            fname = f'test_{i:0>3}_' + pex
            stem = ppath.stem
            #if not any(f'pyontutils/{p}.py' in path for p in neurons):
                #print('skipping:', path)
                #continue
            rp = ppath.relative_to(repo.working_dir)
            module_path = (rp.parent / rp.stem).as_posix().replace('/', '.')
            if stem not in skip:
                def test_file(self, module_path=module_path, stem=stem):
                    try:
                        print(tc.ltyellow('IMPORTING:'), module_path)
                        module = import_module(module_path)  # this returns the submod
                        self._modules[module_path] = module
                        if hasattr(module, '_CHECKOUT_OK'):
                            print(tc.blue('MODULE CHECKOUT:'), module, module._CHECKOUT_OK)
                            setattr(module, '_CHECKOUT_OK', True)
                            #print(tc.blue('MODULE'), tc.ltyellow('CHECKOUT:'), module, module._CHECKOUT_OK)
                    finally:
                        ont_repo.remove_diff_untracked()

                setattr(TestScripts, fname, test_file)

                if stem in mains:
                    argv = mains[stem]
                    if argv and type(argv[0]) == list:
                        argvs = argv
                    else:
                        argvs = argv,
                else:
                    argvs = None,

                for j, argv in enumerate(argvs):
                    mname = f'test_{i + npaths:0>3}_{j:0>3}_' + pex
                    #print('MPATH:  ', module_path)
                    def test_main(self, module_path=module_path, argv=argv, main=stem in mains, test=stem in tests):
                        try:
                            script = self._modules[module_path]
                        except KeyError:
                            return print('Import failed for', module_path, 'cannot test main, skipping.')

                        if argv and argv[0] != script:
                            os.system(' '.join(argv))  # FIXME error on this?

                        try:
                            if argv is not None:
                                sys.argv = argv
                            else:
                                sys.argv = self.argv_orig

                            if main:
                                print(tc.ltyellow('MAINING:'), module_path)
                                script.main()
                            elif test:
                                print(tc.ltyellow('TESTING:'), module_path)
                                script.test()  # FIXME mutex and confusion
                        except BaseException as e:
                            if isinstance(e, SystemExit):
                                return  # --help
                            raise e
                        finally:
                            ont_repo.remove_diff_untracked()

                    setattr(TestScripts, mname, test_main)

    except git.exc.InvalidGitRepositoryError:  # testing elsewhere
        import pyontutils
        import pkgutil
        modinfos = list(pkgutil.iter_modules(pyontutils.__path__))
        modpaths = [pyontutils.__name__ + '.' + modinfo.name
                    for modinfo in modinfos]
        for modpath in modpaths:
            fname = 'test_' + modpath.replace('.', '_')
            def test_file(self, modpath=modpath):
                print(tc.ltyellow('IMPORTING:'), modpath)
                module = import_module(modpath)
                self._modules[modpath] = module

            setattr(TestScripts, fname, test_file)

    if not hasattr(TestScripts, 'argv_orig'):
        TestScripts.argv_orig = sys.argv

populate_tests()
