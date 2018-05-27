""" Intended use is to compare either an owl or ttl file to the ttl file
    pertaining to current ilx database.

TODO
-figure out what options you want
-concat pds and groupby.
-find a way to n**2 check each value without it being crazy in time

BUGS
-currently has list in labels ex [Regional part of gustatory epithelium (nifext 13)]
    also has "Regional part of gustatory epithelium" in it but should be in its
    own ilx row

Author: Troy Michael Sincomb
"""
VERSION = '0.1'
from collections import defaultdict
import json
import pandas as pd
from pathlib import Path as p
import pickle
import rdflib
import re
import requests as r
from sqlalchemy import create_engine, inspect, Table, Column
import subprocess as sb
import sys
from time import time
from ilxutils.args_reader import read_args
from ilxutils.interlex_sql import interlex_sql
from ilxutils.mydifflib import diffcolor, diff, ratio
from ilxutils.scicrunch_client import scicrunch
from IPython.core.display import display



class Graph2Pandas():

    query = """
        select ?subj ?pred ?obj
        where {
            ?subj rdf:type owl:Class .
            ?subj ?pred ?obj .
        } """

    def __init__(self, obj):
        self.g = obj #could be path
        self.path = obj #could be graph
        self.rqname = {}
        self.df = self.graph2pandas_converter()

    def qname(self, uri):
        '''Returns qname of uri in rdflib graph while also saving it'''
        try:
            prefix, namespace, name = self.g.compute_qname(uri)
            qname = prefix + ':' + name
            self.rqname[qname] = uri
            return qname
        except:
            sys.exit('No qname for '+uri)

    def graph2pandas_converter(self):
        '''Updates self.g or self.path bc you could only choose 1'''
        if isinstance(self.path, str):
            print(self.path)
            filetype = p(self.path).suffix
            if filetype == '.pickle':
                self.g = None
                return pickle.load(open(self.path, 'rb'))
            elif filetype == '.ttl':
                self.g = rdflib.Graph()
                self.g.parse(self.path, format='turtle')
                return self.get_sparql_dataframe()
            elif filetype == '.owl':
                self.g = rdflib.Graph()
                self.g.parse(path, format='xml')
                return self.get_sparql_dataframe()
        else:
            try:
                return self.get_sparql_dataframe()
                self.path = None
            except:
                sys.exit('Format options: owl, ttl, df_pickle, rdflib.Graph()')

    def get_sparql_dataframe(self):

        print('Querying...')
        self.result = self.g.query(self.query)

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
            for k, v in value.items():
                if len(v) == 1: #It was annoying to always deal with lists
                    value[k] = v[0]
                else:
                    value[k] = v
            df.loc[str(key)] = pd.Series(value)
        print('Completed Pandas!!!')
        return df

class Graph_Comparator():

    def __init__(self, tgraph, rgraph):
        self.tgraph = Graph2Pandas(tgraph)
        self.rgraph = Graph2Pandas(rgraph)
        self.graph_diff_df = self.compare_graphs()

    def compare_graphs(self):
        #expand qname for ilx and comp. it with qnames expanded with coln names
        '''
        '''
        pass

def main():
    args = read_args(VERSION=VERSION, production=True)
    print(args.target_graph)
    gobj = Graph_Comparator(rgraph=args.reference_graph,
                            tgraph=args.target_graph)
    print(gobj.tdf.df.head(1))
    print(gobj.rdf.df.head(1))

if __name__ == '__main__':
    main()
