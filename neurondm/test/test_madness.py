from .common import _TestNeuronsBase, pyel, tel


# importing any one of these will induce the error
import neurondm.models.basic_neurons
#import neurondm.models.huang2017

# importing any of these will not
#import neurondm.example

# no error caused by the below
#from neurondm import Config, Neuron
#from neurondm.phenotype_namespaces import BBP
#config = Config('nothing')
#Neuron(BBP.Mouse)
#config.write()
#config.write_python()


class TestDoNothing(_TestNeuronsBase):
    def test_ttl_simple(self):
        from neurondm import Config, Neuron, Phenotype, NegPhenotype
        config = Config('test-ttl', ttl_export_dir=tel, py_export_dir=pyel)
        config.write()

        config2 = Config('test-ttl', ttl_export_dir=tel, py_export_dir=pyel)
        config2.load_existing()
        config2.write_python()

        config3 = Config('test-ttl', ttl_export_dir=tel, py_export_dir=pyel)
        config3.load_python()

    def test_py_simple(self):
        from neurondm import Config, Neuron, Phenotype, NegPhenotype

        config = Config('test-py', ttl_export_dir=tel, py_export_dir=pyel)
        config.write_python()

        config2 = Config('test-py', ttl_export_dir=tel, py_export_dir=pyel)
        config2.load_python()  # FIXME load existing python ...
        config2.write()

        config3 = Config('test-py', ttl_export_dir=tel, py_export_dir=pyel)
        config3.load_existing()
