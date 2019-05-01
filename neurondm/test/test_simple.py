import unittest
from neurondm import simple
from neurondm.simple import Phenotype, PhenotypeCollection


class TestSimple(unittest.TestCase):
    # TODO test_0_equality from test_neurons

    def test_phenotype(self):
        p1 = Phenotype('ilxtr:someValue', 'ilxtr:someDimension')
        p2 = Phenotype('ilxtr:someValue', 'ilxtr:someDimension')
        p3 = Phenotype('ilxtr:otherValue', 'ilxtr:someDimension')
        p4 = Phenotype('ilxtr:otherValue', 'ilxtr:otherDimension')
        assert p1 == p2 != p3 != p4

    def test_phenotype_collection(self):
        pc1 = PhenotypeCollection(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'))
        pc2 = PhenotypeCollection(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'))
        pc3 = PhenotypeCollection(Phenotype('ilxtr:otherValue', 'ilxtr:someDimension'))
        pc4 = PhenotypeCollection(Phenotype('ilxtr:otherValue', 'ilxtr:otherDimension'))
        assert pc1 == pc2 != pc3 != pc4

        pc = PhenotypeCollection(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                                 Phenotype('ilxtr:someValue', 'ilxtr:someDimension'))

        assert len(pc) == 1
        breakpoint()

