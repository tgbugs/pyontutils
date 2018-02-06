#!/usr/bin/env python3.6
"""
    Sync the scicrunch registry to a ttl
    file for loading into scigraph for autocomplete. 
"""

# XXX TODO sanity checks
# alt id mapped to more than one SRC id
# garbage in the alt id field

import os
from datetime import date

import rdflib
from IPython import embed
from sqlalchemy import create_engine, inspect
from pyontutils.core import makePrefixes, createOntology
from pyontutils.utils import mysql_conn_helper

_remap_supers = {
    'Resource':'NIFSTD:nlx_63400',  # FIXME do not want to use : but broken because of defaulting to add : to all scr ids (can fix just not quite yet)
    'Commercial Organization':'NIFSTD:nlx_152342',
    'Organization':'NIFSTD:nlx_152328',
    'University':'NIFSTD:NEMO_0569000',  # UWOTM8

    'Institution':'NIFSTD:birnlex_2085',
    'Institute':'NIFSTD:SIO_000688',
    'Government granting agency':'NIFSTD:birnlex_2431',
}

_field_mapping = {
    'Resource Name':'label',
    'Description':'definition',
    'Abbreviation':'abbrev',
    'Synonyms':'synonyms',
    'Alternate IDs':'alt_ids',
    'Supercategory':'superclass',
    #'Keywords':'keywords'  # don't think we need this
    'MULTI':{'Synonyms':'synonym',
             'Alternate IDs':'alt_id',
             'Abbreviation':'abbrev',
            },
}

_column_to_predicate = {
    'abbrev':'NIFRID:abbrev',
    'alt_id':'oboInOwl:hasDbXref',
    'definition':'definition:',
    #'definition':'skos:definition',
    'id':'rdf:type',
    'label':'rdfs:label',
    'old_id':'oboInOwl:hasDbXref',  # old vs alt id?
    'deprecated':'owl:deprecated',
    'superclass':'rdfs:subClassOf',  # translation required
    'synonym':'NIFRID:synonym',
    'type':'FIXME:type',  # bloody type vs superclass :/ ask james
}

def fixesForResourcesAndColumns(resources, resource_columnes):
    resources.extend(((-100, 'NIFSTD:nlx_63400', 'nlx_63400', 'Resource', 'Curated'),
                      (-101, 'NIFSTD:nlx_152342', 'nlx_152342', 'Organization', 'Curated'),
                      (-102, 'NIFSTD:nlx_152328', 'nlx_152328', 'Organization', 'Curated'),
                      (-103, 'NIFSTD:NEMO_0569000', 'NEMO_0569000', 'Institution', 'Curated'),
                      (-104, 'NIFSTD:birnlex_2431', 'birnlex_2431', 'Institution', 'Curated'),
                      (-105, 'NIFSTD:SIO_000688', 'SIO_000688', 'Institution', 'Curated'),
                      (-106, 'NIFSTD:birnlex_2085', 'birnlex_2085', 'Institution', 'Curated'),
                     ))
    resource_columnes.extend(((-100, 'Resource Name', 'Resource', 1),
                              (-101, 'Resource Name', 'Commercial Organization', 1),
                              (-102, 'Resource Name', 'Organization', 1),
                              (-103, 'Resource Name', 'University', 1),
                              (-104, 'Resource Name', 'Government granting agency', 1),
                              (-105, 'Resource Name', 'Institute', 1),
                              (-106, 'Resource Name', 'Institution', 1),
                              (-101, 'Supercategory', 'NIFSTD:nlx_152328', 1), # TODO extract this more intelligently from remap supers please
                             ))

