import unittest
#from pyontutils.nif_neuron import main as make_neurons
#make_neurons()
from pyontutils.neurons import *

class TestNeurons(unittest.TestCase):
    def setup(self):
        print('hello')

    def test_thing(self):
        assert False

    def test_thing2(self):
        assert True

