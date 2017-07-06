#!/usr/bin/env python3

import inspect
from pyontutils.neuron_lang import *
import bbp_names
#from bbp_names import pythonSucks
#from pyontutils.neuron_names_nif import *
from IPython import embed

#config(out_graph_path='/tmp/youcalled.ttl')

#pythonSucks(pred, setLocalName, setLocalNameTrip, NegPhenotype, LogicalPhenotype)
lines = inspect.getsource(bbp_names.BBPNames).split('\n')
nl = []
for line in lines:  # XXX this who approach is monumentally stupid and trying to bind names so they can be used in more than one place is annoying :/
    line = line.replace('\'),','\')')
    line = line.replace(')),','))')
    if line.strip().startswith('('):
        line = line.split('#',1)[0]  # this is dumb
        if line.count(',') == 2:
            line = line.replace(' (\'',' setLocalNameTrip(\'')
        elif line.count(',') == 1:
            line = line.replace(' (\'',' setLocalName(\'')
    elif 'set' in line:
        pass
    else:
        line = ''
    line = line.strip()
    if line:
        nl.append(line)

asdf = '\n'.join(nl)
print(asdf)
#eval(asdf, globals(), locals())

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
#embed()
