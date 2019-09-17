#!/usr/bin/env python3.7

# equivalent indexed as default
# equivalent indexed in map only

import rdflib
from pyontutils.core import OntGraph, BetterNamespaceManager
from pyontutils.namespaces import TEMP, ilx, rdf, owl, ilxtr, npokb, OntCuries
from pyontutils.identity_bnode import IdentityBNode


class GraphToMap(OntGraph):
    def matchNamespace(self, namespace):
        # FIXME can't we hit the cache for these?
        for t in self:
            for e in t:
                if isinstance(e, rdflib.URIRef):
                    if e.startswith(namespace):
                        yield e

    def couldMapEntities(self, *temp_namespaces):
        yield from (e for ns in temp_namespaces for e in self.matchNamespace(ns))

    def diffFromReplace(self, replace_graph, *, new_replaces_old=True):
        """ compute add, remove, same graphs based on a graph
            the contains triples of the form `new replaces old`
            where replaces can be any predicate set new_replaces_old=False
            if the add_and_replace graph is of the form `old replacedBy new`
        """
        if new_replaces_old:
            replace = {old:new for new, _, old in replace_graph}
        else:
            replace = {old:new for old, _, new in replace_graph}

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

    def subjectGraph(self, subject, *, done=None):
        first = False
        if done is None:
            first = True
            done = set()

        done.add(subject)

        for p, o in self[subject::]:
            if first:  # subject free subject graph
                yield p, o
            else:
                yield subject, p, o

            if isinstance(o, rdflib.BNode):
                yield from self.subjectGraph(o, done=done)
            elif isinstance(o, rdflib.URIRef):
                # TODO if we want closed world identified subgraphs
                # then we would compute the identity of the named
                # here as well, however, that is a rare case and
                # would cause identities to change at a distance
                # which is bad, so probably should never do it
                pass

    def subjectIdentity(self, subject, *, debug=False):
        """ calculate the identity of a subgraph for a particular subject
            useful for determining whether individual records have changed
            not quite 
        """

        pairs_triples = list(self.subjectGraph(subject))
        ibn = IdentityBNode(pairs_triples, debug=False)
        if debug:
            triples = [(subject, *pos) if len(pos) == 2 else pos for pos in pairs_triples]
            g = self.__class__()

            _replaced = {}
            def replace(e):
                if isinstance(e, rdflib.BNode):
                    if e not in _replaced:
                        _replaced[e] = rdflib.BNode()

                    e = _replaced[e]

                return e

            def rebnode(t):
                return tuple(replace(e) for e in t)

            # switch out all the bnodes to double check
            [g.add(rebnode(t)) for t in triples]
            self.namespace_manager.populate(g)
            dibn = g.subjectIdentity(subject, debug=False)
            gibn = IdentityBNode(g, debug=True)
            print(g.ttl)
            print(ibn, dibn)
            assert ibn == dibn
            assert ibn != gibn
            breakpoint()

        return ibn

    def named_subjects(self):
        for s in self.subjects():
            if isinstance(s, rdflib.URIRef):
                yield s

    def subjectsChanged(self, other_graph):
        """ in order to detect this the mapped id must be persisted
            by the process that is making the change

            NOTE: To avoid the hashing chicken and egg problem here
            one would have to explicitly exclude triples with the
            predicate used to store the identity, which adds quite a
            bit of complexity. To avoid this, simply keeping and old
            version of the graph around might be easier. TODO explore
            tradeoffs.
        """

        # the case where an external process (e.g. editing in protege)
        # has caused a change in the elements used to calculate the id
        # of the class

        # FIXME mapped but a change to the structure of the class has
        # cause a change in the identity of the class
        # in which case the old hasTemporaryId should still be attached

        #temporary_id_changed = [e for e in self[:ilxtr.hasTemporaryId:] not_mapped ]
        #changed_classes = [(s,
                            #ilxtr.hasTemporaryId,
                            #o) for s, o in self[:ilxtr.hasTemporaryId:]]

        sid = {s:self.subjectIdentity(s) for s in set(self.named_subjects())}
        osid = {s:other_graph.subjectIdentity(s) for s in set(other_graph.named_subjects())}
        ssid = set(sid)
        sosid = set(osid)
        added = not_in_other = ssid - sosid
        removed = not_in_self = sosid - ssid
        changed = [(s, osid[s], i) for s, i in sid.items() if s in osid and i != osid[s]]
        return added, removed, changed

    def addReplaceGraph(self, index_graph, index_namespace, *temp_namespaces):
        """ Given an index of existing ids that map to ids in temporary namespaces
            return a graph of `new replaces old` triples. Currently this works on
            temp_namespaces, but in theory it could operate on any namespace.

            Note that this does attempt to detect changes to classes that
            have already been mapped and have a new temporary id. That
            functionality is implemented elsewhere. """

        existing_indexes  = list(set(index_graph.matchNamespace(index_namespace)))  # target prefix?
        lp = len(index_namespace)
        suffixes = [int(u[lp:]) for u in existing_indexes]
        start = max(suffixes) + 1 if suffixes else 1

        could_map = list(set(self.couldMapEntities(*temp_namespaces)))
        mapped_triples = [(s,
                           ilxtr.hasTemporaryId,
                           o) for s, o in index_graph[:ilxtr.hasTemporaryId:]]
        # FIXME could be mapped into another namespace ? what to do in that case?
        already_mapped = [o for _, _, o in mapped_triples]
        not_mapped = [e for e in could_map if e not in already_mapped]

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

        return add_replace_graph

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

        add_replace_graph = self.addReplaceGraph(index_graph, index_namespace, *temp_namespaces)

        # TODO also want the transitions here if we
        # want to record the record in InterLex
        index_graph.namespace_manager.populate_from(self)
        [index_graph.add(t) for t in add_replace_graph]

        add_only_graph, remove_graph, same_graph = self.diffFromReplace(add_replace_graph)
        # the other semantics that could be used here
        # would be to do an in place modification of self
        # to remove the remove graph and add the add_only_graph

        # NOTE the BNodes need to retain their identity across the 3 graphs
        # so that they reassemble correctly
        new_self = self.__class__()
        [new_self.add(t) for t in add_replace_graph]
        [new_self.add(t) for t in add_only_graph]
        [new_self.add(t) for t in same_graph]

        new_self.namespace_manager.populate_from(index_graph)
        return new_self


def main():
    from pathlib import Path
    from pyontutils.config import devconfig

    index_graph = GraphToMap()

    # testing
    index_graph.bind('npokb', npokb)
    #[index_graph.add((npokb[str(i)], rdf.type, owl.Class)) for i in range(1, 11)]
    #[index_graph.add((npokb[str(i)], ilxtr.hasTemporaryId, TEMP[str(i)])) for i in range(1, 11)]

    ios = []
    for eff in ('common-usage-types', 'huang-2017', 'markram-2015', 'allen-cell-types'):
        path = Path(devconfig.ontology_local_repo, f'ttl/generated/neurons/{eff}.ttl')
        input_graph = GraphToMap()
        input_graph.parse(path.as_posix(), format='ttl')
        output_graph = input_graph.mapTempToIndex(index_graph, npokb, TEMP)
        ios.append((input_graph, output_graph))

    a, r, c = output_graph.subjectsChanged(input_graph)
    breakpoint()

if __name__ == '__main__':
    main()
