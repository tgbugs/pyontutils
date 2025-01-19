import unittest
import pytest
import pathlib
import rdflib
from pyontutils.core import OntGraph, ilxtr
from pyontutils.identity_bnode import IdentityBNode, idf, it as ibn_it


class TestOntGraph(unittest.TestCase):

    def test_subjectGraph(self):
        ge = OntGraph().parse(pathlib.Path('ttlser/test/evil.ttl'))

        sg1 = ge.subjectGraph(ilxtr['evil-1'])
        sg2 = ge.subjectGraph(ilxtr['evil-1'], bnode_multi_parent=True)
        sg3 = ge.subjectsGraph([ilxtr['evil-1'], ilxtr['evil-2']])

        #sg1.debug()
        #sg2.debug()
        #sg3.debug()

        assert ilxtr['evil-2'] not in sg1.subjects(unique=True)
        assert ilxtr['evil-2'] in sg2.subjects(unique=True)


class TestOntGraphOps(unittest.TestCase):
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


class TestOntGraphOpsComplex(TestOntGraphOps):
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


class TestCycleCheckLong(unittest.TestCase):
    def _do_cycle(self, trips, test_trips, neg=False):
        g = OntGraph().populate_from_triples(trips)
        cycles = g.cycle_check_long()
        if neg:
            assert not cycles
        else:
            assert cycles
            assert [c for c in cycles if [ct for ct in c if ct in test_trips]]

    def test_cycles_0(self):
        bn0 = rdflib.BNode()
        bn1 = rdflib.BNode()
        trips = (
            (bn0, ilxtr.c0, bn1),
        )
        test_trips = trips
        self._do_cycle(trips, None, neg=True)

    def test_cycles_1(self):
        bn0 = rdflib.BNode()
        trips = (
            (bn0, ilxtr.c0, bn0),
        )
        test_trips = trips
        self._do_cycle(trips, test_trips)

    def test_cycles_2(self):
        clen = 9999  # bad algos with choke at this size
        nodes = [rdflib.BNode() for _ in range(clen)]
        trips = [(na, ilxtr.p, nb) for na, nb in zip(nodes[:-1], nodes[1:])]
        trips.append((nodes[-1], ilxtr.c0, nodes[0]))
        mid = clen // 2
        l = clen - 2
        u = clen + 2
        test_trips = trips[l:u]
        self._do_cycle(trips, test_trips)


