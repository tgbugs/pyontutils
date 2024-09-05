from pyontutils.core import OntConjunctiveGraph
from .common import skipif_no_net, log, testing_base, _TestNeuronsBase


class TestNeurdf(_TestNeuronsBase):

    def test_models(self, debug=False):
        # XXX FIXME this test requires compiled to already have been populated
        # e.g. by running python -m neurondm.build models
        from neurondm.core import uPREFIXES
        from neurondm.build import make_models
        configs = make_models(source='compiled')
        if debug:
            ncs = [(n, c) for c in configs for n in c.neurons()]
            ng = OntConjunctiveGraph()
            ng.namespace_manager.populate_from(uPREFIXES)
            done = set()
            for n, c in ncs:
                if n in done:
                    msg = f'duplicate neuron in config {c.name} {n.id_}'
                    log.debug(msg)
                    continue
                else:
                    done.add(n)

                for t in n._instance_neurdf():
                    try:
                        ng.add(t)
                    except Exception as e:
                        msg = f'neurdf error for {n}\n{t}'
                        log.error(msg)
                        log.exception(e)

            #ng.debug()
            path_debug = testing_base / 'neurdf-test-debug.ttl'
            ng.write(path_debug, format='nifttl')
            #breakpoint()

        # XXX BEWARE: rdf lists can appear twice in the serialization
        # if a neuron with the same id is present in more than one config
        g = OntConjunctiveGraph()
        g.namespace_manager.populate_from(uPREFIXES)
        for c in configs:
            c.neurdf_graph(graph=g)

        #g.debug()
        path = testing_base / 'neurdf-test.ttl'
        g.write(path, format='nifttl')
        #breakpoint()
