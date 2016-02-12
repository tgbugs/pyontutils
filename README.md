# pyontutils
python utilities for working with ontologies

## NIF-Ontology
Many of these scripts are written for working on the NIF standard ontology
found [here](https://github.com/SciCrunch/NIF-Ontology/).

## scigraph
scigraph.py is code geneator for creating a python client library against a
[SciGraph](https://github.com/SciGraph/SciGraph) REST endpoint.
scigraph_client.py is the client library generated against the nif development scigraph instance.

## ttl-convert
To achieve deterministic serializiation of ttl files we use OWLAPI 4.0.2+.
The java code to accomplish this is located [here](https://github.com/tgbugs/ttl-convert).
Scripts that serialize ttl will fail if ttl-convert is not available.
