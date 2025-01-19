import pytest
import unittest
import subprocess
import pprint
from pathlib import Path
from collections import Counter
import rdflib
import ttlser
from pyontutils.core import yield_recursive, OntGraph, bnNone, OntResIri
from pyontutils.identity_bnode import bnodes, IdentityBNode as IdentityBNodeBase
from pyontutils.namespaces import rdf, ilxtr
from .common import temp_path, ensure_temp_path, log


def formatgraph(g):
    def sigh(e):
        try:
            return g.qname(e)
        except:
            return e

    bah = '\n'.join([' '.join(
        [sigh(e) # FIXME some stateful thing gets skipped here if we only run test_subject_identities so qname fails !??!?! SIGH
            if isinstance(e, rdflib.URIRef) else (e[34:] if isinstance(e, rdflib.BNode) else str(e)) for e in t])
                     for t in sorted(g, key=lambda t: (ttlser.serializers.natsort(t[0]),
                                                       ttlser.serializers.natsort(t[1]),
                                                       ttlser.serializers.natsort(t[2]),
                                                       ))])
    return bah


class TestIBNodeLive(unittest.TestCase):

    IdentityBNode = IdentityBNodeBase

    @property
    def version(self):
        return self.IdentityBNode(b'').version

    def test_bytes(self):
        test = b'hello'
        ident = self.IdentityBNode(test).identity
        m = self.IdentityBNode.cypher()
        m.update(test)
        h = m.digest()
        assert ident == h, ident

    def test_string(self):
        test = 'hello'
        ident = self.IdentityBNode(test).identity
        m = self.IdentityBNode.cypher()
        m.update(test.encode(self.IdentityBNode.encoding))
        h = m.digest()
        assert ident == h, ident

    def test_pair(self):
        # what it should actually be ...
        test = 'hello', 'world'
        ibn = self.IdentityBNode(test, pot=True)
        ident = ibn.identity
        mo = self.IdentityBNode.cypher()
        for i, t in enumerate(test):
            m = self.IdentityBNode.cypher()
            m.update(t.encode(self.IdentityBNode.encoding))
            hi = m.digest()
            mo.update(hi)

        h = mo.digest()
        assert ident == h, ident

    def test_pair_old(self):
        # XXX literally the only place we use separators now is in rdflib.Literal ...
        test = 'hello', 'world'
        ibn = self.IdentityBNode(test)
        ident = ibn.identity
        m = self.IdentityBNode.cypher()

        # FIXME should should never have worked in 2.8 ...
        for i, t in enumerate(test):
            m.update(t.encode(self.IdentityBNode.encoding))
            if not i % 2:
                m.update(ibn.cypher_field_separator_hash)

        h = m.digest()
        if self.version >= 3:  # apparently 2.8 uses the old way
            assert ident != h, ident
        else:
            assert ident == h, ident

    def test_pair_list(self):
        test = (
            ('a', 'b'),
        )
        ibn = self.IdentityBNode(test, debug=True)
        ident = ibn.identity
        m = self.IdentityBNode.cypher()
        digs = []
        sep = ibn.version <= 2
        for tup in test:
            for i, t in enumerate(tup):
                if sep and i > 0:
                    m.update(ibn.cypher_field_separator_hash)

                to_dig = t.encode(self.IdentityBNode.encoding)
                if ibn.version > 2:
                    im = self.IdentityBNode.cypher()
                    im.update(to_dig)
                    idig = im.digest()
                    m.update(idig)
                else:
                    m.update(to_dig)

            h = m.digest()
            digs.append(h)

        def oi(ids):
            m = self.IdentityBNode.cypher()
            for i, id in enumerate(ids):
                m.update(id)

            return m.digest()

        # the reason why there is a double id hash in this case is
        # because when we get to the top level for an ibnode we take
        # the id for a subject by combining the ideas of all triples
        # even if there is only one triple, and take the hash of all
        # subjects in a graph even if there is only a single subject
        # in the graph
        if ibn.version > 2 and ibn.version < 3:
            d = oi(digs)
            dh = d.hex()
            h = oi([oi(digs)])
            hh = h.hex()
            if ident != h:
                breakpoint()

            assert ident.hex() == h.hex(), ident.hex()
        else:
            # for version 1 and version 2 we used the old way of
            # computing the final hash for a single pair which only
            # computed the hash once because technically there should
            # only ever be a single None subject but if we want to be
            # consistent we should still digest one more time as we do
            # starting in v3
            h = oi(digs)
            assert ident.hex() == h.hex(), ident.hex()

    def test_none_list_1(self):
        a = ((        'a', 'b'),)  # (sid      (oid (oid a) (oid b)))
        b = ((bnNone, 'a', 'b'),)  # (sid (sid (oid (oid a) (oid b))))
        bn = rdflib.BNode()
        c = ((bn,   'a', 'b'),)    # (sid (sid (oid (oid a) (oid b))))
        aibn = self.IdentityBNode(a, debug=True)
        bibn = self.IdentityBNode(b, debug=True)
        cibn = self.IdentityBNode(c, debug=True)

        assert bibn.identity != bibn.null_identity, 'oops'
        assert cibn.identity != cibn.null_identity, 'oops'

        # the expected behavior here is
        # a -> (sid      (oid (oid a) (oid b)))
        # b -> (sid (sid (oid (oid a) (oid b))))
        # this is because we want to be able to use
        # the identity of lists of pairs to calculate
        # the identity of a subject id and the function
        # behaves accordingly, if there is no actual subject
        # in a triple then we will not try to put one there
        if aibn.version > 2 and aibn.version < 3:
            if aibn != bibn:
                hrm = {k: bibn._if_cache[k] for k in bibn._if_cache if bnNone in k}
                breakpoint()
            assert aibn == bibn
            #derp = [(k, v, cibn.__dict__[k]) for k, v in bibn.__dict__.items() if v != cibn.__dict__[k]]
            #breakpoint()
            assert bibn == cibn
        else:
            assert aibn != bibn
            assert bibn == cibn

    def test_none_list_2(self):
        a = ((      'a', 'b'),   (        'c', 'd'))
        b = ((bnNone, 'a', 'b'), (bnNone, 'c', 'd'))
        bn = rdflib.BNode()
        c = ((bn,   'a', 'b'), (bn,   'c', 'd'))
        d = ((None, 'a', 'b'), (None, 'c', 'd'))
        aibn = self.IdentityBNode(a, debug=True)
        bibn = self.IdentityBNode(b, debug=True)
        cibn = self.IdentityBNode(c, debug=True)
        dibn = self.IdentityBNode(d, debug=True)
        if aibn.version > 2 and aibn.version < 3:  # see comment in test_none_list_1
            assert aibn == bibn
            #derp = [(k, v, cibn.__dict__[k]) for k, v in bibn.__dict__.items() if v != cibn.__dict__[k]]
            #breakpoint()
            assert bibn == cibn
        else:
            assert aibn != bibn
            assert bibn == cibn

        if aibn.version >= 3:
            # if you actually put None in a triple now
            # it will be treated as null and asigned the
            # expected null_identity but will not trigger
            # bnode-like processing, so don't put None in
            # the subject position
            assert dibn != aibn != cibn

    def test_dangle(self):
        bn = rdflib.BNode()
        bnd = rdflib.BNode()
        # cannot mix strings and bnodes
        # if you have bnodes everything needs to be rdflib compatible
        # because we run the bnode cycle check from an rdflib graph
        c = ((bn,  ilxtr['a'], ilxtr['b']), (bn,  ilxtr['c'], bnd))
        bn_ = rdflib.BNode()
        bnd_ = rdflib.BNode()
        d = ((bn_, ilxtr['a'], ilxtr['b']), (bn_, ilxtr['c'], bnd_))

        cibn = self.IdentityBNode(c, debug=True)
        dibn = self.IdentityBNode(d, debug=True)
        assert cibn == dibn

    def test_pot(self):
        test = ('a', 'b', 'c')
        s = self.IdentityBNode(test[0], debug=True)
        p = self.IdentityBNode(test[1:], pot=True, debug=True)
        t = self.IdentityBNode(test, pot=True, debug=True)
        helper = self.IdentityBNode('', debug=True)
        alt = helper.ordered_identity(s.identity, p.identity, separator=False)
        assert alt == t.identity, (alt.hex(), t.identity.hex())

        t_ = self.IdentityBNode(test, pot=False, debug=True)
        assert t_ != t

        p_ = self.IdentityBNode(test[1:], pot=False, debug=True)
        assert p_ != p

    def test_pair_to_trip(self):
        # no tests here at the moment the desired behavior is
        # specified, but without pot=True the behavior is not easy to
        # test aside from calling ordered_identity with sparator=False
        # where (oid ...)  appears in the spec

        test = ('a', 'b', 'c')
        a = self.IdentityBNode(test[0], debug=True)  # (oid a)
        b = self.IdentityBNode(test[1], debug=True)  # (oid b)
        c = self.IdentityBNode(test[2], debug=True)  # (oid c)
        p = self.IdentityBNode(test[1:], debug=True)  # (oid b c #:sep #t) FIXME vs (oid (oid b) (oid c)) ?
        t = self.IdentityBNode(test, debug=True)
        g = self.IdentityBNode((test,), debug=True)

        helper = self.IdentityBNode('', debug=True)
        condensed = helper.ordered_identity(a.identity, p.identity, separator=False)

        # ((a b c)) -> (oid (oid (oid a) (oid (oid b c #:sep #t))))  # XXX current state bad
        #  (a b c)
        #    (b c)
        # ((s p o) ...) -> (oid (oid s p o #:sep #t) ...)  # old old way
        # ((s (p o) ...) ...) -> (oid (oid (oid s) (oid (oid p o #:sep #t) ...)) ...)  # current way
        # ((s (p o) ...) ...) -> (oid (oid (oid s) (oid (oid (oid p) (oid o)) ...)) ...)  # better
        # in the better way triple ids don't exist but it means that a subject with a single pair is distinghished from the triple containing that pair
        # (oid (oid s)      (oid (oid p) (oid o))) ... !=
        # (oid (oid s) (oid (oid (oid p) (oid o))  ...))

        # because we are calculating the subject id for 'a' as a whole
        # not the id for a single triple, the tradeoff is that you can't
        # obtain a triple id as in condensed = above, and we don't want
        # to calculate the the subject id by attaching the subject identity
        # to each pair first and then calculating all of them because we are
        # back to using the triples as a whole for the id and calculating the
        # id in a silly way that involves an extra hash because it becomes
        # (oid (oid s) (oid p o)) instead of (oid s p o) or (oid (oid s) (oid (oid p o) ...))
        g_condensed = helper.ordered_identity(p.identity)

        g_embedded = helper.ordered_identity(a.identity, g_condensed, separator=False)
        #sigh = helper.ordered_identity(a.identity, p.identity, separator=True)  # thankfully not this one
        #sigh = helper.ordered_identity(a.identity, b.identity, c.identity, separator=False)  # not this either
        #sigh = helper.ordered_identity(a.identity, b.identity, c.identity, separator=True)  # not this either
        sigh = helper.ordered_identity(b'a', b'b', b'c', separator=True)  # this is the one still using the old way  # FIXME
        alt = helper.ordered_identity(condensed)

    def test_method_trip_v3(self):
        helper = self.IdentityBNode('', debug=True)
        hoi = helper.ordered_identity
        ts = (
            (ilxtr.a, ilxtr.b, ilxtr.c),
            (ilxtr.d, ilxtr.e, ilxtr.g),
        )
        its = self.IdentityBNode(ts, debug=True)

        it0 = [hoi(str(_).encode()) for _ in ts[0]]
        it1 = [hoi(str(_).encode()) for _ in ts[1]]
        sci0 = hoi(hoi(it0[1], it0[2], separator=False), separator=False)
        sei0 = hoi(it0[0], sci0, separator=False)
        sei1 = hoi(it1[0], hoi(hoi(it1[1], it1[2], separator=False), separator=False), separator=False)
        itsi = hoi(*sorted((sei0, sei1)), separator=False)
        assert its.identity == itsi, f'wat: {its.identity} {itsi}'

    def test_commute(self):
        helper = self.IdentityBNode('', debug=True)

        # XXX can't use raw strings
        a = rdflib.Literal("1")
        b = rdflib.Literal("2")
        c = rdflib.Literal("3")
        ia = self.IdentityBNode(a, debug=True)
        ib = self.IdentityBNode(b, debug=True)
        ic = self.IdentityBNode(c, debug=True)

        iia = self.IdentityBNode(ia, debug=True)
        assert a != ia != iia, 'oops'

        # XXX argh ... this might be part of the issue
        # these are not different because we sort the ids after
        _ref_1 = helper.ordered_identity(ia.identity, ib.identity).hex()  # why is this with a separator ???
        _ref_1_wat = helper.ordered_identity(ia.identity, ib.identity, separator=False).hex()
        iab = self.IdentityBNode((a, b), debug=True)
        iba = self.IdentityBNode((b, a), debug=True)
        assert iab == iba, 'not sure if want, is footgun'  # this is what pot=True is for

        # these are correctly different
        _ref_2 = helper.ordered_identity(helper.ordered_identity(ia.identity, ib.identity)).hex()
        _ref_3 = helper.ordered_identity(helper.null_identity, helper.ordered_identity(ia.identity, ib.identity)).hex()
        helper.cypher_field_separator_hash
        helper.ordered_identity(ia.identity, ib.identity, separator=False)
        helper.ordered_identity().hex()
        itab = self.IdentityBNode(((a, b),), debug=True)
        itba = self.IdentityBNode(((b, a),), debug=True)
        assert itab != itba, 'do want'

        itiaib = self.IdentityBNode(((ia.identity, ib.identity),), debug=True)
        if ia.version < 3:
            # in version three this is no longer expected because
            # ia and ib are now the hash, not the bytestring ... wait no this isn't what is going on here
            assert itab == itiaib, 'oops'
        else:
            # FIXME i think there is just something weird going on with calculating pairs
            #breakpoint()
            log.warning('something is off here ...')

        itbc = self.IdentityBNode(((b, c),), debug=True)

        ia.recurse((a, b))

        # invar 1: if x != y and u != v then I((x, u)) != I((y, v)) even if x == u and y == v
        assert a != ia and b != ib and self.IdentityBNode((a, b)) != self.IdentityBNode((ia, ib))
        assert a != ia and self.IdentityBNode((a, a)) != self.IdentityBNode((ia, ia))

        assert iab.identity != ia.ordered_identity(*sorted((ia.identity, ib.identity)), separator=True)  # should not have separator
        assert iab.identity == ia.ordered_identity(*sorted((ia.identity, ib.identity)), separator=False)
        iiaib = self.IdentityBNode((ia.identity, ib.identity), debug=True)
        iIaIb = self.IdentityBNode((ia, ib), debug=True)

        soiab = ia.ordered_identity(*sorted((ia.identity, ib.identity)), separator=False)  # this was succeeding by accident, but no longer
        assert iIaIb.identity == iiaib.identity, 'derp'
        assert iab.identity == soiab
        # by invar 1
        assert iiaib.identity != iab.identity

        if self.version < 3:
            # these old versions are severely broken due the the conflation
            # of the identity of identity of a thing with the identity of the thing
            if not iIaIb.identity == soiab == iiaib.identity == iab.identity:
                sigh = iIaIb.identity, soiab, iiaib.identity, iab.identity
                breakpoint()
            assert iIaIb.identity == soiab == iiaib.identity == iab.identity


        # XXX this is where things break down it seems?
        t1 = b, c
        i1 = self.IdentityBNode((t1,), debug=True)
        t2 = a, b, c
        i2 = self.IdentityBNode(t2, debug=True)

        t3 = a, i2.identity
        i3 = self.IdentityBNode(t3, debug=True)

        if False:
            # FIXME heterogenous sequences break the new alt impl
            self.IdentityBNode((a, i2), debug=True)
            self.IdentityBNode((ia, i2), debug=True)

            t4 = self.IdentityBNode(a), i2.identity
            i4 = self.IdentityBNode(t4, debug=True)

        i5 = self.IdentityBNode((ia, ib, ic), debug=True)
        _i5 = self.IdentityBNode((ia.identity , ib.identity , ic.identity ), debug=True)
        assert i5 == _i5
        soiabc = ia.ordered_identity(*sorted(
            ia.ordered_identity(_) for _ in (ia.identity, ib.identity, ic.identity)),
                                     separator=False)

        if self.version < 3:
            # utterly broken conflation of I(a) with I(ia) :/
            assert i5 == i2
        else:
            assert i5 != i2

        # XXX URG only things of len 3 do order preserving, if len 2 is given it will sort the ids before hash
        sigh1 = self.IdentityBNode(((a, b, c),), debug=True)
        sigh2 = self.IdentityBNode((a, b, c), debug=True)
        #breakpoint()
        if False:
            # FIXME ibnode is an bnode to alt unless otherwise specified
            self.IdentityBNode(((ia, itbc),), debug=True)
        if self.version < 2.8:
            # the old triple_identity was computed in a completely different way
            ti_abc = ia.triple_identity(a, b, c)
            assert ti_abc == i2.identity

        # in conclusion, you can't get the id of a whole triple
        # to match the id of the id of the name and the id of the pair ;_;
        # we would have to change the way we hashed graphs entirely to
        # always hash the predicate/object pair first instead of treating
        # a triple is an opaque/uniform object to be identified

    def test_nodes(self):
        assert self.IdentityBNode('hello there') == self.IdentityBNode('hello there')
        assert self.IdentityBNode(b'hello there') == self.IdentityBNode(b'hello there')
        try:
            assert self.IdentityBNode(rdflib.BNode()) != self.IdentityBNode(rdflib.BNode())
            # TODO consider returning the bnode itself?
            raise AssertionError('identity bnode returned identity for bnode')
        except ValueError as e:
            pass
            
        try:
            bnode = rdflib.BNode()
            assert self.IdentityBNode(bnode) == self.IdentityBNode(bnode)
            raise AssertionError('identity bnode returned identity for bnode')
        except ValueError as e:
            pass
        
        lit1 = rdflib.Literal('hello there')
        lit2 = rdflib.Literal('hello there', datatype=rdflib.XSD.string)
        lit3 = rdflib.Literal('hello there', lang='klingon')
        
        assert self.IdentityBNode(lit1) == self.IdentityBNode(lit1)
        assert self.IdentityBNode(lit2) == self.IdentityBNode(lit2)
        assert self.IdentityBNode(lit3) == self.IdentityBNode(lit3)

        assert self.IdentityBNode(lit1) != self.IdentityBNode(lit2)
        assert self.IdentityBNode(lit1) != self.IdentityBNode(lit3)
        assert self.IdentityBNode(lit2) != self.IdentityBNode(lit3)

        uri1 = rdflib.URIRef('http://example.org/1')
        uri2 = rdflib.URIRef('http://example.org/2')

        assert self.IdentityBNode(uri1) == self.IdentityBNode(uri1)
        assert self.IdentityBNode(uri2) == self.IdentityBNode(uri2)

        assert self.IdentityBNode(uri1) != self.IdentityBNode(uri2)

    def test_symmetric(self):
        msp = 'my-sym-pred'
        forward = 'a', msp, 'b'
        backward = tuple(reversed(forward))
        f = self.IdentityBNode([forward], symmetric_predicates=[msp], debug=True)
        b = self.IdentityBNode([backward], symmetric_predicates=[msp], debug=True)
        if self.version >= 3:
            # symmetric predicates were removed in 2.8 so that normalization
            # can be detected using the identity function, normalization should
            # probably be applied before storage into interlex, but pre-normalized
            # identities need to be recorded, with the new caching it should be
            # faster to reid a normalized graph, but will still need some work
            assert f != b
        else:
            assert f == b

    def test_dropout(self):
        # TODO
        # test dropout of all but one subgraphs that share an identity
        pass

    def _inner_list(self, thing):
        ident = self.IdentityBNode(thing, debug=True)
        wat = self.IdentityBNode(thing, debug=True)
        # somehow was/is like we never iterate through the graph at all ???
        # YEP cache hit on a whole graph winds up returning to named_identities DUH
        # now fixed
        err = self.IdentityBNode(list(thing), debug=True)
        assert ident == err, 'hrm'
        assert thing not in ('', b'', [], tuple(), set(), {}, None, False) or wat != self.IdentityBNode([], debug=True), 'sigh'
        if ident.version > 1 and wat != ident:
            breakpoint()

        assert wat == ident, 'AAAAAAAAAAAAAAA'

    def test_list(self):
        inlist = (
            (rdflib.BNode('0'), rdf.type, rdf.List),
            (rdflib.BNode('0'), rdf.first, ilxtr.a),
            (rdflib.BNode('0'), rdf.rest, rdf.nil),
        )
        g = OntGraph(idbn_class=self.IdentityBNode)
        g.populate_from_triples(inlist)
        self._inner_list(g)

    def test_list_1(self):
        inlist = (
            (bnNone, rdf.type, rdf.List),
            (bnNone, rdf.first, ilxtr.a),
            (bnNone, rdf.rest, rdf.nil),
        )
        self._inner_list(inlist)

    def test_list_2(self):
        bn0 = rdflib.BNode('0')
        bn1 = rdflib.BNode('1')
        inlist = (
            (bn0, rdf.type,  rdf.List),
            (bn0, rdf.first, ilxtr.a),
            (bn0, rdf.rest,  bn1),
            (bn1, rdf.first, ilxtr.b),
            (bn1, rdf.rest,  rdf.nil),
        )
        self._inner_list(inlist)

    def test_list_3(self):
        bn1 = rdflib.BNode('1')
        # XXX hypothesis, this happens because subject_identities is populated
        # before we realize that this subject is in triples with bnodes as objects
        # and is therefore order dependent ... XXX partially false not order dependent
        # but that is because resolve_bnode_idents runs after the first pass through recurse
        # which will put the identity for (None, ilxtr.p, ilxtr.d) into subject_identities
        # before resolving bnode idents
        inlist = (
            # any one of these triples is required, it doesn't have to be list involved at all
            #(None, rdf.type,  rdf.List),
            #(None, rdf.first, ilxtr.a),
            (bnNone, ilxtr.p, ilxtr.d),

            (bnNone, rdf.rest,  bn1),  # FIXME the issue is cause by this triple right here

            # one of these two is required, it does have to be list requjired
            #(bn1,  rdf.first, ilxtr.b),
            (bn1,  rdf.rest,  rdf.nil),

            #(bn1, ilxtr.p, ilxtr.c)  # this will not trigger thie issue
        )
        #breakpoint()

        # in version 1 the second time the identity function is invoked the cache hits prevent the yield :/

        # XXX if you know that you have None in your triples
        # then replaced it with a known bnode and work from there
        # that is the properly typed approach
        self._inner_list(inlist)

    def test_list_4(self):
        bn0 = rdflib.BNode('0')
        bn1 = rdflib.BNode('1')
        inlist = (
            (bn0, rdf.type,  rdf.List),
            (bn0, rdf.first, ilxtr.a),
            (bn0, rdf.rest,  bn1),
            (bn1, rdf.type,  rdf.List),
            (bn1, rdf.first, ilxtr.b),
            (bn1, rdf.rest,  rdf.nil),
        )
        self._inner_list(inlist)
        g = OntGraph(idbn_class=self.IdentityBNode)
        g.populate_from_triples(inlist)

        i = self.IdentityBNode(g, debug=True)

        if self.version >= 3:
            pytest.skip('TODO version with no sci')
            return

        issues = False
        for s, sid in i.subject_condensed_identities.items():
            ng = OntGraph(idbn_class=self.IdentityBNode)
            ng.populate_from_triples(g.subject_triples(s))
            ng_idn = self.IdentityBNode(ng, debug=True)
            g_sgi = g.subjectGraphIdentity(s, idbn_class=self.IdentityBNode)
            log.debug('\n' + pprint.pformat((i, ng_idn, g_sgi)))
            if not (i == ng_idn == g_sgi):
                log.debug('\n' + pprint.pformat(
                    (i.id_lookup, ng_idn.id_lookup, g_sgi.id_lookup), width=240))
                #breakpoint()
                #self.IdentityBNode(i.identity)
                issues = True

        # TODO from the debug print here it seems that
        # the issue is that the first computation for g
        # differs, and i thik that it probably should
        # because it is the whole graph not just the
        # bnode subject, give the id_lookup a read
        assert not issues, 'see debug print'

    @pytest.mark.skip('TODO')
    def test_list_5(self):
        bn0 = rdflib.BNode('0')
        bn1 = rdflib.BNode('1')
        bn2 = rdflib.BNode('2')
        bn3 = rdflib.BNode('3')
        inlist = (
            (bn0, rdf.type,  rdf.List),
            (bn0, rdf.first, ilxtr.a),
            (bn0, rdf.rest,  bn1),
            (bn1, rdf.type,  rdf.List),
            (bn1, rdf.first, ilxtr.b),
            (bn1, rdf.rest,  rdf.nil),

            (bn2, rdf.type,  rdf.List),
            (bn2, rdf.first, ilxtr.b),
            (bn2, rdf.rest,  bn3),
            (bn3, rdf.type,  rdf.List),
            (bn3, rdf.first, ilxtr.a),
            (bn3, rdf.rest,  rdf.nil),
        )
        self._inner_list(inlist)
        g = OntGraph(idbn_class=self.IdentityBNode)
        g.populate_from_triples(inlist)

        i = self.IdentityBNode(g, debug=True)

        if self.version >= 3:
            pytest.skip('TODO version with no sci')
            return

        issues = False
        for s, sid in i.subject_condensed_identities.items():
            ng = OntGraph(idbn_class=self.IdentityBNode)
            ng.populate_from_triples(g.subject_triples(s))
            ng_idn = self.IdentityBNode(ng, debug=True)
            g_sgi = g.subjectGraphIdentity(s, idbn_class=self.IdentityBNode)
            log.debug('\n' + pprint.pformat((i, ng_idn, g_sgi)))
            if not (i == ng_idn == g_sgi):
                log.debug('\n' + pprint.pformat(
                    (i.id_lookup, ng_idn.id_lookup, g_sgi.id_lookup), width=240))
                #breakpoint()
                #self.IdentityBNode(i.identity)
                issues = True

        # TODO from the debug print here it seems that
        # the issue is that the first computation for g
        # differs, and i thik that it probably should
        # because it is the whole graph not just the
        # bnode subject, give the id_lookup a read
        breakpoint()
        assert not issues, 'see debug print'

    def test_sigh(self):
        trips_u = (
            (ilxtr.s, ilxtr.p, ilxtr.o0),
            (ilxtr.s, ilxtr.p, ilxtr.o1),
        )
        trips_s = (
            (str(ilxtr.s), ilxtr.p, ilxtr.o0),
            (str(ilxtr.s), ilxtr.p, ilxtr.o1),
        )

        trips_u2 = (
            (ilxtr.s, ilxtr.p, rdflib.Literal('l0')),
            (ilxtr.s, ilxtr.p, rdflib.Literal('l1')),
        )
        trips_s2 = (
            # LOL this induces the problem in the opposite way from uriref
            # where the string version doesn't get hashed but the literal version does

            # FIXME actually literals and strings currently can never be the same because
            # literal always hashes with the datatype and the language even if they are null
            # which is probably dumb, but we did catch part of the double hashing issue
            (ilxtr.s, ilxtr.p, str(rdflib.Literal('l0'))),
            (ilxtr.s, ilxtr.p, str(rdflib.Literal('l1'))),
        )

        _ = self.IdentityBNode('').identity_function(ilxtr.s)
        _ = self.IdentityBNode('').identity_function(ilxtr.p)
        a = self.IdentityBNode((ilxtr.s, ilxtr.p, rdflib.Literal('l0')), pot=True, debug=True)
        b = self.IdentityBNode((ilxtr.s, ilxtr.p, rdflib.Literal('l0', datatype=ilxtr.datatype)), pot=True, debug=True)
        c = self.IdentityBNode((ilxtr.s, ilxtr.p, rdflib.Literal('l0', lang='derp')), pot=True, debug=True)
        if self.version < 3:
            # 2.8 is weird
            lit_no_dt_lang = a.cypher_field_separator_hash + a.null_identity + a.cypher_field_separator_hash + a.null_identity
            l0o = b'l0' + lit_no_dt_lang
            l1o = b'l1' + lit_no_dt_lang
        else:
            l0o = b''.join([a.ordered_identity(_) for _ in (b'l0', b'', b'')])
            l1o = b''.join([a.ordered_identity(_) for _ in (b'l1', b'', b'')])

        d = self.IdentityBNode((ilxtr.s, ilxtr.p, l0o), pot=True, debug=True)
        pid = self.IdentityBNode('').identity_function(ilxtr.p)
        # a and d should be equal, of course is someone intentionally constructs such a string it will be a pita but whatever
        assert a == d, 'oops'

        x = self.IdentityBNode((ilxtr.p, rdflib.Literal('l0')), pot=True, debug=True)
        y = self.IdentityBNode((ilxtr.p, l0o), pot=True, debug=True)
        assert x == y, 'oops'

        trips_salt2 = (
            (ilxtr.s, ilxtr.p, l0o),
            (ilxtr.s, ilxtr.p, l1o),
        )

        i_u2 = self.IdentityBNode(trips_u2, debug=True)
        i_s2 = self.IdentityBNode(trips_s2, debug=True)
        i_salt2 = self.IdentityBNode(trips_salt2, debug=True)
        #assert i_u2 == i_s2, 'sigh 2'  # XXX this will never be true given how to treat literals
        assert i_u2 == i_salt2, 'hrm'

        i_u = self.IdentityBNode(trips_u)
        i_s = self.IdentityBNode(trips_s)
        # TODO version > 2 SIGH
        assert i_u == i_s, 'sigh'

    def test_a_literal(self):
        t = ilxtr.s, ilxtr.p, b''  # just pretend for a moment ... # rdflib.Literal('')
        l = rdflib.Literal(str(ilxtr.s), datatype=ilxtr.p)
        it = self.IdentityBNode(t, pot=True, debug=True)
        il = self.IdentityBNode(l, debug=True)
        assert it != il

    def test_wat(self):
        # every version < 3 has had this problem
        # it seems that somehow the uriref doesn't get hashed but the string does?
        sigh = rdflib.term.URIRef('http://ontology.neuinfo.org/NIF/ttl/nif.ttl')
        sighd = self.IdentityBNode(sigh)
        sighs = self.IdentityBNode(str(sigh))
        sighb = self.IdentityBNode(str(sigh).encode())
        assert sighd == sighs == sighb

        # discovered by accident, have no idea what is going on
        # i think something in rdflib has caused type conversion to coerce it to bytes so somehow the whole string is converted to hex for display ??? why the heck is a uriref considered to be bytes ??!?!
        # oh, maybe it is because rdflib.URIRef is a subclass of rdflib.Node or rdflib.Term or something so ibnode thinks it is a well formed identity already or something ???
        wat = self.IdentityBNode(rdflib.URIRef('http://purl.obolibrary.org/obo/bfo.owlhttp://purl.org/dc/terms/licensehttp://creativecommons.org/licenses/by/4.0/'))
        watd = self.IdentityBNode(rdflib.URIRef('http://purl.obolibrary.org/obo/bfo.owlhttp://purl.org/dc/terms/licensehttp://creativecommons.org/licenses/by/4.0/'), debug=True)
        wats = self.IdentityBNode(str(rdflib.URIRef('http://purl.obolibrary.org/obo/bfo.owlhttp://purl.org/dc/terms/licensehttp://creativecommons.org/licenses/by/4.0/')))  # this one is ok
        watb = self.IdentityBNode(str(rdflib.URIRef('http://purl.obolibrary.org/obo/bfo.owlhttp://purl.org/dc/terms/licensehttp://creativecommons.org/licenses/by/4.0/')).encode())  # ok ... so not a bytes thing
        # check out the length of resulting identity !??!

    @pytest.mark.skip('TODO')
    def test_compare_racket(self):
        # racket pattern matching is better than the tests i do against the length of the
        # thing that was passed to me and the pot= keywork, but good enough for now
        a = self.IdentityBNode(
            (('a', 'b', 'c'),
             ('a', 'd', 'e'),
             ('a', 'f', 'g'),
             ),
            debug=True)
        # XXX SIGH of course this doesn't work because 2 and 3 are special numbers
        # in the currently horridly broken implementation
        """
        b = self.IdentityBNode(
            (('a',
              (
                  ('b', 'c'),
                  ('d', 'e'),
                  ('f', 'g'),
              ),
              ),
             ),
            debug=True)
        """

        c = self.IdentityBNode(
            # this matches racket, but only with an additional nesting level so that means that the current
            # python impl is wrong because it hashes the outer bit one too many times when dealing with pairs
            # (i think)
            (('b', 'c'),
             ('d', 'e'),
             ('f', 'g'),),
            debug=True)

        c2 = self.IdentityBNode(
            # this matches racket, but only with an additional nesting level so that means that the current
            # python impl is wrong because it hashes the outer bit one too many times when dealing with pairs
            # (i think)
            ((bnNone, 'b', 'c'),
             (bnNone, 'd', 'e'),
             (bnNone, 'f', 'g'),),
            debug=True)

        d = self.IdentityBNode((
            # use pot = True to match racket
            'b', 'c'
            ), pot=True, debug=True)

        e = self.IdentityBNode((
            # use pot = True to match racket
            'a', 'b', 'c'
            ), pot=True, debug=True)


        f = self.IdentityBNode((
            rdflib.Literal('l0')  # racket gives 2a953
        ), debug=True)


        g = self.IdentityBNode((
            'p', 'l0'
        ), pot=True, debug=True)

        h = self.IdentityBNode((
            'p', rdflib.Literal('l0')
        ), pot=True, debug=True)

        i = self.IdentityBNode((
            's', 'p', rdflib.Literal('l0')
        ), pot=True, debug=True)

        breakpoint()


