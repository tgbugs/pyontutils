#!/usr/bin/env python3
import inspect
from pathlib import Path
from git.repo import Repo
from rdflib import Graph, URIRef
from neurondm import *
from pyontutils.utils import subclasses
from neurondm.core import NeuronBase, auth, ont_checkout_ok  # FIXME temporary until we can rework the config

__all__ = [
    'AND',
    'OR',
    'graphBase',
    'Config',
    'setLocalContext',
    'getLocalContext',
    'setLocalNames',
    'getLocalNames',
    'resetLocalNames',
    'Phenotype',
    'NegPhenotype',
    'EntailedPhenotype',
    'NegEntailedPhenotype',
    'LogicalPhenotype',
    'EntailedLogicalPhenotype',
    'Neuron',
    'NeuronCUT',
    'NeuronEBM',
    'OntId',
    'OntTerm',
    'ilxtr',  # FIXME
    '_NEURON_CLASS',  # FIXME
    '_CUT_CLASS',
    '_EBM_CLASS',
]


# XXX deprecated kept around until other code can be refactored
def config(remote_base=       'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/',
           local_base=        None,  # auth.get_path('ontology-local-repo') by default
           branch=            auth.get('neurons-branch'),
           core_graph_paths= ['ttl/phenotype-core.ttl',
                              'ttl/phenotypes.ttl'],
           core_graph=        None,
           in_graph_paths=    tuple(),
           out_graph_path=    '/tmp/_Neurons.ttl',
           out_imports=      ['ttl/phenotype-core.ttl'],
           out_graph=         None,
           prefixes=          tuple(),
           force_remote=      False,
           checkout_ok=       ont_checkout_ok,
           scigraph=          None,  # defaults to auth.get('scigraph-api')
           iri=               None,
           sources=           tuple(),
           source_file=       None,
           use_local_import_paths=True,
           ignore_existing=   True):
    """ Wraps graphBase.configGraphIO to provide a set of sane defaults
        for input ontologies and output files. """
    graphBase.configGraphIO(remote_base=remote_base,
                            local_base=local_base,
                            branch=branch,
                            core_graph_paths=core_graph_paths,
                            core_graph=core_graph,
                            in_graph_paths=in_graph_paths,
                            out_graph_path=out_graph_path,
                            out_imports=out_imports,
                            out_graph=out_graph,
                            prefixes=prefixes,
                            force_remote=force_remote,
                            checkout_ok=checkout_ok,
                            scigraph=scigraph,
                            iri=iri,
                            sources=sources,
                            source_file=source_file,
                            use_local_import_paths=use_local_import_paths,
                            ignore_existing=ignore_existing)

    pred = graphBase._predicates
    return pred  # because the python module system is opinionated :/

#try:
    #pred = config()
#except FileNotFoundError as e:
    #pred = None
    #from pyontutils.utils import TermColors as tc
    #print(e)
    #print(tc.red('WARNING:'),
          #'config() failed to run at import (see the above error). Please',
          #'call pred = config(*args, **kwargs) again in your local file with',
          #'corrected arguments.')

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
    pass  # not in an ipython environment so can't register magics


if __name__ == '__main__':
    main()
