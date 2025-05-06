import os
import re
import sys
import difflib
import inspect
import unittest
import subprocess
from io import BytesIO
from random import shuffle
from pathlib import Path
from collections import defaultdict
import rdflib
from rdflib.plugins.serializers.turtle import TurtleSerializer

from ttlser import CustomTurtleSerializer, SubClassOfTurtleSerializer
from ttlser import CompactTurtleSerializer, UncompactTurtleSerializer
from ttlser import RacketTurtleSerializer

thisfile = Path(__file__).resolve()
parent = thisfile.parent.parent


def randomize_dict_order(d):
    random_order_keys = list(d)
    shuffle(random_order_keys)
    out = {}
    for k in random_order_keys:
        out[k] = d[k]

    if tuple(d) == tuple(out):
        return randomize_dict_order(d)  # try again
    else:
        return out


def randomize_prefix_order(graph):
    nm_store = graph.namespace_manager.store
    namespace = getattr(nm_store, f'_{nm_store.__class__.__name__}__namespace')
    prefix = getattr(nm_store, f'_{nm_store.__class__.__name__}__prefix')
    def save(d):
        keys = list(d)
        shuffle(keys)
        out = {}
        for k in keys:
            out[k] = d[k]
        return out
    sn, sp = save(namespace), save(prefix)
    assert namespace == sn and prefix == sp
    def zap(d): [d.pop(k) for k in list(d.keys())]
    zap(namespace)
    zap(prefix)
    graph.namespace_manager.reset()
    def readd(s, d):
        for k, v in s.items():
            d[k] = v
    readd(sn, namespace)
    readd(sp, prefix)
    graph.namespace_manager.reset()  # repopulate the trie


def randomize_BNode_order(graph):
    replaced = {}
    urn = ['{i:0>6}'.format(i=i) for i in range(999999)]
    shuffle(urn)
    assert len(urn) == len(set(urn))  # TRY IT I DARE YOU
    safe_urn = (_ for _ in urn)
    def swap(e):
        if isinstance(e, rdflib.BNode):
            if e in replaced:
                return replaced[e]
            else:
                rnd = next(safe_urn)  # avoid the rare duplicate
                new = rdflib.BNode(rnd)
                replaced[e] = new
                return new
        else:
            return e

    for trip in graph:
        new_trip = tuple(swap(_) for _ in trip)
        if new_trip != trip:
            graph.remove(trip)
            graph.add(new_trip)


class TestTtlser(unittest.TestCase):

    _ntests = 5  # increase to catch infrequent det failures
    format = 'nifttl'
    serializer = CustomTurtleSerializer
    goodpath = 'test/good.ttl'
    badpath = 'test/nasty.ttl'
    actualpath = 'test/actual.ttl'
    actualpath2 = 'test/actual2.ttl'

    def setUp(self):
        with open((parent / self.goodpath).as_posix(), 'rb') as f:
            self.good = f.read()

        self.actual = self.serialize()
        with open((parent / self.actualpath).as_posix(), 'wb') as f:
            f.write(self.actual)

    def make_ser(self):
        header = ('import sys\n' +
                  'from io import BytesIO\n' +
                  'from random import shuffle\n' +
                  'from pathlib import Path\n' +
                  'from collections import defaultdict\n' +
                  'import rdflib\n' +
                  ('from ttlser import ' + self.serializer.__name__ + '\n') +
                  ("rdflib.plugin.register(" + repr(self.format) + ", rdflib.serializer.Serializer, ") +
                  ("'ttlser', " + repr(self.serializer.__name__) + ")\n") +
                  ('parent = Path("' + parent.as_posix() + '")\n') +
                  'class Thing:\n' +
                  ('    serializer = ' + self.serializer.__name__ + '\n') +
                  ('    badpath = ' + repr(self.badpath) + '\n'))
        src0 = inspect.getsource(self.serialize)
        src1 = inspect.getsource(randomize_BNode_order)
        src2 = inspect.getsource(randomize_prefix_order)
        src3 = inspect.getsource(randomize_dict_order)
        after =  't = Thing()\nsys.stdout.buffer.write(t.serialize())\n'
        return header + src0 + '\n\n' + src1 + '\n' + src2 + '\n' + src3 + '\n' + after

    def serialize(self):
        graph = rdflib.Graph()
        graph.parse((parent / self.badpath).as_posix(), format='turtle')
        randomize_BNode_order(graph)
        randomize_prefix_order(graph)

        ttlser = self.serializer(graph)
        ttlser.node_rank = randomize_dict_order(ttlser.node_rank)  # not it
        stream = BytesIO()
        ttlser.serialize(stream)
        actual = stream.getvalue()

        actual = actual.rsplit(b'\n',2)[0]  # drop versioninfo
        return actual

    def deterministic(self):
        nofail = True
        env = os.environ.copy()
        seed = None  # 'random'
        actual = self.actual
        actualpath = self.actualpath
        actualpath2 = self.actualpath2
        for _ in range(self._ntests):
            if seed is not None:
                env['PYTHONHASHSEED'] = str(seed)
            else:
                env.pop('PYTHONHASHSEED', None)
            code = self.make_ser()
            cmd_line = [sys.executable, '-c', code]
            p = subprocess.Popen(cmd_line, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 #stderr=subprocess.DEVNULL,
                                 stderr=subprocess.PIPE,
                                 env=env)
            out, err = p.communicate()
            if err.strip():
                print(code)
                print(err.decode())
            out = re.sub(br"\[\d+ refs, \d+ blocks\]\r?\n?", b"", out)  # nose can't import strip_python_stderr from any test submodule :/
            #out = out.split(b'\n', 1)[1]  # don't need to remove the rdflib noise if using >=rdflib-5.0.0
            actual2 = out
            if actual != actual2:
                print('Determinism failure!')
                if False:
                    hit = False
                    for _1, _2 in zip(actual.decode(), actual2.decode()):
                        if _1 != _2 and not hit:
                            hit = True
                        if hit:
                            print(_1, _2)
                nofail = False
                with open((parent / actualpath2), 'wb') as f:
                    f.write(actual2)
                with open((parent / actualpath), 'wb') as f:
                    f.write(actual)
                diff = '\n'.join(difflib.unified_diff(actual.decode().split('\n'),
                                                      actual2.decode().split('\n')))
                print(diff)
                break

        return nofail


