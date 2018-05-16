""" Simple Python script to query "http://sparql.bioontology.org/sparql/"
    This script uses the SPARQLWrapper Python lib. Download and install from:
        http://sparql-wrapper.sourceforge.net/
"""

from SPARQLWrapper import SPARQLWrapper, JSON, XML, N3, RDF
import pdb
import json

if __name__ == "__main__":
    sparql_service = "http://sparql.bioontology.org/sparql/"
    sparql_service = "http://sparql.hegroup.org/sparql/"
    #To get your API key register at http://bioportal.bioontology.org/accounts/new
    api_key = "48101c4e-e0ae-4bf4-b281-b75bd6ffc12e"

    #Some sample query.
    query_string = """
PREFIX omv: <http://omv.ontoware.org/2005/05/ontology#>
SELECT ?ont ?name ?acr
WHERE { ?ont a omv:Ontology;
             omv:acronym ?acr;
             omv:name ?name .
}
"""
    query_string = """
PREFIX omv: <http://omv.ontoware.org/2005/05/ontology#>
prefix PATO: <http://purl.obolibrary.org/obo/PATO_>
prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
prefix skos: <http://www.w3.org/2004/02/skos/core#>
prefix xml: <http://www.w3.org/XML/1998/namespace>
prefix xsd: <http://www.w3.org/2001/XMLSchema#>
prefix NCBITaxon: <http://purl.obolibrary.org/obo/NCBITaxon_>
SELECT ?s ?p ?o
FROM <http://purl.obolibrary.org/obo/UBERON_0034894>
WHERE {
    ?s ?p ?o.
}
"""
    sparql = SPARQLWrapper(sparql_service)
    sparql.addCustomParameter("apikey",api_key)
    sparql.setQuery(query_string)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    #print(results)
    json.dump(results, open('../bioportal_query.json', 'w'), indent=4)
    #for result in results["results"]["bindings"]:
    #   print (result["ont"]["value"], result["name"]["value"], result["acr"]["value"])
