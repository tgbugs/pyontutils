""" Intended use is to compare owl or ttl to the ttl created from interlx.

Usage:  compare_graphs.py [-h | --help]
        compare_graphs.py [-v | --version]
        compare_graphs.py [-r=<path>] [-t=<path>] (-f=<path> | -p=<path>) (-i | -n) [-s] [--save-pickles] [--html=<path>]

Options:
    -h --help                          Display this help message
    -v --version                       Current version of file
    -r --reference=<path>              [default: /home/troy/Dropbox/interlex.pickle]
    -t --target=<path>                 [default: /home/troy/Dropbox/uberon.pickle]
    -f --full-diff=<path>              Output path of full comparison, even those that dont have a common diff
    -p --partial-diff=<path>           Output of comparisons that have a similar predicate
    -i --ilx                           Treat reference like its ilx bc it has uniqueness
    -n --noilx                         Sanity check for ilx
    --save-pickles                     If you converted files to pickle it's worth using to save them (will save in folder of src)
    -s --shorten-names                 Condensed the names of iris
    --html=<path>                      Converts the json comparison to html (default being the same path of -p | -d)
"""
VERSION = '0.3'
from docopt import docopt
from collections import defaultdict
from pathlib import Path as p
import sys
import pandas as pd
from ilxutils.args_reader import read_args
from ilxutils.mydifflib import diffcolor, diff, ratio
from ilxutils.tools import *
from ilxutils.graph2pandas import graph2pandas
from subprocess import call
from json2html import *

class PredFinder():
    '''=== LABEL ==='''
    label_scheme = ('label', [
            'rdfs:label',
            'skos:prefLabel'
        ])
    '''=== DEFINITION ==='''
    definition_scheme = ('definition', [
            'definition:',
            'skos:definition',
            'NIFRID:birnlexDefinition',
            'NIFRID:externallySourcedDefinition',
            'obo:IAO_0000115'
        ])
    '''=== SYNONYM ==='''
    synonym_scheme = ('synonym', [
            'oboInOwl:hasExactSynonym',
            'oboInOwl:hasNarrowSynonym',
            'oboInOwl:hasBroadSynonym',
            'oboInOwl:hasRelatedSynonym',
            'go:systematic_synonym',
            'NIFRID:synonym',
        ])
    '''=== SUPERCLASS ==='''
    superclass_scheme = ('superclass', [
            'rdfs:subClassOf',
        ])
    '''=== TYPE ==='''
    type_scheme = ('type', [
            'rdf:type',
        ])
    '''=== EXISTING IDS ==='''
    exids_scheme = ('existing_ids', [
            'ilxtr:existingIds',
            'ilxtr:existingId',
        ])
    total_scheme = [
        label_scheme,
        definition_scheme,
        synonym_scheme,
        superclass_scheme,
        type_scheme,
        exids_scheme,
    ]

    def __init__(self):
        self.pred_map = self.compress(list(map(self.unpack, self.total_scheme)))
        self.pred_types = self.get_pred_types()

    def get_pred_types(self):
        return [pt[0] for pt in self.total_scheme]

    def unpack(self, scheme):
        common_name = scheme[0]
        pred_map = {}
        for pred in scheme[1]:
            pred = degrade(pred)
            pred_map[pred] = common_name
            if ':' in pred:
                pred_map[pred.split(':')[1]] = common_name
        return pred_map

    def compress(self, listobj):
        if isinstance(listobj[0], list):
            obj = []
            for item in listobj:
                obj += item
        elif isinstance(listobj[0], dict):
            obj = {}
            for item in listobj:
                obj.update({**item})
        else:
            sys.exit('pred_finder:compress -> cannot compress this list')
        return obj