class TestIBNodeGraph(unittest.TestCase):

    IdentityBNode = IdentityBNodeBase
    path_to_test = Path('ttlser/test/nasty.ttl')
    iri_to_test = None
    format = 'turtle'

    @property
    def version(self):
        return self.IdentityBNode(b'').version

    def setUp(self):
        self.graph1 = OntGraph(idbn_class=self.IdentityBNode)  # rdflib.Graph()
        if self.path_to_test is None:
            if self.iri_to_test is None:
                msg = 'must have iri or path to test'
                raise ValueError(msg)
            self.ser1 = b''.join(list(OntResIri(self.iri_to_test).data))

        else:
            file = self.path_to_test
            with open(file.as_posix(), 'rb') as f:
                self.ser1 = f.read()

        self.graph1.parse(data=self.ser1, format=self.format)

        g2format = 'nt'
        # broken serialization :/ with full length prefixes
        self.ser2 = self.graph1.serialize(format=g2format, encoding='utf-8')
        with open('test_ser2.ttl', 'wb') as f:
            f.write(self.ser2)

        self.graph2 = OntGraph(idbn_class=self.IdentityBNode) # rdflib.Graph()
        self.graph2.parse(data=self.ser2, format=g2format)

        # FIXME this doesn't account for changes in identity
        # under normalization for example by ttlser
        # IBNode should not do the normalization itself
        # because we do want normalized forms to have a
        # different identity, the question does arrise however
        # about where symmetric predicates fit ... I think those
        # are not a normalization of representation case I think
        # they are clearly an ordering cases and thus in scope for
        # IBNode, in the say way reordering lists is in scope

    def test_ser(self):
        assert self.IdentityBNode(self.ser1) != self.IdentityBNode(self.ser2), 'serialization matches!'

    def test_bnodes(self):
        assert sorted(bnodes(self.graph1)) != sorted(bnodes(self.graph2)), 'bnodes match!'

    def test_nifttl(self):
        fmt = 'nifttl'
        s1 = self.graph1.serialize(format=fmt)
        g2 = OntGraph(idbn_class=self.IdentityBNode)  # rdflib.Graph()
        [g2.add(t) for t in self.graph1]
        [g2.namespace_manager.bind(k, str(v)) for k, v in self.graph1.namespaces()]
        s2 = g2.serialize(format=fmt)
        try:
            assert s1 == s2
        except AssertionError as e:
            ensure_temp_path()
            with open(temp_path / 'f1.ttl', 'wb') as f1, open(temp_path / 'f2.ttl', 'wb') as f2:
                f1.write(s1)
                f2.write(s2)
            raise e

    def test_ibnode(self):
        def sbs(l1, l2):
            for a, b in zip(l1, l2):
                print('', a[:5], a[-5:], '\n', b[:5], b[-5:], '\n\n')

        def ds(d1, d2):
            for (k1, v1), (k2, v2) in sorted(zip(sorted(d1.items()), sorted(d2.items()))):
                if k1 != k2:
                    # TODO len t1 != len t2
                    for t1, t2 in sorted(zip(sorted(v1), sorted(v2))):
                        print(tuple(e[:5] if type(e) == bytes else e for e in t1))
                        print(tuple(e[:5] if type(e) == bytes else e for e in t2))
                        print()

        id1 = self.IdentityBNode(self.graph1, debug=True)
        id2 = self.IdentityBNode(self.graph2, debug=True)


        if id1.version >= 3:
            pytest.skip('TODO version without all the various debug values')
            return

        idui1 = sorted(id1.unnamed_subgraph_identities.values())
        idui2 = sorted(id2.unnamed_subgraph_identities.values())
        assert idui1 == idui2, 'unnamed subgraph identities do not match'

        idco1 = sorted(id1.connected_object_identities.keys())
        idco2 = sorted(id2.connected_object_identities.keys())
        assert idco1 == idco2, 'connected object identities do not match'

        idni1 = sorted(id1.named_identities) 
        idni2 = sorted(id2.named_identities) 
        assert idni1 == idni2, 'named identities do not match'

        idli1 = sorted(id1.connected_identities) 
        idli2 = sorted(id2.connected_identities) 
        assert idli1 == idli2, 'linked identities do not match'

        idfi1 = sorted(id1.free_identities) 
        idfi2 = sorted(id2.free_identities) 
        try:
            assert idfi1 == idfi2, 'free identities do not match'
        except AssertionError as e:
            _ = [[print(e[:10]) for e in t] and print() for t in zip(idfi1, idfi2)]
            lu1 = {v:k for k, v in id1.unnamed_subgraph_identities.items()}
            lu2 = {v:k for k, v in id2.unnamed_subgraph_identities.items()}
            s1 = set(id1.unnamed_subgraph_identities.values())
            s2 = set(id2.unnamed_subgraph_identities.values())
            diff = (s1 | s2) - (s1 & s2)
            for d in diff:
                if d in lu1:
                    s = lu1[d]
                    p, o = next(id1._thing[s])
                    print('id1 extra')
                    [print(t)
                     for t in sorted(yield_recursive(s, p, o, id1._thing),
                                     key=lambda t:t[::-1])]
                else:
                    s = lu2[d]
                    p, o = next(id2._thing[s])
                    print('id2 extra')
                    [print(t)
                     for t in sorted(yield_recursive(s, p, o, id2._thing),
                                     key=lambda t:t[::-1])]

            assert len(set(idfi1)) == len(idfi1), 'HRM 1'
            assert len(set(idfi2)) == len(idfi2), 'HRM 2'
            print(len(idfi1), len(idfi2))  # wow... terrifying that these don't match
            print(e)
            breakpoint()
            raise e

        assert id1.identity == id2.identity, 'identities do not match'

    @pytest.mark.skip('too slow')
    def test_subject_identities(self):
        def dos(s):
            # FIXME hitting bnode subjects that are in cycles
            # means that some of these identities will not work
            g = self.graph1.subjectGraph(s)
            gi = g.identity(debug=True)
            si = g.subjectIdentity(s, debug=True)
            sei = g.subjectEmbeddedIdentity(s, debug=True)
            sci = g.subjectCondensedIdentity(s, debug=True)
            segi = g.subjectEmbeddedGraphIdentity(s, debug=True)
            sgi = g.subjectGraphIdentity(s)  # no debug=True here since it invokes crazy extra work

            g1_si = g.subjectIdentity(s, debug=True)
            g1_sei = g.subjectEmbeddedIdentity(s, debug=True)
            g1_sci = g.subjectCondensedIdentity(s, debug=True)
            g1_segi = g.subjectEmbeddedGraphIdentity(s, debug=True)
            g1_sgi = g.subjectGraphIdentity(s)

            assert sci == g1_sci
            assert sei == si == g1_sei == g1_si
            assert segi == sgi == g1_segi == g1_sgi == gi

            def repsub(t, old_s, new_s):
                s, p, o = t

                if s == old_s:
                    # don't replace in object position since it will induce a false cycle
                    s = new_s

                if isinstance(old_s, rdflib.BNode) and o == old_s:
                    # make sure we do preserve true cycles for bnodes
                    o = new_s

                return s, p, o

            gt = OntGraph(idbn_class=self.IdentityBNode)
            new_s = rdflib.BNode()
            gt.populate_from([repsub(t, s, new_s) for t in g])

            new_gi = gt.identity(debug=True)
            new_si = gt.subjectIdentity(new_s, debug=True)
            new_sei = gt.subjectEmbeddedIdentity(new_s, debug=True)
            new_sci = gt.subjectCondensedIdentity(new_s, debug=True)
            new_segi = gt.subjectEmbeddedGraphIdentity(new_s, debug=True)
            new_sgi = gt.subjectGraphIdentity(new_s)

            if sci != new_sci:
                gik = {k:gi._if_cache[k] for k in gi._if_cache if s in k}
                new_gik = {k:new_gi._if_cache[k] for k in new_gi._if_cache if new_s in k}
                # worrying that somehow we have two of the same subgraph with different identities
                # except that we need to ignore the whole graph
                g1i = self.graph1.identity().identity
                hrm = {k: v for k, v in gi._if_debug_cache.items() if k != g1i and (s in v['subject_embedded_identities'] or
                                                                                    new_s in v['subject_embedded_identities']
                                                                                    )}
                #[(k, v) for k, v in gi._if_cache.items() if v in hrm]
                #_sids = [v['subject_embedded_identities'][s] for v in hrm.values()]
                _fhs = [v['free_heads'] for v in hrm.values()]  # not helpful for the nnnn case
                # yeah, the issue is that i have the bnode id in there for debug
                # but also when all the cycles are the same and there is no
                # external then there is no gurantee that you hit exactly the
                # same position for your particular node in the cycle when you
                # happen to have an oracle on cycle position
                from ttlser.serializers import CustomTurtleSerializer
                # uhhhhh why do i get radicatlly different results when these are set?
                # something is very wrong ah yes, in this case there is id overlap so
                # we can't do this at the same time ... right so this is exactly what
                # we expect, and since the cycle is completely equal in rank ttlser
                # also cannot tell the difference and thus inherits the finaly bnode
                # id ordering which changes with the swap to new_s ... maybe there is
                # another way that is a little bit more stable, hrm, like the subject
                # bnode ids for everything else in the cycle?
                CustomTurtleSerializer._idswap = ({k: v[:10] for k, v in gi._alt_debug['subject_embedded_identities'].items()})
                g.debug()
                CustomTurtleSerializer._idswap = ({k: v[:10] for k, v in new_gi._alt_debug['subject_embedded_identities'].items()})
                gt.debug()
                CustomTurtleSerializer._idswap = {}

                gi._alt_debug['free_heads']
                new_gi._alt_debug['free_heads']

                # not the right metric because it depends on the original ordering in the graph
                subject_cycle_position = [[i for i, t in enumerate(c) if s == t[0]] for c in gi._alt_debug['cycles']]
                new_subject_cycle_position = [[i for i, t in enumerate(c) if new_s == t[0]] for c in new_gi._alt_debug['cycles']]

                list(g), list(gt)


                # ok so we're back to hitting the issue i imagined we might
                # where all nodes are identical with no extra information
                # but because the cutpoint is thus essentially random the
                # actual position that is picked for s and new_s do not match
                breakpoint()
                if not hasattr(sci, '_alt_debug'):
                    ok = sci._if_debug_cache[sci.identity]
                else:
                    ok = sci._alt_debug

                if not hasattr(new_sci, '_alt_debug'):
                    nk = new_sci._if_debug_cache[sci.identity]
                else:
                    nk = new_sci._alt_debug

                breakpoint()
            assert sci == new_sci

            assert new_sei == new_si
            assert new_segi == new_sgi
            assert new_sgi == new_gi
            if isinstance(s, rdflib.BNode):
                assert si == new_si
                assert sgi ==  new_sgi
            else:
                assert si != new_si
                assert sgi != new_sgi

            if isinstance(s, rdflib.BNode):
                comp_sei = sci.identity
            else:
                comp_sei = gi.ordered_identity(gi.ordered_identity(gi.to_bytes(s)), sci.identity, separator=False)

            comp_segi = gi.ordered_identity(comp_sei)

            assert sei.identity == comp_sei

            # something that is in free heads but not in replace when object nothing else in free heads even after replace when object
            # and wat
            if (isinstance(s, rdflib.BNode) and (
                    # our subject is in cycles but not the head of the cycle
                    s in segi._alt_debug['cycles_member_index'] and s not in segi._alt_debug['replace_when_object']
                    or
                    # the subjectGraph for our BNode subject contains other free heads
                    len(segi._alt_debug['free_heads']) > 1)
                or
                # the subjectGraph for our URIRef subject contains ANY free heads
                (not isinstance(s, rdflib.BNode) and segi._alt_debug['free_heads'])):
                # when we break a cycle the subject in question may not be the head of the cycle
                # TODO ensure that even if it isn't the head that its hash value is the same e.g. by collecting
                # all the various identities for the same cycle graph one for each member and then comparing
                assert segi.identity != comp_segi
            else:
                # ok yeah, now this fails because we can get a value for comp_sei that matches
                # but because it isn't actually the head of the cycle it won't match the graph
                # identity when we try to compute it this way because it isn't the head
                if segi.identity != comp_segi:
                    from ttlser.serializers import CustomTurtleSerializer
                    _sg = self.graph1.subjectGraph(s)
                    segi._alt_debug['subject_embedded_identities'][s]
                    CustomTurtleSerializer._idswap.update({k: v[:10] for k, v in segi._alt_debug['subject_embedded_identities'].items()})
                    _sg.debug()
                    breakpoint()

                assert segi.identity == comp_segi

        if self.version >= 3:
            lg1b = len(list(self.graph1))
            g1sb = set(self.graph1.subjects(unique=True))
            i = self.IdentityBNode(self.graph1, debug=True)
            g1sa = set(self.graph1.subjects(unique=True))
            assert g1sb == g1sa, 'utoh'
            g1s = g1sa

            for s in g1sb:
                if isinstance(s, rdflib.BNode):
                    dos(s)
                else:
                    dos(s)

            return
            # so here's the deal, subjectIdentity and subjectGraphIdentity are not clearly defined
            # subjectIdentity as implemented is wrong for bnodes, it should probably be subjectCondensedIdentity
            # and then we would have another subjectEmbeddedIdentity
            # and finally subjectGraphIdentity would technically be IdentityBNode([subjectEmbeddedIdentity])
            # because is the identity of the graph that contains only that subject

        # FIXME this takes forever on ro.owl
        # XXX I think this fails right now because there is an extra call to ordered_identity right now?
        lg1b = len(list(self.graph1))
        g1sb = set(self.graph1.subjects(unique=True))
        i = self.IdentityBNode(self.graph1, debug=True)
        g1sa = set(self.graph1.subjects(unique=True))
        assert g1sb == g1sa, 'utoh'
        g1s = g1sa
        issues = False
        for s, sid in i.subject_condensed_identities.items():
            # FIXME where the fuck does this thing come from !??!?!
            if s not in g1s:
                # HOW IS THIS POSSIBLE !?!?!?!?
                # XXX ANSWER: they are being assigned the null identity ...
                # this seems to be cause by dangling objects? going into bnode_identities or something?
                # oh duh, bnodes that appear only as objects ... in which case they should NOT be added to subject_condensed identities
                # or we should note that subject_identities is actually entity_identities
                _hrm = formatgraph(self.graph1.subject_triples(s))
                if _hrm:
                    print(_hrm)
                else:
                    print('subject graph empty ...')

                breakpoint()

            assert s in g1sb or s in g1sa, 'in neither ... really?'
            assert s in g1sb, 'not in before'
            assert s in g1sa, 'not in after'
            ng = OntGraph()
            ng.namespace_manager.populate_from(self.graph1)
            ng.populate_from_triples(self.graph1.subject_triples(s))
            #ng.debug()
            #sidg = self.graph1.subjectIdentity(s)
            hrm = self.IdentityBNode(ng)
            if s not in g1s:
                lg1a = len(list(self.graph1))
                assert lg1b == lg1a, f'derp {lg1b} != {lg1a}'
                # WHAT ??!?!
                breakpoint()

            assert s in g1s #set(self.graph1.subjects())
            assert list(self.graph1.predicate_objects(s))
            sidg = self.graph1.subjectGraphIdentity(s)  # XXX how the heck can s not be in the graph ?!?!?!
            if self.version >= 3:
                wat = self.graph1.subjectIdentity(s, debug=True)
            # an additional call to IdentityBNode is required to match the fact
            # that we are taking the identity of a collection with one element
            # not just the element itself

            # FIXME it seems there is another issue ... which is that sometimes sid contains multiple
            # and so we probably want subject_condensed_identities ??? not sure?
            sidi = self.IdentityBNode(sid, debug=True)

            if self.version >= 3:  # FIXME is this true?
                assert wat == sidi

            sisis = set(i.subject_identities[s])
            sssis = set(sidg.subject_identities[s])
            if sisis != sssis:
                _intersect = sisis & sssis
                if _intersect:
                    # XXX hypothesis ... in a full graph processing of lists results in differences somehow
                    # the one in particular that we hit seems to be from BLX:4.5 in nasty.ttl and I think
                    # that the problem is that that version of the construct is not being hashed like the
                    # reduced list form, one solution (bad) would be to expand all lists such that sublists
                    # were always fully typed internally like in BLX:4.5, of course they tend to drop the rdf:List bit
                    log.error(f'utoh, double hashing case OR incomplete subject_identities or only rdf:rest rdf:nil identity? !? {_intersect}')
                # XXX it looks like this is somehow an off by 1 error
                # where there is a bnode with the correct id in the graph
                # is this an off by one on the rdf list somehow ??? surely not
                #log.debug(f'broken: e.g. due to empty subjectGraph {s}')
                #ng.debug()
                #bah = '\n'.join([' '.join(
                    #[sigh(e) # FIXME some stateful thing gets skipped here if we only run test_subject_identities so qname fails !??!?! SIGH
                     #if isinstance(e, rdflib.URIRef) else (e[34:] if isinstance(e, rdflib.BNode) else str(e)) for e in t]) for t in sorted(ng)])
                bah = formatgraph(ng)
                log.debug('\n' + bah)
                issues = True
                #breakpoint()
                #raise ValueError('stop pls')
                continue

            assert set(i.subject_identities[s]) == set(sidg.subject_identities[s]), 'dag nabbit'
            assert i.subject_condensed_identities[s] == sidg.subject_condensed_identities[s]
            assert sidi == self.IdentityBNode(sidg.subject_condensed_identities[s])

            # here is the proper expression of the invariant starting in version 3 that bnode
            # identity should be the same as the condensed identity for its subgraph and NOT
            # the ordered identity of its subgraph twice (that is, not using its subgraph identity
            # as if it were the subject of the triples)

            # XXX this invariant is wrong, because the graph identity does do one more hash
            # which is the same as an ordered_identity on a single element which is the same as IdentityBNode
            # so in fact these should not be equal, but should always be one more hash
            bnode_id_invariant = not isinstance(s, rdflib.BNode) or sidg.identity == self.IdentityBNode(sidg.subject_condensed_identities[s]).identity
            if not bnode_id_invariant:
                breakpoint()

            assert bnode_id_invariant, 'shit'

            # we do not expect sidi and sidg to be equal due to changes in how we id graphs for bnodes
            # there is also the issue of confusing naming for subjectIdentity and subjectGraphIdentity
            # which needs to be resolve or at least have test to help clarify
            #if sidi != sidg:
                # TODO HOORAY we found a test that breaks when there are cycles!
                # XXX most of these are condensed ids vs identity issues
                #log.debug(f'broken: e.g. due to cycle {s}')
                #breakpoint()
                #ng.debug()
                #issues = True
                #continue
            #assert sidi != sidg, 'oops'  # XXX this can fail in cases where all_idents_new is empty, e.g. due to a cycle?

            # starting in version 3 bnode identity and bnode graph identity are the same
            # so that IdentityBNode can be used recursively as it is used internally in recurse
            bnode_sidi_sidg = (isinstance(s, rdflib.BNode) and sidi == sidg) or sidi != sidg, 'oops'
            assert bnode_sidi_sidg, 'oops'

        assert not issues, 'there were issues see print output'

    def test_check(self):
        id1 = self.IdentityBNode(self.graph1, debug=True)
        id2 = self.IdentityBNode(self.graph2, debug=True)

        if id1.version >= 3:
            pytest.skip('TODO version with no sci, no all_idents_new')
            return

        if id1.version > 1:
            sid1 = set(id1.all_idents_new)
            sid2 = set(id2.all_idents_new)
            ni2 = sid1 - sid2
            ni1 = sid2 - sid1
            ib = sid1 & sid2
            #assert sid1 == sid2

            id1lu = {v:k for k, v in id1.subject_condensed_identities.items()}
            id2lu = {v:k for k, v in id2.subject_condensed_identities.items()}

            # issue is in the lists

            id1_only = sorted([id1lu[i] for i in ni2 if i in id1lu])
            id2_only = sorted([id2lu[i] for i in ni1 if i in id2lu])

            sep = '================================================================'
            # XXX lots of missing subject ids in here for list elements
            #derp = set(e for t in id1.to_skip for e in t if isinstance(e, rdflib.BNode))
            #hrm = set(self.graph1.subjects()) - set(id1.subject_identities)
            #print(sep)
            #_ = [OntGraph(idbn_class=self.IdentityBNode).populate_from_triples(self.graph1.subject_triples(h)).debug() for h in hrm]
            #hd = hrm - derp  # usually empty
            #dh = derp - hrm  # what are these?
            #print(sep)
            #_ = [OntGraph(idbn_class=self.IdentityBNode).populate_from_triples(self.graph1.subject_triples(h)).debug() for h in dh]

            #print(id1_only)
            #print(id2_only)
            if id1_only:
                print()
                print(sep)
                [OntGraph(idbn_class=self.IdentityBNode).populate_from_triples(self.graph1.subject_triples(n)).debug() for n in id1_only]
            if id2_only:
                print(sep)
                [OntGraph(idbn_class=self.IdentityBNode).populate_from_triples(self.graph2.subject_triples(n)).debug() for n in id2_only]
                print(sep)

            # XXX what is truely wild is that the set that cause problems changes from run to run !?!?!?
            sigh = set(id1_only) & set(id2_only)
            #print('not looking so stable', sigh)
            for overlap in sigh:
                print(overlap)
                # when you look at the list that pops it it doesn't even look the same !??!?!
                # XXX LO AN BEHOLD it is another problem with the cache and not traversing to populate
                # the necessary bits ... and then there is some additional issue
                assert (id1.id_lookup[id1.subject_condensed_identities[overlap]] ==  # XXX stochastic failures
                        id2.id_lookup[id2.subject_condensed_identities[overlap]]), 'sigh'
                print(pprint.pformat(id1.id_lookup[id1.subject_condensed_identities[overlap]]))
                print(pprint.pformat(id2.id_lookup[id2.subject_condensed_identities[overlap]]))
                print(sep)
                ng1 = OntGraph(idbn_class=self.IdentityBNode).populate_from_triples(self.graph1.subject_triples(overlap))
                ng2 = OntGraph(idbn_class=self.IdentityBNode).populate_from_triples(self.graph2.subject_triples(overlap))
                ng1.debug()
                print(sep)
                ng2.debug()
                print(sep)
                ng1id = self.IdentityBNode(ng1, debug=True)
                ng2id = self.IdentityBNode(ng2, debug=True)
                if ng1id != ng2id:
                    # ok, the two sublists have the same identity now, but the parent list does not
                    ng1id.__dict__
                    ng2id.__dict__
                    ng1id.subject_identities
                    ng2id.subject_identities
                    # I think the reason id_lookup doens't work is because it does the full resoluiton
                    # not the lifted version or something? sigh
                    # this case should be eaiser to debug and it is stochastic
                    breakpoint()
                assert ng1id == ng2id, 'double sigh'  # XXX stochastic failures

            def key(a):
                return isinstance(a, tuple), isinstance(a, bytes), a
            #id1_only = sorted([id1.id_lookup[i] for i in ni2], key=key)
            #id2_only = sorted([id2.id_lookup[i] for i in ni1], key=key)

            # XXX a separate not-actually-an-issue
            #if id1.dangling_objs or id2.dangling_objs:
                #for i in (id1, id2):
                    #for o in i.dangling_objs:
                        #print(list(i._thing[::o]))

                #breakpoint()

            #breakpoint()

        # lol yes sometimes this can pass by sheer chance when all the
        # possible misalignments manage to randomly align instead
        success12 = id1.check(self.graph2)
        success21 = id2.check(self.graph1)
        success = success12 and success21
        if not success and self.version >= 3:
            from ttlser.serializers import CustomTurtleSerializer
            class AllPredicates:
                def __contains__(self, other):
                    return True

            CustomTurtleSerializer.no_reorder_list = AllPredicates()
            self.graph1.write('/tmp/g1.ttl'), self.graph2.write('/tmp/g2.ttl')

            # the diff on these is terrifying
            # :%s/ \[/\r [\r/g  # oofl
            sigh = (
            id1._alt_debug
            ,
            id2._alt_debug
            )

            in1n2 = set(id1._alt_debug['seids']) - set(id2._alt_debug['seids'])
            in2n1 = set(id2._alt_debug['seids']) - set(id1._alt_debug['seids'])
            derp1 = []
            for e in in1n2:
                _asdf = {k: v for k, v in id1._alt_debug['subject_embedded_identities'].items() if v == e}
                _sg = [self.graph1.subjectGraph(k) for k in _asdf]
                _wat = [t for t in self.graph1 if [e for e in t if e in _asdf]]
                derp1.append((_asdf, _sg, _wat))
                #_seid = id1._alt_debug['subject_embedded_identities'][e]
                #derp1.append((e, _seid))

            derp2 = []
            for e in in2n1:
                _asdf = {k: v for k, v in id2._alt_debug['subject_embedded_identities'].items() if v == e}
                _sg = [self.graph2.subjectGraph(k) for k in _asdf]  # FIXME eek! where's the subject graph !?!?
                _wat = [t for t in self.graph2 if [e for e in t if e in _asdf]]
                derp2.append((_asdf, _sg, _wat))
                #_seid = id2._alt_debug['subject_embedded_identities'][e]
                #derp2.append((e, _seid))

            # it looks like on evil-3 in one case the bnodes go a b and in the other b a :/
            # why that changes the identity when everything else is identical ???

            # and yes the failure is non-deterministic, because of course it is
            evil_sg1 = derp1[0][1][0].subjectGraph(list(derp1[0][0].keys())[0])
            evil_sg2 = derp2[0][1][0].subjectGraph(list(derp2[0][0].keys())[0])
            eid1, eid2 = evil_sg1.identity(debug=True), evil_sg2.identity(debug=True)
            CustomTurtleSerializer._idswap.update({k: v[:10] for k, v in eid1._alt_debug['subject_embedded_identities'].items()})
            CustomTurtleSerializer._idswap.update({k: v[:10] for k, v in eid2._alt_debug['subject_embedded_identities'].items()})
            evil_sg1.debug(), evil_sg2.debug()
            eseid1, eseid2 = eid1._alt_debug['seids'], eid2._alt_debug['seids']
            seis1, seis2 = eid1._alt_debug['subject_embedded_identities'], eid2._alt_debug['subject_embedded_identities']
            # XXX it's not always the same graph but somehow the mismatched ids are what ?!?!! or maybe I'm remembering a previous round
            # last 3 seis are different somehow
            scis1, scis2 = eid1._alt_debug['subject_condensed_identities'], eid2._alt_debug['subject_condensed_identities']
            bni1, bni2 = eid1._alt_debug['bnode_identities'], eid2._alt_debug['bnode_identities']
            rwo1, rwo2 = eid1._alt_debug['replace_when_object'], eid2._alt_debug['replace_when_object']
            list(evil_sg1), list(evil_sg2)
            rwo1, rwo2
            # pzppz vs ppzpz somehow we aren't capturing the consequences for the cycle in mkey
            breakpoint()

        assert success, 'check failed!'


