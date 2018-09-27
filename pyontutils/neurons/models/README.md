# Neuron Models
Put the python code to generate sets of neurons here.

If there are additional files that need to be version controlled
put them in the resources folder defined by `devconfig.resources`
(see [config.py](https://github.com/tgbugs/pyontutils/blob/master/pyontutils/config.py))
and use that config variable as the base to access them.

# Additional models tracked elsewhere
1. Import from NeuroLex [lift_neuron_triples.py](https://github.com/tgbugs/nlxeol/blob/master/lift_neuron_triples.py).
Run [process_csv.py](https://github.com/tgbugs/nlxeol/blob/master/process_csv.py) first.
`./process_csv.py && ./lift_neuron_triples.py`
