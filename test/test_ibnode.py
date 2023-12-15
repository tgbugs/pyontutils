import unittest
from pathlib import Path
import rdflib
from pyontutils.core import yield_recursive, OntGraph
from pyontutils.identity_bnode import bnodes, IdentityBNode as IdentityBNodeBase
from pyontutils.namespaces import rdf, ilxtr
from .common import temp_path, ensure_temp_path


class TestIBNode(unittest.TestCase):

    IdentityBNode = IdentityBNodeBase

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
        test = 'hello', 'world'
        ibn = self.IdentityBNode(test)
        ident = ibn.identity
        m = self.IdentityBNode.cypher()
        for i, t in enumerate(test):
            m.update(t.encode(self.IdentityBNode.encoding))
            if not i % 2:
                m.update(ibn.cypher_field_separator_hash)

        h = m.digest()
        assert ident == h, ident

    def test_commute(self):
        # XXX can't use raw strings
        a = rdflib.Literal("1")
        b = rdflib.Literal("2")
        c = rdflib.Literal("3")
        ia = self.IdentityBNode(a, debug=True)
        ib = self.IdentityBNode(b, debug=True)
        ic = self.IdentityBNode(c, debug=True)

        # XXX argh ... this might be part of the issue
        # these are not different because we sort the ids after
        iab = self.IdentityBNode((a, b), debug=True)
        iba = self.IdentityBNode((b, a), debug=True)
        assert iab == iba, 'not sure if want, is footgun'

        # these are correctly different
        itab = self.IdentityBNode(((a, b),), debug=True)
        itba = self.IdentityBNode(((b, a),), debug=True)
        assert itab != itba, 'do want'

        itiaib = self.IdentityBNode(((ia.identity, ib.identity),), debug=True)
        assert itab == itiaib, 'oops'


        itbc = self.IdentityBNode(((b, c),), debug=True)

        ia.recurse((a, b))

        iiaib = self.IdentityBNode((ia.identity, ib.identity), debug=True)
        iIaIb = self.IdentityBNode((ia, ib), debug=True)
        oiab = ia.ordered_identity(ia.identity, ib.identity)
        assert iIaIb.identity == oiab == iiaib.identity == iab.identity


        # XXX this is where things break down it seems?
        t1 = b, c
        i1 = self.IdentityBNode((t1,), debug=True)
        t2 = a, b, c
        i2 = self.IdentityBNode(t2, debug=True)

        t3 = a, i2.identity
        i3 = self.IdentityBNode(t3, debug=True)

        self.IdentityBNode((a, i2), debug=True)
        self.IdentityBNode((ia, i2), debug=True)

        t4 = self.IdentityBNode(a), i2.identity
        i4 = self.IdentityBNode(t4, debug=True)

        i5 = self.IdentityBNode((ia, ib, ic), debug=True)
        oiabc = ia.ordered_identity(ia.identity, ib.identity, ic.identity)

        assert i5 == i2

        # XXX URG only things of len 3 do order preserving, if len 2 is given it will sort the ids before hash
        sigh1 = self.IdentityBNode(((a, b, c),), debug=True)
        sigh2 = self.IdentityBNode((a, b, c), debug=True)
        #breakpoint()
        self.IdentityBNode(((ia, itbc),), debug=True)
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
        assert f == b

    def test_dropout(self):
        # TODO
        # test dropout of all but one subgraphs that share an identity
        pass

    def test_list(self):
        g = OntGraph()
        g.populate_from_triples((
            (rdflib.BNode('0'), rdf.type, rdf.List),
            (rdflib.BNode('0'), rdf.first, ilxtr.a),
            (rdflib.BNode('0'), rdf.rest, rdf.nil),
        ))
        ident = self.IdentityBNode(g, debug=True)
        wat = self.IdentityBNode(g, debug=True)
        # somehow was is like we never iterate through the graph at all ???
        # YEP cache hit on a whole graph winds up returning to named_identities DUH
        # now fixed
        err = self.IdentityBNode(list(g), debug=True)
        assert ident == err, 'hrm'
        assert wat != self.IdentityBNode([], debug=True), 'sigh'
        assert wat == ident, 'AAAAAAAAAAAAAAA'


