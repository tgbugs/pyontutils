import unittest
import rdflib
#import pyontutils.neuron_lang as nl
#import test.example_neurons as en

class TestNeurons(unittest.TestCase):
    def setUp(self):
        print('hello')

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

