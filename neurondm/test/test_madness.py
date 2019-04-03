import unittest
from pathlib import Path
import sys
from test.common import _TestNeuronsBase, pyel, tel

#import pudb
#sys.breakpointhook = pudb.set_trace

def even_when_transient():
    """ pass imports out of scope """
    # it looksl ike something is up with models
    # not related to anything in models/__init__.py

    # importing any one of these will induce the error
    #from neurondm.models import ma2015
    #import neurondm.models.basic_neurons
    #import neurondm.models.huang2017
    #import neurondm.models.cuts
    #import neurondm.models.ma2015

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

# write the file manually to show the issue is not related to a previous write
# this works with neurondm.lang or neurondm
test_madness_py = '''
#!/usr/bin/env python3.6
from neurondm import *

class NeuronMarkram2015(NeuronEBM):
    owlClass = ilxtr.NeuronMarkram2015
    shortname = 'Markram2015'


config = Config('test-madness',
                file=__file__,
                ttl_export_dir='/home/tom/git/NIF-Ontology/ttl/generated/neurons')
'''

# this by itself will cause an error due to lack of __init__ in /tmp/
# even without running even_when_transient
#madpath = Path('/tmp/test_madness.py')

madpath = Path('/tmp/madness/test_madness.py')
if not madpath.parent.exists():
    madpath.parent.mkdir()
    (madpath.parent / '__init__.py').touch()

with open(madpath, 'wt') as f:
    f.write(test_madness_py)

# one problem would seem to be having two classes with the same name sourced from different files
# so NeuronMarkram2015 in the serialized file is technically different than the one in the generating
# file, so if they someone come into contact with eachother things go boom (I think) this may require a
# metaclass to solve the issue?
class TestDoNothing(unittest.TestCase):
    def test_py_simple(self):
        from neurondm import Config
        config = Config('test-madness', py_export_dir=madpath.parent)
        config.load_python()   # this is required
        #breakpoint()
        config.write_python()  # BOOM HEADSHOT
