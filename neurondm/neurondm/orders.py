def nst_to_adj(l):
    start = l[0]
    if (isinstance(start, list) or isinstance(start, tuple)):
        raise ValueError('malformed')

    first = [] if start == "blank" else [(start, e[0]) for e in l[1:] if e]
    second = [p for r in l[1:] if r for p in nst_to_adj(r)]
    return tuple(first + second)

def assoc(k, ass):
    for a, b in ass:
        if a == k:
            return a, b

def dvals(k, ass):
    pair = assoc(k, ass)
    mem = ass[ass.index(pair):] if pair in ass else False
    tail = mem[1:] if mem else tuple()
    yield from ((pair[1], *dvals(k, tail)) if tail else pair[1:]) if pair else tuple()


def inest(adj, start, seen):
    nl = tuple()
    out = []
    maybe_out = []
    seen = {start} | seen
    for next_start in dvals(start, adj):
        if next_start in seen:
            # do not append if next_start already in seen
            nl, snext = (next_start,), seen
            if not out:  # multi-parent case
                # maybe out can already have results due to multi-child case
                maybe_out.append(nl)
        else:
            nl, snext = inest(adj, next_start, seen)
            out.append(nl)

        seen = snext

    if not out and maybe_out:
        out = maybe_out

    l = tuple(out)
    return ((start, *l) if l else (start,)), seen


def adj_to_nst(adj, start=None):
    keys = set([a[0] for a in adj])
    values = set([a[1] for a in adj])
    inverted = [(a[1], a[0]) for a in adj]
    starts = keys - values
    ends = values - keys

    seen = set()
    nl = None
    out = []
    for start in starts:
        nl, snext = inest(adj, start, seen)
        seen = snext
        out.append(nl)

    l = tuple(out)
    if len(l) == 1 and (isinstance(l[0], list) or isinstance(l[0], tuple)):
        return l[0]
    else:
        return ["blank", *l]


def lin_to_adj(linear):
    return tuple(zip(linear[:-1], linear[1:]))


def adj_to_lin(adj):
    # this is not deterministic when there are runs of equal length
    # this should return a list of linear paths from longest to
    # shortest that are sufficient to cover all nodes, essentially
    # the longest single path through the tree and then branches
    raise NotImplementedError('TODO')


def bind_rdflib():
    import rdflib
    from pyontutils.namespaces import rdf

    def to_rdf(g, nested):
        if isinstance(nested, list) or isinstance(nested, tuple):
            bn0 = rdflib.BNode()
            rdflib.collection.Collection(g, bn0, (to_rdf(g, n) for n in nested))
            return bn0
        elif isinstance(nested, rl):
            bn1 = rdflib.BNode()
            return nested.to_rdf(to_rdf, g, bn1)
        elif isinstance(nested, rdflib.term.Node):
            return nested
        else:
            return rdflib.Literal(nested)

    def from_rdf(g, linker, to_python=False):
        nested = {}
        for s, o in g[:linker:]:
            l = tuple(getlist(g, o, to_python=to_python))
            nested[s] = l

        return nested

    def getlist(g, bn0, to_python=False):
        def f(node, g):
            o = None
            for o in g[node:rdf.first:]:
                if isinstance(o, rdflib.BNode):
                    # unfortunately we have to branch on the result type
                    # or have to look ahead to see if the list continues
                    # picked the look ahead so that we don't have to check
                    # length and we don't have to know about the rl type
                    if list(g[o:rdf.first]):  # list continues
                        # XXX watch out for malformed lists that might not
                        # have a rdf:first ?
                        yield tuple(getlist(g, o, to_python=to_python))
                    else:  # likely [ :a :b ] case
                        yield from getlist(g, o, to_python=to_python)

                else:
                    if to_python and isinstance(o, rdflib.Literal):
                        yield o.toPython()
                    else:
                        yield o

            for o in g[node:rdf.rest:]:
                if o != rdf.nil:
                    yield from getlist(g, o, to_python=to_python)

            if o is None and isinstance(node, rdflib.BNode):  # [ :a  :b ] case
                for p, o in g[node:]:
                    if to_python:
                        yield rl((p.toPython() if isinstance(p, rdflib.Literal) else p),
                                 (o.toPython() if isinstance(o, rdflib.Literal) else o),)
                    else:
                        yield rl(p, o)

        yield from g.transitiveClosure(f, bn0)

    return to_rdf, from_rdf


class rl:
    def __init__(self, region, layer=None):
        self.region = region
        self.layer = layer

    def __repr__(self):
        if self.layer:
            return f"{self.__class__.__name__}({self.region!r}, {self.layer!r})"
        else:
            return f"{self.__class__.__name__}({self.region!r})"

    def to_rdf(self, to_rdf, g, bn):
        r = to_rdf(g, self.region)
        if self.layer is None:
            return r

        l = to_rdf(g, self.layer)
        g.add((bn, r, l))
        return bn

    def __eq__(self, other):
        return type(self) == type(other) and self.region == other.region and self.layer == self.layer

    def __hash__(self):
        return hash((self.__class__, self.region, self.layer))

    def __lt__(self, other):
        # FIXME unstable
        return (type(self) == type(other) and
                type(self.region) == type(other.region) and
                self.region is not None and
                self.region < other.region and
                type(self.layer) == type(self.layer) and
                self.layer is not None and
                self.layer < self.layer)


