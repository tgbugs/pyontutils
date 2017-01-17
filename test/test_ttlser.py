import inspect
import os
import random
import rdflib
import re
import subprocess
import sys
import unittest

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')

class TestTtlser(unittest.TestCase):
    def setUp(self):

        goodpath = 'test/good.ttl'
        self.badpath = 'test/nasty.ttl'
        actualpath = 'test/actual.ttl'
        self.actualpath2 = 'test/actual2.ttl'

        print(self.make_ser())

        with open(goodpath, 'rb') as f:
            self.good = f.read()

        self.actual = self.serialize()
        with open(actualpath, 'wb') as f:
            f.write(self.actual)
        

    def test_ser(self):
        assert self.actual == self.good

    def serialize(self):
        graph = rdflib.Graph()
        graph.parse(self.badpath, format='turtle')
        actual = graph.serialize(format='nifttl')
        #actual = graph.serialize(format='turtle')  # no change when the file is identical
        return actual

    def make_ser(self):
        header = ('import rdflib\n'
                  'import sys\n'
                  "rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')\n"
                  'class Thing:\n'
                  '    badpath = \'%s\'\n') % self.badpath
        src = inspect.getsource(self.serialize)
        after =  't = Thing()\nsys.stdout.buffer.write(t.serialize())\n'
        return header + src + after


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
            out = out.split(b'\n', 1)[1]
            actual2 = out
            if self.actual != actual2:
                print('Determinism failure!')
                nofail = False
                with open(self.actualpath2, 'wb') as f:
                    f.write(actual2)
                break

        assert nofail


