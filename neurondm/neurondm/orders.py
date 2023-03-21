def make_adj(l):
    start = l[0]
    if (isinstance(start, list) or isinstance(start, tuple)):
        raise ValueError('malformed')

    first = [] if start == "blank" else [(start, e[0]) for e in l[1:] if e]
    second = [p for r in l[1:] if r for p in make_adj(r)]
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
    for next_start in dvals(start, adj):
        seen = {start} | seen
        if next_start in seen:
            nl, snext = (next_start,), seen
        else:
            nl, snext = inest(adj, next_start, seen)

        seen = snext
        out.append(nl)

    l = tuple(out)
    return ((start, *l) if l else (start,)), seen


def adj_to_nested(adj, start=None):
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
        return "blank", l


def lin_to_adj(linear):
    return tuple(zip(linear[:-1], linear[1:]))


def to_rdf(g, nested):
    bn0 = rdflib.BNode()
    if isinstance(nested, list) or isinstance(nested, tuple):
        rdflib.collection.Collection(g, bn0, (to_rdf(g, n) for n in nested))
        return bn0
    elif isinstance(nested, rdflib.term.Node):
        return nested
    else:
        return rdflib.Literal(nested)


def test():
    adj_test = (
        ("a", "b"),
        ("b", "c"),
        ("c", "d"),
        ("d", "e"),

        ("a", "f"),
        ("f", "g"),
    )

    nested = adj_to_nested(adj_test)
    print('nested', nested)
    print('asdf', list(dvals('a', adj_test)))
    print('asdf', list(dvals('c', adj_test)))
    print('asdf', list(dvals('d', adj_test)))

    adj_out = make_adj(nested)
    print(adj_out)

    assert set(adj_test) == set(adj_out), 'oops'

    import rdflib
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

        (ilxtr.a, ilxtr.f),
        (ilxtr.f, ilxtr.g),
    )
    nst_2 = adj_to_nested(adj_2)
    print('nst_2', nst_2)
    bn = to_rdf(g, nst_2)
    g.add((ilxtr['sub-2'], ilxtr.predicate, bn))

    lin_3 = [1, 2, 3, 4, 5, 6]
    adj_3 = lin_to_adj(lin_3)
    nst_3 = adj_to_nested(adj_3)
    print('nst_3', nst_3)
    bn = to_rdf(g, nst_3)
    g.add((ilxtr['sub-3'], ilxtr.predicate, bn))

    # multiple linear should work if we concat
    # the outputs together
    adj_4 = tuple(set([pair for lin in
                       ([1, 2, 3, 4, 5],
                        [3, 6, 7],)
             for pair in lin_to_adj(lin)]))
    nst_4 = adj_to_nested(adj_4)
    print('nst_4', nst_4)
    bn = to_rdf(g, nst_4)
    g.add((ilxtr['sub-4'], ilxtr.predicate, bn))

    g.debug()


if __name__ == '__main__':
    test()
