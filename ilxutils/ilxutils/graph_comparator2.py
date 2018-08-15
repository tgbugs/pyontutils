from docopt import docopt
from collections import defaultdict
from pathlib import Path as p
from sys import exit
import pandas as pd
from ilxutils.ilx_pred_map import IlxPredMap
from ilxutils.mydifflib import ratio
from ilxutils.tools import fix_path, degrade
from ilxutils.graph2pandas import Graph2Pandas
from subprocess import call
from json2html import json2html
import json
# from ontologies_compared_brain import visited_onto_iris_hash
""" Intended use is to compare owl or ttl to the ttl created from interlx.

Usage:  compare_graphs.py [-h | --help]
        compare_graphs.py [-v | --version]
        compare_graphs.py [-r=<path>] [-t=<path>] [-f=<path> | -p=<path> | -c=<ext> -o=<path> | --csv=<path> -u=<functype>] [-i] [-s] [--save-pickles] [--html=<path>]

Options:
    -h --help                          Display this help message
    -v --version                       Current version of file
    -r --reference=<path>              [default: /home/troy/Dropbox/interlex.pickle]
    -t --target=<path>                 [default: /home/troy/Dropbox/uberon.pickle]
    -f --full-diff=<path>              Output path of full comparison, even those that dont have a common diff
    -p --partial-diff=<path>           Output of comparisons that have a similar predicate
    -i --ilx                           Treat reference like its ilx bc it has uniqueness
    -c --custom-diff=<ext>             Stems from partial and is ilx only; can only be one to all: 'label, def, syn, super, type'
    -o --output=<path>                 For options that aren't paths themselves
    --save-pickles                     If you converted files to pickle it's worth using to save them (will save in folder of src)
    -s --shorten-names                 Condensed the names of iris
    --html=<path>                      Converts the json comparison to html (default being the same path of -p | -d)
    --csv=<path>                       creats to csv from either full or partial diff
    -m --custom-csv                    for partial, ilx, custom csv
    -u --function=<functype>           What we want to do with the info after it has been cleared to go into scicrunch
"""
VERSION = '0.0.4'

# TODO: need to fill in the unshared iri with matching data and unshared everything to dummy ilx id


class GraphComparator(IlxPredMap):
    '''
        Speed boost!
    '''

    def __init__(self, reference_graph_path, target_graph_path):
        IlxPredMap.__init__(self)
        self.rg_path = fix_path(reference_graph_path)
        self.tg_path = fix_path(target_graph_path)
        self.rgraph = Graph2Pandas(self.rg_path)
        self.tgraph = Graph2Pandas(self.tg_path)
        self.ref_hash, self.tail_ref_hash = self.create_hashes(
            self.rgraph, limit=2)
        self.tar_hash, self.tail_tar_hash = self.create_hashes(
            self.tgraph, limit=2)
        self.diff = self.compare_hashes()

    def create_hashes(self, graph, limit=None):
        """
            hash = {'onto':{'degrade_pred':{'real_pred':{'real_obj':{'degraded_obj': {}}}}}}
        """
        def rec_dd():  # unlimited nested dicts
            return defaultdict(rec_dd)

        ref_hash = rec_dd()
        tail_hash = {}  # reverse hash

        # tier1 is ilx == ilx so using existing_id is not the king....
        limiter = 0  # DEBUG: temp to spot check
        for i, row in graph.df.iterrows():
            if limiter == limit:
                break
            else:
                limiter += 1

            row = row[~row.isnull()]  # removes all Nones

            if row['qname']:  # FIXME: source if you want to add qname functionality
                row.pop('qname')

            if ilx:
                names = row.existing_ids if row.get(
                    'existing_ids') else [row.name]

            for name in names:
                for pred, values in row.items():
                    dpred = self.pred_degrade(pred)

                    for value in values:
                        dvalue = degrade(value)
                        ref_hash[name][dpred][pred][value][dvalue]
                        tail_hash[dvalue] = (
                            name,
                            dpred,
                            pred,
                            value,
                        )

        # makes nested defaultdict into a normal nested dict
        ref_hash = json.dumps(ref_hash)
        return ref_hash, tail_hash

    def compare_hashes(self):
        shared_iris = set(list(self.ref_hash)) & set(list(self.tar_hash))
        unshared_iris = set(list(self.tar_hash)) - set(list(self.ref_hash))
        for shared_iri in shared_iris:
            pass
        count = 0
        for unshared_iri in unshared_iris:
            try:
                data = self.ref_hash[unshared_iri]
                for label in data.keys():
                    ref_hit = self.tail_ref_hash.get(label)
                    if ref_hit:
                        count += 1
            except:
                exit(self.ref_hash)
        print(count)


def main():
    gc = GraphComparator(reference_graph_path='Dropbox/interlex.pickle',
                         target_graph_path='Dropbox/uberon.pickle')


if __name__ == '__main__':
    main()
