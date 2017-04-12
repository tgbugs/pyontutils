#!/usr/bin/env python3
from rdflib import Graph
from pyontutils.neurons import *
from pyontutils.utils import makeGraph, makePrefixes

__all__ = [
    'AND',
    'OR',
    'graphBase',
    'Phenotype',
    'NegPhenotype',
    'LogicalPhenotype',
    'Neuron',
    'pred',
    'WRITE',
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

core_graph_path = '/tmp/NIF-Phenotype-Core.ttl'
pheno_graph_path = '/tmp/NIF-Phenotypes.ttl'

in_graph_path =  '/tmp/output.ttl'
out_graph_path =  '_Neurons'  # TODO actually make it a path...

graphBase.core_graph = Graph()
graphBase.core_graph.parse(core_graph_path, format='turtle')
graphBase.core_graph.parse(pheno_graph_path, format='turtle')
graphBase.in_graph = graphBase.core_graph
graphBase.in_graph.parse(in_graph_path, format='turtle')
graphBase.in_graph.namespace_manager.bind('ILXREPLACE', makePrefixes('ILXREPLACE')['ILXREPLACE'])  # FIXME annoying
graphBase.out_graph = Graph()
graphBase._predicates = getPhenotypePredicates(graphBase.core_graph)
pred = graphBase._predicates  # keep the predicates in their own namespace

newGraph = makeGraph(out_graph_path,
                     prefixes=makePrefixes('owl',
                                           'PR',
                                           'UBERON',
                                           'NCBITaxon',
                                           'ILXREPLACE',
                                           'ilx',
                                           'ILX',
                                           'NIFCELL',
                                           'NIFMOL',),
                     graph=graphBase.out_graph)

tg = makeGraph('NONE', graph=graphBase.in_graph)
e = tg.get_equiv_inter(NIFCELL_NEURON)  # FIXME do this on demand
graphBase.existing_ids = e

def WRITE():
    newGraph.write()

