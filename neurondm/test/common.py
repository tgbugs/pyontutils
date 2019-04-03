import os
import unittest
from pathlib import Path
from git import Repo

testing_base = f'/tmp/.neurons-testing-base-{os.getpid()}'
pyel = Path(testing_base, 'compiled')
tel = Path(testing_base)


class _TestNeuronsBase(unittest.TestCase):
    def setUp(self):
        if not pyel.exists():
            pyel.mkdir(parents=True)  # recrusive clean is called after every test
            (pyel / '__init__.py').touch()

        repo = Repo.init(testing_base)

    def tearDown(self):
        def recursive_clean(path):
            for thing in path.iterdir():
                if thing.is_dir():
                    recursive_clean(thing)
                else:
                    thing.unlink()  # will rm the file

            path.rmdir()

        path = Path(testing_base)
        if path.exists():
            recursive_clean(path)
