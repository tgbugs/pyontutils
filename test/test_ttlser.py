import inspect
import os
import random
import rdflib
import re
import subprocess
import sys
import unittest

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')

def randomize_BNode_order(graph):
    replaced = {}
    def swap(t):
        if isinstance(t, rdflib.BNode):
            if t in replaced:
                return replaced[t]
            else:
                rnd = random.randint(0, 999999999)
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
    def setUp(self):

        goodpath = 'test/good.ttl'
        self.badpath = 'test/nasty.ttl'
        actualpath = 'test/actual.ttl'
        self.actualpath2 = 'test/actual2.ttl'

        with open(goodpath, 'rb') as f:
            self.good = f.read()

        self.actual = self.serialize()
        with open(actualpath, 'wb') as f:
            f.write(self.actual)
        
    def make_ser(self):
        header = ('import sys\n'
                  'import random\n'
                  'import rdflib\n'
                  "rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')\n"
                  'class Thing:\n'
                  '    badpath = \'%s\'\n') % self.badpath
        src0 = inspect.getsource(self.serialize)
        src1 = inspect.getsource(randomize_BNode_order)
        after =  't = Thing()\nsys.stdout.buffer.write(t.serialize())\n'
        return header + src0 + '\n\n' + src1 + after

    def serialize(self):
        graph = rdflib.Graph()
        graph.parse(self.badpath, format='turtle')
        randomize_BNode_order(graph)
        actual = graph.serialize(format='nifttl')
        actual = actual.rsplit(b'\n',2)[0]  # drop versioninfo
        return actual

    def test_ser(self):
        assert self.actual == self.good

    def test_deterministic(self):
        nofail = True
        env = os.environ.copy()
        seed = None  # 'random'
        for _ in range(10):
            if seed is not None:
                env['PYTHONHASHSEED'] = str(seed)
            else:
                env.pop('PYTHONHASHSEED', None)
            cmd_line = [sys.executable, '-c', self.make_ser()]
            p = subprocess.Popen(cmd_line, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 env=env)
            out, err = p.communicate()
            out = re.sub(br"\[\d+ refs, \d+ blocks\]\r?\n?", b"", out)  # nose can't import strip_python_stderr from any test submodule :/
            #out = out.split(b'\n', 1)[1]  # don't need to remove the rdflib noise if using >=rdflib-5.0.0
            actual2 = out
            if self.actual != actual2:
                print('Determinism failure!')
                nofail = False
                with open(self.actualpath2, 'wb') as f:
                    f.write(actual2)
                break

        assert nofail

    def _skip_test_list_ordering(self):  # version used before randomizing bnodes
        _20 = self.actual.split(b'\nBLX:20')[1].split(b'.\n')[0]
        _22 = self.actual.split(b'\nBLX:22')[1].split(b'.\n')[0]
        nofail = True
        if _20 != _22:
            print('List determinism failure')
            for n, t in zip((20, 22), (_20, _22)):
                with open(f'test/list{n}.ttl', 'wb') as f:
                    f.write(f'BLX:{n}'.encode() + t + b'.\n')
            nofail = False

        assert nofail

