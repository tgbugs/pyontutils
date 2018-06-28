#!/usr/bin/env python3
import inspect
from pathlib import Path
from git.repo import Repo
from rdflib import Graph, URIRef
from pyontutils.neurons import *
from pyontutils.core import OntId
from pyontutils.config import devconfig
from IPython import embed

__all__ = [
    'AND',
    'OR',
    'graphBase',
    'Config',
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
    '_CHECKOUT_OK',
]


class Config:
    _subclasses = set()
    def __init__(self,
                 name =                 'test-neurons',
                 prefixes =             tuple(),  # dict or list
                 imports =              tuple(),  # iterable
                 import_from_local =    True,  # also load from local?
                 ):
        import os  # FIXME probably should move some of this to neurons.py?
        imports = list(imports)
        imports += ['NIFTTL:phenotype-core.ttl', 'NIFTTL:phenotypes.ttl']
        remote = OntId('NIFTTL:')
        local = Path(devconfig.ontology_local_repo, 'ttl')
        out_local_base = Path(devconfig.ontology_local_repo, 'ttl/generated/neurons')
        out_remote_base = os.path.join(remote.iri, 'generated/neurons')
        out_base = out_local_base if False else out_remote_base  # TODO switch or drop local?
        imports = [OntId(i) for i in imports]

        remote_base = remote.iri.rsplit('/', 2)[0]
        local_base = local.parent

        if import_from_local:
            # NOTE: we currently do the translation more ... inelegantly inside of config so we
            # have to keep the translation layer out here (sigh)
            core_graph_paths = [Path(local, i.iri.replace(remote.iri, '')).relative_to(local_base).as_posix()
                                if remote.iri in i.iri else
                                i for i in imports]
        else:
            core_graph_paths = imports

        out_graph_path = (out_local_base / f'{name}.ttl')

        class lConfig(self.__class__):
            iri = os.path.join(out_remote_base, f'{name}.ttl')

        self.__class__._subclasses.add(lConfig)

        self.pred = config(remote_base = remote_base,  # leave it as raw for now?
                           local_base = local_base.as_posix(),
                           core_graph_paths = core_graph_paths,
                           out_graph_path = out_graph_path.as_posix(),
                           out_imports = imports, #[i.iri for i in imports],
                           prefixes = prefixes,
                           force_remote = not import_from_local,
                           branch = 'neurons',
                           iri = lConfig.iri,
                           use_local_import_paths = False)  # FIXME conflation of import from local and render with local


def config(remote_base=       'https://github.com/SciCrunch/NIF-Ontology/raw',
           local_base=        None,  # devconfig.ontology_local_repo by default
           branch=            'neurons',
           core_graph_paths= ['ttl/phenotype-core.ttl',
                              'ttl/phenotypes.ttl'],
           core_graph=        None,
           in_graph_paths=    tuple(),
           out_graph_path=    '/tmp/_Neurons.ttl',
           out_imports=      ['ttl/phenotype-core.ttl'],
           out_graph=         None,
           prefixes=          tuple(),
           force_remote=      False,
           checkout_ok=       _CHECKOUT_OK,
           scigraph=          None,
           iri=               None,
           use_local_import_paths=True):  # defaults to devconfig.scigraph_api
    """ Wraps graphBase.configGraphIO to provide a set of sane defaults
        for input ontologies and output files. """
    graphBase.configGraphIO(remote_base, local_base, branch,
                            core_graph_paths, core_graph,
                            in_graph_paths, out_graph_path,
                            out_imports, out_graph, prefixes,
                            force_remote, checkout_ok, scigraph,
                            iri, use_local_import_paths)
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