def test():
    from pprint import pprint
    to_rdf, from_rdf = bind_rdflib()
    adj_test = (
        ("a", "b"),
        ("b", "c"),
        ("c", "d"),
        ("d", "e"),
        ("d", "k"),

        ("a", "f"),
        ("f", "g"),

        ("h", "i"),
        ("i", "j"),
    )

    nested = adj_to_nst(adj_test)
    print('nested', nested)
    print('asdf', list(dvals('a', adj_test)))
    print('asdf', list(dvals('c', adj_test)))
    print('asdf', list(dvals('d', adj_test)))

    adj_out = nst_to_adj(nested)
    print(adj_out)

    assert set(adj_test) == set(adj_out), 'oops'

    from pyontutils.core import OntGraph
    from pyontutils.namespaces import ilxtr, rdf

    g = OntGraph()


    bn = to_rdf(g, nested)
    g.add((ilxtr['sub-1'], ilxtr.predicate, bn))

    adj_2 = (
        (ilxtr.a, ilxtr.b),
        (ilxtr.b, ilxtr.c),
        (ilxtr.c, ilxtr.d),
        (ilxtr.d, ilxtr.e),
        (ilxtr.d, ilxtr.h),

        (ilxtr.a, ilxtr.f),
        (ilxtr.f, ilxtr.g),
    )
    nst_2 = adj_to_nst(adj_2)
    print('nst_2', nst_2)
    bn = to_rdf(g, nst_2)
    g.add((ilxtr['sub-2'], ilxtr.predicate, bn))

    lin_3 = [1, 2, 3, 4, 5, 6]
    adj_3 = lin_to_adj(lin_3)
    nst_3 = adj_to_nst(adj_3)
    print('nst_3', nst_3)
    bn = to_rdf(g, nst_3)
    g.add((ilxtr['sub-3'], ilxtr.predicate, bn))

    # multiple linear should work if we concat
    # the outputs together
    adj_4 = tuple(set([pair for lin in
                       ([1, 2, 3, 4, 5],
                        [3, 6, 7],)
             for pair in lin_to_adj(lin)]))
    nst_4 = adj_to_nst(adj_4)
    print('nst_4', nst_4)
    bn = to_rdf(g, nst_4)
    g.add((ilxtr['sub-4'], ilxtr.predicate, bn))

    adj_5 = (
        (rl(ilxtr.a,), rl(ilxtr.b,)),
        (rl(ilxtr.b,), rl(ilxtr.c, ilxtr.l1)),
        #(rl(ilxtr.c, ilxtr.l1), rl(ilxtr.d,)),  # alt end # this one does not duplicate the final node in adj_to_nst
        (rl(ilxtr.c, ilxtr.l1), rl(ilxtr.c, ilxtr.l2)),
        (rl(ilxtr.c, ilxtr.l2), rl(ilxtr.c, ilxtr.l3)),
        (rl(ilxtr.c, ilxtr.l3), rl(ilxtr.d,)),
    )
    nst_5 = adj_to_nst(adj_5)
    pprint(('nst_5', nst_5))
    bn = to_rdf(g, nst_5)
    g.add((ilxtr['sub-5'], ilxtr.predicate, bn))

    # multi-parent multi-child case
    adj_6 = (
        (3, 1),
        (3, 2),
        (4, 1),
        (4, 2),
        (5, 1),
        (5, 2),
        (6, 1),
        (6, 2),
        (1, 7),
        (1, 8),
        (2, 7),
        (2, 8),
    )
    nst_6 = adj_to_nst(adj_6)
    rej_6 = nst_to_adj(nst_6)
    pprint(('nst_6', nst_6))
    pprint(('rej_6', rej_6))
    assert sorted(adj_6) == sorted(rej_6)
    bn = to_rdf(g, nst_6)
    g.add((ilxtr['sub-6'], ilxtr.predicate, bn))

    un_rdf = from_rdf(g, ilxtr.predicate, to_python=True)
    assert un_rdf[ilxtr['sub-1']] == tuple(nested)
    assert un_rdf[ilxtr['sub-2']] == tuple(nst_2)
    assert un_rdf[ilxtr['sub-3']] == tuple(nst_3)
    assert un_rdf[ilxtr['sub-4']] == tuple(nst_4)
    un_rdf[ilxtr['sub-5']] == tuple(nst_5)  # non-invertable case due to layer=None ambiguity
    assert un_rdf[ilxtr['sub-6']] == tuple(nst_6)

    g.debug()


if __name__ == '__main__':
    test()
