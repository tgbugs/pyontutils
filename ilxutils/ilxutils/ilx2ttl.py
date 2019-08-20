from collections import defaultdict
from pathlib import Path as p
import rdflib
from rdflib import *
from ilxutils.tools import open_pickle, create_pickle
from ilxutils.interlex_sql import IlxSql
import pickle
import os
from typing import *


class rdfGraph(Graph):
    ''' Adds needed functions to rdflib.Graph '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Need bnodes to be saved to keep them as an entity
        self.axiom_triple_2_bnode = {} # (triple): BNode

    def add_annotation(self,
                       subj: URIRef,
                       pred: URIRef,
                       obj: Union[Literal, URIRef],
                       a_p: URIRef,
                       a_o: Union[Literal, URIRef],) -> BNode:
        """ Adds annotation to rdflib graph.

            The annotation axiom will filled in if this is a new annotation for the triple.

            Args:
                subj: Entity subject to be annotated
                pref: Entities Predicate Anchor to be annotated
                obj: Entities Object Anchor to be annotated
                a_p: Annotation predicate
                a_o: Annotation object

            Returns:
                A BNode which is an address to the location in the RDF graph that is
                storing the annotation information.

            Axiom Form Example:
                [ a owl:Axiom ;
                    owl:annotatedSource ILX:id  ;
                    owl:annotatedProperty ilxtr:hasWikiDataId ;
                    owl:annotatedTarget wdt:something ;
                    rdfs:label "ILX label" ;
                    skos:altLabel "wikidata label" ] .
        """
        bnode = self.axiom_triple_2_bnode.get( (subj, pred, obj) )
        # If axiom is not created yet, make one
        if not bnode:
            a_s = BNode()
            self.axiom_triple_2_bnode[(subj, pred, obj)]: BNode = a_s
            self.add( (a_s, RDF.type, OWL.Axiom) )
            self.add( (a_s, OWL.annotatedSource, subj) )
            self.add( (a_s, OWL.annotatedProperty, pred) )
            self.add( (a_s, OWL.annotatedTarget, obj) )
        # Append to existing axiom
        else:
            a_s = bnode
        self.add( (a_s, a_p, a_o) )
        return a_s # In case you have more triples to add

graph = rdfGraph()

prefixes = {
    'hasRole': 'http://purl.obolibrary.org/obo/RO_0000087',
    'inheresIn': 'http://purl.obolibrary.org/obo/RO_0000052',
    'bearerOf': 'http://purl.obolibrary.org/obo/RO_0000053',
    'participatesIn': 'http://purl.obolibrary.org/obo/RO_0000056',
    'hasParticipant': 'http://purl.obolibrary.org/obo/RO_0000057',
    'adjacentTo': 'http://purl.obolibrary.org/obo/RO_0002220',
    'derivesFrom': 'http://purl.obolibrary.org/obo/RO_0001000',
    'derivesInto': 'http://purl.obolibrary.org/obo/RO_0001001',
    'agentIn': 'http://purl.obolibrary.org/obo/RO_0002217',
    'hasAgent': 'http://purl.obolibrary.org/obo/RO_0002218',
    'containedIn': 'http://purl.obolibrary.org/obo/RO_0001018',
    'contains': 'http://purl.obolibrary.org/obo/RO_0001019',
    'locatedIn': 'http://purl.obolibrary.org/obo/RO_0001025',
    'locationOf': 'http://purl.obolibrary.org/obo/RO_0001015',
    'toward': 'http://purl.obolibrary.org/obo/RO_0002503',
    'replacedBy': 'http://purl.obolibrary.org/obo/IAO_0100001',
    'hasCurStatus': 'http://purl.obolibrary.org/obo/IAO_0000114',
    'definition': 'http://purl.obolibrary.org/obo/IAO_0000115',
    'editorNote': 'http://purl.obolibrary.org/obo/IAO_0000116',
    'termEditor': 'http://purl.obolibrary.org/obo/IAO_0000117',
    'altTerm': 'http://purl.obolibrary.org/obo/IAO_0000118',
    'defSource': 'http://purl.obolibrary.org/obo/IAO_0000119',
    'termsMerged': 'http://purl.obolibrary.org/obo/IAO_0000227',
    'obsReason': 'http://purl.obolibrary.org/obo/IAO_0000231',
    'curatorNote': 'http://purl.obolibrary.org/obo/IAO_0000232',
    'importedFrom': 'http://purl.obolibrary.org/obo/IAO_0000412',
    'partOf': 'http://purl.obolibrary.org/obo/BFO_0000050',
    'hasPart': 'http://purl.obolibrary.org/obo/BFO_0000051',
    'ILX': 'http://uri.interlex.org/base/ilx_',
    'ilx': 'http://uri.interlex.org/base/',
    'ilxr': 'http://uri.interlex.org/base/readable/',
    'ilxtr': 'http://uri.interlex.org/tgbugs/uris/readable/',
    'fobo': 'http://uri.interlex.org/fakeobo/uris/obo/',
    'PROTEGE': 'http://protege.stanford.edu/plugins/owl/protege#',
    'UBERON': 'http://purl.obolibrary.org/obo/UBERON_',
    'ILXREPLACE': 'http://ILXREPLACE.org/',
    'FIXME': 'http://FIXME.org/',
    'NIFTTL': 'http://ontology.neuinfo.org/NIF/ttl/',
    'NIFRET': 'http://ontology.neuinfo.org/NIF/Retired/NIF-Retired.owl#',
    'NLXWIKI': 'http://neurolex.org/wiki/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'nsu': 'http://www.FIXME.org/nsupper#',
    'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'ro': 'http://www.obofoundry.org/ro/ro.owl#',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'prov': 'http://www.w3.org/ns/prov#',
    'NIFRID': 'http://uri.neuinfo.org/nif/nifstd/readable/',
}

for prefix, ns in prefixes.items():
    graph.bind(prefix, ns)

ilx_uri_base = 'http://uri.interlex.org/base'
in_sanity_check = {}

DEFINITION = Namespace('http://purl.obolibrary.org/obo/IAO_0000115')
ILXTR = Namespace('http://uri.interlex.org/tgbugs/uris/readable/')
NIFRID = Namespace('http://uri.neuinfo.org/nif/nifstd/readable/')

terms = open_pickle(p.home()/'Dropbox/interlex_backups/ilx_db_terms_backup.pickle')
for row in terms.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    ilx_uri = URIRef(ilx_uri)
    in_sanity_check[ilx_uri] = True

    if row.type in ['term', 'cde', 'fde', 'pde']:
        graph.add((ilx_uri, RDF.type, OWL.Class))
    elif row.type == 'annotation':
        graph.add((ilx_uri, RDF.type, OWL.AnnotationProperty))
    elif row.type == 'relationship':
        graph.add((ilx_uri, RDF.type, OWL.ObjectProperty))
    else:
        graph.add((ilx_uri, RDF.type, OWL.Lost))
        print('We have an no type entity!', row.ilx)

    graph.add((ilx_uri, RDFS.label, Literal(row.label)))
    graph.add((ilx_uri, URIRef(DEFINITION), Literal(row.definition)))
del terms
print('=== Class-AnnotationProperty-ObjectProperty triples complete ===')


ilx2ex = defaultdict(list)
ex = open_pickle(p.home()/'Dropbox/interlex_backups/ilx_db_ex_backup.pickle')
for row in ex.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    ilx_uri = URIRef(ilx_uri)
    if not in_sanity_check.get(ilx_uri):
        print('ex', ilx_uri)
    graph.add( (ilx_uri, ILXTR.existingId, URIRef(row.iri)) )
    ilx2ex[row.ilx].append(row.iri)
del ex
print('=== existingId triples complete ===')


synonyms = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_synonyms_backup.pickle')
for row in synonyms.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    ilx_uri = URIRef(ilx_uri)
    if not in_sanity_check.get(ilx_uri):
        print('synonyms', ilx_uri)
    graph.add( (ilx_uri, NIFRID.synonym, Literal(row.literal)) )
del synonyms
print('=== synonym triples complete ===')


superclasses = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_superclasses_backup.pickle')
for row in superclasses.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.term_ilx])
    ilx_uri = URIRef(ilx_uri)
    if not in_sanity_check.get(ilx_uri):
        print('superclasses', ilx_uri)
    for existing_id in ilx2ex[row.term_ilx]:
        id_ = URIRef(f'http://uri.interlex.org/base/{existing_id}')
        graph.add( (ilx_uri, RDFS.subClassOf, id_) )
del superclasses
print('=== superclass triples complete ===')

### Data is both huge and not useful
annos = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_annos_backup.pickle')
for row in annos.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.term_ilx])
    ilx_uri = URIRef(ilx_uri)
    annotation_ilx_uri = '/'.join([ilx_uri_base, row.annotation_type_ilx])
    if not in_sanity_check.get(ilx_uri):
        print('annotations', ilx_uri)
    prefix = ''.join([w.capitalize() for w in row.annotation_type_label.split()])
    graph.bind(prefix, annotation_ilx_uri)
    annotation_ilx_uri = URIRef(annotation_ilx_uri)
    # TODO: check if row.value is a Literal or a URIRef
    graph.add_annotation(ilx_uri, RDF.type, OWL.Class, annotation_ilx_uri, Literal(row.value))
    # AnnotationProperty was defined in Cllas triples
    graph.add( (ilx_uri, annotation_ilx_uri, Literal(row.value)) )
del annos
print('=== annotation axiom triples complete ===')

relationships = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_relationships_backup.pickle')
for row in relationships.itertuples():

    prefix = ''.join([w.capitalize() for w in row.relationship_label.split()])
    relationship_ilx_uri = '/'.join([ilx_uri_base, row.relationship_ilx])

    graph.bind(prefix, relationship_ilx_uri)

    relationship_ilx_uri = URIRef(relationship_ilx_uri)

    term1_ilx_uri = '/'.join([ilx_uri_base, row.term1_ilx])
    term1_ilx_uri = URIRef(term1_ilx_uri)
    if not in_sanity_check.get(term1_ilx_uri): print('relationships', term1_ilx_uri)

    term2_ilx_uri = '/'.join([ilx_uri_base, row.term2_ilx])
    term2_ilx_uri = URIRef(term2_ilx_uri)
    if not in_sanity_check.get(term2_ilx_uri): print('relationships', term2_ilx_uri)

    graph.add( (term1_ilx_uri, relationship_ilx_uri, term2_ilx_uri) )
    graph.add( (term2_ilx_uri, relationship_ilx_uri, term1_ilx_uri) )
print('=== relationship triples complete ===')

graph.serialize(destination=str(p.home()/'Dropbox/interlex_backups/InterLex.ttl'), format='turtle')
graph.serialize(destination=str(p.home()/'Dropbox/interlex_backups/SciGraph/SciGraph-core/src/test/resources/ontologies/'), format='turtle')
create_pickle(graph, p.home()/'Dropbox/interlex_backups/InterLex.graph.pickle')