@pytest.mark.skip('identity for graphs with cycles is terrifyingly broken right now')
class TestIBNodeGraphAlt(TestIBNodeGraph):
    path_to_test = Path('ttlser/test/evil.ttl')


class TestIBNodeGraphRo(TestIBNodeGraph):
    path_to_test = None
    iri_to_test = 'http://purl.obolibrary.org/obo/ro.owl'
    format = 'xml'

    @pytest.mark.skip('too slow')
    def test_subject_identities(self):
        super().test_subject_identities()


# test previous versions

# 2.8  # aka, old attempt at 3 that had all the problems

class IdentityBNodeBase2_8(IdentityBNodeBase):
    default_version = 2.8


class TestIBNode2_8(TestIBNodeLive):
    IdentityBNode = IdentityBNodeBase2_8

    @pytest.mark.xfail(True, reason='obvious non-injective failure in versions < 3')
    def test_commute(self):
        super().test_commute()


class TestIBNodeGraphAlt2_8(TestIBNodeGraphAlt):
    IdentityBNode = IdentityBNodeBase2_8

    @pytest.mark.xfail(True, reason='flaky due to mkey broken for 2.8 so cycles destroy stability')
    def test_check(self):
        super().test_check()

    @pytest.mark.xfail(True, reason='flaky due to mkey broken for 2.8 so cycles destroy stability')
    def test_ibnode(self):
        super().test_ibnode()


