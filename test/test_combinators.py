import unittest
from pyontutils import combinators as cmb
from pyontutils.core import OntGraph
from pyontutils.namespaces import owl, rdf, rdfs, ilxtr


class TestCmb(unittest.TestCase):
    def _doit(self, gen):
        OntGraph().populate_from_triples(gen).debug()

    def _doit_fail(self, gen):
        try:
            OntGraph().populate_from_triples(gen).debug()
            assert False, 'should have failed'
        except TypeError:
            pass

    def test_predicate(self):
        pc = cmb.PredicateCombinator(ilxtr.predicate)
        objects1 = ilxtr.object1, ilxtr.object2
        gen = pc(ilxtr.subject, *objects1)
        self._doit(gen)

        Restriction = cmb.Restriction(None)
        objects2 = (cmb.unionOf(Restriction(ilxtr.property, ilxtr.value1)),
                    cmb.intersectionOf(Restriction(ilxtr.property, ilxtr.value2)))
        gen = pc(ilxtr.subject, *objects2)
        self._doit(gen)

        gen = pc(ilxtr.subject, *objects1, *objects2)
        self._doit(gen)

    def test_equivalent_to_union_of(self):
        Restriction = cmb.Restriction(None)
        #combinator = cmb.ObjectCombinator.full_combinator(  # broken but don't need ..
            #cmb.Class,
            #cmb.unionOf(Restriction(ilxtr.property, ilxtr.value)))
        combinator = cmb.unionOf(Restriction(ilxtr.property, ilxtr.value))
        #ec = cmb.List({owl.Restriction, rf})
        #combinator = ec(rf(ilxtr.a, ilxtr.b))
        #combinator = ec(cmb.restriction(ilxtr.a, ilxtr.b))
        print(combinator)

        pos1 = combinator(ilxtr.subject, owl.equivalentClass)
        pos2 = combinator(ilxtr.subject)
        pos3 = combinator(ilxtr.subject, ilxtr.thisCanOverwrite)
        self._doit(pos1)
        self._doit(pos2)
        self._doit(pos3)

    def test_equivalent_to_union_of_complement(self):
        Restriction = cmb.Restriction(None)
        combinator = cmb.ObjectCombinator.full_combinator(
            cmb.Class,
            cmb.Pair(owl.complementOf,
                     Restriction(ilxtr.property,
                                 ilxtr.value)))
        print(combinator)
        gen = combinator(ilxtr.subject)
        self._doit(gen)

        combinator = cmb.unionOf(combinator)
        print(combinator)
        gen = combinator(ilxtr.subject, owl.equivalentClass)
        self._doit(gen)
