#!/usr/bin/env python3
import os
import inspect
from git.repo import Repo
from rdflib import Graph, URIRef
from pyontutils.neurons import *
from IPython import embed

__all__ = [
    'AND',
    'OR',
    'graphBase',
    'config',
    'pred',
    'setLocalContext',
    'getLocalContext',
    'setLocalNames',
    'getLocalNames',
    'Phenotype',
    'NegPhenotype',
    'LogicalPhenotype',
    'Neuron',
]

def config(remote_base=       'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/',
           local_base=        os.path.expanduser('~/git/NIF-Ontology/'),
           branch=            'neurons',
           core_graph_paths= ['ttl/NIF-Phenotype-Core.ttl',
                              'ttl/NIF-Phenotypes.ttl'],
           core_graph=        None,
           in_graph_paths=    tuple(),
           out_graph_path=    '/tmp/_Neurons.ttl',
           out_imports=      ['ttl/NIF-Phenotype-Core.ttl'],
           out_graph=         None,
           force_remote=      False,
           scigraph=          'localhost:9000'):
    """ Wraps graphBase.configGraphIO to provide a set of sane defaults
        for input ontologies and output files. """
    graphBase.configGraphIO(remote_base, local_base, branch,
                            core_graph_paths, core_graph,
                            in_graph_paths,
                            out_graph_path, out_imports, out_graph,
                            force_remote, scigraph)

# init the config and make sure pred is bound
config()
pred = graphBase._predicates

# add a handy ipython line magic for scig to look up terms
try:
    ip = get_ipython()
    python_magic = ip.find_cell_magic('python')
    def scig_func(*vals):
        python_magic('-m pyontutils.scig ' + ' '.join(vals), '')
    ip.register_magic_function(scig_func, 'line', 'scig')
except NameError:
    pass  # not in an IPython environment so can't register magics


if __name__ == '__main__':
    main()
