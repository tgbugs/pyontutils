import unittest
from pyontutils.config import devconfig

class TestConfig(unittest.TestCase):
    def test_set_git_local_base(self):
        v1 = devconfig.git_local_base
        o1 = devconfig.ontology_local_repo
        v2 = '/tmp/not-a-thing'
        devconfig.git_local_base = v2
        v3 = devconfig.git_local_base
        o2 = devconfig.ontology_local_repo
        devconfig.git_local_base = v1
        assert o1 != o2  # propagate to other values
        assert v1 != v2
        assert v1 != v3
        assert v2 == v3
        assert v1 == devconfig.git_local_base

    def test_set_scigraph_api(self):
        v1 = devconfig.scigraph_api
        v2 = '/tmp/not-a-thing'
        devconfig.scigraph_api = v2
        v3 = devconfig.scigraph_api
        devconfig.scigraph_api = v1
        assert v1 != v2
        assert v1 != v3
        assert v2 == v3
        assert v1 == devconfig.scigraph_api
