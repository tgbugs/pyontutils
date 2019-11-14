import os
import unittest
from pathlib import Path
from tempfile import gettempdir
import pytest
from git import Repo
from neurondm.core import log

log.setLevel('DEBUG')

SKIP_NETWORK = ('SKIP_NETWORK' in os.environ or
                'FEATURES' in os.environ and 'network-sandbox' in os.environ['FEATURES'])
skipif_no_net = pytest.mark.skipif(SKIP_NETWORK, reason='Skipping due to network requirement')

testing_base = Path(gettempdir(), f'.neurons-testing-base-{os.getpid()}')
pyel = testing_base / 'compiled'
tel = testing_base


@skipif_no_net
class _TestNeuronsBase(unittest.TestCase):
    def setUp(self):
        if not pyel.exists():
            pyel.mkdir(parents=True)  # recrusive clean is called after every test
            (pyel / '__init__.py').touch()

        repo = Repo.init(testing_base.as_posix())

    def tearDown(self):
        def recursive_clean(path):
            for thing in path.iterdir():
                if thing.is_dir():
                    recursive_clean(thing)
                else:
                    thing.unlink()  # will rm the file

            path.rmdir()

        path = testing_base
        if path.exists():
            recursive_clean(path)
