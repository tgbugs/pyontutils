import unittest
from pyontutils.config import devconfig

class TestConfig(unittest.TestCase):
    def test_set_git_local_base(self):
        git_local_base_1 = devconfig.git_local_base
        ontology_local_1 = devconfig.ontology_local_repo
        v2 = '/tmp/not-a-thing'
        devconfig.git_local_base = v2
        v3 = devconfig.git_local_base
        maybe_ontology_local_after_change_base = devconfig._maybe_repo
        devconfig.git_local_base = git_local_base_1
        assert ontology_local_1 != maybe_ontology_local_after_change_base
        # we can only check against _maybe_repo because
        # v2 does not exist and thus will not propagate
        assert git_local_base_1 != v2
        assert git_local_base_1 != v3
        assert v2 == v3
        assert git_local_base_1 == devconfig.git_local_base

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
