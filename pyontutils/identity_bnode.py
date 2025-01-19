import sys
import hashlib
from collections import defaultdict
import rdflib
from enum import Enum

from .utils_fast import log as _log

log = _log.getChild('ibnode')

bnNone = rdflib.BNode()  # BNode to use in cases where subject would be None
#_session_only_token = rdflib.BNode()  # ensure raw bnode identities cannot be compared between sessions

it = Enum(
    'InputTypes',
    [('bytes', 0),

     ('pair', 1),
     ('(p o)', 1),

     ('triple', 2),
     ('(s p o)', 2),

     ('pair-seq', 3),
     ('local-conventions', 3),
     ('((p n) ...)', 3),

     ('graph', 4),
     ('triple-seq', 4),
     ('((s p o) ...)', 4),

     ('graph-and-local-conventions', 5),
     ('(((p n) ...) ((s p o) ...))', 5),

     # this sort of conflates type and method again, except note that
     # the signature is different in it vs idf
     ('graph-combined-and-local-conventions', 6),
     ('(((p n) ...) ((ns np no) ... (us up uo) ...))', 6),

     ('graph-combined', 7),
     ('((ns np no) ... (us up uo) ...)', 7),

     ('graph-named', 8),
     ('((ns np no) ...)', 8),

     ('graph-bnode', 9),
     ('((us up uo) ...)', 9),
     ('((s p _) ... (_ p _) ... (_ p o) ...)', 9),

     # other less used
     ('pair-ident', 10),
     ('(p id)', 10),

     ('tripair-seq', 11),
     ('raw-bnode', 12),
     ('ident', 13),
     ('bytes-seq', 14),
     ('ident-seq', 15),
     ('seq-of-ordered-seqs', 16),
     ('empty-seq', 17),

     ])

idf = Enum(
    'IdTypes',
    [('bytes', 0),

     ('pair', 1),
     ('(p o)', 1),
     ('((p) (o))', 1),

     ('pair-alt', 101),
     ('(p (o))', 101),

     ('triple', 2),
     ('(s (p o))', 2),

     ('triple-alt', 102),
     ('(s p o)', 102),

     ('condensed', 3),
     ('subject-condensed-identity', 3),
     ('((p o) ...)', 3),

     ('record', 4),
     ('embedded', 4),
     ('subject-embedded-identity', 4),
     ('(s ((p o) ...))', 4),  # note that there is one less pair of parens here than for triple
     # that is (s (p o)) != (s ((p o))), triple vs record containing a single triple

     ('multi-record', 5),
     ('multi-embedded', 5),
     ('multi-subject-embedded-identity', 5),
     ('(s ((p o) ...)) ...', 5),

     # FIXME there is also some confusion here because
     # a sequence of triples can be collectively identified
     # in may ways, and here we are conflating the way we
     # compute the record with the expected shape of the record
     # for all of these we assume the input structure is ((s p o) ...)
     # unless otherwise specified, so this is a bit confusing
     # (((p n) ...) ((s p o) ...)) is the general structure
     # and then there are many ways to compute the identity
     # even before we deal with the cyclical graphs bit an
     # how we arrive at the condensed identity ... so I think
     # we may be able to split the as type and the compute ident as bits ...
     ('record-seq', 6),
     ('embedded-seq', 6),
     ('((s ((p o) ...)) ...)', 6),

     # XXX this one is tricky because you can take combined of
     # a pure named and pure bnode graph and the other component
     # will be null so it is not homogenous in the way that we
     # normally like, so I hesitate to include it at all
     ('graph-combined-identity', 7),
     ('(((ns ((np no) ...)) ...) ((us ((up uo) ...)) ...))', 7),

     ('local-conventions', 8),
     ('pair-seq', 8),  # used for local conventions
     ('((p n) ...)', 8),  # XXX explicitly not ((p o) ...)

     # actual trip-seq which we don't use
     #('trip-seq', 4),
     #('((s (p o)) ...)', 4),  # this is what it sounds like

     ('triple-alt-seq', 9),
     ('((s p o) ...)', 9),

     # other infrequently used bits
     ('pair-ident', 10),
     ('(p id)', 10),

     ('ident', 11),
     ('bytes-seq', 12),
     ('ident-seq', 13),
     ('raw-bnode', 14),
     ('tripair-seq', 15),

     ('graph-combined-and-local-conventions', 16),
     ('(((p n) ...) (((ns np no) ...) ((us up uo) ...)))', 16),

     ('graph-combined', 17),
     ('(((ns np no) ...) ((us up uo) ...))', 17),

     ])

# convention mappings
idfun_v1 = {
    it['bytes']: idf['bytes'],
    it['((s p o) ...)']: idf['((s p o) ...)'],
}

#idfun_v2 = {}
idfun_v3 = {
    it['bytes']: idf['bytes'],
    it['ident']: idf['ident'],
    it['(p o)']: idf['(p o)'],
    it['(s p o)']: idf['(s (p o))'],
    it['((s p o) ...)']: idf['((s ((p o) ...)) ...)'],
    it['graph-named']: idf['((s ((p o) ...)) ...)'],
    it['graph-bnode']: idf['((s ((p o) ...)) ...)'],
    it['local-conventions']: idf['((p n) ...)'],
    it['(p id)']: idf['(p id)'],
    it['bytes-seq']: idf['bytes-seq'],
    it['ident-seq']: idf['ident-seq'],
    it['raw-bnode']: idf['raw-bnode'],
    it['graph-combined-and-local-conventions']: idf['graph-combined-and-local-conventions'],
    it['graph-combined']: idf['graph-combined'],
    it['graph-named']: idf['record-seq'],
    it['graph-bnode']: idf['record-seq'],
    #it['']: idf[''],
}


def bnodes(ts):
    return set(e for t in ts for e in t if isinstance(e, rdflib.BNode))


def toposort(adj, unmarked_key=None):
    # XXX NOTE adj cannot be a generator
    _dd = defaultdict(list)
    [_dd[a].append(b) for a, b in adj]
    nexts = dict(_dd)

    _keys = set([a for a, b in adj])
    _values = set([b for a, b in adj])
    starts = list(_keys - _values)

    unmarked = sorted((_keys | _values), key=unmarked_key)
    temp = set()
    out = []
    def visit(n):
        if n not in unmarked:
            return
        if n in temp:
            import pprint
            raise Exception(f'oops you have a cycle {n}\n{pprint.pformat(n)}', n)

        temp.add(n)
        if n in nexts:
            for m in nexts[n]:
                visit(m)

        temp.remove(n)
        unmarked.remove(n)
        out.append(n)

    while unmarked:
        n = unmarked[0]
        visit(n)

    return out


