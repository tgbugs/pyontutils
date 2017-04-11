#!/usr/bin/env python3.5

import os
import csv
from glob import glob
import rdflib
from utils import rowParse, async_getter
from scigraph_client import Graph, Vocabulary
from IPython import embed

sgg = Graph(cache=True)
sgv = Vocabulary(cache=True)

def main():
    files = glob(os.path.expanduser('~/git/methodsOntology-upstream/to_be_integrated_in_NIF/*'))
    rows = []
    got_header = False
    for file in files:
        with open(file, 'rt') as f:
            r = [r for r in csv.reader(f, delimiter='|')]
        if got_header:
            r = r[1:]
        else:
            got_header = True
        rows.extend(r)

    def async_func(row):
        resps = sgv.findByTerm(row[2])
        if resps:
            n = resps[0]
            c, l = n['curie'], n['labels'][0]
        else:
            c, l = None, None
        r = row + [c, l]
        return r

    matched = [rows[0] + ['e_curie', 'e_label']] + async_getter(async_func, [(r,) for r in rows[1:]])

    embed()

if __name__ == '__main__':
    main()
