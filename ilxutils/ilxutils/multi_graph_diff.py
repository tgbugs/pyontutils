"""Intended purpose it to compare NIF-Ontology to interlex

Usage:
    multi_compare_graphs.py [-h | --help]
    multi_compare_graphs.py [-v | --version]
    multi_compare_graphs.py [-r=<path>] (-t=<path> | -t=<paths>...) [-o=<path>]

Options:
    -h --help               Display this help message
    -v --version            Current version of file
    -o --output=<path>      [default: Dropbox/multi_test.json]
    -r --reference=<path>   Reference graph [default: Dropbox/interlex.pickle]
    -t --target=<path>...   Target graphs(s); can be folder or list of files [default: Dropbox/uberon.pickle]
"""
from collections import defaultdict
from docopt import docopt
from glob import glob
import pandas as pd
from pathlib import Path as p
from sys import exit
import hashlib
from ilxutils.ilx_pred_map import IlxPredMap
from ilxutils.mydifflib import ratio
from ilxutils.args_reader import doc2args
from ilxutils.graph2pandas import Graph2Pandas
from ilxutils.graph_comparator import GraphComparator
from ilxutils.tools import open_json, create_json, prettify_ontodiff_json, create_csv
VERSION = '0.0.2'
BLACKLIST = ['synonym', 'superclass']


class MultiGraphDiff(IlxPredMap):

    def __init__(self, ref_file='', tar_card=[]):
        IlxPredMap.__init__(self)
        self.ref_file = ref_file
        self.tar_card = tar_card
        self.tar_files = self.__find_tar_files()
        self.diffs = self.__create_diffs()
        self.merged_diff = self.__merge_diffs()

    def __find_tar_files(self):
        tar_files = []
        accepted_file_types = ['.ttl', '.owl', '.pickle']
        for tar_card in self.tar_card:
            if p(tar_card).is_dir():
                for _type in accepted_file_types:
                    tar_files.extend(
                        glob(tar_card + '/**/*' + _type, recursive=True))
            elif p(tar_card).is_file() and p(tar_card).suffix in accepted_file_types:
                tar_files.append(tar_card)
        return tar_files

    def __create_diffs(self):
        diffs = []
        for i, tar_file in enumerate(self.tar_files, 1):
            print(i, 'of', len(self.tar_files), ':',
                  self.ref_file, 'VS.', tar_file)
            # gc = GraphComparator(self.ref_file, tar_file,
            #                     rg_ilx=True,
            #                     partial_diff=True,
            #                     blacklist=BLACKLIST,
            #                     both_graphs_contain=False,
            #                     likeness_threshold=.8,
            #                     dislikeness_threshold=1,)
            gc = GraphComparator(self.ref_file, tar_file)
            diffs.append(gc.diff)
        return diffs

    def __merge_diffs(self):
        print('Merging...')
        merged_diff = defaultdict(dict)
        for diff in self.diffs:
            for ref_key, exids_data in diff.items():
                merged_diff[ref_key].update(exids_data)
        return merged_diff

    # experiment with hashlib
    def get_csv_ready_df(self):
        header = ['T/F', 'RATIO',
                  'REFERENCE_OBJ', 'TARGET_OBJ',
                  'REFERENCE_PRED', 'TARGET_PRED',
                  'REFERENCE_IRI', 'TARGET_IRI',
                  'REFERENCE_ONTOLOGY', 'TARGET_ONTOLOGY']
        rows = []

        for ref_name, tar_dict in self.merged_diff.items():
            row = {colname: None for colname in header}
            row['REFERENCE_ONTOLOGY'] = p(self.ref_file).stem
            row['REFERENCE_IRI'] = ref_name
            for tar_name, shared_iri_dict in tar_dict.items():
                row['TARGET_ONTOLOGY'] = tar_name
                for shared_iri, diff_dict in shared_iri_dict.items():
                    row['TARGET_IRI'] = shared_iri

                    for ref_pred, ref_obj in diff_dict['reference_graph_only']:
                        for tar_pred, tar_obj in diff_dict['target_graph_only']:
                            if self.pred_degrade(ref_pred) == self.pred_degrade(tar_pred):
                                row['REFERENCE_OBJ'] = ref_obj
                                row['TARGET_OBJ'] = tar_obj
                                row['REFERENCE_PRED'] = ref_pred
                                row['TARGET_PRED'] = tar_pred
                                row['RATIO'] = round(ratio(ref_obj, tar_obj), 3)
                                rows.append(row)

        return pd.DataFrame.from_records(rows, columns=header)


def main():
    '''
    > python3 multi_graph_diff.py -r reference_graph.ttl -t target_folder -o diff.json
    '''
    args = doc2args(docopt(__doc__, version=VERSION))
    mgd = MultiGraphDiff(ref_file=args.reference, tar_card=args.target)
    create_json(mgd.merged_diff, args.output)
    prettify_ontodiff_json(args.output)
    #mgd_csv_ready_df = mgd.get_csv_ready_df()
    #mgd_csv_ready_df.to_csv('~/Dropbox/csv_test.csv', index=False)


if __name__ == '__main__':
    main()
