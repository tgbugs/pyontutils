import unittest
from neurondm import OntTerm
from pyontutils.core import OntGraph
from pyontutils.namespaces import partOf


class TestTriplesSimple(unittest.TestCase):
    def test_part_of(self):
        eeeee = OntTerm('UBERON:0008933', label='primary somatosensory cortex')
        g = OntGraph()
        [g.add(t) for t in eeeee.triples_simple]
        g.debug()
        po = [t for t in eeeee.triples_simple if partOf in t]
        assert po, 'sadness'
