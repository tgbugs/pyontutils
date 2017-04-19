#!/usr/bin/env python3
from pyontutils.neuron_lang import *
from pyontutils.neuron_lang import newGraph

Neuron(Phenotype('ilx:PyramidalPhenotype',
                 pred.hasMorphologicalPhenotype),
       NegPhenotype('ilx:FastSpikingPhenotype',
                    pred.hasElectrophysiologicalPhenotype),
       LogicalPhenotype(OR,
                        Phenotype('ilx:PetillaInitialBurstSpikingPhenotype',
                                  pred.hasElectrophysiologicalPhenotype),
                        NegPhenotype('ilx:PetillaInitialClassicalSpikingPhenotype',
                                     pred.hasElectrophysiologicalPhenotype)))

newGraph.filename = '/tmp/test_en.ttl'
WRITE()
