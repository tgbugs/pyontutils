#!/usr/bin/env python3
import inspect
from git.repo import Repo
from rdflib import Graph, URIRef
from pyontutils.neurons import *
from IPython import embed

current_file = Path(__file__).absolute()

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

def config(remote_base=       'https://github.com/SciCrunch/NIF-Ontology/raw',
           local_base=        (current_file.parent.parent.parent /
                               'NIF-Ontology').as_posix(),
           branch=            'neurons',
           core_graph_paths= ['ttl/phenotype-core.ttl',
                              'ttl/phenotypes.ttl'],
           core_graph=        None,
           in_graph_paths=    tuple(),
           out_graph_path=    '/tmp/_Neurons.ttl',
           out_imports=      ['ttl/phenotype-core.ttl'],
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
    pred = graphBase._predicates
    return pred  # because the python module system is opinionated :/

try:
    pred = config()
except FileNotFoundError as e:
    pred = None
    from pyontutils.utils import TermColors as tc
    print(e)
    print(tc.red('WARNING:'),
          'config() failed to run at import (see the above error). Please',
          'call pred = config(*args, **kwargs) again in your local file with',
          'corrected arguments.')

# set the import to this file instead of neurons
graphBase.__import_name__ = __name__

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
