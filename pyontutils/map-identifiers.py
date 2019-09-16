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

    def add_remove_same(self, add_and_replace_graph, *, new_replaces_old=True):
        """ compute add, remove, same graphs based on a graph
            the contains triples of the form `new replaces old`
            where replaces can be any predicate set new_replaces_old=False
            if the add_and_replace graph is of the form `old replacedBy new`
        """
        if new_replaces_old:
            replace = {old:new for new, _, old in add_and_replace_graph}
        else:
            replace = {old:new for old, _, new in add_and_replace_graph}

        def iri_replace(t):
            return tuple(replace[e] if e in replace else e for e in t)

        add, rem, same = [self.__class__() for _ in range(3)]
        for t in self:
            nt = iri_replace(t)
            if nt != t:
                add.add(nt), rem.add(t)
            else:
                same.add(t)

        return add, rem, same

    def mapTempToIndex(self, index_graph, index_namespace, *temp_namespaces):
        """ In theory index_graph could be self if the namespace in use
            is only relevant for a single file, otherwise there needs to be
            a single shared reference file that maintains the the index for all
            files

            NOTE: either the current graph or the index_graph needs to have the
                  curie mapping for the namespaces defined prior to calling this
                  otherwise you will have to cross populate namespaces again
        """
        if not isinstance(index_graph, self.__class__):
            index_graph = self.__class__(existing=index_graph)

        existing_indexes  = list(set(index_graph.uriPrefix(index_namespace)))  # target prefix?
        lp = len(index_namespace)
        suffixes = [int(u[lp:]) for u in existing_indexes]
        start = max(suffixes) + 1 if suffixes else 1

        could_map = list(set(self.couldMap(*temp_namespaces)))
        mapped_triples = [(s,
                           ilxtr.hasTemporaryId,
                           o) for s, o in index_graph[:ilxtr.hasTemporaryId:]]
        # FIXME could be mapped into another namespace ? what to do in that case?
        already_mapped = [o for _, _, o in mapped_triples]
        not_mapped = [e for e in could_map if e not in already_mapped] # FIXME TODO temp ids that have not been mapped

        # the iri replace operation is common enough that it probably
        # deserves its own semantics since when combined with a known
        # input qualifier the output graph is well defined and it provides
        # much stronger and clearer semantics for what was going on
        # allowing multiple different predicates is fine since different
        # processes may have different use cases for the predicate
        # in the case where the mapping is simply stored and added
        # as an equivalent class along with hasInterLexId, then the new
        # mappings are simply add rather than addAndReplaceUsingMapping
        iri_replace_map = [(index_namespace[str(i + start)],
                            ilxtr.hasTemporaryId,
                            temp_id)
                           for i, temp_id in enumerate(sorted(not_mapped))]

        # need to compute the id of the graph/triples opaque data section
        # this is the pure add graph, in this case it is also used to
        # compute the replace graph as well
        add_replace_graph = self.__class__()
        [add_replace_graph.add(t) for t in iri_replace_map]

        index_graph.namespace_manager.populate_from(self)
        index_graph.addN(add_replace_graph.quads())

        new_self = self.__class__()
        new_self.namespace_manager.populate_from(index_graph)
        add_only_graph, remove_graph, same_graph = self.add_remove_same(add_replace_graph)
        # the other semantics that could be used here
        # would be to do an in place modification of self
        # to remove the remove graph and add the add_only_graph

        # NOTE the BNodes need to retain their identity across the 3 graphs
        # so that they reassemble correctly
        new_self.addN(add_replace_graph.quads())
        new_self.addN(add_only_graph.quads())
        new_self.addN(same_graph.quads())
        breakpoint()
        return new_self


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

    index_graph = GraphToMap()

    # testing
    index_graph.bind('npokb', npokb)
    [index_graph.add((npokb[str(i)], rdf.type, owl.Class)) for i in range(1, 11)]
    [index_graph.add((npokb[str(i)], ilxtr.hasTemporaryId, TEMP[str(i)])) for i in range(1, 11)]

    input_graph = GraphToMap()
    input_graph.parse(path.as_posix(), format='ttl')
    output_graph = input_graph.mapTempToIndex(index_graph, npokb, TEMP)
    breakpoint()

if __name__ == '__main__':
    main()
