#!/usr/bin/env python3

import inspect
from pyontutils.neuron_lang import *
import bbp_names
#from bbp_names import pythonSucks
#from pyontutils.neuron_names_nif import *
from IPython import embed

#config(out_graph_path='/tmp/youcalled.ttl')

#pythonSucks(pred, setLocalName, setLocalNameTrip, NegPhenotype, LogicalPhenotype)
def loadNames(names, glob, loc):
    lines = inspect.getsource(names).split('\n')
    nl = []
    for line in lines:  # XXX this who approach is monumentally stupid and trying to bind names so they can be used in more than one place is annoying :/
        line = line.strip()
        if line.startswith('('):
            try:
                l = len(eval(line)[0]) 
            except NameError:  # ICK
                l = 2  # only time we encounter this is if we are actually constructing a phenotype
            if l == 2:
                line = 'setLocalName' + line
            elif l == 3:
                line = 'setLocalNameTrip' + line
        elif line.startswith('set'):
            pass
        else:
            continue
        nl.append(line)

    asdf = '\n'.join(nl)
    print(asdf)
    for l in nl:
        eval(l, glob, loc)

loadNames(bbp_names.BBPNames, globals(), locals())

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
