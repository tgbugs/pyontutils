import os
import sys
import stat
import shutil
import unittest
import subprocess
from importlib import import_module
import git
import pytest
from pathlib import Path
#from augpathlib import AugmentedPath as Path
from git import Repo as baseRepo
from pyontutils.utils import TermColors as tc
from pyontutils.config import auth


SKIP_NETWORK = ('SKIP_NETWORK' in os.environ or
                'FEATURES' in os.environ and 'network-sandbox' in os.environ['FEATURES'])
skipif_no_net = pytest.mark.skipif(SKIP_NETWORK, reason='Skipping due to network requirement')


def simpleskipif(skip):
    def inner(function):
        if skip:
            return lambda self: pytest.skip('skipping mains')
        else:
            return function

    return inner


def onerror_windows_readwrite_remove(action, name, exc):
    """ helper for deleting readonly files on windows """
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


onerror = onerror_windows_readwrite_remove if os.name == 'nt' else None


def modinfo_to_path(mod):
    p = Path(mod.module_finder.path, mod.name)
    if mod.ispkg:
        return p
    else:
        return p.with_suffix('.py')


class Repo(baseRepo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._untracked_start = self.untracked
        self._tracked_start = self.tracked
        # things
        self.is_dirty()

    @property
    def untracked(self):
        return set(self.untracked_files)

    @property
    def tracked(self):
        """ get a `git status` like diff of unstaged files """
        out = set()
        for diff in self.head.commit.diff(None):
            if diff.change_type == 'M':
                out.add(diff.a_path)

        return out

    def diff_tracked(self):
        new_tracked = self.tracked
        diff = new_tracked - self._tracked_start
        return diff

    def diff_untracked(self):
        new_untracked = self.untracked
        diff = new_untracked - self._untracked_start
        return diff

    def remove_diff_untracked(self):
        wd = Path(self.working_dir)
        for tail in self.diff_untracked():
            path = wd / tail
            print('removing file', path)
            path.unlink()

    def checkout_diff_tracked(self):
        self.git.checkout('--', *self.diff_tracked())


class Folders:
    _folders =  ('ttl', 'ttl/generated', 'ttl/generated/parcellation', 'ttl/bridge')
    def setUp(self):
        super().setUp()
        olr = auth.get_path('ontology-local-repo').resolve()
        olr_default = auth.get_path_default('ontology-local-repo').resolve()
        if olr == olr_default:
            self.fake_local_repo = auth.get_path('git-local-base') / auth.get('ontology-repo')
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


class _TestScriptsBase(unittest.TestCase):
    """ Import everything and run main() on a subset of those
        NOTE If you are debugging this. Most of the functions in this
        class are defined dynamically by populate_tests, and you will not
        find their code here. """
    # NOTE printing issues here have to do with nose not suppressing printing during coverage tests

    temp_path = None

    def setUp(self):
        super().setUp()
        if not hasattr(self, '_modules'):
            self.__class__._modules = {}

        if not hasattr(self, '_do_mains'):
            self.__class__._do_mains = []
            self.__class__._do_tests = []

        if self.temp_path is not None:
            if not self.temp_path.exists():
                self.temp_path.mkdir()

    def tearDown(self):
        if self.temp_path is not None:
            if self.temp_path.exists():
                shutil.rmtree(self.temp_path, onerror=onerror)

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

    @classmethod
    def make_test_file(cls, i_ind, ppath, post_load, module_parent, skip, ci_skip):
        #print('PPATH:  ', ppath)
        pex = ppath.as_posix().replace('/', '_').replace('.', '_')
        fname = f'test_{i_ind:0>3}_' + pex
        stem = ppath.stem
        #rp = ppath.relative_to(Path.cwd())#module_parent)
        rp = ppath.relative_to(module_parent)
        #rp = ppath.relative_path_from(Path(module_parent))
        module_path = (rp.parent / rp.stem).as_posix().replace('/', '.')
        def test_file(self, module_path=module_path, stem=stem, fname=fname):
            try:
                print(tc.ltyellow('IMPORTING:'), module_path)
                module = import_module(module_path)  # this returns the submod
                self._modules[module_path] = module
                if hasattr(module, '_CHECKOUT_OK'):
                    print(tc.blue('MODULE CHECKOUT:'), module, module._CHECKOUT_OK)
                    setattr(module, '_CHECKOUT_OK', True)
                    #print(tc.blue('MODULE'), tc.ltyellow('CHECKOUT:'), module, module._CHECKOUT_OK)
            #except BaseException as e:
                # FIXME this does not work because collected tests cannot be uncollected
                #suffix = fname.split('__', 1)[-1]
                #for mn in dir(self):
                    #if suffix in mn:
                        #old_func = getattr(self, mn)
                        #new_func = pytest.mark.xfail(raises=ModuleNotFoundError)(old_func)
                        #setattr(self, mn, new_func)

                #raise e
            finally:
                post_load()

        if stem in skip:
            test_file = pytest.mark.skip()(test_file)
        elif 'CI' in os.environ and stem in ci_skip:
            test_file = pytest.mark.skip(reason='Cannot test this in CI right now.')(test_file)

        return pex, fname, stem, module_path, test_file

    @classmethod
    def make_test_main(cls, do_mains, post_main, module_path, argv, main, test, skip):
        @simpleskipif(not do_mains)
        def test_main(self, module_path=module_path, argv=argv, main=main, test=test):
            try:
                script = self._modules[module_path]
            except KeyError as e:
                # we have to raise here becuase we can't delete
                # the test mfuncs once pytest has loaded them
                pytest.skip(f'Import failed for {module_path}'
                            ' cannot test main, skipping.')
                return

            if argv and argv[0] != script.__name__.rsplit('.', 1)[-1]:
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
                # docopt exit is a subclass of SystemExit
                # and we need that to fail
                if type(e) == SystemExit and '--help' in argv:
                    return

                print(f'failed to run {argv}')
                raise e
            finally:
                post_main()

        return test_main

    @classmethod
    def populate_from_paths(cls, paths, mains, tests, do_mains, post_load, post_main, module_parent, skip, ci_skip, network_tests):
        network_tests_prefix = [s for s in network_tests if not isinstance(s, str)]
        network_tests = [s for s in network_tests if isinstance(s, str)]
        npaths = len(paths)
        print(npaths)
        for i_ind, path in enumerate(paths):
            print(path)
            (pex, fname, stem, module_path,
             test_file) = cls.make_test_file(i_ind, path, post_load, module_parent, skip, ci_skip)
            setattr(cls, fname, test_file)

            if stem in mains:
                argv = mains[stem]
                if argv and type(argv[0]) == list:
                    argvs = argv
                else:
                    argvs = argv,
            else:
                argvs = None,

            for j_ind, argv in enumerate(argvs):
                mname = f'test_{i_ind + npaths:0>3}_{j_ind:0>3}_' + pex
                if argv:
                    mname += '_' + '_'.join(argv).replace('-', '_')

                #print('MPATH:  ', module_path)
                test_main = cls.make_test_main(do_mains, post_main, module_path, argv,
                                               stem in mains, stem in tests, skip)

                if stem in network_tests:
                    skipif_no_net(test_main)

                if network_tests_prefix and argv:
                    for nt in network_tests_prefix:
                        if len(argv) >= len(nt):
                            if all(arg == prefix for arg, prefix
                                   in zip(argv, nt)):
                                skipif_no_net(test_main)

                # FIXME do we need to setattr these test_files or no?
                if stem in skip:
                    test_file = pytest.mark.skip()(test_main)
                elif 'CI' in os.environ and stem in ci_skip:
                    test_file = pytest.mark.skip(reason='Cannot test this in CI right now.')(test_main)

                setattr(cls, mname, test_main)

    @classmethod
    def populate_tests(cls, module_to_test, working_dir, mains=tuple(), tests=tuple(),
                       lasts=tuple(), skip=tuple(), ci_skip=tuple(), network_tests=tuple(),
                       only=tuple(), do_mains=True,
                       post_load=lambda : None, post_main=lambda : None, module_parent=None):

        if module_parent is None:
            module_parent = working_dir

        if isinstance(working_dir, Path):
            working_dir = working_dir.as_posix()

        if isinstance(module_parent, Path):
            module_parent = module_parent.as_posix()

        p_wd = Path(working_dir)
        p_mp = Path(module_parent)
        relpath = p_mp.relative_to(p_wd).as_posix()
        if relpath == '.':
            relpath = ''
        else:
            relpath += '/'

        skip += Path(__file__).stem,  # prevent this file from accidentally testing itself

        if 'CI' not in os.environ:
            pass

        if only:
            mains = {k:v for k, v in mains.items() if k in only}
            print(mains)

        try:
            repo = git.Repo(working_dir)
            paths = sorted(f.rsplit('/', 1)[0] if '__main__' in f else f
                           for f in repo.git.ls_files().split('\n')
                           if f.endswith('.py') and
                           not print(f) and
                           f.startswith(relpath + module_to_test.__name__) and
                           '__init__' not in f and
                           (True if not only else
                            any(_ + '.py' in f for _ in only) or
                            any(_ + '/__main__.py' in f for _ in only)))

            for last in lasts:
                # FIXME hack to go last
                if last in paths:
                    paths.remove(last)
                    paths.append(last)

            ppaths = [Path(repo.working_dir, path).absolute() for path in paths]

        except git.exc.InvalidGitRepositoryError:  # testing elsewhere
            # FIXME TODO regularize this so that the same tests can run
            # when we are not in the repo ...
            import pkgutil
            modinfos = []
            def _rec(mod):
                for mi in pkgutil.iter_modules(mod):
                    if mi.ispkg:
                        sfl = mi.module_finder.find_spec(mi.name)
                        m = sfl.loader.load_module()
                        _rec(m.__path__)
                        # TODO __main__.py detection
                    else:
                        modinfos.append(mi)

            _rec(module_to_test.__path__)
            ppaths = [modinfo_to_path(m) for m in modinfos]

        cls.populate_from_paths(ppaths, mains, tests, do_mains, post_load, post_main,
                                module_parent, skip, ci_skip, network_tests)

        if not hasattr(cls, 'argv_orig'):
            cls.argv_orig = sys.argv


class _TestCliBase(unittest.TestCase):
    commands = tuple()

    def test_cli(self):  # note this will run itself in all cases, but that is ok
        # we still run these tests to make sure that the install process works as expected
        failed = []
        for command in self.commands:
            try:
                output = subprocess.check_output(command,
                                                 env=os.environ.copy(),
                                                 stderr=subprocess.STDOUT).decode().rstrip()
            except BaseException as e:
                raise e
                failed.append((command, e, e.stdout if hasattr(e, 'stdout') else '', ''))

        msg = '\n'.join('\n'.join(str(e) for e in f) for f in failed)
        assert not failed, msg
