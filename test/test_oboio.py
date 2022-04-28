import os
import shutil
import unittest
import pytest
from pyontutils import obo_io as oio
from .common import temp_path, skipif_no_net

obo_test_string = """format-version: 1.2
ontology: uberon/core
subsetdef: cumbo "CUMBO"
treat-xrefs-as-has-subclass: EV
import: http://purl.obolibrary.org/obo/uberon/chebi_import.owl
treat-xrefs-as-reverse-genus-differentia: TGMA part_of NCBITaxon:44484

[Term]
id: UBERON:0000003
xref: SCTID:272650008
relationship: in_lateral_side_of UBERON:0000033 {gci_relation="part_of", gci_filler="NCBITaxon:7776", notes="hagfish have median nostril"} ! head
!relationship: in_lateral_side_of UBERON:0000034 {gci_filler="NCBITaxon:7776", gci_relation="part_of", notes="hagfish have median nostril"}  ! can't use this due to robot non-determinism
comment: robot does reorder the gci_ so that relation always comes before filler
property_value: external_definition "One of paired external openings of the nasal chamber.[AAO]" xsd:string {date_retrieved="2012-06-20", external_class="AAO:0000311", ontology="AAO", source="AAO:EJS"}
replaced_by: GO:0045202
consider: FMA:67408

[Term]
id: UBERON:0000033
name: head
comment: needed to prevent robot from throwing a null pointer on the relationship axiom above

[Term]
id: UBERON:0000034

[Typedef]
id: in_lateral_side_of
property_value: seeAlso FMA:86003
name: in_lateral_side_of
comment: id needed to prevent robot from throwing a null pointer on the relationship axiom above
comment: apparently also have to have name strangely enough and robot doesn't roundtrip random comments
is_transitive: true
"""


class TMHelper:
    parse = oio.TVPair._parse_modifiers
    serialize = oio.TVPair._format_trailing_modifiers


class TestOboIo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if temp_path.exists():
            shutil.rmtree(temp_path)

        temp_path.mkdir()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(temp_path)

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
        tv = of.asObo()
        assert len(tv.split(test_tag)) > 2, tv

    def test_property_value_bug(self):
        def _test(string):
            pv = oio.Property_value.parse(string)
            assert pv.value() == string
            tv = oio.TVPair(string)
            assert str(tv) == string
            return pv, tv

        minimal = ('property_value: any " ! " xsd:string')
        pv, tv = _test(minimal)


        darn = ('property_value: external_ontology_notes "see also MA:0002165 !'
                ' lieno-pancreatic vein" xsd:string {external_ontology="MA"}')
        pv, tv = _test(darn)

        ouch = ('property_value: editor_note "TODO -'
                ' this string breaks the parser A:0 ! wat" xsd:string')
        pv, tv = _test(ouch)

        hrm = ('property_value: editor_note "TODO -'
               ' consider relationship to UBERON:0000091 ! bilaminar disc" xsd:string')
        pv, tv = _test(hrm)

    def test_robot(self):
        of1 = oio.OboFile(data=obo_test_string)
        obo1 = of1.asObo(stamp=False)
        obor1 = of1.asObo(stamp=False, version=oio.OBO_VER_ROBOT)

        of2 = oio.OboFile(data=obo1)
        obo2 = of2.asObo(stamp=False)
        # can't test against obor2 because obo1 reordered the trailing qualifiers
        # and since there is seemingly no rational way to predict those, we simply
        # preserve the ordering that we got
        obor2 = of2.asObo(stamp=False, version=oio.OBO_VER_ROBOT)

        of3 = oio.OboFile(data=obor1)
        obo3 = of3.asObo(stamp=False)
        obor3 = of3.asObo(stamp=False, version=oio.OBO_VER_ROBOT)

        print(obo1)
        print(obo2)

        print(obor1)
        print(obor2)

        assert obo1 == obo2 == obo3 != obor1
        assert obor1 == obor3

    @skipif_no_net
    @pytest.mark.skipif(not shutil.which('robot'), reason='robot not installed')
    def test_robot_rt(self):
        of = oio.OboFile(data=obo_test_string)
        obor1 = of.asObo(stamp=False, version=oio.OBO_VER_ROBOT)
        rtp = temp_path / 'robot-test.obo'
        robot_path = temp_path / 'robot-test.test.obo'
        of.write(rtp, stamp=False, version=oio.OBO_VER_ROBOT)
        cmd = f'robot convert -vvv -i {rtp.as_posix()} -o {robot_path.as_posix()}'
        wat = os.system(cmd)
        if wat:
            raise ValueError(wat)

        datas = []
        for path in (rtp, robot_path):
            with open(path, 'rt') as f:
                datas.append(f.read())

        ours, rob = datas
        assert ours == rob
