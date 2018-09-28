""" Diff for ontologies

Usage:  ilx_graph_comparator [-h | --help]
        ilx_graph_comparator [-v | --version]
        ilx_graph_comparator [options]

Options:
    -h --help                          Display this help message
    -v --version                       Current version of file
    -d --interlex-db                   extracts interlex data from database itself (longer time)
    -i --interlex=<path>               interlex file path
    -e --external-ontology=<path>      external ontology file path
    -o --output=<path>                 For options that aren't paths themselves
    --degrade-level=<int>              level of obj comparison 0-2; least to greatest [default: 1]
"""
from docopt import docopt
from collections import defaultdict
from ilxutils.graph2pandas import Graph2Pandas
from ilxutils.ilx_pred_map import IlxPredMap
from ilxutils.interlex_sql import IlxSql
from ilxutils.mydifflib import ratio
from ilxutils.nltklib import get_tokenized_sentence
from ilxutils.tools import light_degrade, degrade, open_json, open_pickle, create_json
from IPython import embed
import pandas as pd
from pathlib import Path as p
import os
from subprocess import call
from sys import exit
from typing import Dict, List, NewType, Union
VERSION = '0.0.2'
Records = NewType('Records', List[dict]) # each dict has the same keys


class IlxGraphComparator(IlxPredMap):

    def __init__(
        self,
        interlex: pd.DataFrame,
        external_ontology: pd.DataFrame,
        degrade_level: int = 1,
        nltk: bool = False
    ):
        IlxPredMap.__init__(self) # creates get_common_pred
        self.interlex = interlex
        self.external_ontology = external_ontology
        self.degrade_level = degrade_level
        self.nltk = nltk
        self.create_ilx_hashes()
        self.diff = self.match()

    def custom_degrade(self, string: str,) -> str:
        if self.degrade_level == 0:
            return string.lower().strip()
        elif self.degrade_level == 1:
            return light_degrade(string)
        elif self.degrade_level == 2:
            return degrade(string)
        else:
            exit('Need to give a level of degrade 0-2; least to greatest.')

    def pop_bad_elements_in_row(self, row: dict) -> dict:
        new_row = {}
        for pred, objs in row.items():
            if self.get_common_pred(pred):
                new_row[pred] = objs
        return new_row

    def create_ilx_hashes(self):

        def hash_push(
            _hash: defaultdict,
            obj: str,
            row: dict,
        ):
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

        for row in self.interlex.to_dict('records'):

            iri = row['iri']

            # hash exact iri matches
            self.ilx_iri_hash[iri].append(row)

            # hash iri ends that are the real presumed ids
            _id = self.get_fragment_id(iri)
            hash_push(self.ilx_iri_fragment_hash, _id, row)

            # if all else fails and curies exist we can use this as an id
            curieid = row['curie'].split(':')[1] if row['curie'] else None
            hash_push(self.ilx_iri_fragment_hash, curieid, row)

            # hash by ilx label
            label = self.custom_degrade(row['label'])
            hash_push(self.ilx_label_hash, label, row)

            # hash tokenized labels
            if self.nltk:
                label = get_tokenized_sentence((self.custom_degrade(row['label'])))
                if label:
                    hash_push(self.ilx_nltk_label_hash, label, row)

    def get_fragment_id(self, iri: str) -> str:
        # simulate a fragmented id
        _id = iri.rsplit('/', 1)[-1]
        if '=' in _id:
            _id = _id.rsplit('=', 1)[-1]
        elif '#' in _id:
            _id = _id.rsplit('#', 1)[-1]
        elif '_' in _id:
            _id = _id.rsplit('_', 1)[-1]
        return _id

    def match(self) -> Records:
        ''' Matches data based on greatest to least priority:
            iri, fragmented iri, label, then nltk hits.
        '''

        def update_records(
            records: list,
            hit_type: str,
            ilx_hits: list,
            original_row: List[dict],
            external_ids: list,
        ) -> list:
            visited = {}
            for ilx_data in ilx_hits:
                if not visited.get(ilx_data['ilx']):
                    records.append({
                        'hit_type': hit_type,
                        'ilx_data': ilx_data,
                        'external_data': original_row,
                        'external_ids': external_ids,
                    })
                    visited[ilx_data['ilx']] = True
            return records

        records = []
        for i, row in self.external_ontology.iterrows():

            row = row[~row.isnull()] # removes nulls
            original_row = row.to_dict().copy()
            #row = self.pop_bad_elements_in_row(row) # removes non ilx maps

            iris = []
            for accepted_code_name in ['iri', 'termui', 'code']:
                code_obj = row[accepted_code_name] if row.get(accepted_code_name) else None
                if not code_obj:
                    continue
                elif isinstance(code_obj, list):
                    iris.extend(code_obj)
                else:
                    iris.append(code_obj)
            iris = set(iris)
            for iri in iris:

                # if 'http://id.nlm.nih.gov/mesh/vocab#Concept' not in row['rdf:type']:
                #     continue

                # simulate a fragmented id
                iri_frag = self.get_fragment_id(iri)
                hit = False

                if self.ilx_iri_hash.get(iri):
                    records = update_records(
                        records = records,
                        hit_type = 'iri',
                        ilx_hits = self.ilx_iri_hash.get(iri),
                        original_row = original_row,
                        external_ids = iris,
                    )
                    break

                elif self.ilx_iri_fragment_hash.get(iri_frag):
                    records = update_records(
                        records = records,
                        hit_type = 'iri',
                        ilx_hits = self.ilx_iri_fragment_hash.get(iri_frag),
                        original_row = original_row,
                        external_ids = iris,
                    )
                    break

                else:

                    for pred, objs in row.items():

                        if hit: break

                        common_pred = self.get_common_pred(pred)
                        if not common_pred:
                            continue
                        if common_pred == 'label':
                            for obj in objs:

                                _obj = self.custom_degrade(obj)
                                if self.ilx_label_hash.get(_obj):
                                    records = update_records(
                                        records = records,
                                        hit_type = 'label',
                                        ilx_hits = self.ilx_label_hash.get(_obj),
                                        original_row = original_row,
                                        external_ids = iris,
                                    )
                                    hit = True
                                    break

                                if self.nltk and not hit:
                                    tok_obj = get_tokenized_sentence(_obj)
                                    if self.ilx_nltk_label_hash.get(tok_obj):
                                        records = update_records(
                                            records = records,
                                            hit_type = 'label',
                                            ilx_hits = self.ilx_nltk_label_hash.get(tok_obj),
                                            original_row = original_row,
                                            external_ids = iris,
                                        )
                                        hit = True
                                        break

                if hit:
                    break

            # if not hit:
            #     records.append({
            #         'hit_type':None,
            #         'ilx_data':None,
            #         'external_data':original_row,
            #     })

        return records

    def get_csv_ready_df(self):

        def get_ilx_equal(value, row):
            for pred, objs in row['external_data'].items():
                for obj in objs:
                    if self.custom_degrade(value) == self.custom_degrade(obj):
                        return obj
            embed()

        header = [
            'T/F',
            'RATIO',
            'ILX_LABEL',
            'EX_ONTO_LABEL',
            'ILX_DEF',
            'EX_ONTO_DEF',
            'ILX_ID',
            'EX_ONTO_IDS',
        ]

        records = []
        for row in self.diff:
            if row['hit_type'] == 'label':
                record = {col:None for col in header}

                external_label = get_ilx_equal(row['ilx_data']['label'], row)
                external_def = row['external_data'].get('definition')

                record['RATIO'] = round(ratio(row['ilx_data']['label'], external_label), 3)
                record['ILX_LABEL'] = row['ilx_data']['label']
                record['EX_ONTO_LABEL'] = external_label
                record['ILX_DEF'] = row['ilx_data']['definition']
                record['EX_ONTO_DEF'] = external_def
                record['ILX_ID'] = row['ilx_data']['ilx']
                record['EX_ONTO_IDS'] = row['external_ids']

                records.append(record)

        return pd.DataFrame(records, columns=header)