class TestVersionHistory(unittest.TestCase):
    """
    the test cases here should cover all the possible atomic operations on a store
    triple add
    triple remove
    triple ban

    but then we have to condense history and
    come up with ways to reconstruct the current
    state from a series of diffs and also consider keyfames or similar

    the approach we plan to implement perfers to pay a short term cost of
    diffing two sets of triples in order to be able to store only the things
    that have changed

    sometimes we might be given only the adds or only the adds and removes

    the tables we assume are as follows (simplified to avoid type heterogenaity)

    triples
    id s p o

    current_graphs  # the checked out state
    id_iri id_triple

    triple_graphs
    id=(iri version) id_history
    # all graphs derive from the empty graph

    local_convention_sets
    id user name etc.

    lcs_to_cons
    id_lcs id_namespace_prefix

    cons  # pairs
    namespace prefix

    # graphs with local conventions attached
    # iirc there was one other thing we needed to?
    # maybe the prov train id?
    serialized_graphs
    id_triple_graph id_local_convention_sets

    add
    remove
    ban

    triple_sets
    id triple_id

    # ok, this is closer to what could work, it will require pointer chasing
    # but since we will maintain the current state it will only be needed for
    # looking at old versions, everything else is just a triple set that
    # can be referenced for any reason, when history is empty the tripleset
    # we create is all add ... also need a way to allow multiple histories for an iri
    # in the event that we need to rewrite history e.g. to enhance it with more granular info
    # like going from obo release to commit level changes, the current impl was very strong on
    # using the graph identity function, could also drop the is keyframe column and point
    # back to the empty sets or something and detect another way, will see
    # note also that we don't handle branches and worldlines with a worldline id i think or a perspective id
    # it should go in the iri ? need to figure that out
    history
    id id_iri id_hist_prev id_delta_rem id_delta_add id_delta_ban is_keyframe timestamp

    history_delta
    id_hist id_delta

    history-derp
    graph-version-id
    graph-version-id
    graph-version-id

    deltas
    """

    n = ilxtr
    gn1 = tuple()
    g0 = ((n.s0, n.p0, n.o0),)
    g1 = ((n.s1, n.p0, n.o0),)
    g2 = ((n.s0, n.p1, n.o0),)
    g3 = ((n.s0, n.p0, n.o1),)

    ga0 = tuple()
    ga1 = (
        (n.sa0, n.pa0, n.oa0),
    )
    ga2 = (
        (n.sa0, n.pa0, n.oa0),
        (n.sa0, n.pa1, n.oa1),
    )
    d_ga2_ga3 = {
        'del': (
            (n.sa0, n.pa1, n.oa1),
        ),
        'add': (
            (n.sa0, n.pa2, n.oa2),
        ),
    }
    ga3 = (
        (n.sa0, n.pa0, n.oa0),
        (n.sa0, n.pa2, n.oa2),
    )

    ga2_add = (
        (n.sa0, n.pa6, n.oa6),
        
    )

    ga2_rem = (
        (n.sa0, n.pa1, n.oa1),
    )

    ga2_ban = (
        (n.sa0, n.pa2, n.oa2),
    )

    _bnc0_0 = rdflib.BNode()
    gc0 = (
        (n.sc0, n.pc0, n.oc0),
        (n.sc0, n.pc1, _bnc0_0),
        (_bnc0_0, n.pc2, n.oc1),
    )

    _ga1 = (
        (n.sa0, n.pa0, n.oa0),
        (n.sa0, n.pa1, n.oa1),
        (n.sa0, n.pa2, n.oa2),
           )

    _ga2 = (  # too big for easy testing
        (n.sa0, n.pa0, n.oa0),
        (n.sa0, n.pa1, n.oa1),
        (n.sa0, n.pa2, n.oa2),

        (n.sa0, n.pa3, n.oa3),
        (n.sa0, n.pa4, n.oa4),
        (n.sa0, n.pa5, n.oa5),
    )


    def test_linear_history(self):
        # not worrying about embedded vs external right now

        # XXX REMINDER in order for this to work we have to replace all the bnodes with identity bnodes
        # OR we have to do this on named subject closures, or on serializesd bnodes

        hg = OntGraph()

        gn1 = OntGraph()

        g0 = OntGraph()
        g0.populate_from_triples(self.g0)
        # diffFromGraph self is prior in time to other for adds
        # so the prior graph should always be the one in question
        add0, rem0, same0 = gn1.diffFromGraph(g0)

        g1 = OntGraph()
        g1.populate_from_triples(self.g1)
        add1, rem1, same1 = g0.diffFromGraph(g1)

        IdentityBNode(g0)
        IdentityBNode(list(g0))
        IdentityBNode(list(g0)[0])

        gc0 = OntGraph()
        gc0.populate_from_triples(self.gc0)
        gc0d = gc0.asWithIdentifiedBNodes()
        gi = IdentityBNode(gc0, debug=True)
        i = IdentityBNode(gc0d, debug=True)
        assert gi == i, f'oops {gi} != {i}'
        bads = []
        bn_bytes = [
            (k[1], v) for k, v in i._if_cache.items()
            if gc0d in k and idf['((p o) ...)'] in k and isinstance(k[1], rdflib.BNode)]
        for k, v in bn_bytes:
            #bnvhex = rdflib.BNode(v.hex())
            bnvhex = v.hex()
            nk = k.split('_')[0]
            if nk != bnvhex:
                bads.append((nk, bnvhex))

        if bads:
            breakpoint()


        self.g0
        self.g1
        self.g2
        self.g3

    def test_with_id_bnodes(self):
        gc0 = OntGraph()
        gc0.populate_from_triples(self.gc0)

        gn = OntGraph().parse(pathlib.Path('ttlser/test/nasty.ttl'))
        #ge = OntGraph().parse(pathlib.Path('ttlser/test/evil.ttl'))

        graphs = (
            gc0,
            #ge,  # apparently just as evil as we thought
            gn,  # woah ... this one breaks
        )
        badgraphs = []
        for graph in graphs:
            gi = IdentityBNode(graph, debug=True)
            dgraph = graph.asWithIdentifiedBNodes()
            i = IdentityBNode(dgraph, debug=True)
            #if graph == ge:  # yes, evil graph is evil and causes problems see test_ibnode.py::TestStability::test_stab
            #    if hasattr(sys, 'pypy_version_info'):
            #        dgraph.write('/tmp/sigh-py-d.ttl'), graph.write('/tmp/sigh-py-g.ttl')
            #    else:
            #        dgraph.write('/tmp/sigh-d.ttl'), graph.write('/tmp/sigh-g.ttl')
            assert gi == i, f'oops {gi} != {i}'

            bads = []
            bn_bytes = [
                (k[1], v) for k, v in i._if_cache.items()
                if dgraph in k and idf['((p o) ...)'] in k and isinstance(k[1], rdflib.BNode)]
            for k, v in bn_bytes:
                #bnvhex = rdflib.BNode(v.hex())
                bnvhex = v.hex()
                nk = k.split('_')[0]
                if nk != bnvhex:
                    bads.append((nk, bnvhex))

            if bads:
                badgraphs.append((graph, dgraph, bads))

        if badgraphs:
            breakpoint()

        assert not badgraphs, badgraphs

    def test_linear_ban_history(self):
        pass

    def test_refine_history(self):
        pass

    def test_fork_history(self):
        pass

    @pytest.mark.skip('diff_{from,to} not ready yet')
    def test_hrm(self):
        gt0 = OntGraph()
        gt1 = OntGraph()

        dt10 = gt1.diff_from(gt0)
        df10 = gt0.diff_to(gt1)