def make_records(resources, res_cols, field_mapping=_field_mapping, remap_supers=_remap_supers):
    resources = {id:(scrid, oid, type, status) for id, scrid, oid, type, status in resources}
    res_cols_latest = {}
    versions = {}
    for rid, value_name, value, version in res_cols:
        if rid not in versions:
            versions[(rid, value_name)] = version  # XXX WARNING assumption is that for these fields resources will only ever have ONE but there is no gurantee :( argh myslq

        if version >= versions[(rid, value_name)]:
            res_cols_latest[(rid, value_name)] = (rid, value_name, value)

    latest = {}
    for (rid, value_name), version in sorted(versions.items(), key=lambda a: (a[0][0], a[1], a[0][1]))[::-1]:
        if rid not in latest:
            latest[rid] = version
        if version < latest[rid]:
            res_cols_latest.pop((rid, value_name))  # some entries are not present in the latest and so we need to pop them

    res_cols_l = list(res_cols_latest.values())

    output = {}
        #rc_query = conn.execute('SELECT rid, name, value FROM resource_columns as rc WHERE rc.name IN %s' % str(tuple([n for n in field_mapping if n != 'MULTI'])))
    #for rid, original_id, type_, value_name, value in join_results:
    def internal(rid, value_name, value):
        #print(rid, value_name, value)
        scrid, oid, type_, status = resources[rid]
        if scrid.startswith('SCR_'):
            scrid = scrid.replace('_',':')
        if scrid not in output:
            output[scrid] = []
        #if 'id' not in [a for a in zip(*output[rid])][0]:
            output[scrid].append(('id', scrid))  # add the empty prefix
            if oid:
                output[scrid].append(('old_id', oid))
            #output[scrid].append(('type', type_))  # this should come via the scigraph cats func
            if status == 'Rejected':
                output[scrid].append(('deprecated', True))
        
        if value_name in field_mapping['MULTI']:
            values = [v.strip() for v in value.split(',')]  # XXX DANGER ZONE
            values = [v for v in values if v != 'Inc' and v != 'Inc.']  # XXX temporary fix for a common misuse of commas
            name = field_mapping['MULTI'][value_name]
            for v in values:
                if value_name == 'Abbreviation' and (('label', v) in output[scrid] or ('synonym', v) in output[scrid]):
                    continue
                elif name == 'synonym' and ('label', v) in output[scrid]:
                    continue
                output[scrid].append((name, v))  # TODO we may want functions here
        else:
            if field_mapping[value_name] == 'definition':
                value = value.replace('\r\n','\n').replace('\r','\n').replace("'''","' ''")  # the ''' replace is because owlapi ttl parser considers """ to match ''' :/ probably need to submit a bug
            elif field_mapping[value_name] == 'superclass':
                if value in remap_supers:
                    value = remap_supers[value]
            output[scrid].append((field_mapping[value_name], value))  # TODO we may want functions here

    for rid, value_name, value in (_ for _ in res_cols_l if _[1] == 'Resource Name'):
        internal(rid, value_name, value)
    for rid, value_name, value in (_ for _ in res_cols_l if _[1] == 'Synonyms'):
        internal(rid, value_name, value)
    for rid, value_name, value in (_ for _ in res_cols_l if _[1] != 'Resource Name' and _[1] != 'Synonyms'):
        internal(rid, value_name, value)

    return output

def make_node(id_, field, value, column_to_predicate=_column_to_predicate):
    if field == 'id':
        if value.startswith('SCR:'):
            value = 'owl:NamedIndividual'
        else:
            print(value)
            value = 'owl:Class'
    #if type(value) == bool:
        #if value:
            #value = rdflib.Literal(True)
        #else:
            #value = rdflib.Literal(False)
    return id_, column_to_predicate[field], value

