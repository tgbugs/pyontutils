import json
import unittest
from pathlib import Path
import yaml
from pyontutils.ontload import identity_json


class TestIdentityJson(unittest.TestCase):

    # TODO stability tests with values of known hash

    def test_yamls(self):
        test_yamls = list(Path(__file__).parent.resolve().rglob('*.yaml'))
        assert test_yamls, test_yamls

        for sp in test_yamls:
            p = Path(sp)
            with open(p, 'rt') as f:
                y = yaml.safe_load(f)
            iy = identity_json(y)
            j = json.loads(json.dumps(y))
            ij = identity_json(j)
            assert iy == ij, 'local determinism failure'
