#! /usr/bin/env python3.6

import os
import csv
import json
from pyontutils.scigraph import Cypher, Vocabulary
from utils import async_getter

c = Cypher()
v = Vocabulary(cache=True, basePath='http://localhost:9000/scigraph')

curies = c.getCuries()
curies.pop('')  # don't want NIFSTD uris just yet

with open(os.path.expanduser('~/git/nlxeol/neurolex_full.csv'), 'rt') as f:
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

