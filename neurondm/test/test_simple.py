import unittest
from pyontutils.namespaces import ilxtr
from neurondm import simple
from neurondm.simple import Phenotype, PhenotypeCollection
from .common import skipif_no_net


@skipif_no_net  # FIXME should not need this
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

    def test_and_cell(pc):
        collect = simple.AndCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                                 Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)
        collect.debug()

    def test_or_cell(pc):
        collect = simple.OrCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                                Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)
        collect.debug()

    def test_entailed_cell(pc):
        collect = simple.EntailedCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                                      Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)
        collect.debug()

    def test_cell_collection(self):
        c1 = simple.AndCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                            Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)
        c2 = simple.OrCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                           Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)
        c3 = simple.EntailedCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                                 Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)
        cc = simple.CellCollection()
        cc.add(c1, c2, c3)

        cc.debug(cc.asNeurdf)
        cc.debug(cc.asOwl)

    def test_cell_hash_eq_id(self):
        c1 = simple.AndCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                            Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)

        c2 = simple.OrCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                           Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)

        assert c1 is not c2
        assert c1 != c2
        assert len(set((c1, c2))) == 2

        c1o = simple.AndCell(Phenotype('ilxtr:someValue', 'ilxtr:someDimension'),
                             Phenotype(ilxtr.someOtherValue, ilxtr.someOtherDimension),)
        assert c1 is not c1o
        assert c1 == c1o

        ls = len(set((c1, c1o)))
        assert ls == 1
