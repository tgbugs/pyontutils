import json
import unittest
from pathlib import Path
import yaml
from pyontutils.ontload import identity_json


class TestIdentityJson(unittest.TestCase):

    # TODO stability tests with values of known hash

    def test_yamls_sl(self):
        return self.test_yamls(sl=True)

    def test_yamls(self, sl=False):
        wd = Path(__file__).parent.parent.resolve()
        test_yamls = (*wd.rglob('*.yaml'), *wd.rglob('*.yml'))
        assert test_yamls, test_yamls

        for sp in test_yamls:
            p = Path(sp)
            with open(p, 'rt') as f:
                y = yaml.safe_load(f)
            iy = identity_json(y, sort_lists=sl)
            j = json.loads(json.dumps(y))
            ij = identity_json(j, sort_lists=sl)
            assert iy == ij, 'local determinism failure'
