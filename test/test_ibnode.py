import unittest
from pathlib import Path
import rdflib
from pyontutils.core import yield_recursive
from pyontutils.identity_bnode import bnodes, IdentityBNode
from .common import temp_path


class TestIBNode(unittest.TestCase):
    def setUp(self):
        self.graph1 = rdflib.Graph()
        file = Path('ttlser/test/nasty.ttl')
        with open(file.as_posix(), 'rb') as f:
            self.ser1 = f.read()

        self.graph1.parse(data=self.ser1, format='turtle')

        g2format = 'nt'
        # broken serialization :/ with full lenght prefixes
        self.ser2 = self.graph1.serialize(format=g2format, encoding='utf-8')
        with open('test_ser2.ttl', 'wb') as f:
            f.write(self.ser2)

        self.graph2 = rdflib.Graph()
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

    def test_bytes(self):
        test = b'hello'
        ident = IdentityBNode(test).identity
        m = IdentityBNode.cypher()
        m.update(test)
        h = m.digest()
        assert ident == h, ident

    def test_string(self):
        test = 'hello'
        ident = IdentityBNode(test).identity
        m = IdentityBNode.cypher()
        m.update(test.encode(IdentityBNode.encoding))
        h = m.digest()
        assert ident == h, ident

    def test_pair(self):
        test = 'hello', 'world'
        ibn = IdentityBNode(test)
        ident = ibn.identity
        m = IdentityBNode.cypher()
        for i, t in enumerate(test):
            m.update(t.encode(IdentityBNode.encoding))
            if not i % 2:
                m.update(ibn.cypher_field_separator_hash)

        h = m.digest()
        assert ident == h, ident

    def test_ser(self):
        assert IdentityBNode(self.ser1) != IdentityBNode(self.ser2), 'serialization matches!'

    def test_nodes(self):
        assert IdentityBNode('hello there') == IdentityBNode('hello there')
        assert IdentityBNode(b'hello there') == IdentityBNode(b'hello there')
        try:
            assert IdentityBNode(rdflib.BNode()) != IdentityBNode(rdflib.BNode())
            # TODO consider returning the bnode itself?
            raise AssertionError('identity bnode returned identity for bnode')
        except ValueError as e:
            pass
            
        try:
            bnode = rdflib.BNode()
            assert IdentityBNode(bnode) == IdentityBNode(bnode)
            raise AssertionError('identity bnode returned identity for bnode')
        except ValueError as e:
            pass
        
        lit1 = rdflib.Literal('hello there')
        lit2 = rdflib.Literal('hello there', datatype=rdflib.XSD.string)
        lit3 = rdflib.Literal('hello there', lang='klingon')
        
        assert IdentityBNode(lit1) == IdentityBNode(lit1)
        assert IdentityBNode(lit2) == IdentityBNode(lit2)
        assert IdentityBNode(lit3) == IdentityBNode(lit3)

        assert IdentityBNode(lit1) != IdentityBNode(lit2)
        assert IdentityBNode(lit1) != IdentityBNode(lit3)
        assert IdentityBNode(lit2) != IdentityBNode(lit3)

        uri1 = rdflib.URIRef('http://example.org/1')
        uri2 = rdflib.URIRef('http://example.org/2')

        assert IdentityBNode(uri1) == IdentityBNode(uri1)
        assert IdentityBNode(uri2) == IdentityBNode(uri2)

        assert IdentityBNode(uri1) != IdentityBNode(uri2)

    def test_bnodes(self):
        assert sorted(bnodes(self.graph1)) != sorted(bnodes(self.graph2)), 'bnodes match!'

    def test_nifttl(self):
        fmt = 'nifttl'
        s1 = self.graph1.serialize(format=fmt)
        g2 = rdflib.Graph()
        [g2.add(t) for t in self.graph1]
        [g2.namespace_manager.bind(k, str(v)) for k, v in self.graph1.namespaces()]
        s2 = g2.serialize(format=fmt)
        try:
            assert s1 == s2
        except AssertionError as e:
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

        id1 = IdentityBNode(self.graph1, debug=True)
        id2 = IdentityBNode(self.graph2, debug=True)

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
            embed()
            raise e

        assert id1.identity == id2.identity, 'identities do not match'

    def test_symmetric(self):
        msp = 'my-sym-pred'
        forward = 'a', msp, 'b'
        backward = tuple(reversed(forward))
        f = IdentityBNode([forward], symmetric_predicates=[msp])
        b = IdentityBNode([backward], symmetric_predicates=[msp])
        assert f == b

    def test_check(self):
        id1 = IdentityBNode(self.graph1)
        assert id1.check(self.graph2), 'check failed!'

    def test_dropout(self):
        # TODO
        # test dropout of all but one subgraphs that share an identity
        pass
