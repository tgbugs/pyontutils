import os
import re
import sys
import difflib
import inspect
import unittest
import subprocess
from io import BytesIO
from random import shuffle
import rdflib

# trigger registration of rdflib extensions
import pyontutils.utils
from pyontutils.ttlser import CustomTurtleSerializer, SubClassOfTurtleSerializer
from pyontutils.ttlser import CompactTurtleSerializer, UncompactTurtleSerializer
from pyontutils.ttlser import RacketTurtleSerializer


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
    namespace = graph.namespace_manager.store._IOMemory__namespace
    prefix = graph.namespace_manager.store._IOMemory__prefix
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
    urn = [f'{i:0<6}' for i in range(999999)]
    shuffle(urn)
    def swap(t):
        if isinstance(t, rdflib.BNode):
            if t in replaced:
                return replaced[t]
            else:
                rnd = urn.pop()  # avoid the rare duplicate
                new = rdflib.BNode(rnd)
                replaced[t] = new
                return new
        return t
    for trip in graph:
        new_trip = tuple(swap(t) for t in trip)
        if new_trip != trip:
            graph.remove(trip)
            graph.add(new_trip)


class TestTtlser(unittest.TestCase):

    format = 'nifttl'
    serializer = CustomTurtleSerializer
    goodpath = 'test/good.ttl'
    badpath = 'test/nasty.ttl'
    actualpath = 'test/actual.ttl'
    actualpath2 = 'test/actual2.ttl'

    def setUp(self):
        with open(self.goodpath, 'rb') as f:
            self.good = f.read()

        self.actual = self.serialize()
        with open(self.actualpath, 'wb') as f:
            f.write(self.actual)

    def make_ser(self):
        header = ('import sys\n'
                  'from io import BytesIO\n'
                  'from random import shuffle\n'
                  'import rdflib\n'
                  f'from pyontutils.ttlser import {self.serializer.__name__}\n'
                  f"rdflib.plugin.register({self.format!r}, rdflib.serializer.Serializer, "
                  f"'pyontutils.ttlser', {self.serializer.__name__!r})\n"
                  'class Thing:\n'
                  f'    serializer = {self.serializer.__name__}\n'
                  f'    badpath = {self.badpath!r}\n')
        src0 = inspect.getsource(self.serialize)
        src1 = inspect.getsource(randomize_BNode_order)
        src2 = inspect.getsource(randomize_prefix_order)
        src3 = inspect.getsource(randomize_dict_order)
        after =  't = Thing()\nsys.stdout.buffer.write(t.serialize())\n'
        return header + src0 + '\n\n' + src1 + '\n' + src2 + '\n' + src3 + '\n' + after

    def serialize(self):
        graph = rdflib.Graph()
        graph.parse(self.badpath, format='turtle')
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
        for _ in range(5):  # increase this number of you are suspicious
            if seed is not None:
                env['PYTHONHASHSEED'] = str(seed)
            else:
                env.pop('PYTHONHASHSEED', None)
            code = self.make_ser()
            cmd_line = [sys.executable, '-c', code]
            p = subprocess.Popen(cmd_line, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, #stderr=subprocess.STDOUT,
                                 env=env)
            out, err = p.communicate()
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
                with open(actualpath2, 'wb') as f:
                    f.write(actual2)
                with open(actualpath, 'wb') as f:
                    f.write(actual)
                diff = '\n'.join(difflib.unified_diff(actual.decode().split('\n'),
                                                      actual2.decode().split('\n')))
                print(diff)
                break

        return nofail


class Simple:
    actualpath = '/dev/null'
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
