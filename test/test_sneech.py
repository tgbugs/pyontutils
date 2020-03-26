import unittest
import pathlib as pl
import ontquery as oq
import augpathlib as aug
from pyontutils import sneechenator as snch
from pyontutils.core import OntGraph
from pyontutils.namespaces import rdf
from .common import temp_path

temp_path_aug = aug.AugmentedPath(temp_path)


class TestFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if temp_path_aug.exists():  # in case someone else forgot to clean up after themselves
            temp_path.rmtree()

        temp_path_aug.mkdir()
        rp = temp_path / 'sneechenator'
        cls.wrangler = snch.SneechWrangler(rp)
        path_index = cls.wrangler.new_index('uri.interlex.org', '/tgbugs/uris/')

    @classmethod
    def tearDownClass(cls):
        temp_path_aug.rmtree()

    def test_write(self):
        tt = self.wrangler.dir_process / 'test-target'
        tt.mkdir()
        snchf = snch.SnchFile.fromYaml(pl.Path(__file__).parent / 'sneech-file.yaml')
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
        path_index = wrangler.new_index('uri.interlex.org', '/tgbugs/uris/')
        assert path_index.exists(), 'wat'
        g = OntGraph(path=path_index).parse()
        try:
            next(g[:rdf.type:snch.snchn.IndexGraph])
        except StopIteration:
            assert False, g.debug()


class TestInterLex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if temp_path_aug.exists():  # in case someone else forgot to clean up after themselves
            temp_path.rmtree()

        temp_path_aug.mkdir()
        rp = temp_path / 'sneechenator'
        cls.wrangler = snch.SneechWrangler(rp)
        path_index = cls.wrangler.new_index('uri.interlex.org', '/tgbugs/uris/')

    @classmethod
    def tearDownClass(cls):
        temp_path_aug.rmtree()

    def test_yaml(self):
        snchr = snch.InterLexSneechenator(path_wrangler=self.wrangler.rp_sneech)
        snchf = snch.SnchFile.fromYaml(pl.Path(__file__).parent / 'sneech-file.yaml')
        of = self.wrangler.dir_process / 'SEEEEEEEEEEEEEEEEEEEEEEEEEECH!'
        a = snchf.COMMENCE(snchr, path_out=of)
        b = snchr.COMMENCE(sneech_file=snchf, path_out=of)

    def test_ttl(self):
        snchr = snch.InterLexSneechenator(path_wrangler=self.wrangler.rp_sneech)
        snchf = snch.SnchFile.fromTtl(pl.Path(__file__).parent / 'sneech-file.ttl')
        of = self.wrangler.dir_process / 'SEEEEEEEEEEEEEEEEEEEEEEEEEECH!'
        a = snchf.COMMENCE(snchr, path_out=of)
        b = snchr.COMMENCE(sneech_file=snchf, path_out=of)
