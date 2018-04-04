import json
from sqlalchemy import create_engine, inspect, Table, Column
import pandas as pd
from args_reader import read_args
from scicrunch_client_fast import scicrunch
import sys
import time
import math as m
import numpy as np
from interlex_sql import interlex_sql

ranking = [
    'CHEBI',
    'NCBITaxon',
    'COGPO',
    'CAO',
    'DICOM',
    'UBERON',
    'NLX',
    'NLXANAT',
    'NLXCELL',
    'NLXFUNC',
    'NLXINV',
    'NLXORG',
    'NLXRES',
    'BIRNLEX',
    'SAO',
    'ILX'
]

def superclasses_bug_fix(term_data):

    if term_data.get('superclasses'):
        for i, value in enumerate(term_data['superclasses']):
            term_data['superclasses'][i]['superclass_tid'] = term_data['superclasses'][i].pop('id')
    return term_data

def preferred_change(data):

    mock_rank = ranking[::-1]
    score = []
    for d in data['existing_ids']:
        if d.get('curie'):
            pref = d['curie'].split(':')[0]
            if pref in mock_rank:
                score.append(mock_rank.index(pref))
            else:
                score.append(-1)
        else:
            score.append(-1)

    preferred_index = score.index(max(score))
    for e in data['existing_ids']: e['preferred'] = 0
    data['existing_ids'][preferred_index]['preferred'] = 1

    return data

def merge(new, old):

    for k, vals in new.items():

        if k == 'synonyms':
            if old['synonyms']:
                literals = [s['literal'].lower().strip() for s in old['synonyms']]
                for v in vals:
                    if v['literal'].lower().strip() not in literals:
                        old['synonyms'].append(v)
            else:
                old['synonyms'].append(new['synonyms'])
            print(old['synonyms'])

        elif k == 'existing_ids':
            iris = [e['iri'] for e in old['existing_ids']]
            for v in vals:
                if 'change' not in list(v):
                    sys.exit('Need "change" key for existing_ids!')
                elif v['iri'] not in iris and v['change'] == True:
                    sys.exit('You want to change iri that doesnt exist', '\n', new)
                elif v['iri'] not in iris and v['change'] == False:
                    old['existing_ids'].append(v)
                elif v['iri'] in iris and v['change'] == True:
                    new_existing_ids = []
                    for e in old['existing_ids']:
                        if e['iri'] == v['iri']:
                            new_existing_ids.append(v)
                        else:
                            new_existing_ids.append(e)
                    old['existing_ids'] = new_existing_ids
                    #print(old['existing_ids'])
                elif v['iri'] in iris and v['change'] == False:
                    pass #for sanity readability
                if v.get('delete') == True:
                    if v['iri'] in iris:
                        new_existing_ids = []
                        for e in old['existing_ids']:
                            if e['iri'] == v['iri']:
                                new_existing_ids.append(v)
                            else:
                                new_existing_ids.append(e)
                        old['existing_ids'] = new_existing_ids
                    else:
                        sys.exit("You want to delete an iri that doesn't exist", '\n', new)
            old = preferred_change(old)

        elif k in ['definition', 'superclasses', 'id', 'type', 'comment']:
            old[k] = vals

        else:
            print(old)
            sys.exit('Value: ' + str(k) + " doesn't exist in ilx keys")

    return old

def extract_annotations(data):

    annotaitons = []
    for d in data:
        if d.get('annotations'):
            annotaitons.appened({
                'tid':d['tid'],
                'annotation_tid':d['annotation_tid'],
                'value':d['value'],
            })

    return annotaitons

def fill_data(data, sql):
    existing_ids = sql.get_existing_ids()
    synonyms = sql.get_synonyms()
    superclasses = sql.get_superclasses()

    old_data = {}
    for d in data:
        #print(d)
        old_data.update({
            int(d['id']):{
                'existing_ids':existing_ids.loc[existing_ids.tid == int(d['id'])].to_dict('records'),
                'synonyms':synonyms.loc[synonyms.tid == int(d['id'])].to_dict('records'),
                'superclasses':superclasses.loc[superclasses.tid == int(d['id'])].to_dict('records')
            }
        })
        #print(old_data)

    return old_data
