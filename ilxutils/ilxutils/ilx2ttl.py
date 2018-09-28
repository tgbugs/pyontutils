from collections import defaultdict
from pathlib import Path as p
import rdflib
from ilxutils.tools import open_pickle, create_pickle
from ilxutils.interlex_sql import IlxSql
from ilxutils.simple_rdflib import SimpleGraph, RDF, OWL, RDFS, BNode, Literal, URIRef, Namespace
import os
g = SimpleGraph()


ilx_uri_base = 'http://uri.interlex.org/base'
sanity_check = {}


terms = open_pickle(p.home()/'Dropbox/interlex_backups/ilx_db_terms_backup.pickle')
for row in terms.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    sanity_check[ilx_uri] = True

    if row.type == 'term'
        g.add_triple(ilx_uri, RDF.type, OWL.Class)
    elif row.type == 'annotation':
        g.add_triple(ilx_uri, RDF.type, OWL.AnnotationProperty)
    elif row.type == 'relationship':
        g.add_triple(ilx_uri, RDF.type, OWL.ObjectProperty)
    else:
        g.add_triple(ilx_uri, RDF.type, OWL.Lost) # TODO: should be empty but check this.

    g.add_triple(ilx_uri, RDFS.label, row.label)
    g.add_triple(ilx_uri, 'definition:', row.definition)
del terms


ilx2ex = defaultdict(list)
ex = open_pickle(p.home()/'Dropbox/interlex_backups/ilx_db_ex_backup.pickle')
for row in ex.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    if not sanity_check.get(ilx_uri):
        print('ex', ilx_uri)
    g.add_triple(ilx_uri, 'ilxtr:existingId', row.iri)
    ilx2ex[row.ilx].append(row.iri)
del ex


synonyms = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_synonyms_backup.pickle')
for row in synonyms.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    if not sanity_check.get(ilx_uri):
        print('synonyms', ilx_uri)
    g.add_triple(ilx_uri, 'NIFRID:synonym', row.literal)
del synonyms


superclasses = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_superclasses_backup.pickle')
for row in superclasses.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.ilx])
    if not sanity_check.get(ilx_uri):
        print('superclasses', ilx_uri)
    for existing_id in ilx2ex[row.ilx]:
        g.add_triple(ilx_uri, 'rdfs:subClassOf', existing_id)
del superclasses


annos = open_pickle(p.home() / 'Dropbox/interlex_backups/ilx_db_annos_backup.pickle')
for row in annos.itertuples():
    ilx_uri = '/'.join([ilx_uri_base, row.term_ilx])
    if not sanity_check.get(ilx_uri):
        print('annotations', ilx_uri)
    annotation_label = row.annotation_label.strip().replace(' ', '_')
    g.add_annotation(ilx_uri, RDF.type, OWL.Class, 'ilxtr:'+annotation_label, row.value)
del annos


g.g.serialize(destination=str(p.home()/'Dropbox/ilx-test.ttl'), format='turtle')
