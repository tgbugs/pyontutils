import unittest
import rdflib
from pyontutils.core import OntGraph, ilxtr


class TestOntGraph(unittest.TestCase):
    ts1 = ((ilxtr.a, ilxtr.b, ilxtr.c),)
    ts2 = ((ilxtr.a, ilxtr.b, ilxtr.d),)

    def populate(self, graph, triples):
        [graph.add(t) for t in triples]

    def setUp(self):
        self.graph1 = OntGraph()
        self.graph2 = OntGraph()

    def test_subjectsChanged(self):
        self.populate(self.graph1, self.ts1)
        self.populate(self.graph2, self.ts2)
        d = a, r, c = self.graph1.subjectsChanged(self.graph2)
        assert not a, d
        assert not a, d
        assert c, d

    def test_not_subjectsChanged(self):
        self.populate(self.graph1, self.ts1)
        self.populate(self.graph2, self.ts1)
        d = a, r, c = self.graph1.subjectsChanged(self.graph2)
        assert not a, d
        assert not r, d
        assert not c, d


class TestOntGraphComplex(TestOntGraph):
    bn1 = rdflib.BNode()
    bn2 = rdflib.BNode()
    ts1 = ((ilxtr.a, ilxtr.b, bn1),
           (bn1, ilxtr.predicate, ilxtr.YES))
    ts1_5 = ((ilxtr.a, ilxtr.b, bn2),
             (bn2, ilxtr.predicate, ilxtr.YES))
    ts2 = ((ilxtr.a, ilxtr.b, bn2),
           (bn1, ilxtr.predicate, ilxtr.NO))

    def test_bnode_but_not_subjectsChanged(self):
        self.populate(self.graph1, self.ts1)
        self.populate(self.graph2, self.ts1_5)
        d = a, r, c = self.graph1.subjectsChanged(self.graph2)
        assert self.ts1[0][-1] != self.ts1_5[0][-1], 'why arent these different? {self.ts1} {self.ts1_5}'
        assert not a, d
        assert not r, d 
        assert not c, d