class TestIBNodeGraph(unittest.TestCase):

    IdentityBNode = IdentityBNodeBase
    path_to_test = Path('ttlser/test/nasty.ttl')
    format = 'turtle'

    def setUp(self):
        self.graph1 = OntGraph()  # rdflib.Graph()
        file = self.path_to_test
        with open(file.as_posix(), 'rb') as f:
            self.ser1 = f.read()

        self.graph1.parse(data=self.ser1, format=self.format)

        g2format = 'nt'
        # broken serialization :/ with full length prefixes
        self.ser2 = self.graph1.serialize(format=g2format, encoding='utf-8')
        with open('test_ser2.ttl', 'wb') as f:
            f.write(self.ser2)

        self.graph2 = OntGraph() # rdflib.Graph()
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
        g2 = OntGraph()  # rdflib.Graph()
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

    def test_subject_identities(self):
        # XXX I think this fails right now because there is an extra call to ordered_identity right now?
        i = self.IdentityBNode(self.graph1, debug=True)
        issues = False
        for s, sid in i.subject_condensed_identities.items():
            ng = OntGraph().populate_from_triples(self.graph1.subjectGraph(s))
            #ng.debug()
            #sidg = self.graph1.subjectIdentity(s)
            hrm = self.IdentityBNode(ng)
            sidg = self.graph1.subjectGraphIdentity(s)
            # an additional call to IdentityBNode is required to match the fact
            # that we are taking the identity of a collection with one element
            # not just the element itself

            # FIXME it seems there is another issue ... which is that sometimes sid contains multiple
            # and so we probably want subject_condensed_identities ??? not sure?
            sidi = self.IdentityBNode(sid, debug=True)
            if set(i.subject_identities[s]) != set(sidg.subject_identities[s]):
                print(f'broken: e.g. due to empty subjectGraph {s}')
                ng.debug()
                issues = True
                breakpoint()
                raise ValueError('stop pls')
                continue

            assert set(i.subject_identities[s]) == set(sidg.subject_identities[s]), 'dag nabbit'
            assert i.subject_condensed_identities[s] == sidg.subject_condensed_identities[s]
            if sidi != sidg:
                # TODO HOORAY we found a test that breaks when there are cycles!
                print(f'broken: e.g. due to cycle {s}')
                ng.debug()
                issues = True
                continue

            assert sidi == sidg, 'oops'  # XXX this can fail in cases where all_idents_new is empty, e.g. due to a cycle?

        assert not issues, 'there were issues see print output'

    def test_check(self):
        id1 = self.IdentityBNode(self.graph1, debug=True)
        id2 = self.IdentityBNode(self.graph2, debug=True)

        if id1.version > 1:
            sid1 = set(id1.all_idents_new)
            sid2 = set(id2.all_idents_new)
            ni2 = sid1 - sid2
            ni1 = sid2 - sid1
            ib = sid1 & sid2

            id1lu = {v:k for k, v in id1.subject_condensed_identities.items()}
            id2lu = {v:k for k, v in id2.subject_condensed_identities.items()}

            # issue is in the lists

            id1_only = sorted([id1lu[i] for i in ni2])
            id2_only = sorted([id2lu[i] for i in ni1])

            sep = '================================================================'
            # XXX lots of missing subject ids in here for list elements
            #derp = set(e for t in id1.to_skip for e in t if isinstance(e, rdflib.BNode))
            #hrm = set(self.graph1.subjects()) - set(id1.subject_identities)
            #print(sep)
            #_ = [OntGraph().populate_from_triples(self.graph1.subjectGraph(h)).debug() for h in hrm]
            #hd = hrm - derp  # usually empty
            #dh = derp - hrm  # what are these?
            #print(sep)
            #_ = [OntGraph().populate_from_triples(self.graph1.subjectGraph(h)).debug() for h in dh]

            #print(id1_only)
            #print(id2_only)
            if id1_only:
                print()
                print(sep)
                [OntGraph().populate_from_triples(self.graph1.subjectGraph(n)).debug() for n in id1_only]
            if id2_only:
                print(sep)
                [OntGraph().populate_from_triples(self.graph2.subjectGraph(n)).debug() for n in id2_only]
                print(sep)

            # XXX what is truely wild is that the set that cause problems changes from run to run !?!?!?
            sigh = set(id1_only) & set(id2_only)
            #print('not looking so stable', sigh)
            import pprint
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
                ng1 = OntGraph().populate_from_triples(self.graph1.subjectGraph(overlap))
                ng2 = OntGraph().populate_from_triples(self.graph2.subjectGraph(overlap))
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
        assert id1.check(self.graph2), 'check failed!'


class TestIBNodeGraphAlt(TestIBNodeGraph):
    path_to_test = Path('ttlser/test/evil.ttl')


class TestIBNodeGraphRo(TestIBNodeGraph):
    path_to_test = Path('~/git/interlex/ro.owl').expanduser()
    format = 'xml'


# test previous versions
class IdentityBNodeBase1(IdentityBNodeBase):
    default_version = 1


class TestIBNode1(TestIBNode):
    IdentityBNode = IdentityBNodeBase1


class TestIBNodeGraphAlt1(TestIBNodeGraphAlt):
    IdentityBNode = IdentityBNodeBase1


class TestIBNodeGraphRo1(TestIBNodeGraphRo):
    IdentityBNode = IdentityBNodeBase1


class TestIBNodeGraph1(TestIBNodeGraph):
    IdentityBNode = IdentityBNodeBase1


# test cross version issues

class TextXVersion(unittest.TestCase):

    def test_xversion(self):
        a = IdentityBNodeBase('a')
        b = IdentityBNodeBase1('a')
        try:
            a.check(b)
            assert False, 'should have failed with version mismatch'
        except ValueError as e:  # FIXME change error type when changed interally as well
            pass
