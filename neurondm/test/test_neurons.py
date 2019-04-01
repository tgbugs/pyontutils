import os
import unittest
from pathlib import Path

testing_base = f'/tmp/.neurons-testing-base-{os.getpid()}'
pyel = Path(testing_base, 'compiled')
pyel.mkdir(parents=True)
(pyel / '__init__.py').touch()
tel = Path(testing_base)

from neurondm import Config
# FIXME calling this for the side effect of calling git init is kind of evil
Config('dud', git_repo=testing_base, ttl_export_dir=None)


class TestNeurons(unittest.TestCase):
    def setUp(self):
        pass

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

    def test_ttl(self):  # roundtrip from ttl
        #example_ttl = 'test/example_neurons.ttl'
        #nl.graphBase.in_graph.parse(example_ttl, format='turtle')
        #nl.newGraph.filename = 'test/example_neurons2.ttl'
        #nl.WRITE()
        from neurondm import Config, Neuron, Phenotype

        config = Config('test-ttl', ttl_export_dir=tel, py_export_dir=pyel)
        Neuron(Phenotype('TEMP:turtle-phenotype'))
        config.write()

        config2 = Config('test-ttl', ttl_export_dir=tel, py_export_dir=pyel)
        config2.load_existing()
        config2.write_python()

        config3 = Config('test-ttl', ttl_export_dir=tel, py_export_dir=pyel)
        config3.load_python()

        assert config.neurons() == config2.neurons() == config3.neurons()

    def test_py(self):  # direct to ttl + roundtrip to python
        #en.newGraph.filename = 'test/example_neurons3.ttl'
        #en.WRITE()
        #print('WHAT IS GOING ON')
        from neurondm import Config, Neuron, Phenotype

        config = Config('test-py', ttl_export_dir=tel, py_export_dir=pyel)
        Neuron(Phenotype('TEMP:python-phenotype'))
        config.write_python()

        config2 = Config('test-py', ttl_export_dir=tel, py_export_dir=pyel)
        config2.load_python()  # FIXME load existing python ...
        config2.write()

        config3 = Config('test-py', ttl_export_dir=tel, py_export_dir=pyel)
        config3.load_existing()

        assert config.neurons() == config2.neurons() == config3.neurons()

    # TODO make sure this runs after cli test? it should ...
    # but then we need to keep the output of ndl around
    def test_load_existing(self):
        from neurondm.lang import Neuron, Config
        config = Config('neuron_data_lifted')
        config.load_existing()
        assert len(Neuron.load_graph)
        neurons = Neuron.neurons()
        assert neurons

    def test_adopt(self):
        from neurondm.lang import Neuron, Phenotype, Config
        ndl_config = Config('neuron_data_lifted')
        ndl_config.load_existing()
        bn_config = Config('basic-neurons')
        bn_config.load_existing()
        ndl_neurons = ndl_config.neurons()
        bn_neurons = bn_config.neurons()
        config = Config('__test_output', ttl_export_dir=tel)
        shapeshifter = Neuron(Phenotype('ilxtr:soul-stealer'))
        for n in ndl_neurons:
            shapeshifter.adopt_meta(n)

        assert list(n.symomyms)
        assert list(n.definitions)
        n.write()

        assert list(shapeshifter.synonyms)
        assert list(shapeshifter.definitions)
        shapeshifter.write()

    def test_fail(self):
        from neurondm.lang import Neuron, Phenotype, Config
        bn_config = Config('basic-neurons')
        # TODO config.activate()? context manager for config ... too ...
        Neuron(Phenotype('ilxtr:test'))
        try:
            bn_config.load_existing()
            raise AssertionError('Should have failed because a neuron has been created')
        except Config.ExistingNeuronsError as e:
            pass
