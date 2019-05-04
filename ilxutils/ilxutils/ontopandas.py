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
        -a --all            If seleted you get all types of classes """

from collections import defaultdict
from docopt import docopt
import pandas as pd
from pathlib import Path as p
import pickle
import rdflib
from rdflib import BNode
from sys import exit
from typing import Union, List, Dict
from ilxutils.tools import create_pickle, open_pickle
VERSION = '0.5' # fixed NaN issue in empty cells


class OntoPandas:

    ''' Goal is to speed up and clean up ontologies into a pd.DataFrame and more object. Can be
        transformed back into whatever original or different ontological format. Sparql is used to
        get a more specific batch from the original ontology in one go. You could get all or some,
        thats the beauty in it. '''

    defaultquery = """
        select ?subj ?pred ?obj
        where {
            ?subj rdf:type owl:Class ;
                  ?pred ?obj .
        } """

    def __init__(self,
                 obj: Union[rdflib.graph.Graph, str],
                 query:str=defaultquery,
                 qnamed:bool=False,
                 str_vals:bool=False,) -> None:
        self.query = query
        self.qnamed = qnamed
        self.str_vals = str_vals
        self.g = obj  # could be path
        self.path = obj  # could be graph
        self.df = self.Graph2Pandas_converter()

    def create_pickle(self, output: str) -> None:
        with open(output, 'wb') as outfile:
            pickle.dump(data, outfile)
            outfile.close()

    def save(self, foldername: str, path_to_folder: str=None) -> None:
        ''' Saves entities into multiple files within the same folder because of pickle-recursive
            errors that would happen if squeezed into one '''
        self.create_pickle((self.g.namespaces, ))
        self.df.to_pickle(output)

    def qname(self, uri: str) -> str:
        ''' Returns qname of uri in rdflib graph while also saving it '''
        try:
            prefix, namespace, name = self.g.compute_qname(uri)
            qname = prefix + ':' + name
            return qname
        except:
            try:
                print('prefix:', prefix)
                print('namespace:', namespace)
                print('name:', name)
            except:
                print('Could not print from compute_qname')
            exit('No qname for ' + uri)

    def Graph2Pandas_converter(self):
        '''Updates self.g or self.path bc you could only choose 1'''

        if isinstance(self.path, str) or isinstance(self.path, p):
            self.path = str(self.path)
            filetype = p(self.path).suffix
            if filetype == '.pickle':
                self.g = pickle.load(open(self.path, 'rb'))
                if isinstance(self.g, rdflib.graph.Graph):
                    return self.get_sparql_dataframe()
                else:
                    print('WARNING:: function df() wont work unless an ontology source is loaded')
                    return self.g
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
                exit('Format options: owl, ttl, df_pickle, rdflib.Graph()')
            try:
                return self.get_sparql_dataframe()
                self.path = None
            except:
                exit('Format options: owl, ttl, df_pickle, rdflib.Graph()')

        elif isinstance(self.g, rdflib.graph.Graph):
            self.path = None
            return self.get_sparql_dataframe()

        else:
            exit('Obj given is not str, pathlib obj, or an rdflib.Graph()')

    def get_sparql_dataframe_deprecated_memory_problem(self):
        ''' Iterates through the sparql table and condenses it into a Pandas DataFrame
        !!! OLD !!! Eats up double the memory and produces lists for everything that has a value '''

        self.result = self.g.query(self.query)
        cols = set() # set(['qname'])
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

        del data # to take care of the memory problem if you are stacking this function

        df = df.where((pd.notnull(df)), None) # default Null is fricken Float NaN

        return df

    def get_sparql_dataframe( self ):
        ''' Iterates through the sparql table and condenses it into a Pandas DataFrame '''
        self.result = self.g.query(self.query)
        cols = set() # set(['qname'])
        indx = set()
        data = {}
        curr_subj = None # place marker for first subj to be processed
        bindings = []

        for i, binding in enumerate(self.result.bindings):
            subj_binding = binding[rdflib.term.Variable('subj')]
            pred_binding = binding[rdflib.term.Variable('pred')]
            obj_binding  = binding[rdflib.term.Variable('obj')]

            subj = subj_binding
            pred = pred_binding
            obj  = obj_binding

            # stops at BNodes; could be exanded here
            if isinstance(subj, BNode):
                continue
            elif isinstance(pred, BNode):
                continue
            elif isinstance(obj, BNode) and obj:
                continue

            if self.qnamed:
                pred = self.qname(pred_binding)

            if self.str_vals:
                subj = str(subj)
                pred = str(pred)
                obj  = str(obj)

            cols.add(pred)
            indx.add(subj)
            bindings.append(binding)

        bindings = sorted(bindings, key=lambda k: k[rdflib.term.Variable('subj')])
        df = pd.DataFrame(columns=cols, index=indx)

        for i, binding in enumerate(bindings):

            subj_binding = binding[rdflib.term.Variable('subj')]
            pred_binding = binding[rdflib.term.Variable('pred')]
            obj_binding  = binding[rdflib.term.Variable('obj')]

            subj = subj_binding
            pred = pred_binding
            obj  = obj_binding

            # stops at BNodes; could be exanded here
            if isinstance(subj, BNode):
                continue
            elif isinstance(pred, BNode):
                continue
            elif isinstance(obj, BNode) and obj:
                continue

            if self.qnamed:
                pred = self.qname(pred_binding)

            if self.str_vals:
                subj = str(subj)
                pred = str(pred)
                obj  = str(obj)

            if curr_subj == None:
                curr_subj = subj
                if not data.get(subj): # Prepare defaultdict home if it doesn't exist
                    data[subj] = defaultdict(list)
                data[subj][pred].append(obj)
            elif curr_subj != subj:
                curr_subj = subj
                for data_subj, data_pred_objs in data.items():
                    for data_pred, data_objs in data_pred_objs.items():
                        if len(data_objs) == 1: # clean lists of just 1 value
                            data_pred_objs[data_pred] = data_objs[0]
                    df.loc[data_subj] = pd.Series(data_pred_objs)
                data = {}
                if not data.get(subj): # Prepare defaultdict home if it doesn't exist
                    data[subj] = defaultdict(list)
                data[subj][pred].append(obj)
            else:
                if not data.get(subj): # Prepare defaultdict home if it doesn't exist
                    data[subj] = defaultdict(list)
                data[subj][pred].append(obj)

        for data_subj, data_pred_objs in data.items():
            for data_pred, data_objs in data_pred_objs.items():
                if len(data_objs) == 1: # clean lists of just 1 value
                    data_pred_objs[data_pred] = data_objs[0]
            df.loc[data_subj] = pd.Series(data_pred_objs)

        df = df.where((pd.notnull(df)), None) # default Null is fricken Float NaN
        df = df.reset_index().rename(columns={'index':'iri'})
        return df


def command_line():
    ''' If you want to use the command line '''
    from docopt import docopt
    doc = docopt( __doc__, version=VERSION )
    args = pd.Series({k.replace('--', ''): v for k, v in doc.items()})
    if args.all:
        graph = Graph2Pandas(args.file, _type='all')
    elif args.type:
        graph = Graph2Pandas(args.file, _type=args.type)
    else:
        graph = Graph2Pandas(args.file)
    graph.save(args.output)


if __name__ == '__main__':
    command_line()
