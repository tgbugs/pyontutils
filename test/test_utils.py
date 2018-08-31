import unittest
from pyontutils.utils import injective_dict


class TestInjectiveDict(unittest.TestCase):
    def setUp(self):
        self.test_funcs = (
            lambda d: injective_dict(d),
            lambda d: injective_dict(**d),
        )
    def test_positive(self):
        test_dicts = (
            {'a':'a'},
            {'b':'b'},
            {'a':'a', 'b':'b'},
        )

        for ok in test_dicts:
            for func in self.test_funcs:
                i = func(ok)

    def test_negative(self):
        test_bads = (
            {'a':'a', 'b':'a'},
        )

        for bad in test_bads:
            for func in self.test_funcs:
                try:
                    i = func(bad)
                    raise AssertionError(f'test for {bad} should have failed')
                except injective_dict.NotInjectiveError:
                    pass

    def test_update(self):
        updates = (
            ({'a':'a'}, {'a':'b'}),
            ({'a':'a'}, {'b':'a'}),
        )

        for dict_sequence in updates:
            i = injective_dict()
            try:
                for d in dict_sequence:
                    for k, v in d.items():
                        i[k] = v
                else:
                    raise AssertionError(f'test for {bad} should have failed')
            except injective_dict.NotInjectiveError:
                pass