def open_ontology(path: str) -> pd.DataFrame:
    path = p(path)
    if path.suffix == '.json':
        return pd.DataFrame(open_json(path))
    elif path.suffix == '.pickle':
        return open_pickle(path)
    elif path.suffix in ['.ttl', '.rdf', '.xml', '.xrdf', '.owl', '.nt']:
        return Graph2Pandas(path).df


def main():
    doc = docopt(__doc__, version=VERSION)

    if doc.get('--interlex'):
        interlex = open_ontology(doc['--interlex'])
    elif doc.get('--interelx-db'):
        sql = IlxSql(
            api_key=os.environ.get('SCICRUNCH_API_KEY'),
            db_url=os.environ.get('SCICRUNCH_DB_URL_PRODUCTION')
        )
        interlex = sql.get_existing_ids()
    else:
        exit(
            'Please specify interlex source to use, reference or source (mysql).'
            'If using source, make sure to also to provide the api_key and database url.'
            'If using reference, provide a path to the external_ontology of the following format:'
            'records (List[dict]) as a json file, pd.DataFrame as a picle file'
        )

    if doc.get('--external-ontology'):
        external_ontology = open_ontology(doc['--external-ontology'])
    else:
        exit(
            'Please input a path to the external_ontology of the following format:'
            'records (List[dict]) as a json file, pd.DataFrame as a picle file'
        )

    degrade_level = int(doc['--degrade-level'])

    igc = IlxGraphComparator(
        interlex = interlex,
        external_ontology = external_ontology,
        degrade_level = degrade_level,
        nltk = False,
    )
    create_json(igc.diff, doc['--output'])
    csv_ready_df = igc.get_csv_ready_df()
    csv_ready_df.to_csv('~/Desktop/ilx-mesh-diff-strict.csv', index=False)


if __name__ == '__main__':
    main()