class TestIBNodeGraphRo2_8(TestIBNodeGraphRo):
    IdentityBNode = IdentityBNodeBase2_8


class TestIBNodeGraph2_8(TestIBNodeGraph):
    IdentityBNode = IdentityBNodeBase2_8


# 2

class IdentityBNodeBase2(IdentityBNodeBase):
    default_version = 2


class TestIBNode2(TestIBNodeLive):
    IdentityBNode = IdentityBNodeBase2

    @pytest.mark.xfail(True, reason='version < 2.8 works differently')
    def test_pot(self):
        super().test_pot()

    @pytest.mark.xfail(True, reason='version < 2.8 works differently')
    def test_sigh(self):
        super().test_sigh()

    @pytest.mark.xfail(True, reason='version < 2.8 works differently')
    def test_wat(self):
        super().test_wat()

    @pytest.mark.xfail(True, reason='version < 2.8 works differently')
    def test_method_trip_v3(self):
        super().test_method_trip_v3()

    @pytest.mark.xfail(True, reason='obvious non-injective failure in versions < 3')
    def test_commute(self):
        super().test_commute()

    @pytest.mark.xfail(True, reason='version < 3 works differently')
    def test_pair(self):
        super().test_pair()

    @pytest.mark.xfail(True, reason='just broken apparently')
    def test_pair_old(self):
        super().test_pair_old()


