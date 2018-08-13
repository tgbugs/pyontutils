#!/usr/bin/env python3.6
import csv
from pathlib import Path
from pyontutils.neuron_lang import *
from pyontutils.neurons import *
from pyontutils.neuron_models.compiled import neuron_data_lifted
ndl_neurons = neuron_data_lifted.Neuron.neurons()
from pyontutils.neuron_models.compiled import basic_neurons
bn_neurons = basic_neurons.Neuron.neurons()
from pyontutils.utils import byCol
from IPython import embed


def main():
    resources = Path(__file__).resolve().absolute().parent.parent / 'resources'
    with open((resources / 'common-usage-types.csv').as_posix(), 'rt') as f:
        rows = [l for l in csv.reader(f)]

    bc = byCol(rows)
    labels, *_ = zip(*rows)
    ns = [n for n in ndl_neurons if n._origLabel in labels]  # FIXME empty ...
    # TODO preserve the names from neuronlex on import ...
    embed()

if __name__ == '__main__':
    main()
