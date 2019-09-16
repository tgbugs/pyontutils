#!/usr/bin/env python3.7

# equivalent indexed as default
# equivalent indexed in map only

import rdflib
from pyontutils.core import OntGraph
from pyontutils.namespaces import TEMP, ilx, rdf, owl, ilxtr


class GraphToMap(OntGraph):
    def __init__(self, *args, existing=None, **kwargs):
        if existing:
            self.__dict__ == existing.__dict__
        else:
            super().__init__(*args, **kwargs)

    def uriPrefix(self, prefix):
        for t in self:
            for e in t:
                if isinstance(e, rdflib.URIRef):
                    if e.startswith(prefix):
                        yield e

    def toMap(self, *temp_prefixes):
        yield from (e for p in temp_prefixes for e in self.uriPrefix(p))

    def doMap(self, other_graph, other_prefix, *temp_prefixes):
        if not isinstance(other_graph, self.__class__):
            other_graph = self.__class__(existing=other_graph)

        existing  = list(set(other_graph.uriPrefix(other_prefix)))  # target prefix?
        lp = len(other_prefix)
        suffixes = [int(u[lp:]) for u in existing]
        start = max(suffixes) + 1 if suffixes else 1

        temps = list(set(self.toMap(*temp_prefixes)))
        already_mapped = list(set(e for p in temp_prefixes for e in other_graph.uriPrefix(p)))
        to_map = [t for t in temps if t not in already_mapped] # FIXME TODO temp ids that have not been mapped
        mapped_triples = []

        new_mapped = [(temp_id, ilxtr.mappedTo, other_prefix[str(i + start)])  for i, temp_id in enumerate(sorted(to_map))]
        breakpoint()

def graph_with_temporary_ids_to_graph_with_mapped_ids(input_graph, graph_that_keeps_the_identifiers):
    """ side effect is to increment the ids and update the id graph and the mapping graph """

    # get all the temporary ids
    # read id graph to get all existing mappings
    # update id graph
    graph_that_keeps_the_identifiers.write  # aka mapping graph
    # tracking bag changes is out of scope
    return output_graph


def main():
    from pathlib import Path
    from pyontutils.config import devconfig
    npokb = rdflib.Namespace(ilx['npo/uris/neurons/'])
    path = Path(devconfig.ontology_local_repo, 'ttl/generated/neurons/huang-2017.ttl')
    g = GraphToMap()
    mapping_store = GraphToMap()
    # testing
    [mapping_store.add((npokb[str(i)], rdf.type, owl.Class)) for i in range(1, 11)]
    g.parse(path.as_posix(), format='ttl')
    list(g.uriPrefix(TEMP))
    g.doMap(mapping_store, npokb, TEMP)
    breakpoint()

if __name__ == '__main__':
    main()
