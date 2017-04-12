#!/usr/bin/env python3
from pyontutils.neurons import *
from rdflib import Graph

__all__ = [
    'AND',
    'OR',
    #'graphBase',
    'PhenotypeEdge',
    'NegPhenotypeEdge',
    'LogicalPhenoEdge',
    'Neuron',
    'pred',
]

Neuron = DefinedNeuron

core_graph_path = '/tmp/NIF-Neuron-Phenotype.ttl'  # TODO these will be split
in_graph_path =  '/tmp/NIF-Neuron-Phenotype.ttl'

graphBase.core_graph = Graph()
graphBase.core_graph.parse(core_graph_path, format='turtle')
graphBase.in_graph = Graph()
graphBase.in_graph.parse(core_graph_path, format='turtle')
graphBase.in_graph.parse(in_graph_path, format='turtle')

graphBase.predicates = getPhenotypePredicates(graphBase.core_graph)
pred = graphBase.predicates  # keep the predicates in their own namespace

# including predicates this way polutes the namespace
#globs = globals()
#for literal, value in graphBase.predicates._litmap.items():
    #globs[literal] = value
    #__all__.append(literal)