class TestIBNodeGraphAlt2(TestIBNodeGraphAlt):
    IdentityBNode = IdentityBNodeBase2

    @pytest.mark.xfail(True, reason='version 2 known broken')
    def test_subject_identities(self):
        super().test_subject_identities()

    @pytest.mark.xfail(True, reason='flaky due to bad or absent mkey')
    def test_check(self):
        super().test_check()

    @pytest.mark.xfail(True, reason='flaky due to bad or absent mkey')
    def test_ibnode(self):
        super().test_ibnode()


class TestIBNodeGraphRo2(TestIBNodeGraphRo):
    IdentityBNode = IdentityBNodeBase2


class TestIBNodeGraph2(TestIBNodeGraph):
    IdentityBNode = IdentityBNodeBase2

    @pytest.mark.xfail(True, reason='version 2 known broken')
    def test_subject_identities(self):
        super().test_subject_identities()


# 1

class IdentityBNodeBase1(IdentityBNodeBase):
    default_version = 1


class TestIBNode1(TestIBNodeLive):
    IdentityBNode = IdentityBNodeBase1

    @pytest.mark.xfail(True, reason='broken insantiy')
    def test_list_3(self):
        # calling ident on the same value twice
        # produces a different result, which is
        # why we moved to version 2 iirc
        super().test_list_3()

    @pytest.mark.xfail(True, reason='version < 3 works differently')
    def test_pot(self):
        super().test_pot()

    @pytest.mark.xfail(True, reason='version < 3 works differently')
    def test_sigh(self):
        super().test_sigh()

    @pytest.mark.xfail(True, reason='version < 3 works differently')
    def test_wat(self):
        super().test_wat()

    @pytest.mark.xfail(True, reason='version < 3 works differently')
    def test_method_trip_v3(self):
        super().test_method_trip_v3()

    @pytest.mark.xfail(True, reason='obvious non-injective failure in versions < 3')
    def test_commute(self):
        super().test_commute()

    @pytest.mark.xfail(True, reason='version < 3 works differently')
    def test_pair(self):
        super().test_pair()

    @pytest.mark.xfail(True, reason='just broken apparently')
    def test_pair_old(self):
        super().test_pair_old()


