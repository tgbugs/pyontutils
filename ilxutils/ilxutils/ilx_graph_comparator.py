""" Diff for ontologies

Usage:  ilx_graph_comparator [-h | --help]
        ilx_graph_comparator [-v | --version]
        ilx_graph_comparator [-r=<path>] [-t=<path>] [-o=<path>]

Options:
    -h --help                          Display this help message
    -v --version                       Current version of file
    -r --reference=<path>              [default: /home/troy/Dropbox/interlex.pickle]
    -t --target=<path>                 [default: /home/troy/Dropbox/uberon.pickle]
    -o --output=<path>                 For options that aren't paths themselves
"""
from docopt import docopt
from collections import defaultdict
from pathlib import Path as p
from sys import exit
import pandas as pd
from ilxutils.ilx_pred_map import IlxPredMap
from ilxutils.mydifflib import ratio
from ilxutils.tools import *
from ilxutils.graph2pandas import Graph2Pandas
from ilxutils.nltklib import get_tokenized_sentence
from subprocess import call
VERSION = '0.0.1'


class IlxGraphComparator(IlxPredMap):
    def __init__(self, tpath):
        IlxPredMap.__init__(self)
        self.ex2row = open_pickle('Dropbox/interlex_backups/ilx_db_ex2row_backup')
        self.tgraph = Graph2Pandas(tpath)
        self.create_ilx_hashes()
        self.diff = self.match()

    def get_common_pred(self, pred):
        common_pred = self.ext2ilx_map.get(degrade(pred))
        if not common_pred:
            if ':' in pred:
                pred = pred.split(':')[-1]
                common_pred = self.ext2ilx_map.get(degrade(pred))
        return common_pred

    def pop_bad_data(self, row):
        new_row = {}
        for pred, objs in row.items():
            if self.get_common_pred(pred):
                new_row[pred] = objs
        return new_row

    def create_ilx_hashes(self):
        def push(_hash, obj, row):
            if obj:
                if _hash.get(obj):
                    if row not in _hash[obj]:
                        _hash[obj].append(row)
                else:
                    _hash[obj].append(row)

        '''
        Hashes iris, fragments of iris, label and definition to list of rows
        '''
        self.ilx_iri_hash = defaultdict(list)
        self.ilx_iri_fragment_hash = defaultdict(list)
        self.ilx_label_hash = defaultdict(list)
        self.ilx_nltk_label_hash = defaultdict(list)
        self.ilx_definition_hash = defaultdict(list)

        for iri, row in self.ex2row.items():

            # skip ilx iris for comparisons. they dont exist anywhere else.
            if '/ilx_' in iri:
                continue

            # hash exact iri matches
            self.ilx_iri_hash[iri].append(row)

            # hash iri ends that are the real presumed ids
            _id = self.get_fragment_id(iri)
            push(self.ilx_iri_fragment_hash, _id, row)

            # if all else fails and curies exist we can use this as an id
            curieid = row['curie'].split(':')[1] if row['curie'] else None
            push(self.ilx_iri_fragment_hash, curieid, row)

            # hash by ilx label
            label = light_degrade(row['label'])
            push(self.ilx_label_hash, label, row)

            # hash tokenized labels
            label = get_tokenized_sentence((light_degrade(row['label'])))
            if label:
                push(self.ilx_nltk_label_hash, label, row)

            # hash by ilx definition
            if row['definition']: # some definitions are empty strings
                definition = light_degrade(row['definition'])
                push(self.ilx_definition_hash, definition, row)

    def get_fragment_id(self, iri):
        # simulate a fragmented id
        _id = iri.rsplit('/', 1)[-1]
        if '=' in _id:
            _id = _id.split('=')[1]
        elif '#' in _id:
            _id = _id.split('#')[1]
        elif '_' in _id:
            _id = _id.split('_')[1]
        return _id

    def match(self):
        '''
        matches data based on greatest to least priority:
        iri, fragmented iri, then label or definition
        '''
        data = {'lost_iris': []}
        for iri, row in self.tgraph.df.iterrows():
            # if iri != "http://id.nlm.nih.gov/mesh/2018/T362525":
            #     continue

            row = row[~row.isnull()] # removes nulls
            original_row = row.to_dict().copy()
            row = self.pop_bad_data(row.to_dict()) # removes non ilx maps

            # simulate a fragmented id
            _id = self.get_fragment_id(iri)

            # exact iri match
            if self.ilx_iri_hash.get(iri):
                for ilx_data in self.ilx_iri_hash.get(iri):
                    data.update({
                        ilx_data['ilx']: {
                            iri: {
                                'hit_type': 'iri',
                                'ilx': ilx_data,
                                'graph': original_row,
                            }
                        }
                    })

            elif self.ilx_iri_fragment_hash.get(_id):
                for ilx_data in self.ilx_iri_fragment_hash.get(_id):
                    data.update({
                        ilx_data['ilx']: {
                            iri: {
                                'hit_type': 'iri_id',
                                'ilx': ilx_data,
                                'graph': original_row,
                            }
                        }
                    })

            else:
                hit = False
                for pred, objs in row.items():
                    common_pred = self.get_common_pred(pred)

                    if not common_pred:
                        continue

                    elif common_pred == 'label':
                        for obj in objs:
                            obj = light_degrade(obj)
                            tok_obj = get_tokenized_sentence(obj)
                            if self.ilx_label_hash.get(obj):
                                for ilx_data in self.ilx_label_hash[obj]:
                                    if data.get(ilx_data['ilx']):
                                        if data[ilx_data['ilx']].get(iri):
                                            continue
                                    data.update({
                                        ilx_data['ilx']: {
                                            iri: {
                                                'hit_type': 'label',
                                                'ilx': ilx_data,
                                                'graph': original_row,
                                            }
                                        }
                                    })
                                    hit = True
                            elif self.ilx_nltk_label_hash.get(tok_obj):
                                for ilx_data in self.ilx_nltk_label_hash[tok_obj]:
                                    if data.get(ilx_data['ilx']):
                                        if data[ilx_data['ilx']].get(iri):
                                            continue
                                    data.update({
                                        ilx_data['ilx']: {
                                            iri: {
                                                'hit_type': 'nltk label',
                                                'ilx': ilx_data,
                                                'graph': original_row,
                                            }
                                        }
                                    })
                                    hit = True

                    elif common_pred == 'definition':
                        for obj in objs:
                            obj = light_degrade(obj)
                            if self.ilx_definition_hash.get(obj):
                                for ilx_data in self.ilx_definition_hash[obj]:
                                    if data.get(ilx_data['ilx']):
                                        if data[ilx_data['ilx']].get(iri):
                                            continue
                                    data.update({
                                        ilx_data['ilx']: {
                                            iri: {
                                                'hit_type': 'definition',
                                                'ilx': ilx_data,
                                                'graph': original_row,
                                            }
                                        }
                                    })
                                    hit = True

                # need to know what isnt in ilx in case we want to add it.
                if not hit:
                    data['lost_iris'].append({iri:row})
        return data

def main():
    doc = docopt(__doc__, version=VERSION)
    create_json(IlxGraphComparator(doc['--target']).diff, doc['--output'])

if __name__ == '__main__':
    main()
