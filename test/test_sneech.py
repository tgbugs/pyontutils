import os
import unittest
import pathlib as pl
import pytest
import ontquery as oq
import augpathlib as aug
from pyontutils import sneechenator as snch
from pyontutils.core import OntGraph
from pyontutils.config import auth
from pyontutils.namespaces import rdf
from pyontutils.integration_test_helper import Repo
from .common import temp_path

temp_path_aug = aug.AugmentedPath(temp_path)
sfy = pl.Path(__file__).parent / 'sneech-file.yaml'
sft = pl.Path(__file__).parent / 'sneech-file.ttl'


def fix_file(path):
    with open(path, 'rt') as f:
        sin = f.read()

    sout = sin.replace('~/git/NIF-Ontology',
                       auth.get_path('ontology-local-repo').resolve()
                       .as_posix())
    with open(path, 'wt') as f:
        f.write(sout)

    return sin


class SneechenatorTest(snch.Sneechenator):
    @staticmethod
    def searchSquares(squares):
        """ No matches because no remote index """
        return {s:tuple() for s in squares}


class TestFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if temp_path_aug.exists():  # in case someone else forgot to clean up after themselves
            temp_path.rmtree()

        temp_path_aug.mkdir()
        rp = temp_path / 'sneechenator'
        cls.wrangler = snch.SneechWrangler(rp)
        path_index = cls.wrangler.new_index('uri.interlex.org')
        cls.sins = {}
        for p in (sfy, sft):
            sin = fix_file(p)
            cls.sins[p] = sin

    @classmethod
    def tearDownClass(cls):
        temp_path_aug.rmtree()
        for p, sin in cls.sins.items():
            with open(p, 'wt') as f:
                f.write(sin)

    def test_write(self):
        tt = self.wrangler.dir_process / 'test-target'
        tt.mkdir()
        snchf = snch.SnchFile.fromYaml(sfy)
        tf = tt / 'sneeeeeeeeeeeeeeeeeeeeeeeeeech.ttl'
        g = snchf.writeTtl(tf)
        g.debug()


class TestWrangler(unittest.TestCase):
    def setUp(self):
        if temp_path_aug.exists():  # in case someone else forgot to clean up after themselves
            temp_path.rmtree()

        temp_path_aug.mkdir()

    def tearDown(self):
        temp_path_aug.rmtree()

    def test_new_index(self):
        rp = temp_path / 'sneechenator'
        wrangler = snch.SneechWrangler(rp)
        path_index = wrangler.new_index('uri.interlex.org')
        assert path_index.exists(), 'wat'
        g = OntGraph(path=path_index).parse()
        try:
            next(g[:rdf.type:snch.snchn.IndexGraph])
        except StopIteration:
            assert False, g.debug()


class TestSneechenator(unittest.TestCase):
    _test_class = SneechenatorTest

    @classmethod
    def setUpClass(cls):
        if temp_path_aug.exists():  # in case someone else forgot to clean up after themselves
            temp_path.rmtree()

        temp_path_aug.mkdir()
        rp = temp_path / 'sneechenator'
        cls.wrangler = snch.SneechWrangler(rp)
        path_index = cls.wrangler.new_index(cls._test_class.referenceIndex)
        cls.sins = {}
        for p in (sfy, sft):
            sin = fix_file(p)
            cls.sins[p] = sin

    @classmethod
    def tearDownClass(cls):
        temp_path_aug.rmtree()
        for p, sin in cls.sins.items():
            with open(p, 'wt') as f:
                f.write(sin)


    def test_yaml(self):
        snchr = self._test_class(path_wrangler=self.wrangler.rp_sneech)
        snchf = snch.SnchFile.fromYaml(sfy)
        of = self.wrangler.dir_process / 'SEEEEEEEEEEEEEEEEEEEEEEEEEECH!'
        a = snchf.COMMENCE(snchr, path_out=of)
        b = snchr.COMMENCE(sneech_file=snchf, path_out=of)

    def test_ttl(self):
        snchr = self._test_class(path_wrangler=self.wrangler.rp_sneech)
        snchf = snch.SnchFile.fromTtl(sft)
        of = self.wrangler.dir_process / 'SEEEEEEEEEEEEEEEEEEEEEEEEEECH!'
        a = snchf.COMMENCE(snchr, path_out=of)
        b = snchr.COMMENCE(sneech_file=snchf, path_out=of)


@pytest.mark.skipif('CI' in os.environ, reason='alt mapped endpoint not available in prod')
class TestInterLex(TestSneechenator):
    _test_class = snch.InterLexSneechenator

    def test_yaml(self):
        snchr = self._test_class(path_wrangler=self.wrangler.rp_sneech)
        snchf = snch.SnchFile.fromYaml(sfy)
        of = self.wrangler.dir_process / 'SEEEEEEEEEEEEEEEEEEEEEEEEEECH!'
        a = snchf.COMMENCE(snchr, path_out=of)
        b = snchr.COMMENCE(sneech_file=snchf, path_out=of)

    def test_ttl(self):
        snchr = self._test_class(path_wrangler=self.wrangler.rp_sneech)
        snchf = snch.SnchFile.fromTtl(sft)
        of = self.wrangler.dir_process / 'SEEEEEEEEEEEEEEEEEEEEEEEEEECH!'
        a = snchf.COMMENCE(snchr, path_out=of)
        b = snchr.COMMENCE(sneech_file=snchf, path_out=of)
