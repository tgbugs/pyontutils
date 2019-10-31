import sys
import unittest
from ttlser.ttlfmt import main

f1 = 'test/good.ttl', 'test/f1.ttl'
f2 = 'test/nasty.ttl', 'test/f2.ttl'

class TestTtlfmt(unittest.TestCase):
    argv = ['ttlfmt', f1[1], f2[1], '--slow']
    def setUp(self):
        for source, dest in (f1, f2):
            with open(source, 'rt') as s, open(dest, 'wt') as d:
                d.write(s.read())

        self.oldargv = sys.argv
        sys.argv = self.argv

    def tearDown(self):
        sys.argv = self.oldargv

    def test_multi_slow(self):
        try:
            main()
        except AttributeError as e:
            raise AttributeError('failed with ' + str(self.argv)) from e
