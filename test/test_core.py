import unittest
from pyontutils.core import ilxtr
from pyontutils.combinators import annotation

annotation_ev = """ Axioms

[] a owl:Axiom ;
    owl:annotatedSource ns1:a ;
    owl:annotatedProperty ns1:b ;
    owl:annotatedTarget ns1:c ;
    ns1:e ns1:f ;
    ns1:g ns1:h .

"""


class TestAnnotation(unittest.TestCase):
    def test_annotation(self):
        ac = annotation((ilxtr.a, ilxtr.b, ilxtr.c), (ilxtr.e, ilxtr.f), (ilxtr.g, ilxtr.h))
        assert len(ac.value) == 6, 'wrong number of triples'
        assert ac.debug(ret=True).split('###')[1] == annotation_ev, 'unexpected serialization value'

    def test_annotation_triple_type(self):
        try:
            annotation({1, 2, 3})
            raise AssertionError('should have failed')
        except TypeError:
            pass

    def test_annotation_triple_len(self):
        try:
            annotation((1, 2, 3, 4))
            raise AssertionError('should have failed')
        except TypeError:
            pass
