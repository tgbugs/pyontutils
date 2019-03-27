import os
import sys
import unittest
from pathlib import Path
from importlib import import_module
import git
from pyontutils.utils import TermColors as tc


class TestScriptsBase(unittest.TestCase):
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
                       skip=tuple(), ci_skip=tuple(), only=tuple(), do_mains=True,
                       module_parent=None):

        if module_parent is None:
            module_parent = working_dir

        relpath = Path(module_parent).relative_to(Path(working_dir)).as_posix()
        if relpath == '.':
            relpath = ''
        else:
            relpath += '/'

        skip += Path(__file__).stem,  # prevent this file from accidentally testing itself
        if 'TRAVIS' in os.environ:
            skip += ci_skip

        if 'CI' not in os.environ:
            pass

        if only:
            mains = {k:v for k, v in mains.items() if k in only}

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
                           (True if not only else any(_ + '.py' in f for _ in only)))

            npaths = len(paths)
            print(npaths)
            for i, path in enumerate(paths):
                ppath = Path(path).absolute()
                print('PPATH:  ', ppath)
                pex = ppath.as_posix().replace('/', '_').replace('.', '_')
                fname = f'test_{i:0>3}_' + pex
                stem = ppath.stem
                rp = ppath.relative_to(module_parent)
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
                            pass

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
                                pass

                        setattr(cls, mname, test_main)

        except git.exc.InvalidGitRepositoryError:  # testing elsewhere
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