class GraphComparator(PredFinder):

    def __init__(self, rg_path, tg_path, rg_ilx=False, shorten_names=False, pred_diff=None,
                    get_only_partial_diff=False):
        PredFinder.__init__(self)
        self.rg_path = rg_path
        self.tg_path = tg_path
        self.rgraph = graph2pandas(rg_path)
        self.tgraph = graph2pandas(tg_path)
        self.rg_ilx = rg_ilx
        self.shorten_names = shorten_names
        self.get_only_partial_diff = get_only_partial_diff
        self.diff = self.compare_dataframes()
        self.html = json2html.convert(json = self.diff)

    def find_equivalent_pred(self, tpred, column_names):
        eqnames = [cn for cn in column_names if tpred == self.pred_map.get(degrade(cn))]
        if not eqnames:
            sys.exit('# FAILED :: find_equivalent_pred :: no eqnames found')
        if len(eqnames) == 1:
            return eqnames[0]
        else:
            print('# WARNING :: find_equivalent_pred :: wasnt meant to give back a list')
            return eqnames

    def move_existing_ids_to_index(self, df):
        '''func not used for main but might be useful later on'''
        ex_pred = self.find_equivalent_pred(tpred='existing_ids', column_names=df.columns)

        indx = []
        for existing_ids in df[ex_pred]:
            if isinstance(existing_ids, float): continue
            for existing_id in existing_ids:
                indx.append(existing_id)

        ndf = pd.DataFrame(columns=list(df.columns), index=set(indx))
        for i, row in df.iterrows():
            if isinstance(row[ex_pred], float): continue
            for existing_id in row[ex_pred]:
                ndf.loc[existing_id] = row

        return ndf

    def compare_dataframes(self):
        data = defaultdict(list)
        for rrow, trow in self.sync_dataframes():

            rrow = rrow[~rrow.isnull()]
            trow = trow[~trow.isnull()]
            rname = rrow.pop('qname')
            tname = trow.pop('qname')

            ronly, tonly, both = self.compare_rows(rrow, trow) #each are a tuple

            #You need the graph to be built from owl or ttl source to have qnames
            if not self.shorten_names:
                rname = rrow.name
                tname = trow.name

            data[rname].append({
                tname : {
                    'reference_graph_only' : ronly,
                    'target_graph_only'    : tonly,
                    'both_graphs_contain'  : both,
                }
            })

        return data

    def replace_superclass(self, row, superclass_indx, exids_indx):
        if not isinstance(row[superclass_indx], float) and row[superclass_indx]:
            if self.rgraph.loc_check.get(row[superclass_indx][0]):
                existing_ids=self.rgraph.df.loc[row[superclass_indx][0]][exids_indx]
                if not isinstance(existing_ids, float) and existing_ids:
                    return [ex for ex in existing_ids if '/ilx_' not in ex]
        return row[superclass_indx]

    def sync_dataframes(self):
        row_tuples = []
        if self.rg_ilx: #only if the reference graph is from interlex
            exids_indx = self.find_equivalent_pred('existing_ids', self.rgraph.df.columns)
            superclass_indx = self.find_equivalent_pred('superclass', self.rgraph.df.columns)

            for i, rrow in self.rgraph.df.iterrows():
                rrow[superclass_indx] = self.replace_superclass(rrow, superclass_indx, exids_indx)
                existing_ids = rrow.get(exids_indx)
                if isinstance(existing_ids, float) or not existing_ids:
                    continue
                for existing_id in existing_ids:
                    if self.tgraph.loc_check.get(existing_id):
                        row_tuples.append((rrow, self.tgraph.df.loc[existing_id]))

        else: #just comparing 2 random ontologies
            for i, rrow in self.rgraph.df.iterrows():
                if self.rgraph.loc_check.get(rrow.name):
                    print(rrow.name)
                    row_tuples.append((rrow, self.tgraph.df.loc[rrow.name]))

        return row_tuples

    def compare_rows(self, rrow=None, trow=None):
        ronly, tonly, both = [], [], []
        ronly_both_filter = []
        shared_preds = set()
        for rk, rv in rrow.items(): #reference key, reference value

            ref_com_pred = self.pred_map.get(degrade(rk))
            if not ref_com_pred:
                continue

            for tk, tv in trow.items(): #target key, target value

                target_com_pred = self.pred_map.get(degrade(tk))
                partial_tar_com_pred = self.pred_map.get(degrade(tk.split(':')[1]))

                if target_com_pred == ref_com_pred or partial_tar_com_pred == ref_com_pred:

                    if self.get_only_partial_diff:
                        shared_preds.add(tk)
                        shared_preds.add(rk)

                    tb, rb = self.compare(rv, tv)
                    if rb or tb:
                        both.extend([(tk, _b) for _b in tb])
                        both.extend([(rk, _b) for _b in rb])

        for rk, rvs in rrow.items():
            if self.get_only_partial_diff:
                if rk in shared_preds:
                    ronly += [(rk, rv) for rv in rvs]
            else:
                ronly += [(rk, rv) for rv in rvs]

        for tk, tvs in trow.items():
            if self.get_only_partial_diff:
                if tk in shared_preds:
                    tonly += [(tk, tv) for tv in tvs]
            else:
                tonly += [(tk, tv) for tv in tvs]

        ronly = list(set(ronly) - set(both))
        tonly = list(set(tonly) - set(both))
        return ronly, tonly, list(set(both))

    def compare(self, ref_values, target_values):
        if not isinstance(ref_values, list) and not isinstance(target_values, list):
            sys.exit('compare_dls :: Types need to be both lists')
        rb, tb = [], []
        for ref_value in ref_values:
            ref_visited = False
            for target_value in target_values:
                if degrade(ref_value) == degrade(target_value):
                    rb.append(ref_value)
                    tb.append(target_value)
        return list(set(rb)), tb

    def panel_comparison(self):
        '''
        Going to cross literally everything and create a new matrix from expanded
        cells to make a 1/0 matrix
        '''
        pass

    def save_pickles(self):
        self.rgraph.df.to_pickle(p(self.rg_path).with_suffix('.pickle'))
        print('Saved:', p(self.rg_path).with_suffix('.pickle'))
        self.tgraph.df.to_pickle(p(self.tg_path).with_suffix('.pickle'))
        print('Saved:', p(self.tg_path).with_suffix('.pickle'))

