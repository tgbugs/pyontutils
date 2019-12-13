# ttlser
[![PyPI version](https://badge.fury.io/py/ttlser.svg)](https://pypi.org/project/ttlser/)

Deterministic turtle serialization for rdflib.

## Documentation
See the [docs](./docs/ttlser.md) for the full specification and
details on the implemention.

`ttlser` also includes a number of other turtle serializers for
specific rendering needs.

## ttlfmt
`ttlser` provides a `ttlfmt` script that can convert any rdflib supported
format into the output format supported by the serializers or any other
rdflib serializer. If you want to use it you should install with `ttlser[ttlfmt]`.

## Known issues
1. symmetric predicates: If you have symmetric predicates like `owl:disjointWith` then
ttlser needs to know about them so that it can do the reordering those cases appropriately,
otherwise you will end up with situations where another tool reorders the serialization and
ttlser has to assume that the ordering is semantically meaningful.  See
[`symmetric_predicates`](https://github.com/tgbugs/pyontutils/blob/89789653f51b77b13e32dc4f27e231ab00769429/ttlser/ttlser/serializers.py#L234)
in [serializers.py](./ttlser/serializers.py).
2. multiple prefixes: If there is more than one curie prefix for the same iri prefix
then the one that is selected will depend on the dicationary ordering (which while
stable in newer version of python is not guranteed to be the same based on the
contents of the data, rather on the history of the additions and removals).
3. rdflib version: ttlser cannot produce deterministic results without the changes
added in https://github.com/RDFLib/rdflib/pull/649. Hopefully those will be merged
for rdflib-5.0.0, in the mean time ttlser depends on neurdflib which includes those
changes. Once it is merged then ttlser will depend on versions of rdflib that come
after and neurdflib will be deprecated.
4. Random failures. Every once in awhile list serialization fails specatcuarly.
The cause is not obvious (same input file every time for testing), but it is probably
because the fixed point function used to implement bnode ranking has a bug.
5. scottl is a broken mess. In principle this orders by the `rdfs:subClassOf` hierarchy
and then `natsort`, however in practice it currently does whatever it wants. I'm also
fairly certain that the test template [scogood.ttl](./test/scogood.ttl) is not correct.
