import unittest
from pyontutils import clifun as clif


class TestClifun(unittest.TestCase):

    def test_double_options(self):

        class Options(clif.Options):
            pass

        o1 = Options({'a': True}, {})
        o2 = Options({'b': True}, {})

        assert not hasattr(o2, 'a')
        assert not hasattr(o1, 'b')
