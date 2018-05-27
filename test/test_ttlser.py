import os
import re
import sys
import difflib
import inspect
import unittest
import subprocess
from random import shuffle
import rdflib

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')
rdflib.plugin.register('scottl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'SubClassOfTurtleSerializer')


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

    goodpath = 'test/good.ttl'
    scogoodpath = 'test/scogood.ttl'
    badpath = 'test/nasty.ttl'
    actualpath = 'test/actual.ttl'
    actualpath2 = 'test/actual2.ttl'
    scoactualpath = 'test/scoactual.ttl'
    scoactualpath2 = 'test/scoactual2.ttl'

    def setUp(self):
        with open(self.goodpath, 'rb') as f:
            self.good = f.read()
        with open(self.scogoodpath, 'rb') as f:
            self.scogood = f.read()

        self.actual = self.serialize()
        with open(self.actualpath, 'wb') as f:
            f.write(self.actual)

        self.scoactual = self.serialize(outfmt='scottl')
        with open(self.scoactualpath, 'wb') as f:
            f.write(self.scoactual)
        
    def make_ser(self, outfmt='nifttl'):
        header = ('import sys\n'
                  'from random import shuffle\n'
                  'import rdflib\n'
                  "rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')\n"
                  "rdflib.plugin.register('scottl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'SubClassOfTurtleSerializer')\n"
                  'class Thing:\n'
                  '    badpath = \'%s\'\n') % self.badpath
        src0 = inspect.getsource(self.serialize)
        src1 = inspect.getsource(randomize_BNode_order)
        src2 = inspect.getsource(randomize_prefix_order)
        after =  f't = Thing()\nsys.stdout.buffer.write(t.serialize(\'{outfmt}\'))\n'
        return header + src0 + '\n\n' + src1 + '\n' + src2 + '\n' + after

    def serialize(self, outfmt='nifttl'):
        graph = rdflib.Graph()
        graph.parse(self.badpath, format='turtle')
        randomize_BNode_order(graph)
        randomize_prefix_order(graph)

        actual = graph.serialize(format=outfmt)
        actual = actual.rsplit(b'\n',2)[0]  # drop versioninfo
        return actual

    def deterministic(self, outfmt='nifttl'):
        nofail = True
        env = os.environ.copy()
        seed = None  # 'random'
        if outfmt == 'nifttl':
            actual = self.actual
            actualpath = self.actualpath
            actualpath2 = self.actualpath2
        elif outfmt == 'scottl':
            actual = self.scoactual
            actualpath = self.scoactualpath
            actualpath2 = self.scoactualpath2
        for _ in range(5):  # increase this number of you are suspicious
            if seed is not None:
                env['PYTHONHASHSEED'] = str(seed)
            else:
                env.pop('PYTHONHASHSEED', None)
            cmd_line = [sys.executable, '-c', self.make_ser(outfmt)]
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

    def test_ser(self):
        assert self.actual == self.good

    def _test_scoser(self):  # TODO not clear how scogood should actually work, there are many edge cases
        assert self.scoactual == self.scogood

    def test_deterministic(self):
        assert self.deterministic()

    def _test_scodet(self):  # TODO not deterministic yet
        assert self.deterministic('scottl')

