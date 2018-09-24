#!/usr/bin/env python3.6

import inspect
import pyontutils.neurons
from pyontutils.utils import TermColors as tc
from pyontutils.neurons import *  # always import via pyontutils or you will get errors
from pyontutils.neurons.lang import *
#pred = config(checkout_ok=True)
from pyontutils import phenotype_namespaces as phns
from IPython import embed

def printe(*args, **kwargs):
    print(*(tc.blue(str(a)) for a in args), **kwargs)

def printer(*args, **kwargs):
    printe(*(tc.red(repr(a)) for a in args), **kwargs)


def messup(outer_n):
    print('neurons defined outside local scope')
    print(repr(outer_n))
    print(outer_n)
    setLocalNames(phns.BBP)  # testing to make sure we get an error if we call this in a function
    # there is no error and the names stick around after the function returns
    print(repr(outer_n), outer_n)
    print('neurons defined in local scope')
    n = Neuron(brain, Phenotype('PR:000013502'))
    print(repr(n))

# namespace example
with phns.Layers:
    L23
    try: brain
    except NameError: printe('brain fails as expected')
    with phns.Regions:
        L23
        brain
        Neuron(L23, brain)
        try: Mouse
        except NameError: printe('Mouse fails as expected')
        with phns.Species:
            Neuron(Mouse, L23, CTX)
        try: Mouse
        except NameError: printe('Mouse fails as expected')
    try: brain
    except NameError: printe('brain fails as expected')
    L1
try: L1
except NameError: printe('L1 fails as expected')

with phns.Layers, phns.Regions, phns.Species:
    try:
        with phns.Test:
            pass
    except ValueError as e:
        printe('Test namespace has conflicts and fails as expected.', e)
    Neuron(Rat, L23, CTX)

# context example
with phns.BBP:
    myFirstNeuron = Neuron(Rat, CTX, L23, PV)
    mySecondNeuron = Neuron(Mouse, CA1, SO, PV)
    with myFirstNeuron:  # TODO __add__ for neurons that fails on disjointness
        myThirdNeuron = Neuron(LBC)
        with mySecondNeuron:  # contexts are mutually exclusive even when nested WARNING MAY CHANGE!
            myFourthNeuron = Neuron(LBC)
        with myThirdNeuron:  # use a neuron defined in a context as context to simulate nesting
            try: myFifthNeuron = Neuron(SBC)  # trivia: this neuron can't actually exist as defined
            except TypeError: printe('Neuron(SBC) fails as expected in context of LBC')
            myFifthNeuron = Neuron(SOM)  # trivia: this neuron can't actually exist as defined
    mySixthNeuron = Neuron(brain)
    print('first ', repr(myFirstNeuron))
    print('second', repr(mySecondNeuron))
    print('third ', repr(myThirdNeuron))
    print('fourth', repr(myFourthNeuron))
    print('fifth ', repr(myFifthNeuron))
    print('sixth ', repr(mySixthNeuron))

    do_not_expect = Neuron(Rat)
    with Neuron(brain) as n0, Neuron(Rat) as n1:  # they appear to combine but observer that n1 != Neuron(Rat)
        n2 = Neuron(PV)
        assert n1 != do_not_expect
        printer(n0, n1, n2)

    expect = Neuron(brain, Rat, PV)
    with Neuron(SOM) as n3, n1:  # last one wins when setting multiple contexts
        n4 = Neuron(PV)
        assert n4 == expect
        printer(n3, n1, n4)

# addition
try: myFirstNeuron + mySecondNeuron
except TypeError: printe('myFirstNeuron + mySecondNeuron fails as expected')
with phns.BBP:
    sumn = Neuron(S1, SOM) + Neuron(Mouse, PV)
    print('sumn a neuron', repr(sumn))
    nn = sum((sumn, Neuron(NGC)))
    print('sumn a neuron again', repr(nn))

setLocalNames(phns.BBP)
setLocalContext(Phenotype('NCBITaxon:10090', pred.hasInstanceInSpecies))
Neuron(Phenotype('UBERON:0001950', pred.hasSomaLocatedIn, label='neocortex'))
Neuron(brain, Phenotype('PR:000013502'))
Neuron(Phenotype('UBERON:0000955'), Phenotype('CHEBI:18243'))
Neuron(Phenotype('UBERON:0001950', pred.hasSomaLocatedIn))
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

if __name__ == '__main__':
    embed()

# XXX these have to be called inside this module or the state persists in graphBase FIXME
resetLocalNames()
setLocalContext()
