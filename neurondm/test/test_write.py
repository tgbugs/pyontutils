import os
import unittest
from pathlib import Path
import pytest
from git import Repo

testing_base = f'/tmp/.neurons-testing-base-{os.getpid()}'
pyel = Path(testing_base, 'compiled')
tel = Path(testing_base)


class TestWrite(unittest.TestCase):
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

    def test_0_write_py_after_load_none(self):
        from neurondm import Config, Neuron, Phenotype
        #config = Config('test-write', ttl_export_dir=tel, py_export_dir=pyel)
        #Neuron(Phenotype('TEMP:hello'))
        #config.write()
        config2 = Config('test-write-after-same', ttl_export_dir=tel, py_export_dir=pyel)
        Neuron(Phenotype('TEMP:after-other'))
        config2.write_python()
        # first ttl at write python
        # after loading from another repo location?
        # possibly after write python has already been called once?

    def test_1_write_py_after_load_same(self):
        from neurondm import Config, Neuron, Phenotype
        # trickier
        pytest.skip('TODO')

    def test_2_write_py_after_load_other(self):
        from neurondm.lang import Config, Neuron, Phenotype
        config = Config('huang-2017')
        config.load_existing()

        config2 = Config('test-write-after-other', ttl_export_dir=tel, py_export_dir=pyel)
        Neuron(Phenotype('TEMP:after-other'))
        config2.write_python()
