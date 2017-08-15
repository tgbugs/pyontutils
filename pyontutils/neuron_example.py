#!/usr/bin/env python3

import inspect
from pyontutils.neurons import *  # always import via pyontutils or you will get errors
from pyontutils.neuron_lang import *
from pyontutils import phenotype_namespaces
from IPython import embed

def messup(outer_n):
    print('neurons defined outside local scope')
    print(repr(outer_n))
    print(outer_n)
    setLocalNames(phenotype_namespaces.BBP)  # testing to make sure we get an error if we call this in a function
    # there is no error and the names stick around after the function returns
    print(repr(outer_n), outer_n)
    print('neurons defined in local scope')
    n = Neuron(brain, Phenotype('PR:000013502'))
    print(repr(n))

# namespace example
with phenotype_namespaces.Layers():
    L23
    try: brain
    except NameError: print('brain fails as expected')
    with phenotype_namespaces.Regions():
        L23
        brain
        Neuron(L23, brain)
        try: Mouse
        except NameError: print('Mouse fails as expected')
        with phenotype_namespaces.Species():
            Neuron(Mouse, L23, CTX)
        try: Mouse
        except NameError: print('Mouse fails as expected')
    try: brain
    except NameError: print('brain fails as expected')
    L1
try: L1
except NameError: print('L1 fails as expected')

with phenotype_namespaces.Layers(), phenotype_namespaces.Regions(), phenotype_namespaces.Species():
    try:
        with phenotype_namespaces.Test():
            pass
    except ValueError as e:
        print('Test namespace has conflicts and fails as expected.', e)
    Neuron(Rat, L23, CTX)

# context example
with phenotype_namespaces.BBP():
    myFirstNeuron = Neuron(Rat, CTX, L23, PV)
    mySecondNeuron = Neuron(Mouse, CA1, SO, PV)
    with myFirstNeuron:  # TODO __add__ for neurons that fails on disjointness
        myThirdNeuron = Neuron(LBC)
        with mySecondNeuron:  # contexts are mutually exclusive even when nested WARNING MAY CHANGE!
            myFourthNeuron = Neuron(LBC)
        with myThirdNeuron:  # use a neuron defined in a context as context to simulate nesting
            myFifthNeuron = Neuron(SBC)  # trivia: this neuron can't actually exist as defined
    mySixthNeuron = Neuron(brain)
    print('first ', repr(myFirstNeuron))
    print('second', repr(mySecondNeuron))
    print('third ', repr(myThirdNeuron))
    print('fourth', repr(myFourthNeuron))
    print('fifth ', repr(myFifthNeuron))
    print('sixth ', repr(mySixthNeuron))

#print(graphBase.neurons())

setLocalNames(phenotype_namespaces.BBP)
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
pv = Neuron(brain, Phenotype('PR:000013502'))

setLocalNames()
messup(pv)  # the localNames call inside here persists
print('testing printing pv after localNames is called inside messup')
print(repr(pv))

print(graphBase.neurons())
embed()
