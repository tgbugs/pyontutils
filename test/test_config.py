import unittest
from pyontutils.config import devconfig

class TestConfig(unittest.TestCase):
    def test_set(self):
        v1 = devconfig.git_local_base
        v2 = '/tmp/not-a-thing'
        devconfig.git_local_base = v2
        v3 = devconfig.git_local_base
        devconfig.git_local_base = v1
        assert v1 != v2
        assert v1 != v3
        assert v2 == v3
        assert v1 == devconfig.git_local_base

