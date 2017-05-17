#!/usr/bin/env python3

import csv
from io import StringIO
import requests
from pyontutils.utils import rowParse, makePrefixes, makeGraph)

from IPython import embed

source = 'https://raw.githubusercontent.com/BlueBrain/nat/master/nat/modelingDictionary.csv'
delimiter = ';'


resp = requests.get(source)
rows = [r for r in csv.reader(resp.text.split('\n'), delimiter=delimiter) if r and r[0][0] != '#']
header = ['Record_ID', 'parent_category', 'name','description', 'required_tags']

graph = makeGraph('measures.ttl')

class nat(rowParse):
    def Record_ID(self, value):
        print(value)
        pass
    def parent_category(self, value):
        pass
    def name(self, value):
        pass
    def description(self, value):
        pass
    def required_tags(self, value):
        pass

asdf = nat(rows, header)

embed()
