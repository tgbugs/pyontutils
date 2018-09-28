import json
from sqlalchemy import create_engine, inspect, Table, Column
import pandas as pd
from ilxutils.args_reader import read_args
import sys
import time
import math as m
import numpy as np


def superclasses_bug_fix(term_data):

    if term_data.get('superclasses'):
        for i, value in enumerate(term_data['superclasses']):
            try:
                term_data['superclasses'][i]['superclass_tid'] = term_data[
                    'superclasses'][i].pop('id')
            except:
                pass
    return term_data


def preferred_change(data):
    ''' Determines preferred existing id based on curie prefix in the ranking list '''
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
        'NLXSUB'
        'BIRNLEX',
        'SAO',
        'NDA.CDE',
        'PRO',
        'NIFEXT',
        'ILX',
    ]
    mock_rank = ranking[::-1]
    score = []
    old_pref_index = None
    for i, d in enumerate(data['existing_ids']):
        if int(d['preferred']) == 1:
            old_pref_index = i
        if d.get('curie'):
            pref = d['curie'].split(':')[0]
            if pref in mock_rank:
                score.append(mock_rank.index(pref))
            else:
                score.append(-1)
        else:
            score.append(-1)

    new_pref_index = score.index(max(score))
    new_pref_iri = data['existing_ids'][new_pref_index]['iri']
    if new_pref_iri.rsplit('/', 1)[0] == 'http://uri.interlex.org/base':
        if old_pref_index:
            if old_pref_index != new_pref_index:
                return data
    for e in data['existing_ids']:
        e['preferred'] = 0
    data['existing_ids'][new_pref_index]['preferred'] = 1
    return data


def merge(new, old):
    ''' synonyms and existing_ids are part of an object bug that can create duplicates if in the same batch '''

    for k, vals in new.items():

        if k == 'synonyms':
            if old['synonyms']:
                literals = [
                    s['literal'].lower().strip() for s in old['synonyms']
                ]
                for v in vals:
                    if vals['literal'].lower().strip() not in literals:
                        old['synonyms'].append(vals)
            else:
                old['synonyms'].append(new['synonyms'])

        elif k == 'existing_ids':
            iris = [e['iri'] for e in old['existing_ids']]
            vals['preferred'] = 0

            if 'change' not in list(vals):  # notion that you want to add it
                vals['change'] = False

            if vals.get('delete') == True:
                if vals['iri'] in iris:
                    new_existing_ids = []
                    for e in old['existing_ids']:
                        if e['iri'] != vals['iri']:
                            new_existing_ids.append(e)
                    old['existing_ids'] = new_existing_ids
                else:
                    print(vals)
                    sys.exit("You want to delete an iri that doesn't exist",
                             '\n', new)

            elif vals.get('replace') == True:
                if not vals.get('old_iri'):
                    sys.exit(
                        'Need to have old_iri as a key to have a ref for replace'
                    )
                old_iri = vals.pop('old_iri')
                if old_iri in iris:
                    new_existing_ids = []
                    for e in old['existing_ids']:
                        if e['iri'] == old_iri:
                            if vals.get('curie'):
                                e['curie'] = vals['curie']
                            if vals.get('iri'):
                                e['iri'] = vals['iri']
                        new_existing_ids.append(e)
                    old['existing_ids'] = new_existing_ids
                else:
                    print(vals)
                    sys.exit("You want to replace an iri that doesn't exist",
                             '\n', new)

            else:
                if vals['iri'] not in iris and vals['change'] == True:
                    sys.exit('You want to change iri that doesnt exist ' + str(new))
                elif vals['iri'] not in iris and vals['change'] == False:
                    old['existing_ids'].append(vals)
                elif vals['iri'] in iris and vals['change'] == True:
                    new_existing_ids = []
                    for e in old['existing_ids']:
                        if e['iri'] == vals['iri']:
                            if not vals.get('curie'):
                                vals['curie'] = e['curie']
                            new_existing_ids.append(vals)
                        else:
                            new_existing_ids.append(e)
                    old['existing_ids'] = new_existing_ids
                elif vals['iri'] in iris and vals['change'] == False:
                    pass  # for sanity readability
                else:
                    sys.exit('Something broke while merging in existing_ids')
            old = preferred_change(old)

        elif k in [
                'definition', 'superclasses', 'id', 'type', 'comment', 'label', 'uid'
        ]:
            old[k] = vals

        # TODO: still need to mark them... but when batch elastic for update works
        old['uid'] = 34142  # DEBUG: need to mark as mine manually until all Old terms are fixed

    ''' REMOVE REPEATS; needs to exist due to server overloads '''
    visited = {}
    new_synonyms = []
    for synonym in old['synonyms']:
        if not visited.get(synonym['literal']):
            new_synonyms.append(synonym)
            visited[synonym['literal']] = True
    old['synonyms'] = new_synonyms
    visited = {}
    new_existing_ids = []
    for e in old['existing_ids']:
        if not visited.get(e['iri']):
            new_existing_ids.append(e)
            visited[e['iri']] = True
    old['existing_ids'] = new_existing_ids

    return old


def extract_annotations(data):

    annotaitons = []
    for d in data:
        if d.get('annotations'):
            annotaitons.appened({
                'tid': d['tid'],
                'annotation_tid': d['annotation_tid'],
                'value': d['value'],
            })

    return annotaitons


def fill_data(data, sql):
    existing_ids = sql.get_existing_ids()
    synonyms = sql.get_synonyms()
    superclasses = sql.get_superclasses()

    old_data = {}
    for d in data:
        # print(d)
        old_data.update({
            int(d['id']): {
                'existing_ids':
                existing_ids.loc[existing_ids.tid == int(d['id'])].to_dict(
                    'records'),
                'synonyms':
                synonyms.loc[synonyms.tid == int(d['id'])].to_dict('records'),
                'superclasses':
                superclasses.loc[superclasses.tid == int(d['id'])].to_dict(
                    'records')
            }
        })
        # print(old_data)

    return old_data
