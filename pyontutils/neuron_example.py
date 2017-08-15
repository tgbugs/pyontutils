#!/usr/bin/env python3

import inspect
from pyontutils.neuron_lang import *
from pyontutils import phenotype_namespaces
from IPython import embed

#config(out_graph_path='/tmp/youcalled.ttl')

def messup():
    loadNames(phenotype_namespaces.BBP)  # testing to make sure we get an error if we call this in a function
    Neuron(brain, Phenotype('PR:000013502'))

with phenotype_namespaces.Layers():
    L23
    try: brain
    except NameError: print('working')
    with phenotype_namespaces.Regions():
        L23
        brain
        Neuron(L23, brain)
        with phenotype_namespaces.Species():
            Neuron(Mouse, L23, CTX)
    try: brain
    except NameError: print('working')
    L1

with phenotype_namespaces.Layers(), phenotype_namespaces.Regions(), phenotype_namespaces.Species():
    # including phenotype_namespaces.Test() raises and error as expected
    Neuron(Rat, L23, CTX)

print(graphBase.neurons())

loadNames(phenotype_namespaces.BBP)
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
