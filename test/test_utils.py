import ast
import unittest
from datetime import datetime, date
from pyontutils import utils
from pyontutils.utils import injective_dict, Async, deferred, listIn, asStr


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


class TestAsync(unittest.TestCase):
    def test_fast(self):
        out = Async()(deferred(lambda a:a)('lol') for _ in range(1000))

    def test_rate(self):
        out = Async(rate=10)(deferred(lambda a:a)('lol') for _ in range(10))

    def test_rate_empty(self):
        out = Async(rate=20)(deferred(lambda a:a)('lol') for _ in range(0))


class TestListIn(unittest.TestCase):
    def test(self):
        assert listIn([1, 2], [1]) == 0
        assert listIn([1, 2], [2]) == 1
        assert listIn([1, 2, 3, 4], [2, 3]) == 1
        assert listIn([2, 2, 3], [2, 3]) == 1
        assert listIn([2, 2, 3, 3], [2, 3]) == 1
        assert listIn(['skip1>', 'skip1>', 'end', 'end'], ['skip1>', 'end']) == 1


class TestAstString(unittest.TestCase):
    def test_docstring(self):
        asdf = asStr(ast.parse("f'''i am a format docstring {_ddconf}'''"),
                    prior=ast.parse("_ddconf='another-string'\n").body,)
        assert ast.literal_eval(asdf) == "i am a format docstring 'another-string'"


class TestDateFormats(unittest.TestCase):
    def test_isoformat(self):
        now = datetime.now()
        n = utils.isoformat(now)
        today = date.today()
        t = utils.isoformat(today)
