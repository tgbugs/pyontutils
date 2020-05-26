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

    def test_construct_simple_file(self):
        of = oio.OboFile()
        ids_names = [['123', 'test'],
                     ['234', 'yee'],
                     ['345', 'haw'],
                     ['456', 'oio']]
        terms = [oio.Term(id=i, name=n) for i, n in ids_names]
        of.add(*terms)
        str(of)

    def test_header_treat_xrefs(self):
        of = oio.OboFile()
        test_tag = 'treat-xrefs-as-is_a'
        tags_values = [
            [test_tag, 'TEMP:test1'],
            [test_tag, 'TEMP:test2'],
        ]
        tvpairs = [oio.TVPair(tag=t, value=v) for t, v in tags_values]
        of.header.add(*tvpairs)
        tv = str(of)
        assert len(tv.split(test_tag)) > 2, tv