def get_records(field_mapping=_field_mapping):
    DB_URI = 'mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db}'
    #config = mysql_conn_helper('mysql5-stage.crbs.ucsd.edu', 'nif_eelg', 'nif_eelg_secure')
    config = mysql_conn_helper('nif-mysql.crbs.ucsd.edu', 'nif_eelg', 'nif_eelg_secure')
    engine = create_engine(DB_URI.format(**config))
    config = None  # all weakrefs should be gone by now?
    del(config)  # i wonder whether this actually cleans it up when using **config
    insp = inspect(engine)
    #names = [c['name'] for c in insp.get_columns('registry')]
    #resource_columns = [c['name'] for c in insp.get_columns('resource_columns')]
    #resource_data = [c['name'] for c in insp.get_columns('resource_data')]
    #resource_fields = [c['name'] for c in insp.get_columns('resource_fields')]
    #resources = [c['name'] for c in insp.get_columns('resources')]
    #conn.execute('SELECT * from registry;')
    if 1:  # this if for indentation purposes only
    #with engine.connect() as conn:
        conn = engine
        tables = ('resource_columns', 'resource_data', 'resource_fields', 'resources')
        data = {t:([c['name'] for c in insp.get_columns(t)], conn.execute('SELECT * from %s limit 20;' % t).fetchall()) for t in tables}
        all_fields = [n[0] for n in conn.execute('SELECT distinct(name) FROM resource_fields;').fetchall()]

        #query = conn.execute('SELECT r.rid, r.original_id, r.type, rc.name, rc.value from resources as r JOIN'
                            #' resource_columns as rc ON r.id=rc.rid'
                            #' WHERE rc.name IN %s limit 1000;' % str(tuple([n for n in field_mapping if n != 'MULTI'])))  # XXX DANGER THIS QUERY IS O(x^n) :x
                            #' ORDER BY r.rid limit 2000;'

        #query = conn.execute('SELECT r.rid, r.original_id, r.type, rc.name, rc.value from resource_columns as rc JOIN'
                             #' resources as r ON rc.rid=r.id'
                             #' WHERE rc.name IN %s;' % str(tuple([n for n in field_mapping if n != 'MULTI'])))  # XXX DANGER why does > 2000 limit break stuff?

        #join = query.fetchall()

        #print('running join')
        print('running 1')
        r_query = conn.execute('SELECT id, rid, original_id, type, status FROM resources WHERE id < 16000;')  # avoid the various test entries :(
        print('fetching 1 ')
        r = r_query.fetchall()
        print('running 2')
        rc_query = conn.execute('SELECT rid, name, value, version FROM resource_columns as rc WHERE rc.rid < 16000 AND rc.name IN %s;' % str(tuple([n for n in field_mapping if n != 'MULTI'])))
        print('fetching 2')
        rc = rc_query.fetchall()

    fixesForResourcesAndColumns(r, rc)
    records = make_records(r, rc, field_mapping)
    print('Fetching and data prep done.')
    return records

def make_file(graph, records):
    for id_, rec in records.items():
        for field, value in rec:
            #print(field, value)
            if not value:  # don't add empty edges  # FIXME issue with False literal
                print('caught an empty value on field', id_, field)
                continue
            if field != 'id' and (str(value).replace('_',':') in id_ or str(value) in id_):
            #if field == 'alt_id' and id_[1:] == value:
                print('caught a mainid appearing as altid', field, value)
                continue
            graph.add_trip(*make_node(id_, field, value))

    graph.write()

def main():
    records = get_records()
    graph = createOntology('scicrunch-registry',
                           'scicrunch registry exported ontology',
                           makePrefixes('owl',
                                        'rdf',
                                        'rdfs',
                                        'skos',
                                        'definition',
                                        'SCR',  # generate base from this directly?
                                        #'obo':'http://purl.obolibrary.org/obo/',
                                        #'FIXME':'http://fixme.org/',
                                        'NIFSTD',  # for old ids??
                                        'NIFRID',
                                        'oboInOwl'), # these aren't really from OBO files but they will be friendly known identifiers to people in the community
                           'screxp',
                           'This file is automatically generated from the SciCrunch resource registry on a weekly basis via https://github.com/tgbugs/pyontutils/blob/master/scr_sync.py.',
                           path='')

    make_file(graph, records)

if __name__ == '__main__':
    main()
