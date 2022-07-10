import rdflib
from pyontutils.core import OntResIri, OntResPath, OntGraph
from pyontutils.namespaces import rdf, rdfs, owl
from pyontutils.config import auth


def main():
    olr = auth.get_path('ontology-local-repo')
    ori = OntResIri('http://purl.obolibrary.org/obo/doid.owl')
    orp = OntResPath(olr / 'ttl/external/doid.owl')
    ort = ori
    g = ori.graph
    query = """
    SELECT DISTINCT ?s ?o ?l
    WHERE {
        ?s a owl:Class .
        ?s rdfs:subClassOf* <http://purl.obolibrary.org/obo/DOID_4> .
        ?s rdfs:subClassOf ?o .
        ?s rdfs:label ?l .
    }"""
    res = list(g.query(query))
    filt = [r for r in res if not isinstance(r[1], rdflib.BNode)]
    spath = 'ttl/generated/doidslim.ttl'
    go = OntGraph(path=olr / spath)
    # TODO prov record like the one we have for chebi
    go.bind('DOID', 'http://purl.obolibrary.org/obo/DOID_')
    s = rdflib.URIRef('http://ontology.neuinfo.org/NIF/' + spath)
    go.populate_from_triples(
        ((s, p, o) for p, o in
         ((rdf.type, owl.Ontology),
          (rdfs.label, rdflib.Literal("NIF DOID slim")),)))
    ds = rdflib.URIRef('http://purl.obolibrary.org/obo/DOID_4')
    go.add((ds, rdf.type, owl.Class))
    go.add((ds, rdfs.label, rdflib.Literal('disease')))
    go.populate_from_triples(
        (t for s, o, l in filt for t in
         ((s, rdf.type, owl.Class),
          (s, rdfs.subClassOf, o),
          (s, rdfs.label, l))))
    go.write()


if __name__ == '__main__':
    main()
