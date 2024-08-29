import unittest
from pyontutils.core import OntGraph
from pyontutils.namespaces import ilxtr
#from neurondm import simple
from neurondm.core import (Neuron, Phenotype, IntersectionOf, IntersectionOfPartOf, UnionOf,
                           Config, LogicalPhenotype, OR, EntailedPhenotype, EntailedLogicalPhenotype)
# FIXME for offline testing
try:
    #config = Config('owl-object-test', import_no_net=True)
    pass
except:
    raise
    Phenotype._location_predicates = (
        ilxtr.hasAxonLocatedIn,
    )
    Phenotype.part_of_graph = OntGraph()


class TestOwlObject(unittest.TestCase):
    _Phenotype = Phenotype
    _LogicalPhenotype = LogicalPhenotype

    def setUp(self):
        self.Phenotype = self._Phenotype
        self.LogicalPhenotype = self._LogicalPhenotype
        self.config = Config('owl-object-test', import_no_net=True)

    def _do(self, n):
        print(n)
        print(self.config.python())
        print(self.config.ttl())

        # this testing call needs to happen after we test ttl
        # and python out due to the braindead stateful nature of
        # infixowl
        g = OntGraph()
        n._graphify(graph=g)
        g.debug()

    def test_uo(self):
        n = Neuron(self.Phenotype(UnionOf(ilxtr.somaloc1, ilxtr.somaloc2, ilxtr.somaloc3), ilxtr.hasSomaLocatedIn))
        self._do(n)

    def test_io(self):
        n = Neuron(self.Phenotype(IntersectionOf(ilxtr.thing1, ilxtr.thing2)))
        self._do(n)

    def test_io_loc(self):
        n = Neuron(self.Phenotype(IntersectionOf(ilxtr.region, ilxtr.layer), ilxtr.hasAxonLocatedIn))
        self._do(n)

    def test_iopo(self):
        # TODO should iopo check whether the predicate is a location predicate?
        n = Neuron(self.Phenotype(IntersectionOfPartOf(ilxtr.region, ilxtr.layer)))
        self._do(n)

    # mixed

    def test_uo_m(self):
        n = Neuron(self.Phenotype(UnionOf(ilxtr.somaloc1, ilxtr.somaloc2, ilxtr.somaloc3), ilxtr.hasSomaLocatedIn),
                   self.Phenotype(ilxtr.other))
        self._do(n)

    def test_io_m(self):
        n = Neuron(self.Phenotype(IntersectionOf(ilxtr.thing1, ilxtr.thing2)),
                   self.Phenotype(ilxtr.other))
        self._do(n)

    def test_io_loc_m(self):
        n = Neuron(self.Phenotype(IntersectionOf(ilxtr.region, ilxtr.layer), ilxtr.hasAxonLocatedIn),
                   self.Phenotype(ilxtr.other))
        self._do(n)

    def test_iopo_m(self):
        # TODO should iopo check whether the predicate is a location predicate?
        n = Neuron(self.Phenotype(IntersectionOfPartOf(ilxtr.region, ilxtr.layer)),
                   self.Phenotype(ilxtr.other))
        self._do(n)

    # mixed with logical

    def test_uo_m(self):
        n = Neuron(self.Phenotype(UnionOf(ilxtr.somaloc1, ilxtr.somaloc2, ilxtr.somaloc3), ilxtr.hasSomaLocatedIn),
                   self.LogicalPhenotype(OR,
                                         self.Phenotype(ilxtr.other),
                                         self.Phenotype(ilxtr.another)))
        self._do(n)

    def test_io_m(self):
        n = Neuron(self.Phenotype(IntersectionOf(ilxtr.thing1, ilxtr.thing2)),
                   self.LogicalPhenotype(OR,
                                         self.Phenotype(ilxtr.other),
                                         self.Phenotype(ilxtr.another)))
        self._do(n)

    def test_io_loc_m(self):
        n = Neuron(self.Phenotype(IntersectionOf(ilxtr.region, ilxtr.layer), ilxtr.hasAxonLocatedIn),
                   self.LogicalPhenotype(OR,
                                         self.Phenotype(ilxtr.other),
                                         self.Phenotype(ilxtr.another)))
        self._do(n)

    def test_iopo_m(self):
        # TODO should iopo check whether the predicate is a location predicate?
        n = Neuron(self.Phenotype(IntersectionOfPartOf(ilxtr.region, ilxtr.layer)),
                   self.LogicalPhenotype(OR,
                                         self.Phenotype(ilxtr.other),
                                         self.Phenotype(ilxtr.another)))
        self._do(n)


class TestEntailedOwlObject(TestOwlObject):
    _Phenotype = EntailedPhenotype
    _LogicalPhenotype = EntailedLogicalPhenotype


class TestNestOwlObject(unittest.TestCase):
    # so in theory (aka owl) it is possible to nest intersectionOf and unionOf arbitrariliy however
    # the practical use cases where that ability is needed are currently not known all the use
    # cases for OwlObject essentially end at a single leve I suppose there might be a case where we
    # have (uo (io region-1 layer-1) (io region-2 layer-2)) so we could implement it, noting that
    # other tools (like composer) currently only have support for the equivalent of (io region
    # layer) and support for (uo soma-loc-1 soma-loc-2 ...)  only implicitly when using the
    # hasSomaLocatedIn property

    # we also generally want to discourage the use of OwlObjects because the whole point of bagging
    # phenotypes is to keep the phenotypes as simple as possible

    # we need (iopo region layer) to achieve parity with ApiNATOMY semantics and to reduce the need
    # to mint identifiers for simple intersection cases, but union-of actually poses something of
    # an interpretational challeng for partial orders, even though it does clarify the fact that
    # there is only one soma location for any individual type, and is also technically necessary to
    # work around the fact that having multiple soma locations makes the owl classes unsatisfiable
    # for any individual real neuron because the top level restriction is an intersection of
    # multiple discrete anatomical locations, we could use LogicalPhenotype for somal location, but
    # OwlObject union of seems to make more sense? ... and thus the challenge

    _Phenotype = Phenotype
    _LogicalPhenotype = LogicalPhenotype

    setUp = TestOwlObject.setUp
    _do = TestOwlObject._do

    def test_uo_io(self):
        n = Neuron(self.Phenotype(UnionOf(IntersectionOf(ilxtr.a, ilxtr.b), IntersectionOf(ilxtr.c, ilxtr.d))))
        self._do(n)

    def test_uo_io_loc(self):
        n = Neuron(self.Phenotype(UnionOf(IntersectionOf(ilxtr.a, ilxtr.b),
                                          IntersectionOf(ilxtr.c, ilxtr.d)),
                                  ilxtr.hasAxonLocatedIn))
        self._do(n)


class TestEntailedNestOwlObject(TestNestOwlObject):
    _Phenotype = EntailedPhenotype
    _LogicalPhenotype = EntailedLogicalPhenotype
