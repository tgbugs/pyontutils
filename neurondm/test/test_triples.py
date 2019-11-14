import unittest
from neurondm import OntTerm as OntTerm_
from neurondm.core import OntTermOntologyOnly
from pyontutils.core import OntGraph
from pyontutils.namespaces import partOf
from .common import skipif_no_net


@skipif_no_net
class TriplesSimple:
    OntTerm = None
    def test_part_of(self):
        eeeee = self.OntTerm('UBERON:0008933',
                             label='primary somatosensory cortex')
        g = OntGraph()
        [g.add(t) for t in eeeee.triples_simple]
        g.debug()
        po = [t for t in eeeee.triples_simple if partOf in t]
        assert po, 'sadness'


class TestOT(TriplesSimple, unittest.TestCase):
    OntTerm = OntTerm_


class TestOTOO(TriplesSimple, unittest.TestCase):
    OntTerm = OntTermOntologyOnly
