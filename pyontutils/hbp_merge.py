#!/usr/bin/env python3.6

import os
import csv
from glob import glob
from pathlib import Path
import rdflib
from pyontutils.utils import rowParse, async_getter
from pyontutils.scigraph import Graph, Vocabulary
from IPython import embed

current_file = Path(__file__).absolute()
gitf = current_file.parent.parent.parent

sgg = Graph(cache=True)
sgv = Vocabulary(cache=True)

def main():
    files = glob((gitf / 'methodsOntology-upstream/to_be_integrated_in_NIF/').as_posix() + '*')
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
