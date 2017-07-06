#!/usr/bin/env python3

import inspect
from pyontutils.neuron_lang import *
from pyontutils import neuron_names
from IPython import embed

#config(out_graph_path='/tmp/youcalled.ttl')

def messup():
    loadNames(neuron_names.BBPNames)  # testing to make sure we get an error if we call this in a function
    Neuron(brain, Phenotype('PR:000013502'))

loadNames(neuron_names.BBPNames)
setLocalContext(Phenotype('NCBITaxon:10090', pred.hasInstanceInSpecies))
Neuron(Phenotype('UBERON:0001950', 'ilx:hasSomaLocatedIn', label='neocortex'))
Neuron(brain, Phenotype('PR:000013502'))
Neuron(Phenotype('UBERON:0000955'), Phenotype('CHEBI:18243'))
Neuron(Phenotype('UBERON:0001950', 'ilx:hasSomaLocatedIn'))
Neuron(Phenotype('UBERON:0000955'), Phenotype('CHEBI:18243'), Phenotype('PR:000013502'))

def inner():
    Neuron(SOM, Phenotype('PR:000013502'))
inner()

#resetLocalNames()  # works as expected at the top level
#resetLocalNames(globals())  # works as expected
Neuron(brain, Phenotype('PR:000013502'))

print(graphBase.neurons())
embed()
