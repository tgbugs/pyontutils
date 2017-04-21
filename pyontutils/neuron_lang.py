#!/usr/bin/env python3
from rdflib import Graph, URIRef
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

core_graph_path = 'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/neurons/ttl/NIF-Phenotype-Core.ttl'
pheno_graph_path = 'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/neurons/ttl/NIF-Phenotypes.ttl'

in_graph_path = core_graph_path #/tmp/output.ttl'
out_graph_path =  '/tmp/_Neurons.ttl'

graphBase.core_graph = Graph()
graphBase.core_graph.parse(core_graph_path, format='turtle')
graphBase.core_graph.parse(pheno_graph_path, format='turtle')
graphBase.in_graph = graphBase.core_graph
graphBase.in_graph.parse(in_graph_path, format='turtle')
graphBase.in_graph.namespace_manager.bind('ILXREPLACE', makePrefixes('ILXREPLACE')['ILXREPLACE'])  # FIXME annoying
graphBase.in_graph.namespace_manager.bind('GO', makePrefixes('GO')['GO'])  # FIXME annoying
graphBase.in_graph.namespace_manager.bind('CHEBI', makePrefixes('CHEBI')['CHEBI'])  # FIXME annoying
graphBase.out_graph = Graph()
graphBase._predicates = getPhenotypePredicates(graphBase.core_graph)
pred = graphBase._predicates  # keep the predicates in their own namespace

newGraph = makeGraph('',
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
newGraph.filename = out_graph_path
ontid = URIRef('file://' + out_graph_path)
newGraph.add_ont(ontid, 'Some Neurons')
newGraph.add_node(ontid, 'owl:imports', URIRef(pheno_graph_path))  # core should be in the import closure

tg = makeGraph('NONE', graph=graphBase.in_graph)
e = tg.get_equiv_inter(NIFCELL_NEURON)  # FIXME do this on demand
graphBase.existing_ids = e

def WRITE():
    newGraph.write()

