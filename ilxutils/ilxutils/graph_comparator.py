from docopt import docopt
from collections import defaultdict
from pathlib import Path as p
from sys import exit
import pandas as pd
from ilxutils.ilx_pred_map import IlxPredMap
from ilxutils.mydifflib import ratio
from ilxutils.tools import *
from ilxutils.graph2pandas import Graph2Pandas
from subprocess import call
from json2html import json2html
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
VERSION = '0.3'

# TODO: need to fill in the unshared iri with matching data and unshared everything to dummy ilx id


class GraphComparator(IlxPredMap):
    def __init__(self,
                 rg_path,
                 tg_path,
                 rg_ilx=False,
                 shorten_names=False,
                 pred_diff=None,
                 partial_diff=False,
                 custom_diff=None,
                 function=None,
                 blacklist=[],
                 both_graphs_contain=True,
                 likeness_threshold=1,
                 dislikeness_threshold=1,):
        IlxPredMap.__init__(self)
        self.rg_path = rg_path
        self.tg_path = tg_path
        self.rgraph = Graph2Pandas(rg_path)
        self.tgraph = Graph2Pandas(tg_path)
        self.rg_ilx = rg_ilx
        self.shorten_names = shorten_names
        self.partial_diff = partial_diff
        self.custom_diff = custom_diff
        self.blacklist = blacklist
        self.both_graphs_contain = both_graphs_contain
        self.diff = self.compare_dataframes()
        self.html = json2html.convert(json=self.diff)
        self.csv_ready_df = None
        self.function = function

    def find_equivalent_pred(self, tpred, column_names):
        eqnames = [
            cn for cn in column_names
            if tpred == self.ext2ilx_map.get(degrade(cn))
        ]
        if not eqnames:
            exit('# FAILED :: find_equivalent_pred :: no eqnames found')
        if len(eqnames) == 1:
            return eqnames[0]
        else:
            for cn in column_names:
                if tpred == self.ext2ilx_map.get(degrade(cn)):
                    print(tpred, cn, self.ext2ilx_map.get(degrade(cn)))
            print(
                '# WARNING :: find_equivalent_pred :: wasnt meant to give back a list'
            )
            return eqnames

    def move_existing_ids_to_index(self, df):
        '''func not used for main but might be useful later on'''
        ex_pred = self.find_equivalent_pred(
            tpred='existing_ids', column_names=df.columns)

        indx = []
        for existing_ids in df[ex_pred]:
            if isinstance(existing_ids, float):
                continue
            for existing_id in existing_ids:
                indx.append(existing_id)

        ndf = pd.DataFrame(columns=list(df.columns), index=set(indx))
        for i, row in df.iterrows():
            if isinstance(row[ex_pred], float):
                continue
            for existing_id in row[ex_pred]:
                ndf.loc[existing_id] = row

        return ndf

    def compare_dataframes(self):
        data = defaultdict(lambda: defaultdict(dict))
        shared_rows, unshared_rows = self.sync_dataframes()
        for rrow, trow in shared_rows:

            rrow = rrow[~rrow.isnull()]
            trow = trow[~trow.isnull()]
            rname = rrow.pop('qname')
            tname = trow.pop('qname')
            print(rname)

            ronly, tonly, both = self.compare_rows(rrow, trow)
            ronly = [v for v in ronly if self.pred_degrade(
                v[0]) not in self.blacklist]
            tonly = [v for v in tonly if self.pred_degrade(
                v[0]) not in self.blacklist]
            both = [(v1,v2)  for v1,v2 in both if self.pred_degrade(v1[0]) not in self.blacklist]

            if not self.shorten_names:
                try:
                    rname = rrow.name
                    tname = trow.name
                except:
                    continue

            if tonly:
                data[rname][p(self.tg_path).stem].update({
                    tname: {
                        'reference_graph_only': ronly,
                        'target_graph_only': tonly,
                        'both_graphs_contain': both,
                    }
                })
                # if self.both_graphs_contain:
                #     data[rname][tname]['both_graphs_contain'] = both

        # FIXME: this is for iris that dont exist in interlex
        #ref_super_hash = defaultdict(list)
        # for i, row in self.rgraph.df.iterrows():
        #    ref_super_hash[degrade(row['rdfs:label'])].append(row.name)
        #    if row['definition:']:
        #        ref_super_hash[degrade(row['definition:'])].append(row.name)

        # unchared but checking for hits in the data itself
        for i, trow in enumerate(unshared_rows):
            if i == 0:
                print('end')
                break
            for j, rrow in self.rgraph.df.iterrows():
                rrow = rrow[~rrow.isnull()]
                trow = trow[~trow.isnull()]
                try:
                    rname = rrow.pop('qname')
                    tname = trow.pop('qname')
                except:
                    tname = trow.name  # tname might not work and this is fine based on the logic

                ronly, tonly, both = self.compare_rows(
                    rrow, trow, whitelist=['label, definition'])

                #temp_trow = {}
                # for tk, tv in trow.items():
                #    temp_trow[self.ext2ilx_map.get(tk)] = tv

                if both:
                    ronly = [v for v in ronly if self.pred_degrade(
                        v[0]) not in self.blacklist]
                    tonly = [v for v in tonly if self.pred_degrade(
                        v[0]) not in self.blacklist]

                    if not self.shorten_names:
                        rname = rrow.name
                        tname = trow.name

                    data[rname][p(self.tg_path).stem].update({
                        tname: {
                            'reference_graph_only': ronly,
                            'target_graph_only': tonly,
                            'hint': both
                        }
                    })
                else:  # if no hits, dump into dummy ilx
                    data['dummy_ilx_id'][p(self.tg_path).stem].update({
                        tname: {
                            'reference_graph_only': None,
                            'target_graph_only': tonly,
                        }
                    })

        for row in unshared_rows:
            is_class = [True for _type in row['rdf:type'] if 'class' in _type.lower()]
            if is_class:
                data[str(p(self.tg_path).stem) + '_only'][row.name]
        return data

    def replace_superclass(self, row, superclass_indx, exids_indx):
        if not isinstance(row[superclass_indx],
                          float) and row[superclass_indx]:
            if self.rgraph.loc_check.get(row[superclass_indx][0]):
                existing_ids = self.rgraph.df.loc[row[superclass_indx][0]][
                    exids_indx]
                if not isinstance(existing_ids, float) and existing_ids:
                    return [ex for ex in existing_ids if '/ilx_' not in ex]
        return row[superclass_indx]

    def sync_dataframes(self):
        row_tuples = []
        shared_iri = {}
        unshared_rows = []
        if self.rg_ilx:  # only if the reference graph is from interlex
            exids_indx = self.find_equivalent_pred('existing_ids',
                                                   self.rgraph.df.columns)
            superclass_indx = self.find_equivalent_pred('superclass',
                                                        self.rgraph.df.columns)

            for i, rrow in self.rgraph.df.iterrows():
                rrow[superclass_indx] = self.replace_superclass(rrow,
                                                                superclass_indx,
                                                                exids_indx)
                existing_ids = rrow.get(exids_indx)
                if isinstance(existing_ids, float) or not existing_ids:
                    continue
                for existing_id in existing_ids:
                    if self.tgraph.loc_check.get(existing_id):
                        row_tuples.append((rrow,
                                           self.tgraph.df.loc[existing_id]))
                        shared_iri[existing_id] = True

        else:  # just comparing 2 random ontologies
            for i, rrow in self.rgraph.df.iterrows():
                if self.rgraph.loc_check.get(rrow.name):
                    print(rrow.name)
                    row_tuples.append((rrow, self.tgraph.df.loc[rrow.name]))

        for i, row in self.tgraph.df.iterrows():
            if not shared_iri.get(row.name):
                unshared_rows.append(row)

        return row_tuples, unshared_rows

    def compare_rows(self, rrow=None, trow=None, whitelist=None):
        ronly, tonly, both, prime_both = [], [], [], []
        pred_needed_in_target = set()
        shared_preds = set()
        for rk, rv in rrow.items():  # reference key, reference value

            ref_com_pred = self.ext2ilx_map.get(degrade(rk))
            if whitelist:
                if ref_com_pred not in whitelist:
                    continue
            if not ref_com_pred:
                continue

            for tk, tv in trow.items():  # target key, target value
                target_com_pred = self.ext2ilx_map.get(degrade(tk))
                if tk[-1] != ':':
                    partial_tar_com_pred = self.ext2ilx_map.get(
                        degrade(tk.split(':')[1]))
                else:
                    partial_tar_com_pred = None

                if target_com_pred == ref_com_pred or partial_tar_com_pred == ref_com_pred:

                    if self.custom_diff:
                        if ref_com_pred not in self.custom_diff:
                            continue

                    if self.partial_diff:
                        shared_preds.add(tk)
                        shared_preds.add(rk)

                    rb, tb = self.compare(rv, tv)
                    if rb or tb:
                        prime_both.extend([((rk, _rb), (tk, _tb))
                                           for _tb, _rb in zip(tb, rb)])
                        both.extend([(tk, _b) for _b in tb])
                        both.extend([(rk, _b) for _b in rb])

        for tk, tvs in trow.items():
            if self.partial_diff:
                if tk in shared_preds:
                    tonly += [(tk, tv) for tv in tvs]
            else:
                tonly += [(tk, tv) for tv in tvs]

        if both:
            tonly = list(set(tonly) - set(both))
        # DEBUG: messy and recalls a lot of functions
        for pred, obj in tonly:
            target_com_pred = self.ext2ilx_map.get(degrade(pred))
            if tk[-1] != ':':
                partial_tar_com_pred = self.ext2ilx_map.get(
                    degrade(pred.split(':')[1]))
            else:
                partial_tar_com_pred = None
            if target_com_pred:
                pred_needed_in_target.add(target_com_pred)
            if partial_tar_com_pred:
                pred_needed_in_target.add(target_com_pred)

        for rk, rvs in rrow.items():
            if self.ext2ilx_map.get(degrade(rk)) in pred_needed_in_target:
                ronly += [(rk, rv) for rv in rvs]

        return ronly, tonly, list(set(prime_both))

    def compare(self, ref_values, target_values):
        if not isinstance(ref_values, list) and not isinstance(
                target_values, list):
            exit('compare_dls :: Types need to be both lists')
        rb, tb = [], []
        for ref_value in ref_values:
            for target_value in target_values:
                if degrade(ref_value) == degrade(target_value):
                    rb.append(ref_value)
                    tb.append(target_value)
        return list(set(rb)), tb


