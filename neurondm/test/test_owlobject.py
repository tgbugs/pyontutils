import unittest
from pyontutils.core import OntGraph
from pyontutils.namespaces import ilxtr
#from neurondm import simple
from neurondm.core import Neuron, Phenotype, IntersectionOf, IntersectionOfPartOf, UnionOf, Config, LogicalPhenotype, OR

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

    def setUp(self):
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
        n = Neuron(Phenotype(UnionOf(ilxtr.somaloc1, ilxtr.somaloc2, ilxtr.somaloc3), ilxtr.hasSomaLocatedIn))
        self._do(n)

    def test_io(self):
        n = Neuron(Phenotype(IntersectionOf(ilxtr.thing1, ilxtr.thing2)))
        self._do(n)

    def test_io_loc(self):
        n = Neuron(Phenotype(IntersectionOf(ilxtr.region, ilxtr.layer), ilxtr.hasAxonLocatedIn))
        self._do(n)

    def test_iopo(self):
        # TODO should iopo check whether the predicate is a location predicate?
        n = Neuron(Phenotype(IntersectionOfPartOf(ilxtr.region, ilxtr.layer)))
        self._do(n)

    # mixed

    def test_uo_m(self):
        n = Neuron(Phenotype(UnionOf(ilxtr.somaloc1, ilxtr.somaloc2, ilxtr.somaloc3), ilxtr.hasSomaLocatedIn), Phenotype(ilxtr.other))
        self._do(n)

    def test_io_m(self):
        n = Neuron(Phenotype(IntersectionOf(ilxtr.thing1, ilxtr.thing2)), Phenotype(ilxtr.other))
        self._do(n)

    def test_io_loc_m(self):
        n = Neuron(Phenotype(IntersectionOf(ilxtr.region, ilxtr.layer), ilxtr.hasAxonLocatedIn), Phenotype(ilxtr.other))
        self._do(n)

    def test_iopo_m(self):
        # TODO should iopo check whether the predicate is a location predicate?
        n = Neuron(Phenotype(IntersectionOfPartOf(ilxtr.region, ilxtr.layer)), Phenotype(ilxtr.other))
        self._do(n)

    # mixed with logical

    def test_uo_m(self):
        n = Neuron(Phenotype(UnionOf(ilxtr.somaloc1, ilxtr.somaloc2, ilxtr.somaloc3), ilxtr.hasSomaLocatedIn), LogicalPhenotype(OR, Phenotype(ilxtr.other), Phenotype(ilxtr.another)))
        self._do(n)

    def test_io_m(self):
        n = Neuron(Phenotype(IntersectionOf(ilxtr.thing1, ilxtr.thing2)), LogicalPhenotype(OR, Phenotype(ilxtr.other), Phenotype(ilxtr.another)))
        self._do(n)

    def test_io_loc_m(self):
        n = Neuron(Phenotype(IntersectionOf(ilxtr.region, ilxtr.layer), ilxtr.hasAxonLocatedIn), LogicalPhenotype(OR, Phenotype(ilxtr.other), Phenotype(ilxtr.another)))
        self._do(n)

    def test_iopo_m(self):
        # TODO should iopo check whether the predicate is a location predicate?
        n = Neuron(Phenotype(IntersectionOfPartOf(ilxtr.region, ilxtr.layer)), LogicalPhenotype(OR, Phenotype(ilxtr.other), Phenotype(ilxtr.another)))
        self._do(n)

