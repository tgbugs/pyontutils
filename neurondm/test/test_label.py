import unittest
import rdflib
from neurondm.core import (LabelMaker,
                           Phenotype,
                           NegPhenotype,
                           Neuron,
                           LogicalPhenotype,
                           AND,
                           OR,)


class TestLabelMaker(unittest.TestCase):

    def setUp(self):
        self.lm = LabelMaker()

        def ns(suffix):
            if isinstance(suffix, rdflib.URIRef):
                raise TypeError('you called this twice')
            return self.lm.predicate_namespace[suffix]

        def ms(*suffixes, p=None):
            return Neuron(*[Phenotype(s, p) for s in suffixes])

        def ls(*suffixes, p=None, op=AND):
            # not reasonable but useful for display testing
            return Neuron(LogicalPhenotype(
                op,
                *[Phenotype(s, p) for s in suffixes],
                *[NegPhenotype(s, p) for s in suffixes]))

        self.ns = ns
        self.ms = ms
        self.ls = ls

    def test_logical(self):
        ns = self.ns
        ls = self.ls
        hmp = ns('hasMolecularPhenotype')
        a = 'PR:000015665'  # sst
        b = 'NCBIGene:19293'  # pv
        c = 'PR:000017299'  # vip

        bads = []
        for op in (AND, OR):
            hrm = ls(a, b, c, p=hmp, op=op)
            test = hrm.label
            if not ('+PV' in test and '-VIP' in test):
                bads.append(test)

        assert not bads, bads

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