def main():
    '''Create options to read 2 files and only judge but the predicates given.
    Should be a misc add-on for PredFinder. This way if its not empty, you should
    only use this. <f> <f> <pred>. There should also be a html option --html if you
    want the json file to be converted to html
    '''
    doc = docopt(__doc__, version=VERSION)
    args = pd.Series(
        {k.replace('--', '').replace('-', '_'): v
         for k, v in doc.items()})
    print(args)
    if args.partial_diff or args.custom_diff:
        partial_diff = True
    else:
        partial_diff = False

    if args.custom_diff:
        args.ilx = True  # Needs to be forced bc this is the only option it will work
        args.custom_diff = args.custom_diff.split(
            ',') if ',' in args.custom_diff else [args.custom_diff]

    gobj = DfDiff(
        rg_path=args.reference,
        tg_path=args.target,
        rg_ilx=args.ilx,
        shorten_names=args.shorten_names,
        partial_diff=partial_diff,
        custom_diff=args.custom_diff,
        function=args.function)

    # if args.custom_csv:
    #    gobj.partial_csv(args.output)

    if args.csv:
        gobj.csv(args.csv)

    elif args.full_diff:
        if args.csv:
            gobj.csv(args.full_diff)
        cj(gobj.diff, args.full_diff)
        prettify_ontodiff_json(args.full_diff)

    elif args.partial_diff:
        cj(gobj.diff, args.partial_diff)
        prettify_ontodiff_json(args.partial_diff)

    if args.save_pickles:
        gobj.save_pickles()

    if args.html:
        cf(gobj.html, p(args.html).with_suffix('.html'))


'''
>>> python3 compare_graphs.py -c 'label' -o ~/Dropbox/custom_test.csv --csv --function 'add'
>>> python3 compare_graphs --ilx --full-diff-output ~/Dropbox/example.json
'''
if __name__ == '__main__':
    main()
