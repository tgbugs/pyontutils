""" Converts owl or ttl or raw rdflib graph into a pandas DataFrame. Saved in .pickle format.

Usage:
    clean_ontology_df.py [-h | --help]
    clean_ontology_df.py [-v | --version]
    clean_ontology_df.py [options]

Options:
    -h --help               Display this help message
    -v --version            Current version of file
    -d --dataframe=<path>
    -o --output=<path>
"""
from docopt import docopt
from ilxutils.ilx_pred_map import IlxPredMap
from ilxutils.tools import open_pickle, create_json
from pathlib import Path as p
VERSION = '0.0.2'


ipm = IlxPredMap()


def clean_ontology_df(ontology, extras=[]):

    cols = set()
    records = []

    # Find all accepted columns
    for i, row in ontology.iterrows():
        row = row[~row.isnull()]
        for pred, objs in row.items():
            if ipm.accepted_pred(pred, extras=extras):
                pred = ipm.clean_pred(pred, ignore_warning=True)
                cols.add(pred)

    # Fill in data from accepted columns
    for i, row in ontology.iterrows():
        row = row[~row.isnull()]
        data = {p:None for p in cols}
        for pred, objs in row.items():
            if ipm.accepted_pred(pred, extras=extras):
                pred = ipm.clean_pred(pred, ignore_warning=True)
                data[pred] = objs
        data['iri'] = row.name.rsplit('/', 1)[-1]
        records.append(data)

    return records


def main():
    doc = docopt(__doc__, version=VERSION)
    ontology = open_pickle(doc['--dataframe'])
    records = clean_ontology_df(ontology=ontology, extras=['termui'])
    create_json(records, doc['--output'])

if __name__ == '__main__':
    main()
