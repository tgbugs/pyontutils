import json
import pandas as pd
import rdflib
from pyontutils.utils import rdf, rdfs, owl, skos, oboInOwl, makeGraph
from sqlalchemy import create_engine, inspect, Table, Column
import scicrunch_client
import sys
import pandas as pd
from args_reader import read_args

args = read_args(keys='../keys.txt', production='-p')
curr_stage = 'production'
engine_key=args['engine_key']

def get_subj_to_tid(engine_key):
    engine = create_engine(engine_key)
    data =  """
            SELECT ti.curie, t.label, ti.tid, ti.iri
            FROM term_existing_ids AS ti
            JOIN terms AS t
            WHERE ti.tid=t.id
            """
    df = pd.read_sql(data, engine)
    subj_to_tid = {row.iri:row.tid for row in df.itertuples()}
    return subj_to_tid

def update_existing_ids(existing_ids, tid, subj, curie):
    for existing_id in existing_ids:
        if existing_id['curie'] == subj:
            #print(existing_ids)
            existing_id['curie'] = curie
            return existing_ids
    return None

def diff_term_data(k, new_term_data, old_term_data):
    dont_care = ['existing_ids', 'time', 'version', 'ilx', 'definition']

    for key, value in new_term_data.items():

        if key in dont_care: continue

        if key == 'synonyms':
            if old_term_data.get('synonyms') != None and new_term_data.get('synonyms') == None:
                print('FAILED')
                sys.exit(str(k)+'\n'+str(old_term_data)+'\n'+str(new_term_data))
            else:
                continue

        if key == 'superclasses':
            if len(old_term_data.get('superclasses')) != len(new_term_data.get('superclasses')):
                print('FAILED')
                sys.exit(str(k)+'\n'+str(old_term_data)+'\n'+str(new_term_data))
            continue

        if new_term_data[key] != old_term_data[key]:
            print('FAILED')
            print(key)
            print(new_term_data[key])
            print(old_term_data[key])
            sys.exit(str(k)+'\n'+str(old_term_data)+'\n'+str(new_term_data))

#subj_to_tid = get_subj_to_tid(engine_key)
filename = ''
new_existing_ids = json.load(open('/Users/tmsincomb/Desktop/dump/'+filename+'.json'))
print(len(new_existing_ids))
for i, new_existing_id in enumerate(new_existing_ids[:]):

    if i % 10 == 0: print(i)
    #print(i)

    #if not subj_to_tid.get(new_existing_id['subj']): continue
    #_id = int(subj_to_tid[new_existing_id['subj']]) #odd int bug in some of the data

    _id = new_existing_id['tid']
    term_data = sci.identifierSearch(identifier=_id)['data']
    existing_ids = term_data['existing_ids']
    existing_ids = update_existing_ids(
                        existing_ids=existing_ids,
                        tid = _id,
                        subj = new_existing_id['subj'],
                        curie = new_existing_id['obj'],
                    )
    if not existing_ids: continue

    #print(term_data['label'])

    #FIXME superclasses php bug...
    if term_data['superclasses']:
        for i, value in enumerate(term_data['superclasses']):
            term_data['superclasses'][i]['superclass_tid'] = term_data['superclasses'][i].pop('id')

    result = sci.updateTerm(
        i = i,
        term = term_data['label'],
        tid = term_data['id'],
        existing_ids = existing_ids, #makes new id
        superclasses = term_data['superclasses'], #changes tid to superclass_tid and back
        ontologies = term_data['ontologies'],
        synonyms = term_data['synonyms'], #makes new id
        relationships = term_data['relationships'],
        annotations = term_data['annotations'],
        mappings = term_data['mappings'],
        comment = term_data['comment'],
    )
    new_term_data = sci.identifierSearch(identifier=_id)['data']
    diff_term_data(i, new_term_data, term_data)
    #print(term_data['label'])
