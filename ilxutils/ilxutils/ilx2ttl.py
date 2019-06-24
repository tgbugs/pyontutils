from collections import defaultdict
from pathlib import Path as p
import rdflib
from rdflib import *
from ilxutils.tools import open_pickle, create_pickle
from ilxutils.interlex_sql import IlxSql
# from ilxutils.RdflibWrapper import RdflibWrapper, RDF, OWL, RDFS, BNode, Literal, URIRef, Namespace, ilxtr, DEFINITION, NIFRID
import pickle
import os
# graph = RdflibWrapper()
graph = Graph()

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
}

for prefix, ns in prefixes.items():
    graph.bind(prefix, ns)

ilx_uri_base = 'http://uri.interlex.org/base'
in_sanity_check = {}

DEFINITION = Namespace('http://purl.obolibrary.org/obo/IAO_0000115')
ILXTR = Namespace('http://uri.interlex.org/tgbugs/uris/readable/')

terms = open_pickle(p.home()/'Dropbox/interlex_backups/ilx_db_terms_backup.pickle')
for row in terms.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    ilx_uri = URIRef(ilx_uri)
    in_sanity_check[ilx_uri] = True

    if row.type in ['term', 'cde', 'fde', 'pde']:
        graph.add((ilx_uri, RDF.type, OWL.Class))
    elif row.type == 'annotation':
        pass # g.add(ilx_uri, RDF.type, OWL.AnnotationProperty)
    elif row.type == 'relationship':
        pass # g.add(ilx_uri, RDF.type, OWL.ObjectProperty)
    else:
        graph.add((ilx_uri, RDF.type, OWL.Lost))
        print('We have an no type entity!', row.ilx)

    graph.add((ilx_uri, RDFS.label, Literal(row.label)))
    # graph.add((ilx_uri, URIRef(DEFINITION), Literal(row.definition)))
del terms
print('=== Class-AnnotationProperty-ObjectProperty triples complete ===')


ilx2ex = defaultdict(list)
ex = open_pickle(p.home()/'Dropbox/interlex_backups/ilx_db_ex_backup.pickle')
for row in ex.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    ilx_uri = URIRef(ilx_uri)
    if not in_sanity_check.get(ilx_uri):
        print('ex', ilx_uri)
    graph.add((ilx_uri, ILXTR.existingId, URIRef(row.iri)))
    ilx2ex[row.ilx].append(row.iri)
del ex
print('=== existingId triples complete ===')


# synonyms = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_synonyms_backup.pickle')
# for row in synonyms.itertuples():
#     ilx_uri = '/'.join([ilx_uri_base, row.ilx])
#     if not in_sanity_check.get(ilx_uri):
#         print('synonyms', ilx_uri)
#     g.add(ilx_uri, NIFRID.synonym, row.literal)
# del synonyms
# print('=== synonym triples complete ===')
#
#
# superclasses = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_superclasses_backup.pickle')
# for row in superclasses.itertuples():
#     ilx_uri = '/'.join([ilx_uri_base, row.term_ilx])
#     if not in_sanity_check.get(ilx_uri):
#         print('superclasses', ilx_uri)
#     for existing_id in ilx2ex[row.term_ilx]:
#         g.add(ilx_uri, RDFS.subClassOf, existing_id)
# del superclasses
# print('=== superclass triples complete ===')

### Data is both huge and not useful
# annos = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_annos_backup.pickle')
# for row in annos.itertuples():
#     ilx_uri = '/'.join([ilx_uri_base, row.term_ilx])
#     annotation_ilx_uri = '/'.join([ilx_uri_base, row.annotation_ilx])
#     if not in_sanity_check.get(ilx_uri):
#         print('annotations', ilx_uri)
#     prefix = ''.join([w.capitalize() for w in row.annotation_label.split()])
#     pred = prefix + ':'
#     g.add_namespace(prefix, annotation_ilx_uri)
#     g.add_annotation(ilx_uri, RDF.type, OWL.Class, pred, row.value)
#     g.add(ilx_uri, pred, row.value)
# del annos
# print('=== annotation axiom triples complete ===')

### Data not useful
# relationships = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_relationships_backup.pickle')
# for row in relationships.itertuples():
#
#     prefix = ''.join([w.capitalize() for w in row.relationship_label.split()])
#     pred = prefix + ':'
#     relationship_ilx_uri = '/'.join([ilx_uri_base, row.relationship_ilx])
#     g.add_namespace(prefix, relationship_ilx_uri)
#
#     term1_ilx_uri = '/'.join([ilx_uri_base, row.term1_ilx])
#     if not in_sanity_check.get(term1_ilx_uri): print('relationships', term1_ilx_uri)
#
#     term2_ilx_uri = '/'.join([ilx_uri_base, row.term2_ilx])
#     if not in_sanity_check.get(term2_ilx_uri): print('relationships', term2_ilx_uri)
#
#     g.add(term1_ilx_uri, pred, term2_ilx_uri)
#     g.add(term2_ilx_uri, pred, term1_ilx_uri)
#
#     # TODO: create axiom for relationship?
# print('=== relationship triples complete ===')

graph.serialize(destination=str(p.home()/'Dropbox/interlex_backups/InterLex.ttl'), format='turtle')
# graph.picklize(p.home()/'Dropbox/interlex_backups/InterLex.Graph.pickle')
