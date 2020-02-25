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

class TestPythonIdentifier(unittest.TestCase):
    strings = [
        '1<hello>',
        '2(lol)',
        '3…',
        '4a+b',
        '5\x83wat',
        '6i-love-kebab',
        'asdfasdf  a asdf 8'
        'some . hideous, stuff ; is | going & on here'
        'class',  # LOL PYTHON
    ]

    def test_strings(self):
        for string in self.strings:
            pi = clif.python_identifier(string)
            assert pi.isidentifier(), f'oops {pi}'
