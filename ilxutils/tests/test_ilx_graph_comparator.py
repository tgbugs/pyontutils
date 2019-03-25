import rdflib
from IPython import embed
from ilxutils.ilx_graph_comparator import IlxGraphComparator


tdata = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix umls: <http://bioportal.bioontology.org/ontologies/umls/> .
@prefix mesh: <http://purl.bioontology.org/ontology/MESH/> .

mesh:1 a owl:Class ;
    skos:prefLabel "COMPENSATION, FlOw"@en .

mesh:2 a owl:Class ;
    skos:label "flow/mech type"^^xsd:string .

mesh:0001063 a owl:Class ;
    umls:label "sincomb"^^xsd:string .

mesh:4 a owl:Class ;
    umls:label "Flow Compensations"^^xsd:string .

mesh:5 a owl:Class ;
    umls:label "troy"^^xsd:string .
"""
tgraph = rdflib.Graph()
tgraph.parse(data=tdata, format='n3')


class TestILXGraphCompatator:

    def setup(self):
        self.ilxgc = IlxGraphComparator(rpath='tiny_ilx_db_ex2row.json', tpath=tgraph)

    def teardown(self):
        pass

    def test_get_fragment_id(self):
        assert self.ilxgc.get_fragment_id('http://scicrunch.org/123') == '123'
        assert self.ilxgc.get_fragment_id('http://scicrunch.org/ex=123') == '123'
        assert self.ilxgc.get_fragment_id('http://scicrunch.org/ex#123') == '123'
        assert self.ilxgc.get_fragment_id('http://scicrunch.org/ex_123') == '123'

    def test_pop_bad_elements_in_row(self):
        row = {
            'ns1:label': 'exlabel',
            'ns1:BadSuffix' : 'misc_data',
        }
        assert self.ilxgc.pop_bad_elements_in_row(row) == {'ns1:label': 'exlabel'}


def main():
    ilxgc = IlxGraphComparator(rpath='tiny_ilx_db_ex2row.json', tpath=tgraph)
    embed()

if __name__ == '__main__':
    main()
