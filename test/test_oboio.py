import unittest
from pyontutils import obo_io as oio


class TMHelper:
    parse = oio.TVPair._parse_modifiers
    serialize = oio.TVPair._format_trailing_modifiers

class TestOboIo(unittest.TestCase):
    def test_parse_trailing_modifiers(self):
        thm = TMHelper()

        lines = (
            (('relationship: part_of UBERON:0000949 '
              '{source="AAO", source="FMA", source="XAO"} ! endocrine system'),
             (('source', 'AAO'), ('source', 'FMA'), ('source', 'XAO'))),
            ('{oh="look", a="thing!"}', (('oh', 'look'), ('a', 'thing!'))),
            ('some randome values {oh="look", a="thing!"} ! yay!', (('oh', 'look'), ('a', 'thing!'))),
            ('some rando}me values {oh="l{ook", a="t{hing!"} ! yay!', (('oh', 'l{ook'), ('a', 't{hing!'))),
            ('some rando}me values {oh="l{ook", a="t}hing!"} ! yay!', (('oh', 'l{ook'), ('a', 't}hing!'))),
        )

        bads = [(expect, actual) for line, expect in lines
                for _, actual in (thm.parse(line),)
                if actual != expect]

        assert not bads, '\n' + '\n\n'.join(f'{e}\n{a}' for e, a in bads)
