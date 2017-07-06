#!/usr/bin/env python3

from pyontutils.neuron_lang import *
from bbp_names import *
#from bbp_names import pythonSucks
#from pyontutils.neuron_names_nif import *
from IPython import embed

#config(out_graph_path='/tmp/youcalled.ttl')

#pythonSucks(pred, setLocalName, setLocalNameTrip, NegPhenotype, LogicalPhenotype)

setLocalContext(Phenotype('NCBITaxon:10090', pred.hasInstanceInSpecies))
Neuron(Phenotype('UBERON:0001950', 'ilx:hasSomaLocatedIn', label='neocortex'))
Neuron(brain, Phenotype('PR:000013502'))
Neuron(Phenotype('UBERON:0000955'), Phenotype('CHEBI:18243'))
Neuron(Phenotype('UBERON:0001950', 'ilx:hasSomaLocatedIn'))
Neuron(Phenotype('UBERON:0000955'), Phenotype('CHEBI:18243'), Phenotype('PR:000013502'))

#resetLocalNames()  # works as expected at the top level
#resetLocalNames(globals())  # works as expected
#Neuron(brain, Phenotype('PR:000013502'))

print(graphBase.neurons())
embed()
