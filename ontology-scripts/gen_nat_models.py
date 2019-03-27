#!/usr/bin/env python3

import csv
from io import StringIO
import rdflib
import requests
from pyontutils.utils import rowParse
from pyontutils.core import makePrefixes, makeGraph
from pyontutils.ilx_utils import ILXREPLACE
from pyontutils.namespaces import makePrefixes
from IPython import embed

def main():
    source = 'https://raw.githubusercontent.com/BlueBrain/nat/master/nat/data/modelingDictionary.csv'
    delimiter = ';'


    resp = requests.get(source)
    rows = [r for r in csv.reader(resp.text.split('\n'), delimiter=delimiter) if r and r[0][0] != '#']
    header = ['Record_ID', 'parent_category', 'name','description', 'required_tags']

    PREFIXES = makePrefixes('owl','skos','ILX','ILXREPLACE','definition')
    graph = makeGraph('measures', prefixes=PREFIXES)

    class nat(rowParse):
        def Record_ID(self, value):
            print(value)
            self.old_id = value
            self._id = ILXREPLACE(value)
        def parent_category(self, value):
            self.super_old_id = value
            self.super_id = ILXREPLACE(value)
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
        embed()

if __name__ == '__main__':
    main()
