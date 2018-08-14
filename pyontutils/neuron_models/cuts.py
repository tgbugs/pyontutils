#!/usr/bin/env python3.6
import csv
from pathlib import Path
from pyontutils.neuron_models.compiled import neuron_data_lifted
ndl_neurons = neuron_data_lifted.Neuron.neurons()
from pyontutils.neuron_models.compiled import basic_neurons
bn_neurons = basic_neurons.Neuron.neurons()
from pyontutils.utils import byCol
from pyontutils.core import Source
# import these last so that graphBase resets (sigh)
from pyontutils.neuron_lang import *
from pyontutils.neurons import *
from IPython import embed

# TODO
# 1. convert to use simple ont
# 2. inheritance for owlClass from python classes
# 3. add ttl serialization for subclasses of EBM

class NeuronSWAN(NeuronEBM):
    owlClass = 'ilxtr:NeuronSWAN'


def main():
    resources = Path(__file__).resolve().absolute().parent.parent / 'resources'
    cutcsv = resources / 'common-usage-types.csv'
    with open(cutcsv.as_posix(), 'rt') as f:
        rows = [l for l in csv.reader(f)]

    bc = byCol(rows)
    labels, *_ = zip(*rows)
    ns = [n for n in ndl_neurons if n._origLabel in labels]  # FIXME empty ...

    class SourceCUT(Source):
        source = __file__  # FIXME
        source_original = True
        sourceFile = 'pyontutils/resources/common-usage-types.csv'  # FIXME relative to git workingdir...
        #artifact = None
        
    sources = SourceCUT(),
    Config('common-usage-types', sources=sources)
    new = [NeuronSWAN(*n.pes) for n in ns]
    # TODO preserve the names from neuronlex on import ...
    embed()

if __name__ == '__main__':
    main()
