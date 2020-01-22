import unittest
import rdflib
from pyontutils.core import OntResIri, OntResPath, OntResGit, OntResAny
from pyontutils.core import OntGraph, OntConjunctiveGraph
from .common import skipif_no_net


@skipif_no_net
class TestOntResIri(unittest.TestCase):
    def setUp(self):
        # TODO localhost server running in thread ?
        self.ori = OntResIri('https://raw.githubusercontent.com/tgbugs/pyontutils/master/ttlser/test/nasty.ttl')

    def test_1_hrm(self):  # FIXME naming
        headers = self.ori.headers
        assert headers, 'no headers?'

    def test_2_metadata(self):
        metadata = self.ori.metadata()
        assert metadata, 'no metadata?'

    def test_3_data(self):
        data = self.ori.data
        assert data, 'no data?'

    def test_4_graph(self):
        g = self.ori.graph
        assert next(iter(g)), 'no graph?'

    def test_5_asConjunctive(self):
        g = self.ori.graph
        c = g.asConjunctive()
        assert next(iter(c)), 'wat'
        assert not [g for g in c.contexts() if not isinstance(g, OntGraph)]


@skipif_no_net
class TestOntResIriConsecutive(TestOntResIri):
    @classmethod
    def setUpClass(cls):
        cls.ori = OntResIri('https://raw.githubusercontent.com/tgbugs/pyontutils/master/ttlser/test/nasty.ttl')

    def setUp(self): pass

    def test_1_hrm(self):  # FIXME naming
        super().test_1_hrm()

    def test_2_metadata(self):
        assert hasattr(self.ori, '_headers') and self.ori._headers, 'headers not populated'
        super().test_2_metadata()

    def test_3_data(self):
        assert hasattr(self.ori, '_metadata') and self.ori._metadata, 'metadata not populated'
        super().test_3_data()

    #def test_4_graph(self):
        #assert hasattr(self.ori, '_data') and self.ori._data, 'data not populated'
        #super().test_4_graph()


