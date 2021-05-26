import shutil
import unittest
import augpathlib as aug
#import sys
#import pudb
#sys.breakpointhook = pudb.set_trace

# TestRoundtrip by itself is not sufficient to induce the cross module version
#from test.test_neurons import TestRoundtrip  # for now comment this out due to issue in test_ttl_simple
from .common import skipif_no_net

# write the file manually to show the issue is not related to a previous write
# this works with neurondm.lang or neurondm
test_madness_py = '''
#!/usr/bin/env python3
from neurondm import *

class NeuronMarkram2015(NeuronEBM):
    owlClass = ilxtr.NeuronMarkram2015
    shortname = 'Markram2015'


config = Config('test-madness',
                file=__file__,
                ttl_export_dir='/home/tom/git/NIF-Ontology/ttl/generated/neurons')
'''

# one problem would seem to be having two classes with the same name sourced from different files
# so NeuronMarkram2015 in the serialized file is technically different than the one in the generating
# file, so if they someone come into contact with eachother things go boom (I think) this may require a
# metaclass to solve the issue?
@skipif_no_net
class TestDoNothing(unittest.TestCase):
    def setUp(self):
        # this by itself will cause an error due to lack of __init__ in /tmp/
        # even without running even_when_transient
        #madpath = Path('/tmp/test_madness.py')

        self.madpath = aug.AugmentedPath(__file__).parent / 'madness/test_madness.py'
        if not self.madpath.parent.exists():
            self.madpath.parent.mkdir()
            (self.madpath.parent / '__init__.py').touch()

        with open(self.madpath, 'wt') as f:
            f.write(test_madness_py)

    def tearDown(self):
        self.madpath.parent.rmtree()

    def test_rewrite_source_module(self):
        from neurondm import Config
        config = Config('test-madness', py_export_dir=self.madpath.parent)
        config.load_python()   # this is required
        #breakpoint()
        config.write_python()  # BOOM HEADSHOT
