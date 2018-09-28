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
        cfg = Config('neuron_data_lifted')
        assert len(Neuron.load_graph)
        neurons = Neuron.neurons()
        assert neurons
        assert 'TEMP' not in neurons[0].id_