def split_named_bnode(triple_seq):
    # use graph so that they show up in cache as expected
    named = rdflib.Graph()
    for t in triple_seq:
        if (not isinstance(t[0], rdflib.BNode)
        and not isinstance(t[2], rdflib.BNode)):
            named.add(t)

    bnode = rdflib.Graph()
    for t in triple_seq:
        if (isinstance(t[0], rdflib.BNode)
         or isinstance(t[2], rdflib.BNode)):
            bnode.add(t)

    return named, bnode


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
    sortlast = b'\uf8ff'
    default_version = 3

    def __new__(cls, triples_or_pairs_or_thing, *, version=None, debug=False, pot=False,
                as_type=None, id_method=None, in_graph=None, symmetric_predicates=tuple(), no_reorder_list_predicates=tuple()):
        self = super().__new__(cls)  # first time without value
        self.version = self.default_version if version is None else version
        if self.version not in self._reccache_top:
            # FIXME sigh overhead every instance UGH separate classes ...
            self._reccache_top[self.version] = {}

        # FIXME also ... reccache is useless ... it is usually just the bytes conversions :/
        # it is for attempting to emulate old v1 iirc but very broken
        self._reccache = self._reccache_top[self.version]
        if self.version not in self._oi_cache_top:
            # FIXME sigh overhead every instance UGH separate classes ...
            self._oi_cache_top[self.version] = {}

        self._oi_cache = self._oi_cache_top[self.version]
        self.debug = debug
        self._pot = pot  # pair or triple, use when you explicitly want to get the id for a pair or triple not just a list of 2 or 3 things
        self.id_lookup = {}
        self.symmetric_predicates = symmetric_predicates  # FIXME this is ok, but a bit awkward
        self._thing = triples_or_pairs_or_thing

        if not hasattr(self, f'_{self.version}_cfs'):
            m = self.cypher()
            m.update(self.to_bytes(self.cypher_field_separator))
            _cfs = m.digest()  # prevent accidents


            setattr(self, f'_{self.version}_cfs', _cfs)

        self.cypher_field_separator_hash = getattr(self, f'_{self.version}_cfs')

        if not hasattr(self, f'_{self.version}_ni'):
            self.cypher_check()  # only run this the first time, so stash this in here instead of every time
            m = self.cypher()
            _ni = m.digest()
            setattr(self, f'_{self.version}_ni', _ni)

        self.null_identity = getattr(self, f'_{self.version}_ni')

        if self.version > 2:
            treat_as_type = as_type if as_type else self.tat(triples_or_pairs_or_thing, self.version, pot)
            self._idfun_map = idfun_v3
            self._alt_identity = self._identity_function(
                triples_or_pairs_or_thing, treat_as_type, id_method=id_method, in_graph=in_graph)
            if self.version >= 3:
                self.identity = self._alt_identity
                #if debug:
                    #self._old_identity = self.identity_function(triples_or_pairs_or_thing)
            else:
                self.identity = self.identity_function(triples_or_pairs_or_thing)

        else:
            self._idfun_map = {}  # TODO
            self.identity = self.identity_function(triples_or_pairs_or_thing)

        real_self = super().__new__(cls, self.identity)
        if debug == True:
            return self

        # not set unless in debug
        #real_self._alt_subject_condensed_identities = self._alt_subject_condensed_identities
        #real_self._alt_subject_embedded_identities = self._alt_subject_embedded_identities

        # FIXME if you need this set debug=True for now until we get versions sorted out correctly
        # for backward compat we shuffle these along so that calls to IBN('').identity_function work
        real_self._reccache = self._reccache
        real_self._oi_cache = self._oi_cache

        real_self.version = self.version
        real_self.debug = debug
        real_self._idfun_map = self._idfun_map
        real_self._pot = self._pot
        real_self.identity = self.identity
        real_self.null_identity = self.null_identity
        real_self.symmetric_predicates = self.symmetric_predicates
        real_self.cypher_field_separator_hash = self.cypher_field_separator_hash
        return real_self

    @staticmethod
    def tat(thing, version, pot):
        if pot:
            if len(thing) == 2:
                return it['pair']
            elif len(thing) == 3:
                return it['triple']
            else:
                raise TypeError(f'{type(thing)} not a pair or triple ... {thing}')

        if isinstance(thing, IdentityBNode):
            if thing.version != version:
                raise ValueError(f'versions do not match! {thing.version} != {version}')  # FIXME error type
            return it['ident']
        elif isinstance(thing, rdflib.BNode):
            return it['raw-bnode']
        elif isinstance(thing, bytes) or isinstance(thing, str):
            return it['bytes']
        elif isinstance(thing, rdflib.Graph):
            return it['triple-seq']
        elif isinstance(thing, rdflib.namespace.NamespaceManager):  # FIXME TODO
            raise NotImplementedError('TODO')
        elif isinstance(thing, tuple) or isinstance(thing, list):
            if thing:
                t0 = thing[0]
                if isinstance(t0, tuple):  # assume pair or trip seq based on t0, which is not always true
                    if len(t0) == 2:
                        return it['pair-seq']  # XXX local conventions, NO BNODES!
                    elif len(t0) == 3:
                        return it['triple-seq']
                    else:
                        raise NotImplementedError(f'TODO {len(t0)}')
                else:
                    t0type = IdentityBNode.tat(t0, version, pot)
                    return it[f'{t0type.name}-seq']
                    #raise NotImplementedError(f'TODO {type(t0)} {t0}')
            else:
                return it['empty-seq']
        else:
            raise NotImplementedError(f'{type(thing)} {thing}')

    def check(self, other):
        if self.version >= 3:
            oid = self._identity_function(other, self.tat(other, self.version, False))
        else:
            oid = self.identity_function(other)

        return self.identity == oid

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

    null_equivalents = None, list(), tuple(), set(), dict(), b'', '', False
    def to_bytes(self, thing):
        if isinstance(thing, bytes):
            raise TypeError(f'{thing} is already bytes')
        elif type(thing) == str:
            return thing.encode(self.encoding)
        elif thing is None or thing in self.null_equivalents:
            return b''  # this makes much more sense
            # not catching None here will lead to nasty silent failures
            breakpoint()
            raise ValueError(f'not converting {thing!r} to bytes directly!')
        else:
            return str(thing).encode(self.encoding)

    # FIXME this is get shared betwen versions!
    _oi_cache_top = {}  # as or more important that caching at recurse
    def ordered_identity(self, *things, separator=True):
        """ this assumes that the things are ALREADY ordered correctly """
        if (things, separator) in self._oi_cache:
            return self._oi_cache[(things, separator)]

        m = self.cypher()
        for i, thing in enumerate(things):
            if separator and i > 0:  # insert field separator
                m.update(self.cypher_field_separator_hash)
            if thing is None:  # all null are converted to the starting hash
                raise TypeError("should already have converted None -> b'' at this point")
                thing = self.null_identity
            if type(thing) != bytes:
                raise TypeError(f'{type(thing)} is not bytes, did you forget to call to_bytes first?')
            m.update(thing)

        identity = m.digest()
        if self.debug:
            self.id_lookup[identity] = tuple(self.id_lookup[t] if
                                             t in self.id_lookup else
                                             t for t in things)

        self._oi_cache[(things, separator)] = identity
        return identity

    def triple_identity(self, subject, predicate, object):
        """ Compute the identity of a triple.
            Also handles symmetric predicates.

            NOTE that ordering for sympreds is on the bytes representation
            of a node, regardless of whether it is has already been digested """

        bytes_s, bytes_p, bytes_o = self.recurse((subject, predicate, object))
        if predicate in self.symmetric_predicates and bytes_s < bytes_o:
            # FIXME not clear we should do this here at all, I'm pretty sure we
            # should alter that a symmetric predicate has been detected ???
            # or maybe as long as they have to be passed in explicitly we are ok?
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

    _reccache_top = {}  # FIXME shared between versions !!!
    _cache_hits = 0
    def recurse(self, triples_or_pairs_or_thing, bnodes_ok=False, pot=False):
        """ Absolutely must memoize the results for this otherwise
        processing large ontologies might as well be mining bitcon """

        no_cache = False  # for debug
        if no_cache or [ty for ty in (list, rdflib.Graph) if isinstance(triples_or_pairs_or_thing, ty)]:
            # FIXME TODO make sure we filter the right types here
            yield from self._recurse(triples_or_pairs_or_thing, bnodes_ok=bnodes_ok, pot=pot)
        else:
            if triples_or_pairs_or_thing not in self._reccache:
                ids = list(self._recurse(triples_or_pairs_or_thing, bnodes_ok=bnodes_ok, pot=pot))
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

    def _recurse(self, triples_or_pairs_or_thing, bnodes_ok=False, pot=False):
        if triples_or_pairs_or_thing is None or isinstance(triples_or_pairs_or_thing, str):
            breakpoint()

        if ((isinstance(triples_or_pairs_or_thing, list) or isinstance(triples_or_pairs_or_thing, tuple)) and
            (not [_ for _ in triples_or_pairs_or_thing if not ((isinstance(_, list) or isinstance(_, tuple)) and len(_) == 3)]) and
            [(s, p, o) for s, p, o in triples_or_pairs_or_thing if s == None and p == rdflib.RDF.rest and isinstance(o, rdflib.BNode)]):
            #breakpoint()  # test_list_3
            pass

        # FIXME somehow we are getting null subjects when dealing with lists ???
        if pot:
            ltpot = len(triples_or_pairs_or_thing)
            if ltpot != 2 and ltpot != 3:
                msg = f'not a pair or triple {ltpot}'
                raise ValueError(msg)
            triples_or_pairs_or_thing = triples_or_pairs_or_thing,

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

                # FIXME this is really what induces the double hasing because everything else comes out of here unhashed
                v, d, l = self.recurse((str(thing), thing.datatype, thing.language))
                yield self.ordered_identity(v, d, l)
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
                                    # FIXME we don't want this, for symmetric either duplicate the predicate on both
                                    # parents, or normalize in some other way, ibnode should not modify the graph
                                    # it should just warn if lack of normalization is detected

                                    # have to do this a bit differently than in triple_identity due to tracking subject
                                    if o < s:  # for symmetric both should be urirefs but who knows
                                        s, o = o, s

                                # reminder that recurse will process this not as a pair
                                # but as two individual values and then compute id
                                # FIXME why am i getting an identity back on the second round !??!
                                #if self.version == 2:
                                    #breakpoint()
                                id_or_bytes = list(self.recurse((p, o)))  # can't set pot=True here or None gets inserted in subject_identities
                                if len(id_or_bytes) == 2:
                                    if self.version > 2:
                                        _p, _o = id_or_bytes
                                        if isinstance(o, rdflib.Literal):
                                            # literals have already been hashed
                                            # TODO FIXME yes we will get this
                                            # cleaned up ... what a mess
                                            pid = self.ordered_identity(
                                                self.ordered_identity(_p),
                                                _o,
                                                separator=False)
                                        else:
                                            pid = self.ordered_identity(
                                                self.ordered_identity(_p),
                                                self.ordered_identity(_o),
                                                separator=False)
                                    else:
                                        ## XXX oh no we were double digesting because of caching !?!??
                                        pid = self.ordered_identity(*id_or_bytes)

                                    self.subject_identities[s].append(pid)
                                else:
                                    # already in subject_identities
                                    if not id_or_bytes:
                                        breakpoint()
                                    pid = id_or_bytes[0]

                                # XXX DO NOT YIELD pid HERE as populating the cache will prevent
                                # subject_identities from populating correct
                                #yield pid

                                #if s not in self.subject_identities:
                                    #self.subject_identities[s].append(pid)

                                #breakpoint()  # FIXME somehow we don't hit this ???
                                #log.debug((s, p, o, pid))
                            elif self.version == 1:
                                yield self.triple_identity(s, p, o)  # old way
                            else:
                                raise NotImplementedError(f'unknown version {self.version}')

                        elif lt == 2:
                            # don't sort, preserve the original ordering in this case
                            # FIXME still worried about cases where something is 2 long but not a pair
                            if self.version > 2:
                                p, o = thing
                                _p, _o = self.recurse(thing)
                                if isinstance(o, rdflib.Literal):
                                    pid = self.ordered_identity(
                                        self.ordered_identity(_p),
                                        _o,
                                        separator=False)
                                else:
                                    pid = self.ordered_identity(
                                        self.ordered_identity(_p),
                                        self.ordered_identity(_o),
                                        separator=False)
                            else:
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
                                # DO NOT YEILD HERE EITHER because we need subject_identities
                                # to be populated each time
                                # FIXME this seems wrong and wasteful, except for
                                # the fact that this branch only runs for top level pairs
                                # maybe in v4 we will get it correct
                                #yield pid  # ok to yield pid for pairs
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

                        if (p == rdflib.RDF.first or p == rdflib.RDF.rest) or (p == rdflib.RDF.type and o == rdflib.RDF.List):
                            #breakpoint()  # test_list_4
                            pass

                        if isinstance(p, rdflib.BNode) and not isinstance(p, self.__class__):
                            # predicates cannot be blank, unless it is actually an identity being passed
                            raise TypeError(f'predicates cannot be blank {thing}')

                        if p == rdflib.RDF.type and o == rdflib.RDF.List:
                            # just ignore these
                            # XXX LOOOOL this fixed the problem in test_list_4 altogether
                            continue
                        elif True:
                            # there is NO easy way to deal with list reordering
                            # at this phase of the pipeline so for now leave the
                            # lists as they are, and explore other ways of achieving
                            # ordering invariance, all of these cases require special
                            # treatment of lists  ... so not implementing for now
                            pass
                        elif p == rdflib.RDF.rest:
                            # FIXME TODO no reorder list predicates
                            if o == rdflib.RDF.nil:
                                self.to_lift.add(thing)
                            else:
                                if o in self.find_heads:
                                    # FIXME turns out that this CAN and does happen
                                    # if there is a malformed list
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
                                if self.version > 2:
                                    _p, _o = self.recurse((p, o))  # XXX watch out for cached results issue ?
                                    if isinstance(o, rdflib.Literal):
                                        # see note above, in the current implementation rdflib.Literal is already
                                        # hashed by recurse :/
                                        pid = self.ordered_identity(
                                            self.ordered_identity(_p),
                                            _o,
                                            separator=False)
                                    else:
                                        pid = self.ordered_identity(
                                            self.ordered_identity(_p),
                                            self.ordered_identity(_o),
                                            separator=False)
                                else:
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

        from pyontutils.core import OntGraph  # FIXME for cycle check, but can implement without the dep
        count = 0
        limit = 999999
        #starting = {k:v for k, v in self.awaiting_object_identity.items()}
        prev = len(self.awaiting_object_identity) + 1
        #if self.awaiting_object_identity:  # XXX yeah both bnodes and urirefs are in here
            #log.debug(f'awaiting types: {set(type(e) for e in self.awaiting_object_identity)}')
        last = False
        while self.awaiting_object_identity or last or count == 0:
            count += 1
            # XXX FIXME how is it that we avoid cycles here ???
            this = len(self.awaiting_object_identity)
            if last or this == 0:
                pass
            elif this == prev:
                # cycle check any remaining nodes if we appear to be in steady state

                #awaiting_by_object = {}
                #for v in self.awaiting_object_identity.values():
                #    for s, p, o in v:
                #        if o not in awaiting_by_object:
                #            awaiting_by_object[o] = []

                #        awaiting_by_object[o].append((s, p, o))

                none_bnode = rdflib.BNode() # since None is usually a substition for metadata subject the risk of cycles is zero (among other reasons)
                g = OntGraph().populate_from_triples([
                    (none_bnode, *t[1:]) if t[0] is None else t for v in self.awaiting_object_identity.values() for t in v])

                cycles = g.cycle_check_long()
                in_cycles = {}
                cycle_members = []
                for cycle in cycles:
                    members = set(e for _s, _, _o in cycle for e in (_s, _o))
                    cycle_members.append(members)
                    for e in members:
                        if e not in in_cycles:
                            in_cycles[e] = []

                        in_cycles[e].append(cycle)

                connected_members = []
                done = []
                for i, mem1 in enumerate(cycle_members):
                    if mem1 in done:
                        # since set intersection is transitive once a
                        # connection is made any other connections
                        # will also be made in the first pass through
                        # the list so we don't need to do any more
                        # because they will actually be subsets that
                        # are missing members from earlier cycles
                        continue
                    connected = set(mem1)
                    for mem2 in cycle_members[i + 1:]:
                        if connected & mem2:
                            connected.update(mem2)
                            done.append(mem2)

                    connected_members.append(connected)


                # when we have to break a cycle the process is the following
                # get a count of the number of nodes in the cycle
                # the order matters, but because it is cyclical there are n
                # equivalent orders so we have to pick one, and the one we pick
                # should be the one that ranks lowest based on the following
                # critiera:
                # negative of the number of triples awaiting ids with that node as a subject (many appear first)
                # negative of number of existing ids already computed for that node (many appear first)
                # the sort ranking of the predicates in the triples awaiting
                # the sort ranking of the sorted existing identities
                # 
                # if there is still a tie for which node should start
                # after that then if there another node which is not tied
                # with some other node that is greater those that are tied
                # then that node because the starting point
                # if that does not work then if they are all identical we just pick one
                # i think we don't have to resort to the case where we need to compute
                # the hash with everything in the cycle
                # absolute worst case the starting the cycle number tied the
                # least the checksum of the cycle will be computed for each possible starting node

                # note that if all nodes are identical e.g. just _:0 :p _:1, _:1 :p _:0
                # then the position doesn't matter because they are all the same and the
                # result will be the same no matter what

                # XXX we actually want to replace the object with a cycle-break value
                # and the place we want to cut is at any node which participats in
                # the largest number of cycles with the least number of triples where
                # it is the ... ??? object ??? or is it subject ??? least number of cuts
                # and largest number of outstanding triples, if we replace where it is
                # as an object ... but we don't currently index that way
                def mkey(b):
                    #if len(in_cycles[b]) != len(self.awaiting_object_identity[b]):
                        #wat = in_cycles[b], self.awaiting_object_identity[b]
                        #breakpoint()
                    #assert len(in_cycles[b]) == len(self.awaiting_object_identity[b]), f'{in_cycles[b]} {self.awaiting_object_identity[b]}'
                    return (
                        -len(in_cycles[b]),  # number of cycles (before a shared cycle point has more due to rdf asymmetry)
                        len(self.awaiting_object_identity[b]),  # number of cycle triples (cycle point has more)
                        -sum([len(c) for c in in_cycles[b]]),  # combined length of cycles
                        -len(self.bnode_identities[b]),  # number of non-cycle triples
                        sorted([p for s, p, o in self.awaiting_object_identity[b]]),
                        sorted(self.bnode_identities[b]),
                        b,  # debug only
                    )

                # FIXME length one cycle is a degenerate case that we need to handle ??
                # or rather the cycle breaking bnode needs to take into account its predicate
                # so maybe it becomes (p cycle-break-{cycle-length}) or something like that?
                # or maybe it is (p cycle-break-{hash-of-all-the-predicates-in-the-cycle}) ???
                # actually we also have any other identities for such triples as well which
                # complicates the single triple cycle quite badly, also if the breakpoint
                # in question has more than one cycle length that complicates matters ...
                # maybe the better way to think about this is that when we break a cycle
                # it isn't the subject that gets an identity it is as if we replace the
                # object with something else entirely and just cycle-break by itself might
                # be sufficient though there could be confusion if someone creates a literal
                # with cycle-break as the value, so maybe the hash of cycle-break ?

                # TODO i think what we do is replace the triple in awaiting object identity and then
                # process_awaiting_triples handles the rest??
                # the other option is to provide a semi-real identity for the subject, the problem
                # is that some of these subjects have other ids already, but we want to minimize the
                # number of cut points?

                btc = rdflib.BNode('BREAK-THE-CYCLE')
                if btc not in self.subject_identities:
                    self.subject_identities[btc] = [self.ordered_identity(b'BREAK-THE-CYCLE')]
                    self.bnode_identities[btc] = self.subject_identities[btc][0]
                _done = set()
                #for members in connected_members:
                for members in cycle_members:
                    qq = sorted([mkey(_) for _ in members])
                    hrm = sorted(members, key=mkey)
                    #give_me_an_identity = hrm[0]
                    break_the_cycle = hrm[0]
                    if break_the_cycle in _done:
                        #log.debug('let the cycle already be broken')
                        continue

                    _done.add(break_the_cycle)
                    self.awaiting_object_identity[break_the_cycle] = [
                        # in this version we are selecting the tail of the cycle
                        # instead of the head ... FIXME if there are multiple common
                        # cycles we will need to make sure we are able to cut each
                        # cycle so we don't iterate over connected members ... we
                        # iterate over cycles for the purposes of cutting and by
                        # choosing nodes that participant in the largest number of
                        # cycles we should already be done with them
                        (s, p, btc)
                        for s, p, o in self.awaiting_object_identity[break_the_cycle]]

                    self.subject_identities[break_the_cycle].append(self.subject_identities[btc][0])

            elif count > limit:
                # XXX the last issue is with bnode cycles which should be impossible but somehow is not !??!
                # looks like there is some issue in the internal transformations before we get to the graph?
                # maybe the issue is in rapper or something?
                breakpoint()
                raise NotImplementedError('oops')
            else:
                prev = this

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

                        #if self._pot:  # no this wasn't the issue because the bug is not happening in the pot case
                            #subject_identity = subject_idents[0]
                        #else:
                        # FIXME subject_idents is what is wrong for the bnode case ...
                        subject_identity = self.ordered_identity(*sorted(subject_idents), separator=False)

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

                        # FIXME somehow this blanknodes in meta sections result in spurious inclusion in unnamed heads ?!??!
                        # XXX likely because I didn't handle metadata containing subgraphs at all originally
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

            # second complete any nodes that are fully identified
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

    _if_cache = {}  # FIXME version issue
    _if_debug_cache = {}
    _if_predicate_cache = {}  # this one usually doesn't need to be reset and is heavily used
    def _identity_function(self, thing, treat_as_type, *, id_method=None, in_graph=None, is_pred=False):
        # FIXME TODO treat_as_type to something other than
        # strings for better performance maybe? probably much later

        # FIXME consider a variant of these that doesn't
        # require continual tuple unpacking and repacking
        oid = self.ordered_identity

        def sid(*things, separator=True):
            return oid(*sorted(things), separator=separator)

        input_type = treat_as_type
        if id_method:
            treat_as_type = id_method
        else:
            # by keeping this indirection here it is possible to reuse this
            # function for multiple different identity functions
            treat_as_type = self._idfun_map[input_type]

        try:
            # we can't/dont't cache unhashable things (e.g. lists)
            if is_pred:
                try:
                    return self._if_predicate_cache[thing]
                except KeyError:
                    pass

            elif in_graph is not None and (in_graph, thing, treat_as_type) in self._if_cache:
                return self._if_cache[(in_graph, thing, treat_as_type)]
            elif (thing, treat_as_type) in self._if_cache:
                return self._if_cache[thing, treat_as_type]
        except TypeError:
            pass

        if treat_as_type == idf['bytes']:
            if isinstance(thing, bytes):
                ident = oid(thing)
            elif isinstance(thing, rdflib.Literal):
                # TODO make sure str(thing) is what we want, I'm pretty sure it is based on how the serialization works
                # e.g. rdflib.Literal('True', datatype=xsd.boolean) is "True" "xsd:boolean-expanded-string" internally
                # even though rdflib.Literal.toPython() gives something else
                v, d, l = [self._identity_function(e, treat_as_type=it['bytes']) for e in (str(thing), thing.datatype, thing.language)]
                ident = oid(v, d, l, separator=False)
            elif isinstance(thing, rdflib.BNode):
                breakpoint()
                raise TypeError(f'no bnodes here {type(thing)}')
            elif thing in self.null_equivalents:
                ident = self.null_identity
            #elif thing is True:  # FIXME TODO ...
                #ident = oid(b'1')
            else:
                ident = oid(self.to_bytes(thing))  # FIXME dangerous stringification happens in to_bytes right now
        elif treat_as_type == idf['pair']:  # in ('pair', '(p o)'):
            ident = oid(self._identity_function(thing[0], it['bytes'], is_pred=True), self._identity_function(thing[1], it['bytes']), separator=False)
        elif treat_as_type == idf['pair-ident']:  # in ('pair-ident', '(p id)'):
            # it looks like in the current implementation we do not
            # double hash the identity of the bnode in the object position
            # because it already IS the identity of the bnode in that position
            # its just that passing in an actual blanknode and looking up its
            # id is a separate process
            p, ident_o = thing
            ident = oid(self._identity_function(p, it['bytes'], is_pred=True), ident_o, separator=False)
        elif treat_as_type == idf['triple']:  # in ('triple', '(s (p o))'):
            s, p, o = thing
            ident = oid(self._identity_function(s, it['bytes']),
                        self._identity_function((p, o), it['pair']), separator=False)
        elif treat_as_type == idf['record-seq']:  # in ('trip-seq', '((s ((p o) ...)) ...)'):
            bnode_identities = defaultdict(list)
            subject_identities = defaultdict(list)

            # we might as well process as much of the bnode work as we can for now
            connected_heads = set()
            bsubjects = defaultdict(lambda: 0)  # turns out we need to count this too
            bobjects = defaultdict(lambda: 0)  # need to know how many times a node appears as an object in general because > 1 means free head
            unresolved_bnodes = defaultdict(list)
            transitive_triples = defaultdict(list)
            for s, p, o in thing:
                sn = isinstance(s, rdflib.BNode)
                on = isinstance(o, rdflib.BNode)
                # if you try to on := here you will footgun and on will take the value of the last loop where sn was False ...
                # two seemingly orthogonal features combining to reck your day
                # i think that definitately classifies as an excellent LOL PYTHON
                if (sn or on):
                    unresolved_pair = True
                    if sn:
                        bsubjects[s] += 1
                        transitive_triples[s].append((s, p, o))

                    if on:
                        bobjects[o] += 1
                        if isinstance(s, rdflib.URIRef):
                            connected_heads.add(o)
                    else:
                        unresolved_pair = False

                    if unresolved_pair:
                        unresolved_bnodes[s].append((p, o))
                        continue  # TODO

                ident_po = self._identity_function((p, o), it['pair'])
                if sn:
                    bnode_identities[s].append((ident_po, (p, o)))
                else:
                    subject_identities[s].append((ident_po, (p, o)))

            if input_type == it['graph-named'] and (bsubjects or bobjects):
                raise TypeError(f'graph-named contains bnodes! {bsubjects} {bobjects}')
            elif input_type == it['graph-bnode'] and subject_identities:
                # there shouldn't be anything here at this point except in the
                # case where there were dangling identities
                bads = []
                for _s, (_, (_p, _o)) in subject_identities.items():
                    if not isinstance(_o, rdflib.BNode):
                        bads.append((_s, _p, _o))

                if bads:
                    raise TypeError(f'graph-bnode contains named! {bads}')

            subject_condensed_identities = {}
            subject_embedded_identities = {}
            free_heads = set(k for k, v in bobjects.items() if v > 1)
            replace_when_object = set()
            cycles_member_index = defaultdict(list)
            cycles = []  # for debug in case there aren't any unresolved bnodes at all
            _debug_mkey = []
            if unresolved_bnodes:
                sbsubjects = set(bsubjects)
                sbobjects = set(bobjects)
                more_free_heads = sbsubjects - sbobjects
                free_heads.update(more_free_heads)
                dangling = sbobjects - sbsubjects

                # resolve dangling
                for o in dangling:
                    subject_condensed_identities[o] = self.null_identity
                    subject_embedded_identities[o] = self.null_identity
                    try:
                        # we can't/dont't cache unhashable things (e.g. lists)
                        self._if_cache[thing, o, idf['((p o) ...)']] = self.null_identity
                        self._if_cache[thing, o, idf['(s ((p o) ...))']] = self.null_identity
                    except TypeError:
                        pass

                # FIXME TODO move cycle check to its own file to avoid you got it, circular imports HAH
                from pyontutils.core import OntGraph
                g = OntGraph().populate_from_triples((s, p, o) for s, pos in unresolved_bnodes.items() for p, o in pos)

                # detect cycles
                cycles = g.cycle_check_long()
                btc = rdflib.BNode('BREAK-THE-CYCLE')

                # break cycles
                if cycles:
                    ident_btc = self.ordered_identity(b'BREAK-THE-CYCLE')
                    if btc not in subject_embedded_identities:
                        subject_condensed_identities[btc] = ident_btc
                        subject_embedded_identities[btc] = ident_btc

                    # the sparse member ids approach allows us to choose the
                    # cutpoint based on the total structure of the cycle
                    # without trying to come up with arbitrary rules
                    sparse_member_ids = {}
                    cycle_members = []
                    for i, cycle in enumerate(cycles):
                        if len(cycle) > 99:
                            # TODO better logging
                            log.warning(f'absurd bnode cycle detect with length {len(cycle)}')

                        members = set(e for _s, _, _o in cycle for e in (_s, _o))
                        cycle_members.append(members)
                        for member in members:
                            # construct a cycle where the member of the moment will be at the head
                            mem_cycle = [(s, p, btc) if o == member else (s, p, o) for s, p, o in cycle]
                            # FIXME performance can be quite bad here, consider using a single graph
                            mg = OntGraph().populate_from_triples(mem_cycle)
                            mi = mg.subjectEmbeddedIdentity(member)
                            sparse_member_ids[i, member] = mi

                    if self.debug:
                        for _cm in cycle_members:
                            for _m in _cm:
                                cycles_member_index[_m].append(_cm)

                    def make_mkey(i):
                        def mkey(b, *, _i=i):
                            return sparse_member_ids[_i, b]

                        return mkey

                    for i, members in enumerate(cycle_members):
                        mkey = make_mkey(i)
                        break_the_cycle = sorted(members, key=mkey)[0]
                        if self.debug:
                            _debug_mkey.append(sorted([(mkey(b), b) for b in members]))

                        replace_when_object.add(break_the_cycle)

                    # new free heads are those that will now no longer appear as objects
                    # i.e. those in replace_when_object because that is equivalent to
                    # removing them from bobjects above, if they are in a cycle
                    # then they by definition must have appeard in free head position
                    # regardless of whether or not they were in connected heads as well
                    free_heads.update(replace_when_object)

                    valid_replace_triples = set(t for c in cycles for t in c if t[-1] in replace_when_object)
                    cycles_broken = dict(unresolved_bnodes)
                    for s, pos in unresolved_bnodes.items():
                        new_pos = []
                        for p, o in pos:
                            if (s, p, o) in valid_replace_triples:
                                new_pos.append((p, btc))
                            else:
                                new_pos.append((p, o))

                        cycles_broken[s] = new_pos

                    msg = '''NotImplementedCorrectlyError
see test/test_ibnode::TestStability::test_stab, this impl is NOT stable on
cpython and pretty much never collides with the stable behavior in pypy
until this is resolved do not use this for graphs with cycles, otherwise
you will only very rarely be able to determine that two graphs are the same'''
                    raise NotImplementedError(msg)

                else:
                    cycles_broken = unresolved_bnodes

                if self.debug:
                    ncg = OntGraph().populate_from_triples((s, p, o) for s, pos in cycles_broken.items() for p, o in pos)
                    should_not_but_cycles = ncg.cycle_check_long(btc_node=btc)
                    if should_not_but_cycles:
                        watg = tuple(set(t for cyc in should_not_but_cycles for t in cyc))
                        try:
                            toposort([(s, o) for s, p, o in watg])  # fortunately toposort is correct so use it for sanity
                            breakpoint()  # WAT
                        except Exception as e:
                            ecyc = e.args[1]
                            cycs = [cyc for cyc in should_not_but_cycles if [t for t in cyc if ecyc in t]]
                            _sigh = sorted(_debug_mkey, reverse=True)
                            log.exception(e)
                            breakpoint()
                            raise e

                # toposort
                subject_order = toposort([(s, o) for s, pos in cycles_broken.items() for p, o in pos])

                # resolve identities in a single pass
                for s in subject_order:
                    if s not in cycles_broken:
                        # this means that all component identities
                        # have already been calculated and we should
                        # finish up here
                        if s in bnode_identities:
                            ident_s = sid(*[i for i, po in bnode_identities[s]], separator=False)
                            subject_condensed_identities[s] = ident_s
                            subject_embedded_identities[s] = ident_s
                            if s in free_heads:
                                assert s not in subject_identities, 'bah'
                                subject_identities[s] = bnode_identities[s]
                            else:
                                try:
                                    self._if_cache[thing, s, idf['((p o) ...)']] = ident_s
                                    self._if_cache[thing, s, idf['(s ((p o) ...))']] = ident_s
                                except TypeError:
                                    # we can't/won't cache unhashable things (e.g. lists)
                                    pass
                        elif s not in subject_embedded_identities:
                            raise ValueError(f'oops no {s}')

                        continue

                    pos = cycles_broken[s]
                    idents_po = []
                    for p, o in pos:
                        if isinstance(o, rdflib.BNode):
                            if o not in subject_embedded_identities:
                                breakpoint()
                            ident_o = subject_embedded_identities[o]
                            ident_po = self._identity_function((p, ident_o), it['(p id)'])
                        else:
                            raise ValueError('should never get here, should have been dealt with above')
                            ident_po = self._identity_function((p, o), it['pair'])

                        idents_po.append((ident_po, (p, o)))

                        if o in transitive_triples:
                            transitive_triples[s].extend(transitive_triples[o])  # FIXME maybe pop

                    if isinstance(s, rdflib.BNode):
                        bnode_identities[s].extend(idents_po)  # bnode_identities[s] might already have identities
                        ident_s = sid(*[i for i, po in bnode_identities[s]], separator=False)
                        subject_condensed_identities[s] = ident_s
                        subject_embedded_identities[s] = ident_s
                        if s in free_heads:
                            assert s not in subject_identities, 'bah'
                            subject_identities[s] = bnode_identities[s]
                        else:
                            # we set these even though they are derived from
                            # the break the cycle bnode or are part of subgraph
                            # we do not put them in subject identifiers so they
                            # do not go as top level, but they can be recovered
                            # and should be stable if we got the cycle break
                            # logic right
                            try:
                                self._if_cache[thing, s, idf['((p o) ...)']] = ident_s
                                self._if_cache[thing, s, idf['(s ((p o) ...))']] = ident_s
                            except TypeError:
                                # we can't/won't cache unhashable things (e.g. lists)
                                pass
                    else:
                        # FIXME TODO watch out for that case where a
                        # uri subject has references to two identical
                        # connected subgraphs replicas, aka no set()
                        subject_identities[s].extend(idents_po)

                # when we reach the end of processing and are sure that
                # there aren't any remaining nodes to process then we can
                # safely process any free heads that were totally identified
                # as part of the first step that we have not already inserted
                # into subject_identities
                for s in free_heads:
                    if s not in subject_identities:
                        idents_po = bnode_identities[s]
                        ident_s = sid(*[i for i, po in idents_po], separator=False)
                        subject_condensed_identities[s] = ident_s
                        subject_embedded_identities[s] = ident_s
                        subject_identities[s] = bnode_identities[s]

            elif bnode_identities:
                # all bnodes might be resolved because there were only bnodes
                # at the heads of free subgraphs
                for s, idents_po in bnode_identities.items():
                    free_heads.add(s)
                    ident_s = sid(*[i for i, po in idents_po], separator=False)
                    subject_condensed_identities[s] = ident_s
                    subject_embedded_identities[s] = ident_s
                    # s is in free heads but free heads does not exist in this branch
                    assert s not in subject_identities, 'bah'
                    subject_identities[s] = bnode_identities[s]

            seids = []
            for s, idpos in subject_identities.items():
                if s in subject_embedded_identities:
                    # free subgraph case, so e and c are the same value
                    _seid = subject_embedded_identities[s]
                    try:
                        self._if_cache[thing, s, idf['((p o) ...)']] = subject_condensed_identities[s]
                        self._if_cache[thing, s, idf['(s ((p o) ...))']] = _seid
                    except TypeError:
                        # we can't/won't cache unhashable things (e.g. lists)
                        pass

                    seids.append(_seid)
                    continue

                ids, pos = zip(*idpos)
                try:
                    condensed = sid(*ids, separator=False)  # TODO should this call identity function recursively?
                except Exception as e:
                    breakpoint()
                    raise e
                spos = tuple(sorted(pos))
                self._if_cache[spos, idf['condensed']] = condensed  # XXX probably not helpful  # TODO perf/mem check to see if needed
                embedded = oid(self._identity_function(s, it['bytes']), condensed, separator=False)
                try:
                    self._if_cache[thing, s, idf['((p o) ...)']] = condensed
                    self._if_cache[thing, s, idf['(s ((p o) ...))']] = embedded
                except TypeError:
                    # we can't/won't cache unhashable things (e.g. lists)
                    pass
                self._if_cache[(s, spos), idf['(s ((p o) ...))']] = embedded  # TODO perf/mem check to see if needed
                subject_condensed_identities[s] = condensed
                subject_embedded_identities[s] = embedded
                seids.append(embedded)

            # XXX returning a list of identities as an identity is type
            # insanity, but at least it is marked by having to pass as_type
            try:
                self._if_cache[thing, idf['(s ((p o) ...)) ...']] = seids  # better version of all_idents_new
            except TypeError:
                # we can't/won't cache unhashable things (e.g. lists)
                pass

            ident = sid(*seids, separator=False)

            if self.debug:
                # these are for debug only because values will not repopulate
                # the new caching in this implementation means that we should
                # be able to just apply IdentityBNode to the raw object and
                # get the cached result
                self._alt_debug = dict(
                    transitive_triples = transitive_triples,
                    debug_mkey = _debug_mkey,  # up top because it can get very long
                    subject_condensed_identities = subject_condensed_identities,
                    subject_embedded_identities = subject_embedded_identities,
                    seids = seids,
                    bnode_identities = bnode_identities,
                    subject_identities = subject_identities,
                    connected_heads = connected_heads,
                    free_heads = free_heads,
                    replace_when_object = replace_when_object,
                    cycles_member_index = cycles_member_index,
                    cycles = cycles,
                )
                # FIXME this only partially works because we also want it for all sub-identities too
                self._if_debug_cache[ident] = self._alt_debug

        elif treat_as_type == idf['graph-combined-and-local-conventions']:
            lc = self._identity_function(thing.namespace_manager, treat_as_type=it['pair-seq'])
            gc = self._identity_function(thing, treat_as_type=it['graph-combined'])
            ident = oid(lc, gc, separator=False)
        elif treat_as_type == idf['graph-combined']:
            named, bnode = split_named_bnode(thing)
            gn = self._identity_function(named, treat_as_type=it['graph-named'])
            gb = self._identity_function(bnode, treat_as_type=it['graph-bnode'])
            # TODO figure out if there is some more consistent way to deal with this?
            for nkey in [k for k in self._if_cache if named in k]:
                new_nkey = (thing, 'named'), *nkey[1:]
                self._if_cache[new_nkey] = self._if_cache.pop(nkey)

            for bkey in [k for k in self._if_cache if bnode in k]:
                new_bkey = (thing, 'bnode'), *bkey[1:]
                self._if_cache[new_bkey] = self._if_cache.pop(bkey)

            ident = oid(gn, gb, separator=False)
        elif treat_as_type == idf['pair-seq']:
            # XXX NOTE pair seqs may not have any bnodes, there are
            # different than the meta section! think curies
            ids = []
            for p, o in thing:
                if isinstance(o, rdflib.BNode):
                    breakpoint()
                    raise TypeError('pair-seq cannot contain bnodes')
                    continue  # TODO

                ident_po = self._identity_function((p, o), it['pair'])
                ids.append(ident_po)

            ident = sid(*ids, separator=False)

        elif treat_as_type == idf['bytes-seq']:
            ident = sid(*[self._identity_function(_, it['bytes']) for _ in thing], separator=False)
        elif treat_as_type == idf['ident-seq']:
            ident = sid(*[self._identity_function(_, it['ident']) for _ in thing], separator=False)
        elif treat_as_type == 'empty-seq':
            # FIXME TODO '' vs b'' vs [] vs tupe() vs set() etc. WHAT IS '()
            ident = self.null_identity
        elif treat_as_type == idf['ident']:
            ident = oid(thing.identity)  # oid() to make behavior homogenous
            # ironically in no cases should an identity function ever return
            # the same value that it was given because that only works if you
            # are dealing in pure mathematics and not in a reduced space if it
            # were to return the same value then a colision attack becomes
            # trivial because there are always guranteed to be two inputs that
            # return the same value, the thing itself and identity of the thing
            # which makes it impossible to use the identity function to
            # distinguish between the thing itself and its identity, a big oops
        elif treat_as_type == idf['raw-bnode']:
            raise ValueError('BNodes only have names or collective identity...')
            if False:  # bnodes_ok:  # old feature which seems not to have been used anywhere?
                # if you explicitly want to compare raw bnodes we'll let you
                # but their identity is themselves this type should never be
                # used internally and is only for backward compat
                ident = f'bnode-{_session_only_token}-{thing}'.encode()
                # to keep the types sane we still return an identity, however
                # the session only token is there to ensure that comparisons
                # cannot be made between bnodes from different processes
        elif treat_as_type == idf['tripair-seq']:
            # XXX don't use this, only for backward compat
            # amusingly the only place this shows up is where we remove the
            # subject in the first place >_<
            _new_thing = [tp if len(tp) == 3 else (bnNone, *tp) for tp in thing]
            ident = self._identity_function(_new_thing, it['triple-seq'])
        elif treat_as_type == 'seq-of-ordered-seqs':
            # FIXME TODO this is actually the unifying
            # version for pairs and triples, the issue is that
            # the caller might not always know, AND there is
            # the question of how to specify which if any
            # should be accumulated over ... so not implementing right now
            raise NotImplementedError('maybe in the future?')
        elif treat_as_type == '(s ((p o) ...))':
            raise NotImplementedError('todoish')
        elif treat_as_type == '((p o) ...)':
            raise NotImplementedError('todoish')
        else:
            raise NotImplementedError(f'unknown type {treat_as_type}')

        if is_pred:
            self._if_predicate_cache[thing] = ident
        else:
            try:
                self._if_cache[thing, treat_as_type] = ident
            except TypeError:
                # we can't/won't cache unhashable things (e.g. lists)
                pass

        return ident

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

        def pot_test():
            if self._pot:
                msg = f'{triples_or_pairs_or_thing} not a pair or triple unset pot=True'
                raise TypeError(msg)

        if isinstance(triples_or_pairs_or_thing, bytes):  # serialization
            pot_test()
            return self.ordered_identity(triples_or_pairs_or_thing)
        elif isinstance(triples_or_pairs_or_thing, rdflib.term.Identifier):
            pot_test()
            # NOTE rdflib.term.Node includes graphs themselves, which is good to know
            if self.version > 2 and (
                    isinstance(triples_or_pairs_or_thing, rdflib.URIRef) or
                    isinstance(triples_or_pairs_or_thing, rdflib.Literal)):
                # consistent homogenous hashing all the way down for v3, literals
                # were being hashed directly in recurse which was leading to double
                # hashing, there is a hacked fix for that right now, urirefs are
                # handled consistently now as well, ugh this thing needs a complete
                # rewrite once the relevant tests are in place :/
                if isinstance(triples_or_pairs_or_thing, rdflib.Literal):
                    # FIXME SIGH literal already hashed in recurse etc. etc.
                    return next(self.recurse((triples_or_pairs_or_thing,)))
                else:
                    return self.ordered_identity(next(self.recurse((triples_or_pairs_or_thing,))))
            else:
                return next(self.recurse((triples_or_pairs_or_thing,)))
        elif type(triples_or_pairs_or_thing) == str:  # FIXME isinstance? or is that dangerous? e.g. OntId
            pot_test()
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
            self.named_identities = tuple(self.recurse(triples_or_pairs_or_thing, pot=self._pot))  # memory :/
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
                if self._pot:
                    if len(self._thing) == 2:
                        return self.subject_identities[None][0]
                    else:
                        s = self._thing[0]
                        sid = self.__class__(s).identity
                        pid = self.subject_identities[s][0]  # should always be 1 long
                        #log.debug((sid.hex(), pid.hex()))
                        _id = self.ordered_identity(sid, pid, separator=False)
                        self.subject_condensed_identities[s] = pid
                        self.subject_embedded_identities[s] = _id
                        return _id

                for k, v in self.subject_identities.items():
                    if isinstance(k, rdflib.BNode) and k not in self.unnamed_heads:  # FIXME because we don't condense these in advance wtf are we doing?
                        # FIXME yep, bnode_identities are being calculated differently and incorrectly
                        #breakpoint()
                        continue

                    # FIXME this list should not include bnodes !??! or what ...
                    # what changed? don't we resolve all ids so that we don't need
                    # the bnode ids as subjects because they are already accounteded for?
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
                    #breakpoint()
                    log.debug('self.all_idents_new was empty')

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
