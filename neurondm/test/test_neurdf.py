import unittest
from .common import skipif_no_net, log
from pyontutils.core import OntConjunctiveGraph


@skipif_no_net
class TestNeurdf(unittest.TestCase):
    def test_models(self):
        # XXX FIXME test dependency requires compiled to already have been populated
        from neurondm.core import uPREFIXES
        from neurondm.build import make_models
        configs = make_models(source='compiled')
        neurons = [n for c in configs for n in c.neurons()]
        ng = OntConjunctiveGraph()
        ng.namespace_manager.populate_from(uPREFIXES)
        for n in neurons:
            try:
                ng.populate_from_triples(n._instance_neurdf())
            except Exception as e:
                msg = f'neurdf error for neuron {n}'
                log.error(msg)
                log.exception(e)

        ng.debug()
        breakpoint()
        g = OntConjunctiveGraph()
        g.namespace_manager.populate_from(uPREFIXES)
        for c in configs:
            c.neurdf_graph(graph=g)

        g.debug()
        breakpoint()
