#! /usr/bin/env python3.7

import os
import csv
import json
from pathlib import Path
from pyontutils.utils import async_getter
from pyontutils.scigraph import Cypher, Vocabulary

current_file = Path(__file__).absolute()
gitf = current_file.parent.parent.parent

c = Cypher()
v = Vocabulary(cache=True)

def main():
    curies = c.getCuries()
    curies.pop('')  # don't want NIFSTD uris just yet

    with open((gitf / 'nlxeol/neurolex_full.csv').as_posix(), 'rt') as f:
        rows = [r for r in csv.reader(f)]

    Id = rows[0].index('Id')
    ids = [(r[Id],) for r in rows if r[Id] and r[Id] != 'Id' and 'Resource:' not in r[0]]

    items = tuple(curies.items())
    findById = v.findById
    def async_func(id_):
        if ':' in id_:
            out = findById(id_)
            if out:
                return id_, out['curie']
        for prefix, uri in items:
            curie = prefix + ':' + id_
            out = findById(curie)
            if out:
                return id_, out['curie']
        return id_, 'NLXONLY'

    id_curie = async_getter(async_func, ids)
    j = {id_:curie for id_, curie in id_curie}


    with open('/tmp/total_curie_fragment.json', 'wt') as f:
        json.dump(j, f, sort_keys=True, indent=4)

if __name__ == '__main__':
    main()
