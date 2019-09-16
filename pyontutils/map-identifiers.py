#!/usr/bin/env python3.7

# equivalent indexed as default
# equivalent indexed in map only

import rdflib
from pyontutils.core import OntGraph, BetterNamespaceManager
from pyontutils.namespaces import TEMP, ilx, rdf, owl, ilxtr, npokb, OntCuries


class GraphToMap(OntGraph):
    def __init__(self, *args, existing=None, **kwargs):
        if existing:
            self.__dict__ == existing.__dict__
            if not hasattr(existing, '_namespace_manager'):
                self._namespace_manager = BetterNamespaceManager(self)
                self.namespace_manager.populate_from(existing)
        else:
            super().__init__(*args, **kwargs)

    def uriPrefix(self, namespace):
        for t in self:
            for e in t:
                if isinstance(e, rdflib.URIRef):
                    if e.startswith(namespace):
                        yield e

    def couldMap(self, *temp_namespaces):
        yield from (e for p in temp_namespaces for e in self.uriPrefix(p))

    def doMap(self, index_graph, index_namespace, *temp_namespaces):
        """ In theory index_graph could be self if the namespace in use
            is only relevant for a single file, otherwise there needs to be
            a single shared reference file that maintains the the index for all
            files
        """
        if not isinstance(index_graph, self.__class__):
            index_graph = self.__class__(existing=index_graph)

        existing  = list(set(index_graph.uriPrefix(index_namespace)))  # target prefix?
        lp = len(index_namespace)
        suffixes = [int(u[lp:]) for u in existing]
        start = max(suffixes) + 1 if suffixes else 1

        temps = list(set(self.couldMap(*temp_namespaces)))
        mapped_triples = [(s,
                           ilxtr.hasTemporaryId,
                           o) for s, o in index_graph[:ilxtr.hasTemporaryId:]]
        #already_mapped = list(set(e for p in temp_namespaces for e in index_graph.uriPrefix(p)))
        already_mapped = [o for _, _, o in mapped_triples]
        # FIXME could be mapped into another namespace ? what to do in that case?
        to_map = [t for t in temps if t not in already_mapped] # FIXME TODO temp ids that have not been mapped

        new_mapped = [(index_namespace[str(i + start)],
                       ilxtr.hasTemporaryId,
                       temp_id)
                      for i, temp_id in enumerate(sorted(to_map))]

        replace = {old:new for new, _, old in new_mapped}
        def rep(t):
            return [replace[e] if e in replace else e for e in t]

        # need to compute the id of the graph/triples opaque data section
        add_graph = self.__class__()
        [add_graph.add(t) for t in new_mapped]

        index_graph.namespace_manager.populate_from(self)
        index_graph.addN(add_graph.quads())

        if False: # old way of updating index_graph, but index_graph needs to store the state
            combined_graph = self.__class__()
            combined_graph.namespace_manager.populate_from(self, index_graph)
            #self.namespace_manager.populate(combined_graph)
            #index_graph.namespace_manager.populate(combined_graph)
            #ns_prefixes = [str(ns) for ns in (index_namespace, *temp_namespaces)]
            #curie_prefixes = [combined_graph.qname(ns).rstrip(':') for ns in ns_prefixes]
            combined_graph.addN(index_graph.quads())
            combined_graph.addN(add_graph.quads())
            print(combined_graph.ttl)

        new_self = self.__class__()
        new_self.namespace_manager.populate_from(index_graph)
        [new_self.add(rep(t)) for t in self]
        new_self.addN(add_graph.quads())
        return new_self()


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
    path = Path(devconfig.ontology_local_repo, 'ttl/generated/neurons/huang-2017.ttl')
    g = GraphToMap()
    index_graph = GraphToMap()
    index_graph.bind('npokb', npokb)
    # testing
    [index_graph.add((npokb[str(i)], rdf.type, owl.Class)) for i in range(1, 11)]
    [index_graph.add((npokb[str(i)], ilxtr.hasTemporaryId, TEMP[str(i)])) for i in range(1, 11)]

    g.parse(path.as_posix(), format='ttl')
    mapped_graph = g.doMap(index_graph, npokb, TEMP)
    #mapped_graph.write(path=path)
    breakpoint()

if __name__ == '__main__':
    main()
