import unittest
from .common import _TestNeuronsBase, pyel, tel


def even_when_transient():
    # it looksl ike something is up with models
    # not related to anything in models/__init__.py

    # importing any one of these will induce the error
    #import neurondm.models.basic_neurons
    #import neurondm.models.huang2017
    #import neurondm.models.cuts
    import neurondm.models.ma2015
    #from neurondm.models import ma2015

    # importing any of these will not
    #import neurondm.example
    #import neurondm.models
    #import neurondm.lang
    #import neurondm.phenotype_namespaces

    # no error caused by the below
    #from neurondm import Config, Neuron
    #from neurondm.phenotype_namespaces import BBP
    #config = Config('nothing')
    #Neuron(BBP.Mouse)
    #config.write()
    #config.write_python()


even_when_transient()


class TestDoNothing(unittest.TestCase):
    def test_py_simple(self):
        from neurondm import Config
        config = Config('test-madness', py_export_dir='/tmp/')
        config.write_python()  # this alone will not trigger
        config.load_python()   # this is required
        config.write_python()  # BOOM HEADSHOT