def prettify_ontodiff_json(output):
    if '.json' not in output:
        output += '.json'
    shellcommand = 'ex -s +\'g/\[[\ \\n]\+"/j4\' -cwq ' + output
    if call(shellcommand, shell=True) == 1:
        print('Could not prettify the json file')
    else:
        print('Prettify Complete For:', output)

def main():
    '''Create options to read 2 files and only judge but the predicates given.
    Should be a misc add-on for PredFinder. This way if its not empty, you should
    only use this. <f> <f> <pred>. There should also be a html option --html if you
    want the json file to be converted to html
    '''
    doc = docopt(__doc__, version=VERSION)
    args = pd.Series({k.replace('--','').replace('-', '_'):v for k, v in doc.items()})

    if args.partial_diff:
        get_only_partial_diff = True
    else:
        get_only_partial_diff = False

    gobj = GraphComparator( rg_path=args.reference,
                            tg_path=args.target,
                            rg_ilx=args.ilx,
                            shorten_names=args.shorten_names,
                            get_only_partial_diff=get_only_partial_diff)

    if args.save_pickles:
        gobj.save_pickles()

    if args.html:
        cf(gobj.html, p(args.html).with_suffix('.html'))

    if args.full_diff:
        cj(gobj.diff, args.full_diff)
        prettify_ontodiff_json(args.full_diff)

    if args.partial_diff:
        cj(gobj.diff, args.partial_diff)
        prettify_ontodiff_json(args.partial_diff)
'''
>>> python3 compare_graphs --ilx --full-diff-output ~/Dropbox/example.json
'''
if __name__ == '__main__':
    main()