class TestIBNodeGraphAlt1(TestIBNodeGraphAlt):
    IdentityBNode = IdentityBNodeBase1

    @pytest.mark.xfail(True, reason='flaky version 1 did not handle cycles at all much less correctly')
    def test_check(self):
        super().test_check()

    @pytest.mark.xfail(True, reason='version 1 did not handle cycles at all much less correctly')
    def test_ibnode(self):
        super().test_ibnode()


class TestIBNodeGraphRo1(TestIBNodeGraphRo):
    IdentityBNode = IdentityBNodeBase1


class TestIBNodeGraph1(TestIBNodeGraph):
    IdentityBNode = IdentityBNodeBase1


# test cross version issues

class TextXVersion(unittest.TestCase):

    def test_xversion(self):
        a = IdentityBNodeBase('a')
        b = IdentityBNodeBase1('a')
        c = IdentityBNodeBase2('a')
        for i, j in ((a, b), (b, c), (a, c)):
            try:
                i.check(j)
                assert False, 'should have failed with version mismatch'
            except ValueError as e:  # FIXME change error type when changed interally as well
                pass


class TestStability(unittest.TestCase):

    @pytest.mark.skip('requires pypy and cpython TODO a cpython only version to hunt down the problem')
    def test_stab(self):
        ''' Puttling the STAB in stability '''
        # so ... pypy3 is stable across a multiple runs, but cpython is not, HOORAY !!!!!!!
        # with nasty.ttl we get the same answer every time for pypy and cpython
        # with evil.ttl same answer every time for pypy but cpython produces a different answer every time
        # and this happens even when I modify the notation3 parser to use the exact same bnode ids
        # it seems the issue is likely in IdentityBNode because for evil.ttl the output to
        # sigh-test is identical every time for pypy and cpython but the IdentityBNode value changes for cpython
        # for nasty.ttl the contents of sigh-test are different every time because there are non-literal bnodes
        # but since there are no cycles the IdentityBNode values is the same every time
        # also, testing 100 times there are some hashes that start to recur but literally none of them match
        # the stable pypy value of 884f8ebc113119bf30672a28b329ad1bcab9b8ee990de5db7a40d78ea740aa71
        # pretty clearly related to cycles, but the difference between pypy and cpython behavior
        # is terrifying to the point where I think I need to raise an error if there are cycles
        # until this is fixed

        pyrts = [('/usr/bin/pypy3', 4, 'py'), ('/usr/bin/python3.12', 100, 'cp')]

        res = {}
        results = []
        for fn in ('nasty', 'evil'):
            argh = {}
            for pyrt, runs, sn in pyrts:
                ivars = []
                for rn in range(runs):
                    tv = f'''import sys, pathlib, rdflib
from pprint import pformat
from pyontutils.core import OntGraph
from pyontutils.identity_bnode import IdentityBNode
g = OntGraph().parse(pathlib.Path('ttlser/test/{fn}.ttl'))
with open('/tmp/sigh-test-{fn}-{sn}-{rn}.py', 'wt') as f:
    f.write(pformat(sorted(g)))
print(sys.executable, rdflib.__file__, IdentityBNode(g).identity.hex())
'''
                    argv = [pyrt, '-c', tv]
                    p = subprocess.Popen(argv,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,)
                    out, err = p.communicate()
                    if err.strip():
                        print(err.decode())

                    sigh = py, r, ident = out.decode().split()
                    ivars.append(ident)
                    grrr = [fn, rn] + sigh
                    results.append(grrr)


                argh[pyrt] = dict(Counter(ivars).most_common())

            res[fn] = argh

        breakpoint()
