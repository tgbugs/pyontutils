import sys
import hashlib
from collections import defaultdict
import rdflib

from .utils import log as _log
log = _log.getChild('ibnode')


def bnodes(ts):
    return set(e for t in ts for e in t if isinstance(e, rdflib.BNode))


class IdentityBNode(rdflib.BNode):
    # FIXME __eq__ needs to warn if types are the same but versions are different

    # TODO this requires a new serialization rule which 'disambiguates'
    # subgraphs with the same identity that appear as an object in
    # different triples

    # FIXME I think one property that we probably want for an identity
    # function is that it should be homogenous, that it, if you apply it
    # any subset of the data you will get the same identity that is used
    # if that subpart were to be incorporated into a larger whole, the issue
    # with the current implementation is that the only data structure it cares
    # about is the triple, except when dealing with bnodes, and even then it is
    # only because it is forced to treat bnodes as defining their own subgraph
    # TODO I suspect that this means I need to implement a variant that deals
    # with more intervening structure than just a list of triples, so yeah,
    # we want recursive calls to be reusable basically and not have the weird
    # all identifiers thing going on
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
    default_version = 3

    def __new__(cls, triples_or_pairs_or_thing, *, version=None, debug=False,
                symmetric_predicates=tuple(), no_reorder_list_predicates=tuple()):
        self = super().__new__(cls)  # first time without value
        self.version = self.default_version if version is None else version
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

        real_self.version = self.version
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

    _reccache = {}
    _cache_hits = 0
    def recurse(self, triples_or_pairs_or_thing, bnodes_ok=False):
        """ Absolutely must memoize the results for this otherwise
        processing large ontologies might as well be mining bitcon """

        no_cache = False  # for debug
        if no_cache or [type for type in (list, rdflib.Graph) if isinstance(triples_or_pairs_or_thing, type)]:
            # FIXME TODO make sure we filter the right types here
            yield from self._recurse(triples_or_pairs_or_thing, bnodes_ok=bnodes_ok)
        else:
            if triples_or_pairs_or_thing not in self._reccache:
                ids = list(self._recurse(triples_or_pairs_or_thing, bnodes_ok=bnodes_ok))
                if ids:
                    # in version 2 when triples_or_pairs_or_thing = self._thing there
                    # will be no results because we don't yield for each triple
                    # therefore we don't cache this to force ids to be computed again
                    # all the sub-ids are cached so the repopulation should still be
                    # fast, we can't cache the identity for top level mutable objects
                    # such as rdflib.Graph anyway, so this is a reasonable approach
                    # we handle lists and graphs above, but other types fall through here
                    if len(ids) > 1:
                        # if the thing we were iterating over contained multiple items
                        # then there is a possibliity any triples with bnodes were not
                        # processed correctly and we can't just take the ids without
                        # running over everything again
                        yield from ids
                        return
                    else:
                        self._reccache[triples_or_pairs_or_thing] = ids
                else:
                    return
            else:
                self._cache_hits += 1

            yield from self._reccache[triples_or_pairs_or_thing]

    def _recurse(self, triples_or_pairs_or_thing, bnodes_ok=False):
        if triples_or_pairs_or_thing is None or isinstance(triples_or_pairs_or_thing, str):
            breakpoint()

        if ((isinstance(triples_or_pairs_or_thing, list) or isinstance(triples_or_pairs_or_thing, tuple)) and
            (not [_ for _ in triples_or_pairs_or_thing if not ((isinstance(_, list) or isinstance(_, tuple)) and len(_) == 3)]) and
            [(s, p, o) for s, p, o in triples_or_pairs_or_thing if s == None and p == rdflib.RDF.rest and isinstance(o, rdflib.BNode)]):
            #breakpoint()  # test_list_3
            pass

        # FIXME somehow we are getting null subjects when dealing with lists ???
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
                if thing.version != self.version:
                    raise ValueError(f'versions do not match! {thing.version} != {self.version}')  # FIXME error type
                yield thing.identity # TODO check that we aren't being lied to?
            elif isinstance(thing, rdflib.BNode):
                if bnodes_ok:
                    yield thing
                else:
                    raise ValueError('BNodes only have names or collective identity...')
            else:
                lt = len(thing)
                if lt == 3 or lt == 2:
                    if not any(isinstance(e, rdflib.BNode) and not isinstance(e, self.__class__) for e in thing):  # TODO compare vs [e for e in thing if isinstance(e, rdflib.BNode)]
                        if lt == 3:
                            s, p, o = thing
                            if self.version > 1:
                                # new way
                                if p in self.symmetric_predicates:
                                    # have to do this a bit differently than in triple_identity due to tracking subject
                                    if o < s:  # for symmetric both should be urirefs but who knows
                                        s, o = o, s

                                # reminder that recurse will process this not as a pair
                                # but as two individual values and then compute id
                                pid = self.ordered_identity(*self.recurse((p, o)))
                                self.subject_identities[s].append(pid)
                                #log.debug((s, p, o, pid))
                            elif self.version == 1:
                                yield self.triple_identity(s, p, o)  # old way
                            else:
                                raise NotImplementedError(f'unknown version {self.version}')

                        elif lt == 2:
                            # don't sort, preserve the original ordering in this case
                            # FIXME this will break for graphs that are only 2 elements wrong no?
                            pid = self.ordered_identity(*self.recurse(thing))
                            if self.version > 2:
                                # changed in version 3 to have consistent behavior
                                # between pairs and multiple pairs
                                # FIXME this might not be right because at least
                                # pair lists can be hashed with the subject id to
                                # the the value ??? man derp if i know but why the
                                # hell aren't they matching the internal ? is it because
                                # we don't condense ???
                                # XXXXXXXXX we don't actually want to do this
                                # because then we double hash on the way out
                                # and can't reuse the id, the reason for the mismatch
                                # between this and recursive is that the actual subject id
                                # is included in the subject graph, there is no way to
                                # get IdentityBNode to give this right now because we stash
                                # the condensed id with the subject already embedded which is
                                # WRONG
                                self.subject_identities[None].append(pid)
                            else:
                                yield pid

                        else:
                            raise NotImplementedError('shouldn\'t ever get here ...')
                    else:
                        if lt == 3:
                            s, p, o = thing

                        # XXX we do not correctly handle the case where a bnode appeared in multiple object positions for reserialization, we need to know that the bnode appeard in multiple object positions in the original serialization and was deduplicated, because our default is to re-materialize subgraphs
                        elif lt == 2:  # FIXME not clear we ever hit this branch unless there is a bnode in the pair ???
                            # XXX FIXME I think this is breaking lists or something ???
                            s = None  # safe, only isinstance(o, rdflib.BNode) will trigger below
                            p, o = thing
                            thing = s, p, o

                        if self.debug:
                            self.add_to_subgraphs(thing, self.subgraphs, self.subgraph_mappings)

                        if (s == self.null_identity or s == None) and (p == rdflib.RDF.first or p == rdflib.RDF.rest):
                            #breakpoint()  # test_list_3
                            pass

                        if isinstance(p, rdflib.BNode) and not isinstance(p, self.__class__):
                            # predicates cannot be blank, unless it is actually an identity being passed
                            raise TypeError(f'predicates cannot be blank {thing}')
                        elif p == rdflib.RDF.rest:
                            # FIXME TODO no reorder list predicates
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

                            # hack to detect nesting
                            #self._bfirst_s.add(s)
                            #self._bfirst_o.add(o)

                            # FIXME I think we somehow incorrectly ignore the triples where
                            # nestpoints these are objects ??? for the purposes of ordering?
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
                            if self.version == 1:
                                ident = self.triple_identity(None, p, o)
                            else:
                                # we go with separator=True here to match the behavior where we calculate
                                # pid = above, this avoids issues with b'a', b'b' being eqv to b'ab'
                                pid = self.ordered_identity(*self.recurse((p, o)), separator=True)  # FIXME separator vs no separator issue
                                ident = pid
                                # XXX we do NOT append to subject_identities here because it will trigger
                                # the wat error when we resolve identities, but this may be why we are seeing
                                # an inconsistency so we may actually need to append stuff here because that
                                # is why we aren't getting the results we expect and are seeing conflation
                                # or empty subject_identities lists, in fact no, if we append here then when
                                # we go to resolve bnode identities then we wind up double hashing any identifiers
                                # that are already present in the list, so we do not append to subject_identities here
                                # self.subject_identities[s].append(ident)  # XXX DO NOT DO THIS

                            self.bnode_identities[s].append(ident)
                            #breakpoint()  # FIXME this seems to be the source of the problem in test_none_list
                            pass
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
        #self._nestpoints = self._bfirst_s & self._bfirst_o
        #if nestpoints:
            #hrm = nestpoints & set(self.find_heads)  # XXX empty ???
            #breakpoint()

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
            _debug_chain = [upstream]
            while upstream in self.find_heads:
                #if upstream in self._nestpoints:  # never happens
                    #breakpoint()
                    #break
                # XXX FIXME errors only in the nested lists case somehow ???
                # I think the issues is 0 rdf:first 1 rdf:first 2
                #                                   1 rdf:rest 3
                # specifically the rdf:first ? rdf:first pattern
                # when you have a bnode that is connected first both ways
                upstream = self.find_heads[upstream]
                _debug_chain.append(upstream)
                # FIXME upstream is None case ???
                # XXX this can happen if you have a blank node as an object in
                # pairs situation maybe in a nested list?
                # this happens when calling from OntGraph.subjectIdentity since
                # we intentionally insert None, it is _probably_ safe to treat
                # None as a legitimate value in such cases since we do handle it below
                if not (isinstance(upstream, rdflib.BNode) or upstream is None):
                    msg = (f'upstream not a BNode!?: {type(upstream)} {upstream!r}\n'
                           f'{_debug_chain!r}')
                    assert False, msg

            if isinstance(o, rdflib.BNode):
                # XXX FIXME this ignores list reordering!
                # FIXME also how to deal with case where the bnode for the head
                # of the list is already being waited for ???
                #if not isinstance(upstream, rdflib.BNode):  # never happens it seems
                    #breakpoint()
                    #raise ValueError('u wot m8')
                self.awaiting_object_identity[upstream].add((upstream, p, o))
                #if isinstance(upstream, rdflib.URIRef):
                    #breakpoint()
            else:
                if self.version == 1:
                    ident = self.triple_identity(None, p, o)
                    self.bnode_identities[upstream].append(ident)
                else:
                    # XXX cannot use separator=False here because we are operating on
                    # p and o directly and not on identities
                    ident = self.ordered_identity(*self.recurse((p, o)), separator=True)
                    # FIXME this seems VERY wrong, it goes all the way to the head
                    # and ignores the interveingin first/rest !??!
                    # XXX yeah ... the problem is list reordering! EEK
                    self.bnode_identities[upstream].append(ident)
                    #breakpoint()  # FIXME we don't hit this branch in the test_none_list case
                    #if isinstance(self._thing, rdflib.Graph):
                        #_parents = list(self._thing[::upstream])
                        #if not _parents:
                            #log.debug(upstream)
                    #log.debug(self.bnode_identities[upstream])

        # resolve dangling cases
        for o in self.dangling_objs:
            # XXX FIXME I'm not sure whether this is correct or not
            # or whether we need to distinguish these cases somehow?
            self.bnode_identities[o].append(self.null_identity)

        def process_awaiting_triples(subject, triples, subject_idents=None):
            #nonlocal starting
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
                            if self.version == 1:
                                ident = self.triple_identity(None, p, object_ident)
                            else:
                                # this was it, this was the problem, sometimes an entity would
                                # be processed with separator=True or separator=False depending on
                                # which order it came in, now that all 3 branches use separator=False
                                # the problem is gone
                                ident = self.ordered_identity(*self.recurse((p, object_ident)), separator=False)

                            subject_idents.append(ident)
                        elif isinstance(subject, rdflib.BNode):  # unnamed case
                            subject_idents = self.bnode_identities[s]
                            if subject_idents and type(subject_idents) is not list:
                                msg = f'problems incoming {subject_idents}'
                                log.critical(msg)
                                raise ValueError(msg)

                            if self.version == 1:
                                ident = self.triple_identity(None, p, object_ident)
                            else:
                                ident = self.ordered_identity(*self.recurse((p, object_ident)), separator=False)

                            subject_idents.append(ident)
                        else:  # named case
                            if self.version == 1:
                                ident = self.triple_identity(s, p, object_ident)
                                self.named_subgraph_identities[s, p].append(ident)
                                self.connected_object_identities[object_ident] = o
                            else:
                                ident = self.ordered_identity(*self.recurse((p, object_ident)), separator=False)
                                self.subject_identities[s].append(ident)

                        # in a sane world ...
                        # there is only single triple where a
                        # bnode is an object so it is safe to pop
                        if False:
                            # XXX but apparently not in real ontologies
                            # we keep the mapping around becuase there are clearly some cases where
                            # the assumptions are violated
                            gone = self.bnode_identities.pop(o)
                            if self.debug and o in self.connected_heads or o in self.unnamed_heads:
                                self.blank_identities[o] = gone
                            assert gone == object_ident, 'something weird is going on'

                        triples.remove(t)
                else:
                    done = False

            return done

        count = 0
        #limit = 9999
        #starting = {k:v for k, v in self.awaiting_object_identity.items()}
        #prev = len(self.awaiting_object_identity) + 1
        #if self.awaiting_object_identity:  # XXX yeah both bnodes and urirefs are in here
            #log.debug(f'awaiting types: {set(type(e) for e in self.awaiting_object_identity)}')
        last = False
        while self.awaiting_object_identity or last or count == 0:
            count += 1
            # XXX FIXME how is it that we avoid cycles here ???
            #this = len(self.awaiting_object_identity)
            #if last or this == 0:
            #    pass
            #elif this == prev or count > limit:
            #    # XXX the last issue is with bnode cycles which should be impossible but somehow is not !??!
            #    # looks like there is some issue in the internal transformations before we get to the graph?
            #    # maybe the issue is in rapper or something?
            #    breakpoint()
            #else:
            #    prev = this

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
                        # XXX don't compute subject identity here because we don't know if we are at the top of the graph or not
                        # and if we call self.ordered_identity at this step then it is called an extra time for any subjects
                        # that were resolved in this way, the correct solution is to just assign subject_identities ?
                        # XXX NO, that is incorrect, we assign to subject_condensed_identity i think
                        subject_identity = self.ordered_identity(*sorted(subject_idents), separator=False)  # FIXME subject_idents is what is wrong for the bnode case ...
                        #breakpoint()  # FIXME none_list issue
                        gone = self.bnode_identities.pop(subject)
                        assert gone == subject_idents, 'something weird is going on'
                        if subject in self.subject_identities and self.subject_identities[subject]:
                            _intersect = set(subject_idents) & set(self.subject_identities[subject])
                            if _intersect:
                                msg = f'you were about to double hash something {_intersect}'
                                raise ValueError(msg)
                                breakpoint()
                            else:
                                # this is the case where a blank subject is in triples with
                                # objects where the objects are both uriref and a bnode in a list
                                # the test is to make sure that our lifting doesn't conflate cases
                                # like spa spb spc with spa sp(bc)
                                self.subject_identities[subject].extend(subject_idents)  # test_list_3 mercifully this is NOT the cause if issues in test_subject_identities
                                pass
                                #breakpoint()
                                #raise ValueError('wat')

                            # pretty sure this happens when there are subjects
                            # with both no bnode triples and bnode triples
                        else:
                            #self.subject_condensed_identities[subject] = subject_identity
                            # XXX DO NOT assign to subject_identity here otherwise we get a double hash at the end
                            self.subject_identities[subject] = subject_idents

                    if subject in self.unnamed_heads:
                        # question: should we assign a single identity to each unnamed subgraph
                        #  or just include the individual triples?
                        # answer: we need to assign a single identity otherwise we will have loads
                        #  if identical identities since bnodes are all converted to null
                        self.unnamed_subgraph_identities[subject] = subject_identity
                    elif subject not in self.bnode_identities:  # we popped it off above
                        # XXX NOTE this is an incredibly stupid approach where we switch
                        # the behavior depending on whether subject_idents is bytes or a list
                        # this is where we set the bytes if we haven't already, if we don't
                        # do this then we can't complete the call process_awaiting_triples correctly
                        self.bnode_identities[subject] = subject_identity
                    else:
                        # the subject is already in bnode_identities somehow?
                        pass

            # second complete any nodes that have are fully identified
            for subject, triples in list(self.awaiting_object_identity.items()):  # list to pop from dict
                if process_awaiting_triples(subject, triples):
                    # we do not need to consolidate identifiers for named subgraphs
                    # the subject does disambiguation for us in a way that is consistent
                    # with how we identify other named triples
                    self.awaiting_object_identity.pop(subject)

            # XXX FIXME HACK to ensure that self.ordered_identity gets called on the last round
            if last:
                break

            if not self.awaiting_object_identity:
                last = True

        sigh = []
        for k, v in self.bnode_identities.items():
            if isinstance(v, self.bnode_identities.default_factory):
                sigh.append((k, v))
                # XXX something has gone wrong
                #breakpoint()
                #break

        if sigh:
            breakpoint()

    def identity_function(self, triples_or_pairs_or_thing):
        """ at the moment identity_function should not be called recursively so
        that it is possible to access the original entrypoint without passing
        it down the chain as things are computed, this indicates a design issue
        around the desire to reach inside the implementation for efficiencies sake
        without having a proper abstraction for actually doing it

        see also idlib/docs/stream-grammer.org
XXX this docstring is completely wrong, ibnode uses a completely different approach
it simply hashes all whole triples and divides them into two sets, those that contain
bnodes and those that do not


metadata        | metadata a owl:Ontology ; m:p "mvalue" ; m:p2 [ m:abn "bnv" ] .
    data        | class a owl:Class ; c:p "cvalue" ; c:p2 [ c:oh-no-a-blank-node [ c:and-another-one "some value"] ] .
    data        | [] a owl:Restriction ; f:p "freeeeee" .  # free unnamed subgraph

meta named      | metadata a owl:Ontology
meta named      | metadata m:p "mvalue"
meta connected  | metadata m:p2 0
meta ???        | 0 m:abn "bnv"
data named      | class a owl:Class
data named      | class c:p "cvalue"
data connected  | class c:p2 1
data ???        | 1 c:oh-no-a-blank-node 2
data ???        | 2 c:and-another-one "some value"
data free ???   | 3 a owl:Restriction   # should be called unnamed probably?
data free ???   | 3 f:p "freeeeee"

        """
        # in order to minimize rework when we want to detect whether something is the same
        # data entities should be hashed in the same way as metadata, not as whole triples

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
            self.subject_identities = defaultdict(list)
            self.bnode_identities = defaultdict(list)
            self.connected_heads = set()
            self.named_heads = set()
            self.bsubjects = set()
            self.bobjects = set()
            self.to_skip = set()
            self.to_lift = set()
            self.find_heads = {}

            #self._bfirst_s = set()
            #self._bfirst_o = set()

            # TODO parallelize here maybe?
            #self._top_cached = False
            self.named_identities = tuple(self.recurse(triples_or_pairs_or_thing))  # memory :/
            #if self._top_cached and self.named_identities:
                #breakpoint()
                #return
            #[t for t in triples_or_pairs_or_thing if not [e for e in t if isinstance(e, rdflib.BNode)]]  # don't do this for memory reasons
            #log.debug(f'cache hits during recurse {self._cache_hits}')

            self.unnamed_heads = self.bsubjects - self.bobjects
            self.dangling_objs = self.bobjects - self.bsubjects  # TODO use this to detect cases where we need to defer loading

            self.unnamed_subgraph_identities = {}
            self.named_subgraph_identities = defaultdict(list)
            self.connected_object_identities = {}  # needed for proper identity calculation?
            # FIXME I think the confusion about this implementation is that
            # bnodes have their identities calculated differently from named
            # subjects which are completely ignored as an organizing principle
            self.resolve_bnode_idents()

            free = list(self.unnamed_subgraph_identities.values())
            assert all(type(i) == bytes for i in free), 'free contains a non identity!'
            connected = [i for ids in self.named_subgraph_identities.values() for i in ids]
            assert all(type(i) == bytes for i in connected), 'connected contains a non identity!'
            self.free_identities = free
            self.connected_identities = connected

            # FIXME surely this is wrong because there are named identities that are missing
            # blank node identities that have not been resolved???
            # no, the way I do it now technically works, but the use of connected_identities
            # directly means that subject and object they are connected to are not correctly
            # included in the hash of the named subgraph that contains a blank node
            # XXX sigh, no the connected identities ARE the identities of the whole triple
            # but it means that named identities are separated from their unnamed subparts
            # pretty sure I did this for performance reasons, but the end result is that
            # you can only know the identity for a subgraph as the separate identities
            # for the named and uunamed portions, and the whole identity cannot be calcuated
            # without accumulating those independently :/
            # we would have keep the identities of the individual triples in the named portion
            # around and then combine them together with all connected unnamed identities for
            # that subgraph and THEN sort rather than combine the result for the named portion first
            # this is what we need for interlex, but is in point of face different than how we
            # actually compute the identity right now

            # one change: we wanted the named identities and the connected_identities to be paired up XXX nope, that is not how this thing works, if we want that kind of granularity have to do it using ibnode on a modified input
            # open question: do we want triple identities or pair identities, or rather (None, p, o)
            #breakpoint()

            self.subject_condensed_identities = {}  # FIXME there are often duplicate identities that do NOT have the same graph
            self.subject_embedded_identities = {}  # this is sci with the subject id embedded if such a thing is possible
            if self.version > 1 and self.subject_identities:
                for k, v in self.subject_identities.items():
                    id_values = self.ordered_identity(*sorted(v), separator=False)  # TODO can we actually leave out the separator here? probably?
                    self.subject_condensed_identities[k] = id_values
                    if k is None or isinstance(k, rdflib.BNode):
                        # this way the result of id_values can be reused
                        # if a named subject needs its subgraph without that
                        # you can get it from subject_condensed_identifiers now
                        # without having to recompute it each time, but it is now
                        # possible to recompute for individual subgraphs to match
                        oid = id_values
                    else:
                        id_key = self.__class__(k).identity
                        oid = self.ordered_identity(id_key, id_values, separator=False)

                    self.subject_embedded_identities[k] = oid
                    continue
                    if False:  # derp
                        # the subgraph bnode is used as the id for the subject of the subgraph
                        # when it is at the top level FIXME this is annoying again
                        # because it means that the actual identity of a bnode subgraph is not what
                        # is returned by IdentityBNode so it can't be used recursively still :/
                        # but we are a bit closer ... maybe we don't need to distinguish between
                        # the list of pairs for a bnode and the triples with the bnode? what kind of
                        # trouble would that get us into? certainly a nicer and more homogenous interface ...
                        id_key = (id_values if isinstance(k, rdflib.BNode) else self.__class__(k).identity)
                    continue
                    # use id_values for id_key if key is a bnode consistent with how we deal with
                    # making bnode ids consistent in other contexts
                    if k is None:
                        #id_key = id_values
                        #breakpoint()
                        #oid = self.ordered_identity(None, id_values, separator=False)  # doing this _completely_ breaks the identity

                        # returning id_values directly when k is None is the only thing that
                        # allows the calling scope to obtain id_values and combine it with
                        # the actual value for k that is presumably known in the calling scope
                        # it still requires that the caller also call ordered_identity(k, oid)
                        # FIXME TODO there is still something that mangles the returned id though
                        # which is cause by the final call to ordered_identities for all_idents_new
                        oid = id_values  # XXX oid = id_values is wrong it should have been id_values id_values if None is passed at top level XXX ACTUALLY no, not quite, the issue is that if None is present or if it is just pairs then the thing that should be returned IS id_values directly because there is no subject graph, only the subgraph, and that will line up with subject_condensed_identifiers values in the future
                        #raise NotImplementedError("don't do this")
                    else:
                        id_key = (id_values if isinstance(k, rdflib.BNode) else self.__class__(k).identity)  # XXX NOTE we DO have to double hash id_values when there is a bnode to distinguish between the id for the pair subgraph and the whole, but maybe there is some other way? or maybe not needed once we are storing sci correctly
                        oid = self.ordered_identity(id_key, id_values, separator=False)

                    # FIXME ok, here is our problem, we never stored the condensed id for JUST values
                    # which si what we actually need for this to be reusable and recursively sound
                    # id_values should match the way we computed in version 1 for pairs where there
                    # was no subject
                    self.subject_condensed_identities[k] = oid

                #subject_condensed_identities = {
                #    # FIXME TODO, we might even be able to skip this one
                #    # if we store the associated id, s_blank 0 or the named subject
                #    k: self.ordered_identity(
                #        self.ordered_identity(*sorted(v))  # XXX not sure whether this is the best way, but it helps distingish the list of pairs from the triples I think? alternative would be to use null, but I think that is inconsistent
                #        if isinstance(k, rdflib.BNode) else
                #        self.__class__(k).identity,
                #        self.ordered_identity(*sorted(v)))
                #    for k, v in self.subject_identities.items()}

                top_sci = {
                    # FIXME this fails for cycles
                    k:v for k, v in self.subject_embedded_identities.items()
                    # FIXME if statement is overly restrictive
                    if not isinstance(k, rdflib.BNode) or k in self.unnamed_heads}

                self.all_idents_new = sorted(top_sci.values())
                #log.debug(self.all_idents_new)
                if not self.all_idents_new:
                    # one case that can land us here is if there is a bnode cycle
                    breakpoint()

                # use separator=False here to ensure that behavior matches that of internal call in recurse
                # if we don't do that then we get a mismatch when we try to use IdentityBNode recursively
                # e.g. when we test that the interal identity for a named subject matches OntGraph.subjectIdentity
                return self.ordered_identity(*self.all_idents_new, separator=False)
            #elif self._top_cached and self.named_identities:
                #breakpoint()
            else:
                # old way for all or if the top level thing is e.g. a single pair
                self.all_idents_old = sorted(
                    self.named_identities +  # no bnodes
                    tuple(self.connected_identities) +  # bnodes in objects
                    tuple(self.free_identities))  # bnodes at least in subjects and not connected

                return self.ordered_identity(*self.all_idents_old)

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
