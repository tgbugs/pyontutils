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
from pathlib import Path as p
VERSION = '0.0.1'



class ttl2pd():

    def __init__(self, graph, query, args=None):
        self.args = args
        self.g = graph
        self.query = query
        print('Querying...')
        self.result = self.g.query(self.query)
        self.df = self.get_sparql_dataframe()

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

        print('Organizing Data...')
        for i, binding in enumerate(self.result.bindings):

            subj = str(binding[rdflib.term.Variable('subj')])
            pred = str(self.qname(binding[rdflib.term.Variable('pred')]))
            obj = str(binding[rdflib.term.Variable('obj')])

            if not data.get(subj):
                data[subj] = defaultdict(list)

            data[subj][pred].append(obj)
            cols.add(pred)
            indx.add(subj)

        print('Building DataFrame...')
        df = pd.DataFrame(columns=cols, index=indx)
        for key, value in data.items():
            for k, v in value.items(): #It was annoying to always deal with lists
                #v = [str(e) for e in v]
                if len(v) == 1:
                    value[k] = v[0]
                else:
                    value[k] = v

            df.loc[str(key)] = pd.Series(value)

        if self.args:
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

def local_ttl2pd(infile):
    graph = rdflib.Graph()
    if p(infile).suffix == '.ttl':
        graph.parse(infile, format='turtle')
    elif p(infile).suffix == '.owl':
        graph.parse(infile, format='xml')
    else:
        sys.exit('file format must be ttl or owl.')
    query = """
        select ?subj ?pred ?obj
        where {
            ?subj rdf:type owl:Class .
            ?subj ?pred ?obj .
        }
    """
    return ttl2pd(graph, query).df

def main():
    doc = docopt(__doc__, version=VERSION)
    args = pd.Series({k.replace('--',''):v for k, v in doc.items()})

    graph = rdflib.Graph()
    graph.parse(args.file, format='turtle')

    #FIXME if you want just classes; should add this as an option
    classtype = 'owl:Class'
    query= """
        select ?subj ?pred ?obj
        where {
            ?subj ?rdftype %s .
            ?subj ?pred ?obj .
        }
    """ % classtype

    query= """
        select ?subj ?pred ?obj
        where {
            ?subj rdf:type ?type .
            ?subj ?pred ?obj .
        }
    """

    df = ttl2pd(graph, query, args).df
    #print(list(df))
    print('=== COMPLETE ===')

if __name__ == '__main__':
    main()
