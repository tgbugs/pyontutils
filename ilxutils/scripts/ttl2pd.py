""" Changes turtle files to pandas dataframe stored in pickle. Maintains all its dataself.

Usage:
    ttl2pd.py [-h | --help]
    ttl2pd.py [-v | -- version]
    ttl2pd.py [-f FILE] [-o OUTPUT]

Options:
    -f, --file=<path>       Path to turtle file to be converted to pandas DataFrame
    -o, --output=<path>     Path to output file that is the pickled pandas DataFrame
"""
from docopt import docopt
import pandas as pd
import sys
import rdflib
from collections import defaultdict
import progressbar
VERSION = '0.0.1'



class ttl2pd():

    def __init__(self, graph, query, args):
        self.args = args
        self.g = graph
        self.query = query
        print('Querying...')
        self.result = self.g.query(self.query)
        self.df = self.get_sparql_dataframe()

    def createBar(self, maxval):
        return progressbar.ProgressBar(maxval=maxval, \
            widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])

    def qname(self, uri):
        try:
            prefix, namespace, name = self.g.compute_qname(uri)
            return prefix + ':' + name
        except:
            sys.exit('No qname for '+uri)

    def get_sparql_dataframe(self):

        cols = set()
        indx = set()
        data = {}

        print('=== Organizing Data ===')
        bar = self.createBar(len(self.result.bindings)); bar.start()
        for i, binding in enumerate(self.result.bindings):

            if not data.get(binding[rdflib.term.Variable('subj')]):
                data[binding[rdflib.term.Variable('subj')]] = defaultdict(list)

            subj = binding[rdflib.term.Variable('subj')]
            pred = self.qname(binding[rdflib.term.Variable('pred')])
            obj = binding[rdflib.term.Variable('obj')]

            data[subj][pred].append(obj)
            cols.add(pred)
            indx.add(subj)

            bar.update(i)
        bar.finish()

        df = pd.DataFrame(columns=cols, index=indx)
        bar = self.createBar(len(self.result.bindings)); bar.start()
        for k, v in data.items():
            df.loc[k] = pd.Series(v)

        if self.args.output:
            df.to_pickle(self.args.output)

        return df

def get_df_from_ttl(graph, args):
    classtype = 'owl:Class'
    query= """
        select ?subj ?pred ?obj
        where {
            ?subj ?rdftype %s .
            ?subj ?pred ?obj .
        }
    """ % classtype
    df = ttl2pd(graph, query, args).df
    return df

def main():
    doc = docopt(__doc__, version=VERSION)
    args = pd.Series({k.replace('--',''):v for k, v in doc.items()})

    graph = rdflib.Graph()
    graph.parse(args.file, format='turtle')

    classtype = 'owl:Class'
    query= """
        select ?subj ?pred ?obj
        where {
            ?subj ?rdftype %s .
            ?subj ?pred ?obj .
        }
    """ % classtype

    df = ttl2pd(graph, query, args).df
    print(list(df))

if __name__ == '__main__':
    main()
