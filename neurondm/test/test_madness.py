import unittest
from pathlib import Path
#import sys
#import pudb
#sys.breakpointhook = pudb.set_trace

# TestRoundtrip by itself is not sufficient to induce the cross module version
from test.test_neurons import TestRoundtrip

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
    def test_rewrite_source_module(self):
        from neurondm import Config
        config = Config('test-madness', py_export_dir=madpath.parent)
        config.load_python()   # this is required
        #breakpoint()
        config.write_python()  # BOOM HEADSHOT
