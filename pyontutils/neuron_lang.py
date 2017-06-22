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
    'graphBase',
    'config',
    'pred',
    'setLocalContext',
    #'Controller',
    'Phenotype',
    'NegPhenotype',
    'LogicalPhenotype',
    'Neuron',
    #'getPredicates',  # set globally when Controller is instantiated
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
    graphBase.configGraphIO(remote_base, local_base, branch,
                            core_graph_paths, core_graph,
                            in_graph_paths,
                            out_graph_path, out_imports, out_graph,
                            force_remote, scigraph)

config()
pred = graphBase._predicates

try:
    ip = get_ipython()
    def scig_func(val):
        ip.find_cell_magic('python')(os.path.expanduser('~/git/pyontutils/pyontutils/scig.py') + ' %s' % val, '')
    ip.register_magic_function(scig_func, 'line', 'scig')
except NameError:
    pass  # not in an IPython environment so can't register magics

class Controller:
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
            # in thise case we also want to wipe any existing python Neuron entires
            # that we use to serialize so that behavior is consistent
            Neuron.existing_pes = {}
            Neuron.existing_ids = {}
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

    def write_python(self):
        with open('/tmp/_Neurons.py', 'wt') as f:  # FIXME
            f.write(self.python())

    def python(self):
        out = '#!/usr/bin/env python3\n'
        out += 'from %s import *\n\n' % __name__
        #out += '\n\n'.join('\n'.join(('# ' + n.label, '# ' + n._origLabel, str(n))) for n in neurons)
        out += '\n\n'.join('\n'.join(('# ' + n.label, str(n))) for n in sorted(Neuron.existing_pes)) # FIXME this does not reset correctly when a new Controller is created, it probably should...
        return out

    def ttl(self):
        return self.ng.g.serialize(format='nifttl').decode()


def main():
    config(out_graph_path='/tmp/youcalled.ttl')
    setLocalContext(Phenotype('NCBITaxon:10090', pred.hasInstanceInSpecies))
    Neuron(Phenotype('UBERON:0001950', 'ilx:hasLocationPhenotype', label='neocortex'))
    Neuron(Phenotype('UBERON:0000955'), Phenotype('PR:000013502'))
    Neuron(Phenotype('UBERON:0000955'), Phenotype('CHEBI:18243'))
    Neuron(Phenotype('UBERON:0001950', 'ilx:hasLocationPhenotype'))
    Neuron(Phenotype('UBERON:0000955'), Phenotype('CHEBI:18243'), Phenotype('PR:000013502'))
    print(graphBase.neurons())
    #return
    embed()

if __name__ == '__main__':
    main()
