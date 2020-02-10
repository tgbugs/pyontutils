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

    def test_run(self):
        try:
            main()
        except AttributeError as e:
            raise AttributeError('failed with ' + str(self.argv)) from e


class TestXml(TestTtlfmt):
    argv = ['ttlfmt', f1[0], '--outfmt', 'xml', '--output', 'test/good.owl']
    argv2 = ['ttlfmt', 'test/good.owl', '--outfmt', 'ttl', '--output', 'test/good2.ttl']
    def test_run(self):
        super().test_run()
        self.__class__.argv = self.argv2

    def test_run_2(self):
        super().test_run()
