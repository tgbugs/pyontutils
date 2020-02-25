#!/usr/bin/env python3

import csv
from io import StringIO
import rdflib
import requests
from pyontutils.utils import rowParse
from pyontutils.core import makePrefixes, makeGraph
from pyontutils.namespaces import makePrefixes, TEMP
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint

def main():
    source = 'https://raw.githubusercontent.com/BlueBrain/nat/master/nat/data/modelingDictionary.csv'
    delimiter = ';'


    resp = requests.get(source)
    rows = [r for r in csv.reader(resp.text.split('\n'), delimiter=delimiter) if r and r[0][0] != '#']
    header = ['Record_ID', 'parent_category', 'name','description', 'required_tags']

    PREFIXES = makePrefixes('owl', 'skos', 'ILX', 'definition')
    graph = makeGraph('measures', prefixes=PREFIXES)

    class nat(rowParse):
        def Record_ID(self, value):
            print(value)
            self.old_id = value
            self._id = TEMP[value]
        def parent_category(self, value):
            self.super_old_id = value
            self.super_id = TEMP[value]
        def name(self, value):
            self.hidden = value
            self.label = value.replace('_', ' ')
        def description(self, value):
            self.definition = value
        def required_tags(self, value):
            pass
        def _row_post(self):
            graph.add_class(self._id, self.super_id, label=self.label)
            graph.add_trip(self._id, 'skos:hiddenLabel', self.hidden)
            graph.add_trip(self._id, 'definition:', self.definition)

    asdf = nat(rows, header)
    graph.write()
    if __name__ == '__main__':
        breakpoint()

if __name__ == '__main__':
    main()
