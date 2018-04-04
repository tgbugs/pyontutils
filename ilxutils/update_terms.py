import json
from sqlalchemy import create_engine, inspect, Table, Column
import pandas as pd
from args_reader import read_args
from scicrunch_client_fast import scicrunch
import sys
import time
import math as m

""" Need to find current ID in sql to address api """
def create_labels_to_ids_dict(engine_key):
    engine = create_engine(engine_key)
    data =  """
            SELECT t.* FROM terms as t
            """
    df = pd.read_sql(data, engine)
    visited = {}
    label_to_id = {}
    for row in df.itertuples():
        label = row.label.lower().strip()
        if visited.get(label):
            continue
        else:
            label_to_id[label] = int(row.id)
            visited[label]=True
    return label_to_id

""" Scans type and Reads file into Dictionary """
def file_opener(infile):
    return json.load(open(infile, 'r'))

""" Merges edits with old term info from api. Currently on merges: definition, synonyms """
def merge_old_with_new(old, new):

    """Definition"""
    if new.get('definition'):
        old['definition'] = new['definition']

    """Synonyms"""
    if new.get('synonyms'):
        if not old['synonyms']:
            old['synonyms'] = new['synonyms']
        else:
            literals = [synonym.get('literal').lower().strip() for synonym in old['synonyms']]
            if new['synonyms'].lower().strip() not in literals:
                old['synonyms'].append({'tid':old['id'], 'literal':new['synonyms']})

    """Existing_ids"""
    if new.get('existing_ids'):
        pass

    """annotations"""
    if new.get('value'):
        old['annotation_tid'] = new['annotation_tid']
        old['value'] = new['value']

    """all other objects need this"""
    old['tid'] = old['id']

    return old

""" Superclasses does read id, needs to be changed to superclass_tid """
def superclasses_bug(data):

    def helper(term_data):
        if term_data['superclasses']:
            for i, value in enumerate(term_data['superclasses']):
                term_data['superclasses'][i]['superclass_tid'] = term_data['superclasses'][i].pop('id')
        return term_data

    return [helper(d) for d in data]

def main():
    args = read_args()
    data = file_opener(infile=args['file'])#get labels to update

    #labels_to_ids_dict = create_labels_to_ids_dict(engine_key=args['engine_key'])
    #with open('../dump/labels_to_ids_dict_complete_interlex_sql.json', 'w') as f: json.dump(labels_to_ids_dict, f, indent=4); sys.exit()
    labels_to_ids_dict = json.load(open('../dump/labels_to_ids_dict_complete_interlex_sql.json', 'r'))

    sci = scicrunch(key=args['api_key'], base_path=args['base_path'])

    new_label_data = {labels_to_ids_dict.get(label.lower().strip().replace("'",'&#39;')):label_data for label, label_data in data.items() if labels_to_ids_dict.get(label.lower().strip().replace("'",'&#39;'))}

    batch_ids = list(new_label_data)[198700:] #DEBUG
    #batch_data = {k:v for k, v in new_label_data.items() if k in batch_ids}
    #with open('remaining-second-tier-cdes.json', 'w') as f: json.dump(batch_data, f, indent=4)
    #sys.exit()
    seg_length = 25
    total_batch_ids = [batch_ids[x:x+seg_length] for x in range(0,len(batch_ids),seg_length)]
    total_count = m.floor(len(batch_ids) / seg_length)

    """ Limit the batch amount to deal with timeout issue """
    for i, ids in enumerate(total_batch_ids):
        print('Batch', i, 'out of', total_count)

        print('=== Collecting Terms Data from API ===')
        start_time = time.time()
        old_label_data = sci.identifierSearchs(ids)
        print (round(time.time() - start_time, 2), "seconds", 'id search')

        merged_labels = [merge_old_with_new(old=old_label_data[tid], new=new_label_data[tid]) for tid in ids]
        merged_labels = superclasses_bug(merged_labels) #BUG

        #print([v['label'] for k,v in old_label_data.items()][:]) #DEBUG

        """ Adding Annotations """
        annotations = []
        for labels_data in merged_labels:
            if labels_data.get('value'):
                for value in labels_data['value']:
                    annotations.append({
                        'annotation_tid':labels_data['annotation_tid'],
                        'tid':labels_data['id'],
                        'value':value,
                    })
        start_time = time.time()
        sci.addAnnotations(annotations)
        print (round(time.time() - start_time, 2), "seconds", 'add annotations')

        """ Updating Terms/CDEs """
        #Should be last incase this works for deleting values and the rest add
        start_time = time.time()
        sci.updateTerms(merged_labels[:])
        print (round(time.time() - start_time, 2), "seconds", 'update terms')

if __name__ == '__main__':
    main()
