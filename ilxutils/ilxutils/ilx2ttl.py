from collections import defaultdict
from pathlib import Path as p
import rdflib
from ilxutils.tools import open_pickle, create_pickle
from ilxutils.interlex_sql import IlxSql
from ilxutils.simple_rdflib import SimpleGraph, RDF, OWL, RDFS, BNode, Literal, URIRef, Namespace
import pickle
import os
g = SimpleGraph()


ilx_uri_base = 'http://uri.interlex.org/base'
in_sanity_check = {}


terms = open_pickle(p.home()/'Dropbox/interlex_backups/ilx_db_terms_backup.pickle')
for row in terms.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    in_sanity_check[ilx_uri] = True

    if row.type in ['term', 'cde', 'fde', 'pde']:
        g.add_triple(ilx_uri, RDF.type, OWL.Class)
    elif row.type == 'annotation':
        pass # g.add_triple(ilx_uri, RDF.type, OWL.AnnotationProperty)
    elif row.type == 'relationship':
        pass # g.add_triple(ilx_uri, RDF.type, OWL.ObjectProperty)
    else:
        g.add_triple(ilx_uri, RDF.type, OWL.Lost)
        print('We have an no type entity!', row.ilx)

    g.add_triple(ilx_uri, RDFS.label, row.label)
    g.add_triple(ilx_uri, 'definition:', row.definition)
del terms
print('=== Class-AnnotationProperty-ObjectProperty triples complete ===')


# ilx2ex = defaultdict(list)
# ex = open_pickle(p.home()/'Dropbox/interlex_backups/ilx_db_ex_backup.pickle')
# for row in ex.itertuples():
#     ilx_uri = '/'.join([ilx_uri_base, row.ilx])
#     if not in_sanity_check.get(ilx_uri):
#         print('ex', ilx_uri)
#     g.add_triple(ilx_uri, 'ilxtr:existingId', row.iri)
#     ilx2ex[row.ilx].append(row.iri)
# del ex
# print('=== existingId triples complete ===')
#
#
# synonyms = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_synonyms_backup.pickle')
# for row in synonyms.itertuples():
#     ilx_uri = '/'.join([ilx_uri_base, row.ilx])
#     if not in_sanity_check.get(ilx_uri):
#         print('synonyms', ilx_uri)
#     g.add_triple(ilx_uri, 'NIFRID:synonym', row.literal)
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
#         g.add_triple(ilx_uri, 'rdfs:subClassOf', existing_id)
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
#     g.add_triple(ilx_uri, pred, row.value)
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
#     g.add_triple(term1_ilx_uri, pred, term2_ilx_uri)
#     g.add_triple(term2_ilx_uri, pred, term1_ilx_uri)
#
#     # TODO: create axiom for relationship?
# print('=== relationship triples complete ===')


# g.serialize(destination=str(p.home()/'Dropbox/interlex_backups/InterLex.ttl'), format='turtle')
with open(p.home()/'Dropbox/interlex_backups/InterLex.Graph.pickle', 'wb') as outfile:
    pickle.dump(g.g, outfile)
