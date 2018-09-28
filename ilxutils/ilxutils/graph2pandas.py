""" Converts owl or ttl or raw rdflib graph into a pandas DataFrame. Saved in .pickle format.

    Usage:
        Graph2Pandas.py [-h | --help]
        Graph2Pandas.py [-v | --version]
        Graph2Pandas.py [-f=<path>] [-a | -t=<str>] [-o=<path>]

    Options:
        -h --help           Display this help message
        -v --version        Current version of file
        -o --output=<path>  Output path of picklized pandas DataFrame
        -f --file=<path>    owl | ttl | rdflib.Graph() -> df.to_pickle
        -t --type=<str>     type of class you want in the ttl file
        -a --all            If seleted you get all types of classes

"""
from docopt import docopt
import pandas as pd
import pickle
from pathlib import Path as p
import rdflib
from rdflib import BNode
from collections import defaultdict
import sys
VERSION = '0.2'


class Graph2Pandas():

    query = """
        select ?subj ?pred ?obj
        where {
            ?subj rdf:type %s .
            ?subj ?pred ?obj .
        } """

    def __init__(self, obj, _type='owl:Class'):
        self.query = self.query % self.eval_type(_type)
        self.g = obj  # could be path
        self.path = obj  # could be graph
        self.rqname = {}
        self.df = self.Graph2Pandas_converter()
        self.loc_check = self.create_loc_check()

    def eval_type(self, _type):
        if _type.lower().strip() == 'all':
            return '?type'
        else:
            return _type

    def save(self, output):
        self.df.to_pickle(output)

    def create_loc_check(self):
        return {index: True for index in self.df.index}

    def qname(self, uri):
        '''Returns qname of uri in rdflib graph while also saving it'''
        try:
            prefix, namespace, name = self.g.compute_qname(uri)
            qname = prefix + ':' + name
            self.rqname[qname] = uri
            return qname
        except:
            try:
                print('prefix:', prefix)
                print('namespace:', namespace)
                print('name:', name)
            except:
                print('Could not print from compute_qname')
            sys.exit('No qname for ' + uri)

    def Graph2Pandas_converter(self):
        '''Updates self.g or self.path bc you could only choose 1'''

        if isinstance(self.path, str) or isinstance(self.path, p):
            self.path = str(self.path)
            filetype = p(self.path).suffix
            if filetype == '.pickle':
                self.g = None
                return pickle.load(open(self.path, 'rb'))
            elif filetype == '.ttl' or filetype == '.rdf':
                self.g = rdflib.Graph()
                self.g.parse(self.path, format='turtle')
                return self.get_sparql_dataframe()
            elif filetype == '.nt':
                self.g = rdflib.Graph()
                self.g.parse(self.path, format='nt')
                return self.get_sparql_dataframe()
            elif filetype == '.owl' or filetype == '.xrdf':
                self.g = rdflib.Graph()
                try:
                    self.g.parse(self.path, format='xml')
                except:
                    # some owl formats are more rdf than owl
                    self.g.parse(self.path, format='turtle')
                return self.get_sparql_dataframe()
            else:
                sys.exit('Format options: owl, ttl, df_pickle, rdflib.Graph()')
            try:
                return self.get_sparql_dataframe()
                self.path = None
            except:
                sys.exit('Format options: owl, ttl, df_pickle, rdflib.Graph()')

        elif isinstance(self.g, rdflib.graph.Graph):
            self.path = None
            return self.get_sparql_dataframe()

        else:
            exit('Obj given is not str, pathlib obj, or an rdflib.Graph()')

    def get_sparql_dataframe(self):
        self.result = self.g.query(self.query)

        cols = set(['qname'])
        indx = set()
        data = {}

        for i, binding in enumerate(self.result.bindings):

            subj_binding = binding[rdflib.term.Variable('subj')]
            pred_binding = binding[rdflib.term.Variable('pred')]
            obj_binding  = binding[rdflib.term.Variable('obj')]

            subj = subj_binding
            pred = self.qname(pred_binding)
            obj  = obj_binding

            # stops at BNodes; could be exanded here
            if isinstance(subj, BNode):
                continue
            elif isinstance(pred, BNode):
                continue
            elif isinstance(obj, BNode) and obj:
                continue
            else:
                subj = str(subj)
                pred = str(pred)
                obj  = str(obj)

            # Prepare defaultdict home if it doesn't exist
            if not data.get(subj):
                data[subj] = defaultdict(list)
                # I really dont think i need this...
                # data[subj]['qname'] = self.qname(subj_binding)

            data[subj][pred].append(obj)
            cols.add(pred)
            indx.add(subj)

        # Building DataFrame
        df = pd.DataFrame(columns=cols, index=indx)
        for key, value in data.items():
            df.loc[str(key)] = pd.Series(value)

        del data

        return df


def main():
    from docopt import docopt
    doc = docopt(__doc__, version=VERSION)
    args = pd.Series({k.replace('--', ''): v for k, v in doc.items()})
    if args.all:
        graph = Graph2Pandas(args.file, _type='all')
    elif args.type:
        graph = Graph2Pandas(args.file, _type=args.type)
    else:
        graph = Graph2Pandas(args.file)
    graph.save(args.output)


if __name__ == '__main__':
    main()
