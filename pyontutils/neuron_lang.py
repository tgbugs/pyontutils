#!/usr/bin/env python3
import os
from git.repo import Repo
from rdflib import Graph, URIRef
from pyontutils.neurons import *
from pyontutils.utils import makeGraph, makePrefixes
from IPython import embed

__all__ = [
    'AND',
    'OR',
    #'graphBase',
    'Controller',
    'Phenotype',
    'NegPhenotype',
    'LogicalPhenotype',
    'Neuron',
    'pred',  # set globally when Controller is instantiated
    'WRITE',  # set globally when Controller is instantiated
    'WRITEPYTHON',
]

# quick way to do renaming during dev and testing
g = globals()
def rename(classname, newname):
    cls = g[classname]
    setattr(cls, '__name__', newname)
    g[newname] = cls

_ = [rename(old, new) for old, new in (
    ('DefinedNeuron','Neuron'),
    ('PhenotypeEdge','Phenotype'),
    ('NegPhenotypeEdge','NegPhenotype'),
    ('LogicalPhenoEdge','LogicalPhenotype'),
)]


class Controller:
    """ If you pass new arguments here any Neurons
    that you have previously defined will be wiped.

    To set your own output_graph_path write
    `Controller().output_graph_path = 'myOutFile.ttl'`

    NOTE: if you change your core files you will need
    to redefine pred.
    """
    instance = None
    class __Controller:
        remote_base = 'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/'
        local_base = os.path.expanduser('~/git/NIF-Ontology/')
        branch = 'neurons'
        def __init__(self, *args,
                     core_graph=None,  # FIXME why do I think that I'm just slightly shifting the api here and duplicating everything... sigh
                     core_graph_paths=['ttl/NIF-Phenotype-Core.ttl',
                                       'ttl/NIF-Phenotypes.ttl'],
                     in_graph_paths=tuple(),
                     out_graph=None,
                     out_graph_path='/tmp/_Neurons.ttl',
                     out_imports=['ttl/NIF-Phenotype-Core.ttl'],
                     force_remote = False):

            # check for local base
                # check if on branch, otherwise fail with a warning
                # if no outgraph is specified write to the file specified in in_graph_path
            # otherwise pull from remote and save to /tmp/

            remote_core_paths, local_core_paths = self._make_lr(core_graph_paths)
            remote_in_paths, local_in_paths = self._make_lr(in_graph_paths)
            remote_out_path, local_out_path = [_[0] for _ in self._make_lr([out_graph_path])]  # XXX fail w/ tmp
            remote_out_imports, local_out_imports = self._make_lr(out_imports)
            if force_remote:
                use_core_paths = remote_core_paths
                use_in_paths = remote_in_paths
            elif os.path.exists(self.local_base):
                repo = Repo(self.local_base)
                if repo.active_branch.name != self.branch:
                    raise FileNotFoundError('Local git repo not on %s branch! Please run `git checkout %s` in %s' % (self.branch, self.branch, self.local_base))
                use_core_paths = local_core_paths
                use_in_paths = local_in_paths
            else:
                print("Warning local ontology path '%s' not found!" % self.local_base)
                #raise FileNotFoundError('Local ontology path \'%s\' not found!' % self.local_base)
                use_core_paths = remote_core_paths
                use_in_paths = remote_in_paths
                #if not out_graph_path:  # TODO?
                    #pass

            # core graph setup
            if core_graph is None:
                graphBase.core_graph = Graph()
            else:
                graphBase.core_graph = core_graph
            for cg in use_core_paths:
                graphBase.core_graph.parse(cg, format='turtle')

            graphBase._predicates = getPhenotypePredicates(graphBase.core_graph)

            # input graph setup
            graphBase.in_graph = graphBase.core_graph
            for ig in use_in_paths:
                graphBase.in_graph.parse(ig, format='turtle')

            ig = makeGraph('',  # fast way to attach prefixes
                           prefixes=makePrefixes('ILXREPLACE', 'GO', 'CHEBI'),
                           graph=graphBase.in_graph)

            # output graph setup
            if out_graph is None:
                graphBase.out_graph = Graph()
            else:
                graphBase.out_graph = out_graph
            self.ng = makeGraph('',
                                prefixes=makePrefixes('owl',
                                                      'GO',
                                                      'PR',
                                                      'CHEBI',
                                                      'UBERON',
                                                      'NCBITaxon',
                                                      'ILXREPLACE',
                                                      'ilx',
                                                      'ILX',
                                                      'NIFCELL',
                                                      'NIFMOL',),
                                graph=graphBase.out_graph)

            self.ng.filename = out_graph_path
            ontid = URIRef('file://' + out_graph_path)
            self.ng.add_ont(ontid, 'Some Neurons')
            for remote_out_import in remote_out_imports:
                self.ng.add_node(ontid, 'owl:imports', URIRef(remote_out_import))  # core should be in the import closure

            #e = ig.get_equiv_inter(NIFCELL_NEURON)  # FIXME do this on demand
            #graphBase.existing_ids = e

            g = globals()
            g['WRITE'] = self.ng.write

            g['pred'] = graphBase._predicates

        def _make_lr(self, suffixes):
            local = [self.local_base + s for s in suffixes]
            remote = [self.remote_base + self.branch + '/' + s for s in suffixes]
            return local, remote

        @property
        def _predicates(self):
            return graphBase._predicates

        @property
        def out_graph_path(self):
            return self.ng.filename

        @out_graph_path.setter
        def out_graph_path(self, value):
            self.ng.filename = value

        def newOutGraph():
            graphBase.outGraph = Graph()
            self.ng = makeGraph('', prefixes=makePrefixes(*self.ng.namespaces), graph=graphBase.outGraph)


        def write(self):
            self.ng.write()

        def ttl(self):
            return self.ng.g.serialize(format='nifttl').decode()


    def __new__(cls, *args, **kwargs):
        if Controller.instance is None:
            Controller.instance = Controller.__Controller(**kwargs)
        elif kwargs:
            Controller.instance = Controller.__Controller(**kwargs)
        return Controller.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name):
        return setattr(self.instance, name)

Controller()

pred = Controller()._predicates
# ideally what we want is a class pred that looks up the id of Controller() every time a method is called and if it has changed updates its class dict..., of course this means we have to throw an error if the called name no longer exists...

def WRITE():
    Controller().ng.write()  # singleton does not work correctly
    # if we do c = Controller() and then add or remove lines after writing
    # then the original state is retained when we first called write and
    # we cannot recover it

def WRITEPYTHON(neurons):
    out = '#!/usr/bin/env python3\n'
    out += 'from %s import *\n\n' % __name__
    #out += '\n\n'.join('\n'.join(('# ' + n.label, '# ' + n._origLabel, str(n))) for n in neurons)
    out += '\n\n'.join('\n'.join(('# ' + n.label, str(n))) for n in neurons)
    with open('/tmp/_Neurons.py', 'wt') as f:
        f.write(out)

