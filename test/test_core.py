import unittest
from pyontutils.core import annotation, ilxtr

annotation_ev = """ Axioms

[] a owl:Axiom ;
    owl:annotatedSource ns1:a ;
    owl:annotatedProperty ns1:b ;
    owl:annotatedTarget ns1:c ;
    ns1:e ns1:f ;
    ns1:g ns1:h .

"""


class TestCore(unittest.TestCase):
    def test_annotation(self):
        ac = annotation((ilxtr.a, ilxtr.b, ilxtr.c), (ilxtr.e, ilxtr.f), (ilxtr.g, ilxtr.h))
        assert len(ac.value) == 6, 'wrong number of triples'
        assert ac.debug(ret=True).split('###')[1] == annotation_ev, 'unexpected serialization value'


