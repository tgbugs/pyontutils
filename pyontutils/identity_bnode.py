import sys
import hashlib
from collections import defaultdict
import rdflib


def bnodes(ts):
    return set(e for t in ts for e in t if isinstance(e, rdflib.BNode))


class IdentityBNode(rdflib.BNode):
    # TODO this requires a new serialization rule which 'disambiguates'
    # subgraphs with the same identity that appear as an object in
    # different triples
    """ An identity blank node is a blank node that is identified by
        the output of some identity function on the subgraph that it
        identifies. IBNodes do not need to be connected into quads for
        the named parts of a graph because they will fail to bind on
        any set of triples whose identity does not match their identity.

        However, for graphs that are unnamed, practically they should be
        bound as quads to prevent collisions. When serialized to triples
        it is reasonable to use the identity as a prefix for the local
        node ordering.

        IBNodes should only be used at the head of an unnamed graph or
        a collection of triples. Even if the triples around bound to a
        name by convention, the IBNode should still be used to identify them.

        When calculating the identity, it may be useful to use the identity
        function to provide a total ordering on all nodes.

        When directly mapping an IBNode to a set of pairs that has a name
        the identity can be reattached, but it must be by convention, otherwise
        the identity of the pairs will change.

        This is also true for lists. Note that IBNodes bound by convention are
        NOT cryptographically secure because it is trivial to tamper with the
        contents of the message and regenerate the IBNode. IBNodes are therefore
        not useful as bound identifiers, but only as unbound or pointing identifiers.
    """
    cypher = hashlib.sha256
    cypher_field_separator = ' '
    encoding = sys.getdefaultencoding()
    sortlast = b'\xff' * 64

    def __new__(cls, triples_or_pairs_or_thing, symmetric_predicates=tuple(), debug=False):
        self = super().__new__(cls)  # first time without value
        self.debug = debug
        self.id_lookup = {}
        m = self.cypher()
        m.update(self.to_bytes(self.cypher_field_separator))
        self.cypher_field_separator_hash = m.digest()  # prevent accidents
        self.cypher_check()
        m = self.cypher()
        self.null_identity = m.digest()
        self.symmetric_predicates = symmetric_predicates  # FIXME this is ok, but a bit awkward
        self._thing = triples_or_pairs_or_thing
        self.identity = self.identity_function(triples_or_pairs_or_thing)
        real_self = super().__new__(cls, self.identity)
        if debug == True:
            return self

        real_self.debug = debug
        real_self.identity = self.identity
        real_self.null_identity = self.null_identity
        real_self.symmetric_predicates = self.symmetric_predicates
        real_self.cypher_field_separator_hash = self.cypher_field_separator_hash
        return real_self

    def check(self, other):
        return self.identity == self.identity_function(other)

    def cypher_check(self):
        m1 = self.cypher()
        m2 = self.cypher()
        assert m1.digest() == m2.digest(), f'Cypher {self.cypher} does not have a stable starting point!'

        if not hasattr(self, 'cypher_field_separator_hash'):
            m1.update(b'12')
            m1.update(b'3')

            m2.update(b'123')
            assert m1.digest() != m2.digest() , f'Cypher {self.cypher} is invariant to the number of updates'
        else:
            m1.update(b'12')
            m1.update(self.cypher_field_separator_hash)
            m1.update(b'3')

            m2.update(b'123')
            assert m1.digest() != m2.digest() , f'Cypher {self.cypher} is invariant to the number of updates'

    def to_bytes(self, thing):
        if isinstance(thing, bytes):
            raise TypeError(f'{thing} is already bytes')
        elif type(thing) == str:
            return thing.encode(self.encoding)
        else:
            return str(thing).encode(self.encoding)

    def ordered_identity(self, *things, separator=True):
        """ this assumes that the things are ALREADY ordered correctly """
        m = self.cypher()
        for i, thing in enumerate(things):
            if separator and i > 0:  # insert field separator
                m.update(self.cypher_field_separator_hash)
            if thing is None:  # all null are converted to the starting hash
                thing = self.null_identity
            if type(thing) != bytes:
                raise TypeError(f'{type(thing)} is not bytes, did you forget to call to_bytes first?')
            m.update(thing)

        identity = m.digest()
        if self.debug:
            self.id_lookup[identity] = tuple(self.id_lookup[t] if
                                             t in self.id_lookup else
                                             t for t in things)

        return identity

    def triple_identity(self, subject, predicate, object):
        """ Compute the identity of a triple.
            Also handles symmetric predicates.

            NOTE that ordering for sympreds is on the bytes representation
            of a node, regardless of whether it is has already been digested """

        bytes_s, bytes_p, bytes_o = self.recurse((subject, predicate, object))
        if predicate in self.symmetric_predicates and bytes_s < bytes_o:
            return self.ordered_identity(bytes_o, bytes_p, bytes_s)
        else:
            return self.ordered_identity(bytes_s, bytes_p, bytes_o)

    def add_to_subgraphs(self, thing, subgraphs, subgraph_mapping):
        # useful for debug and load use cases
        # DO NOT USE FOR COMPUTING IDENTITY
        t = s, p, o = thing
        if s in subgraph_mapping:
            ss = subgraph_mapping[s]
        else:
            ss = False

        if o in subgraph_mapping:
            os = subgraph_mapping[o]
        else:
            os = False

        if ss and os:
            if ss is not os:  # this should only happen for 1:1 bnodes
                new = ss + [t] + os
                try:
                    subgraphs.remove(ss)
                    subgraphs.remove(os)
                    subgraphs.append(new)
                    for bn in bnodes(ss):
                        subgraph_mapping[bn] = new
                    for bn in bnodes(os):
                        subgraph_mapping[bn] = new
                except ValueError as e:
                    printD(e)
                    embed()
                    raise e
            else:
                ss.append(t)
        elif not (ss or os):
            new = [t]
            subgraphs.append(new)
            if isinstance(s, rdflib.BNode):
                subgraph_mapping[s] = new
            if isinstance(o, rdflib.BNode):
                subgraph_mapping[o] = new
        elif ss:
            ss.append(t)
            if isinstance(o, rdflib.BNode):
                subgraph_mapping[o] = ss
        elif os:
            os.append(t)
            if isinstance(s, rdflib.BNode):
                subgraph_mapping[s] = os

    def recurse(self, triples_or_pairs_or_thing, bnodes_ok=False):
        for thing in triples_or_pairs_or_thing:
            if thing is None:
                yield self.null_identity
            elif isinstance(thing, bytes):
                yield thing
            elif type(thing) == str:  # exact match, the rest are instances of str
                yield self.to_bytes(thing)
            elif isinstance(thing, rdflib.URIRef):
                yield self.to_bytes(thing)
            elif isinstance(thing, rdflib.Literal):
                # "http://asdf.asdf" != <http://asdf.asdf>
                # need str(thing) breaks recursion on rdflib.Literal
                yield self.ordered_identity(*self.recurse((str(thing), thing.datatype, thing.language)))
            elif isinstance(thing, IdLocalBNode) or isinstance(thing, IdentityBNode):
                yield thing.identity # TODO check that we aren't being lied to?
            elif isinstance(thing, rdflib.BNode):
                if bnodes_ok:
                    yield thing
                else:
                    raise ValueError('BNodes only have names or collective identity...')
            else:
                lt = len(thing)
                if lt == 3 or lt == 2:
                    if not any(isinstance(e, rdflib.BNode) for e in thing):
                        if lt == 3:
                            yield self.triple_identity(*thing)
                        elif lt == 2:
                            yield self.ordered_identity(*self.recurse(thing))
                        else:
                            raise NotImplementedError('shouldn\'t ever get here ...')
                    else:
                        if lt == 3:
                            s, p, o = thing

                        elif lt == 2:
                            s = None  # safe, only isinstance(o, rdflib.BNode) will trigger below
                            p, o = thing
                            thing = s, p, o

                        if self.debug:
                            self.add_to_subgraphs(thing, self.subgraphs, self.subgraph_mappings)

                        if isinstance(p, rdflib.BNode):
                            raise TypeError(f'predicates cannot be blank {thing}')
                        elif p == rdflib.RDF.rest:
                            if o == rdflib.RDF.nil:
                                self.to_lift.add(thing)
                            else:
                                if o in self.find_heads:
                                    raise ValueError('this should never happen')
                                self.find_heads[o] = s
                                self.to_skip.add(thing)
                                if isinstance(o, rdflib.BNode):
                                    self.bobjects.add(o)

                            self.bsubjects.add(s)
                            continue
                        elif p == rdflib.RDF.first:
                            self.to_lift.add(thing)
                            self.bsubjects.add(s)
                            if isinstance(o, rdflib.BNode):
                                self.bobjects.add(o)
                            continue

                        if isinstance(s, rdflib.BNode) and isinstance(o, rdflib.BNode):
                            self.bsubjects.add(s)
                            self.bobjects.add(o)
                            # we have to wait until the end to run this since we don't know
                            # how many triples will have the object as a subject until we have
                            # looked at all of them ... another fun issue with rdf
                            self.awaiting_object_identity[s].add(thing)
                        elif isinstance(s, rdflib.BNode):
                            self.bsubjects.add(s)
                            # leaves
                            ident = self.triple_identity(None, p, o)
                            self.bnode_identities[s].append(ident)
                        elif isinstance(o, rdflib.BNode):
                            self.bobjects.add(o)
                            # named head
                            self.named_heads.add(s)
                            self.connected_heads.add(o)
                            self.awaiting_object_identity[s].add(thing)
                        else:
                            raise ValueError('should never get here')

                else:
                    raise ValueError('wat, dont know how to compute the identity of '
                                     f'{triples_or_pairs_or_thing}')

    def resolve_bnode_idents(self):
        # resolve lifts and skips
        for t in self.to_lift:
            s, p, o = t
            if s is None:
                # upstream is not relevant because
                # we are idenitfying it implicitly
                # when processing pairs
                continue

            assert isinstance(s, rdflib.BNode)
            upstream = s
            while upstream in self.find_heads:
                upstream = self.find_heads[upstream]
                assert isinstance(upstream, rdflib.BNode)

            if isinstance(o, rdflib.BNode):
                self.awaiting_object_identity[upstream].add((upstream, p, o))
            else:
                ident = self.triple_identity(None, p, o)
                self.bnode_identities[upstream].append(ident)

        # resolve dangling cases
        for o in self.dangling_objs:
            self.bnode_identities[o].append(self.null_identity)

        def process_awaiting_triples(subject, triples, subject_idents=None):
            done = True
            for t in list(triples):  # list to allow remove from set
                s, p, o = t
                assert s == subject, 'oops'
                if o not in self.awaiting_object_identity and o in self.bnode_identities:
                    object_ident = self.bnode_identities[o]
                    if type(object_ident) == self.bnode_identities.default_factory:
                        done = False  # dealt with in while loop
                    else:
                        if subject_idents is not None:  # leaf case
                            ident = self.triple_identity(None, p, object_ident)
                            subject_idents.append(ident)
                        elif isinstance(subject, rdflib.BNode):  # unnamed case
                            subject_idents = self.bnode_identities[s]
                            ident = self.triple_identity(None, p, object_ident)
                            subject_idents.append(ident)
                        else:  # named case
                            ident = self.triple_identity(s, p, object_ident)
                            self.named_subgraph_identities[s, p].append(ident)
                            self.connected_object_identities[object_ident] = o

                        # in a sane world ...
                        # there is only single triple where a
                        # bnode is an object so it is safe to pop
                        gone = self.bnode_identities.pop(o)
                        if self.debug and o in self.connected_heads or o in self.unnamed_heads:
                            self.blank_identities[o] = gone
                        assert gone == object_ident, 'something weird is going on'
                        triples.remove(t)
                else:
                    done = False

            return done

        count = 0
        while self.awaiting_object_identity:
            # first process all bnodes that already have identities
            for subject, subject_idents in list(self.bnode_identities.items()):  # list to pop from dict
                # it is safe to pop here only if all objects attached to the bnode are not in awaiting
                if subject in self.awaiting_object_identity:
                    assert type(subject_idents) != bytes, 'hrm'
                    triples = self.awaiting_object_identity[subject]
                    subject_done = process_awaiting_triples(subject, triples, subject_idents)
                    if subject_done:
                        self.awaiting_object_identity.pop(subject)
                else:
                    subject_done = True

                if subject_done:
                    if type(subject_idents) == bytes:  # already calculated but not yet used
                        subject_identity = subject_idents
                    else:
                        # this is where we assign a single identity to a subgraph
                        # when hashing ordered identities do not use a separator
                        subject_identity = self.ordered_identity(*sorted(subject_idents), separator=False)
                        gone = self.bnode_identities.pop(subject)
                        assert gone == subject_idents, 'something weird is going on'

                    if subject in self.unnamed_heads:
                        # question: should we assign a single identity to each unnamed subgraph
                        #  or just include the individual triples?
                        # answer: we need to assign a single identity otherwise we will have loads
                        #  if identical identities since bnodes are all converted to null
                        self.unnamed_subgraph_identities[subject] = subject_identity
                    elif subject not in self.bnode_identities:  # we popped it off above
                        self.bnode_identities[subject] = subject_identity

            # second complete any nodes that have are fully identified
            for subject, triples in list(self.awaiting_object_identity.items()):  # list to pop from dict
                if process_awaiting_triples(subject, triples):
                    # we do not need to consolidate identifiers for named subgraphs
                    # the subject does disambiguation for us in a way that is consistent
                    # with how we identify other named triples
                    self.awaiting_object_identity.pop(subject)

    def identity_function(self, triples_or_pairs_or_thing):
        if isinstance(triples_or_pairs_or_thing, bytes):  # serialization
            return self.ordered_identity(triples_or_pairs_or_thing)
        elif isinstance(triples_or_pairs_or_thing, rdflib.term.Identifier):
            # NOTE rdflib.term.Node includes graphs themselves, which is good to know
            return next(self.recurse((triples_or_pairs_or_thing,)))
        elif type(triples_or_pairs_or_thing) == str:  # FIXME isinstance? or is that dangerous? e.g. OntId
            return self.ordered_identity(next(self.recurse((triples_or_pairs_or_thing,))))
        else:
            if self.debug:
                self.subgraphs = []
                self.subgraph_mappings = {}
                self.blank_identities = {}

            self.awaiting_object_identity = defaultdict(set)
            self.bnode_identities = defaultdict(list)
            self.connected_heads = set()
            self.named_heads = set()
            self.bsubjects = set()
            self.bobjects = set()
            self.to_skip = set()
            self.to_lift = set()
            self.find_heads = {}
            self.named_identities = tuple(self.recurse(triples_or_pairs_or_thing))  # memory :/

            self.unnamed_heads = self.bsubjects - self.bobjects
            self.dangling_objs = self.bobjects - self.bsubjects

            self.unnamed_subgraph_identities = {}
            self.named_subgraph_identities = defaultdict(list)
            self.connected_object_identities = {}  # needed for proper identity calculation?
            self.resolve_bnode_idents()

            free = list(self.unnamed_subgraph_identities.values())
            assert all(type(i) == bytes for i in free), 'free contains a non identity!'
            connected = [i for ids in self.named_subgraph_identities.values() for i in ids]
            assert all(type(i) == bytes for i in connected), 'connected contains a non identity!'
            self.free_identities = free
            self.connected_identities = connected

            self.all_idents = sorted(self.named_identities +
                                     tuple(self.connected_identities) +
                                     tuple(self.free_identities))

            return self.ordered_identity(*self.all_idents)

    def __repr__(self):
        id = str(self)
        return f'{self.__class__.__name__}({id!r})'  # FIXME not quite right ... given what calling IBNode does ...

    def __str__(self):
        return self.identity.hex()

    def __hash__(self):
        # for reasons I do not entirely understand
        # str.__hash__ does not produce identical hashes
        # for IdentityBNodes with the same identity ...
        # which is ... worrying
        return hash((self.__class__, self.identity))


class IdLocalBNode(rdflib.BNode):
    """ For use inside triples.
        Local ids should be consecutive integers.
        Ordering can be by sub-identity or by string ordering
        on the named portions of the graph.
    """
    def __init__(self, identity, local_id):
        self.identity = identity
        self.local_id = local_id

    def __str__(self):
        return f'{self.identity}_{self.local_id}'
