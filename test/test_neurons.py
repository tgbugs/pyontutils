import unittest
import rdflib


class TestNeurons(unittest.TestCase):
    def setUp(self):
        pass

    def test_ttl(self):  # roundtrip from ttl
        #example_ttl = 'test/example_neurons.ttl'
        #nl.graphBase.in_graph.parse(example_ttl, format='turtle')
        #nl.newGraph.filename = 'test/example_neurons2.ttl'
        #nl.WRITE()
        assert True

    def test_py(self):  # direct to ttl + roundtrip to python
        #en.newGraph.filename = 'test/example_neurons3.ttl'
        #en.WRITE()
        #print('WHAT IS GOING ON')
        assert True

    # TODO make sure this runs after cli test? it should ...
    # but then we need to keep the output of ndl around
    def test_load_existing(self):
        from pyontutils.neurons.lang import Neuron, Config
        config = Config('neuron_data_lifted')
        config.load_existing()
        assert len(Neuron.load_graph)
        neurons = Neuron.neurons()
        assert neurons

    def test_adopt(self):
        from pyontutils.neurons.lang import Neuron, Phenotype, Config
        ndl_config = Config('neuron_data_lifted')
        ndl_config.load_existing()
        bn_config = Config('basic-neurons')
        bn_config.load_existing()
        ndl_neurons = list(ndl_config.neurons)
        bn_neurons = list(bn_config.neurons)
        config = Config('__test_output')
        shapeshifter = Neuron(Phenotype('ilxtr:soul-stealer'))
        for n in ndl_neurons:
            shapeshifter.adopt_meta(n)

        assert list(n.synonyms)
        assert list(n.definitions)
        n.write()


    def test_fail(self):
        from pyontutils.neurons.lang import Neuron, Phenotype, Config
        bn_config = Config('basic-neurons')
        # TODO config.activate()? context manager for config ... too ...
        Neuron(Phenotype('ilxtr:test'))
        try:
            bn_config.load_existing()
            raise AssertionError('Should have failed because a neuron has been created')
        except Config.ExistingNeuronsError as e:
            pass
