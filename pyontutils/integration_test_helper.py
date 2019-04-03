import os
import sys
import unittest
import subprocess
from pathlib import Path
from importlib import import_module
import git
import pytest
from git import Repo as baseRepo
from pyontutils.utils import TermColors as tc
from pyontutils.config import devconfig


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


class _TestScriptsBase(unittest.TestCase):
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


    @classmethod
    def populate_tests(cls, module_to_test, working_dir, mains=tuple(), tests=tuple(),
                       lasts=tuple(), skip=tuple(), ci_skip=tuple(), only=tuple(), do_mains=True,
                       post_load=lambda : None, post_main=lambda : None, module_parent=None):

        if module_parent is None:
            module_parent = working_dir

        if isinstance(working_dir, Path):
            working_dir = working_dir.as_posix()

        if isinstance(module_parent, Path):
            module_parent = module_parent.as_posix()

        relpath = Path(module_parent).relative_to(Path(working_dir)).as_posix()
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

        if not do_mains:
            mains = {}

        _do_mains = []
        _do_tests = []
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

            npaths = len(paths)
            print(npaths)
            for i, path in enumerate(paths):
                print(path)
                ppath = Path(repo.working_dir, path).absolute()
                print('PPATH:  ', ppath)
                pex = ppath.as_posix().replace('/', '_').replace('.', '_')
                fname = f'test_{i:0>3}_' + pex
                stem = ppath.stem
                #rp = ppath.relative_to(Path.cwd())#module_parent)
                rp = ppath.relative_to(module_parent)
                module_path = (rp.parent / rp.stem).as_posix().replace('/', '.')
                print(module_path)
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
                    test_file = pytest.mark.skip(reason='Cannot tests this in CI right now.')(test_file)

                setattr(cls, fname, test_file)

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
                        except KeyError as e:
                            # we have to raise here becuase we can't delete
                            # the test mfuncs once pytest has loaded them
                            pytest.skip(f'Import failed for {module_path}'
                                        ' cannot test main, skipping.')
                            return

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
                            post_main()

                    if stem in skip:
                        test_file = pytest.mark.skip()(test_main)
                    elif 'CI' in os.environ and stem in ci_skip:
                        test_file = pytest.mark.skip(reason='Cannot tests this in CI right now.')(test_main)

                    setattr(cls, mname, test_main)

        except git.exc.InvalidGitRepositoryError:  # testing elsewhere
            # FIXME TODO regularize this so that the same tests can run
            # when we are not in the repo ...
            import pkgutil
            modinfos = list(pkgutil.iter_modules(module_to_test.__path__))
            modpaths = [module_to_test.__name__ + '.' + modinfo.name
                        for modinfo in modinfos]
            for modpath in modpaths:
                fname = 'test_' + modpath.replace('.', '_')
                def test_file(self, modpath=modpath):
                    print(tc.ltyellow('IMPORTING:'), modpath)
                    module = import_module(modpath)
                    self._modules[modpath] = module

                setattr(cls, fname, test_file)

        if not hasattr(cls, 'argv_orig'):
            cls.argv_orig = sys.argv


class _TestCliBase(unittest.TestCase):
    commands = tuple()

    def test_cli(self):
        # we still run these tests to make sure that the install process works as expected
        failed = []
        for command in self.commands:
            try:
                output = subprocess.check_output(command,
                                                 env=os.environ.copy(),
                                                 stderr=subprocess.STDOUT).decode().rstrip()
            except BaseException as e:
                failed.append((command, e, e.stdout if hasattr(e, 'stdout') else '', ''))

        msg = '\n'.join('\n'.join(str(e) for e in f) for f in failed)
        assert not failed, msg
