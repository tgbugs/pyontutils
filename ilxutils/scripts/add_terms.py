"""
AUTHOR: TROY SINCOMB

#BUG == There is a current problem with server or php that is being worked around.
#FIXME == Target not verbose enough for my taste. Will upgrade later.

Reads Json with key as Label and value as the rest of what to add.
"""
import json
from sqlalchemy import create_engine, inspect, Table, Column
import pandas as pd
from args_reader import read_args
from scicrunch_client_fast import scicrunch
import sys


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
    labels_to_ids_dict = json.load(open('../dump/labels_to_ids_dict_complete_interlex_sql.json', 'r'))

    sci = scicrunch(key=args['api_key'], base_path=args['base_path'])

    print(len(data))

    new_label_data = [label_data for label, label_data in data.items() if not labels_to_ids_dict.get(label.lower().strip().replace("'",'&#39;'))][:]
    #print([label['label'] for label in new_label_data])

    print(len(new_label_data))
    #print(new_label_data[0])

    output = sci.addTerms(new_label_data[:])
    #print(output)
    annotations = []
    for labels_data in new_label_data[:]:
        if labels_data.get('annotations'):
            for annotation in labels_data['annotations']:
                annotations.append({
                    'annotation_tid':annotation['annotation_tid'],
                    'tid':output[labels_data['label'].replace("'",'&#39;')]['id'], #need ID to continue; get it from addTerm output
                    'value':annotation['value'],
                })

    if annotations:
        #print(annotations)
        sci.addAnnotations(annotations)

if __name__ == '__main__':
    main()
