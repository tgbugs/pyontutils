import unittest
from .common import skipif_no_net


@skipif_no_net
class TestWrite(unittest.TestCase):
    def test_load_huang(self):
        from neurondm import Config
        # FIXME placeholder for loading and roundtripping
        # neurons with other neurons as asserted equivalent
        # or disjoint classes
        config = Config('huang-2017')
        config.load_existing()
