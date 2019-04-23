import unittest
import rdflib
from neurondm.core import LabelMaker, Phenotype, Neuron

class TestLabelMaker(unittest.TestCase):

    def setUp(self):
        self.lm = LabelMaker()

        def ns(suffix):
            if isinstance(suffix, rdflib.URIRef):
                raise TypeError('you called this twice')
            return self.lm.predicate_namespace[suffix]

        def ms(*suffixes, p=None):
            return Neuron(*[Phenotype(s, p) for s in suffixes])

        self.ns = ns
        self.ms = ms

    def test_hasCircuitRole(self):
        ns = self.ns
        ms = self.ms
        hcr = ns('hasCircuitRolePhenotype')
        inter = ns('InterneuronPhenotype')
        intrin = ns('IntrinsicPhenotype')
        proj = ns('ProjectionPhenotype')
        prin = ns('PrincipalPhenotype')
        s = ns('SensoryPhenotype')
        m = ns('MotorPhenotype')

        sets = (
            ms(intrin, p=hcr),
            ms(inter, p=hcr),
            ms(prin, p=hcr),
            ms(proj, p=hcr),
            ms(s, p=hcr),
            ms(m, p=hcr),
            ms(inter, intrin, p=hcr),
            ms(intrin, inter, p=hcr),
        )
        wat = next(self.lm.hasCircuitRolePhenotype((Phenotype(inter),)))
        assert wat != 'intrinsic'
        for neuron in sets:
            label = self.lm(neuron)
            print(neuron.pes, label)