class Simple:
    actualpath = 'NUL' if os.name == 'nt' else '/dev/null'
    def test_simple(self):
        self.serialize()


class TestCmp(Simple, TestTtlser):
    format = 'cmpttl'
    serializer = CompactTurtleSerializer


class TestUncmp(Simple, TestTtlser):
    format = 'uncmpttl'
    serializer = UncompactTurtleSerializer


class TestRkt(Simple, TestTtlser):
    format = 'rktttl'
    serializer = RacketTurtleSerializer


class TestDet(TestTtlser):
    def test_ser(self):
        assert self.actual == self.good

    def test_deterministic(self):
        assert self.deterministic()


class TestList(TestDet):
    badpath = 'test/list-nasty.ttl'
    goodpath = 'test/list-good.ttl'
    actualpath = 'test/list-act.ttl'
    actualpath2 = 'test/list-act-2.ttl'


class TestSCO(Simple, TestTtlser):  # TODO TestDet, but not ready yet
    format = 'scottl'
    serializer = SubClassOfTurtleSerializer
    goodpath = 'test/scogood.ttl'
    actualpath = 'test/scoactual.ttl'
    actualpath2 = 'test/scoactual2.ttl'


class TestNoReorderRdfStar(Simple, TestTtlser):
    format = 'nifttl'
    serializer = CustomTurtleSerializer
    goodpath = 'test/no-reorder.ttl'
    actualpath = 'test/no-reorder-actual.ttl'
    actualpath2 = 'test/no-reorder-actual-2.ttl'


class TestMultiBNode(unittest.TestCase):

    format = 'nifttl'

    def test_mb(self):
        g = rdflib.Graph()
        s1 = rdflib.URIRef('http://example.org/a')
        s2 = rdflib.URIRef('http://example.org/b')
        p = rdflib.URIRef('http://example.org/p')
        o = rdflib.BNode()
        oops = rdflib.Literal('oops!')
        [g.add(t) for t in
         ((s1, p, o),
          (s2, p, o),
          (o, p, oops),)]
        ser = g.serialize(format=self.format)
        g2 = rdflib.Graph()
        g2.parse(data=ser)
        assert oops in list(g.objects())
        assert oops in list(g2.objects())


class TestCycle(unittest.TestCase):

    path = 'test/evil.ttl'
    serializer = CustomTurtleSerializer

    def test_cycle(self):
        g = rdflib.Graph()
        g.parse(self.path)
        tser = TurtleSerializer(g)
        nser = self.serializer(g)

        stream = BytesIO()
        tser.serialize(stream)
        ttl = stream.getvalue().decode()

        stream = BytesIO()
        nser.serialize(stream)
        nit = stream.getvalue().decode()

        gn = rdflib.Graph().parse(data=nit)
        gt = rdflib.Graph().parse(data=ttl)
        print(ttl)
        print(nit)
        assert len(g) == len(gt), 'urg'
        assert len(g) == len(gn), 'urg'
        assert len(gt) == len(gn), 'urg'


class TestPredicateScoStrEq(unittest.TestCase):

    serializer = CustomTurtleSerializer

    def test_sco_pred(self):
        class OtherType: pass
        class Oof(rdflib.URIRef):
            def __hash__(self):
                return hash((self.__class__, super().__hash__()))

            def __eq__(self, other):
                def complex_type_compare(a, b):
                    aii = isinstance(a, OtherType)
                    bii = isinstance(b, OtherType)
                    return aii and bii or (not aii and not bii)

                if type(self) == type(other) or complex_type_compare(self, other):
                    # XXX down cast to str for equality is what causes the issue
                    return str(self) == str(other)

                else:
                    return False

            def __ne__(self, other):
                return not self.__eq__(other)


        g = rdflib.Graph()
        s = rdflib.BNode()
        preds = (
            str(rdflib.RDF.type),
            str(rdflib.RDFS.label),
            'http://example.org/p1',
            'http://example.org/p2',
        )
        for p in preds:
            p_u = rdflib.URIRef(p)
            p_o = Oof(p)
            g.add((s, p_u, rdflib.BNode()))
            g.add((s, p_o, rdflib.BNode()))

        nser = self.serializer(g)

        stream = BytesIO()
        nser.serialize(stream)
        nit = stream.getvalue().decode()
        pord = [
            ((self.serializer.predicateOrder.index(p)
              if p in self.serializer.predicateOrder else
              -1),
             p)
            for p in nser.predicateOrder]
