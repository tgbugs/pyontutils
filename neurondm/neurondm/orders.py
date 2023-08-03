from collections import Counter


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


def inest(adj, start, seen, expect, starts):
    nl = tuple()
    out = []
    maybe_out = []
    seen[start] += 1
    for next_start in sorted(dvals(start, adj)):
        if next_start in seen and seen[next_start] > 0:
            # do not append if next_start already seen more than expected
            nl, snext = (next_start,), seen
            if seen[next_start] < expect[next_start]:
                out.append(nl)
                seen[next_start] += 1
            elif next_start in starts and seen[next_start] == expect[next_start]:
                out.append(nl)
            else:
                pass  # pretty sure should never get here now
        else:
            nl, snext = inest(adj, next_start, seen, expect, starts)
            out.append(nl)

        seen = snext

    l = tuple(out)
    return ((start, *l) if l else (start,)), seen


def adj_to_nst(adj, start=None):
    if not adj:
        return tuple()

    keys = set([a[0] for a in adj])
    values = set([a[1] for a in adj])
    #inverted = [(a[1], a[0]) for a in adj]  # unused
    starts = keys - values
    #ends = values - keys  # unused

    if not starts:
        # the graph forms a full cycle with all potential starting points
        # involved in a cycle, therefore pick an arbitrary but stable start
        starts = {sorted(adj)[0][0]}

    seen = {thing: 0 for thing in (keys | values)}
    expect = dict(Counter([a[1] for a in adj]))
    nl = None
    out = []
    for start in sorted(starts):
        nl, snext = inest(adj, start, seen, expect, starts)
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
        return type(self) == type(other) and self.region == other.region and self.layer == other.layer

    def __hash__(self):
        return hash((self.__class__, self.region, self.layer))

    def __lt__(self, other):
        if type(self) == type(other):
            sreg = '' if self.region is None else self.region
            slay = '' if self.layer is None else self.layer
            oreg = '' if other.region is None else other.region
            olay = '' if other.layer is None else other.layer
            return sreg < oreg or slay < olay


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
    pprint(('adj_6', adj_6))
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

    adj_raw_7 = [  # aacar-6 (confusingly)
        # the issue here is that the graph is not fully connected
        # AND that some of the disconnected parts have auto cycles
        (('ILX:0774266', None), ('ILX:0787082', None)),
        (('ILX:0786141', None), ('ILX:0784439', None)),
        (('ILX:0786228', None), ('ILX:0791105', None)),
        (('ILX:0786272', None), ('ILX:0788945', None)),
        (('ILX:0786722', None), ('ILX:0787562', None)),
        (('ILX:0789947', None), ('ILX:0787946', None)),
        (('ILX:0793555', None), ('UBERON:0000948', 'UBERON:0015129')),
        (('ILX:0793556', None), ('UBERON:0000948', 'UBERON:0015129')),
        (('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0000948', 'UBERON:0002348')),
        (('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0002078', 'UBERON:0002349')),
        (('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0002079', 'UBERON:0002349')),
        (('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0002080', 'UBERON:0002349')),
        (('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0002084', 'UBERON:0002349')),
        (('UBERON:0000948', 'UBERON:0015129'), ('ILX:0793555', None)),
        (('UBERON:0000948', 'UBERON:0015129'), ('ILX:0793556', None)),
        (('UBERON:0000948', 'UBERON:0015129'), ('UBERON:0000948', 'UBERON:0002348')),
        (('UBERON:0002078', 'UBERON:0002349'), ('UBERON:0002078', 'UBERON:0002165')),
        (('UBERON:0002079', 'UBERON:0002349'), ('UBERON:0002079', 'UBERON:0002165')),
        (('UBERON:0002080', 'UBERON:0002349'), ('UBERON:0002080', 'UBERON:0002165')),
        (('UBERON:0002084', 'UBERON:0002349'), ('UBERON:0002084', 'UBERON:0002165')),
    ]

    adj_raw_7 = [
        # the issue here is the auto cyclic nodes
        # when all these are run reg_7 -> empty
        #(('ILX:0793556', None), ('ILX:0793556', None)),  # cycle here
        # somehow the autocycle will cause output issues if it is placed in the 0th position in the list
        # but not down below ??? answer: because rl.__lt__ was using and instead of or (derp)
        (('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0000948', 'UBERON:0002348')),  # cycle here
        (('ILX:0793556', None), ('UBERON:0000948', 'UBERON:0015129')),
          (('UBERON:0000948', 'UBERON:0015129'), ('UBERON:0000948', 'UBERON:0002348')),  # when only this and cycle it works ish ???
            #(('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0000948', 'UBERON:0002348')),  # cycle here
            (('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0002084', 'UBERON:0002349')),
              (('UBERON:0002084', 'UBERON:0002349'), ('UBERON:0002084', 'UBERON:0002165')),
            (('UBERON:0000948', 'UBERON:0002348'), ('UBERON:0002080', 'UBERON:0002349')),
              (('UBERON:0002080', 'UBERON:0002349'), ('UBERON:0002080', 'UBERON:0002165')),
    ]
    adj_7 = tuple(tuple(rl(*(a if a is None else a for a in _rl)) for _rl in rls) for rls in adj_raw_7)
    nst_7 = adj_to_nst(adj_7)
    rej_7 = nst_to_adj(nst_7)
    pprint(('nst_7', nst_7))
    pprint(('adj_7', sorted(adj_7)))
    pprint(('rej_7', sorted(rej_7)))
    assert sorted(adj_7) == sorted(rej_7)
    bn = to_rdf(g, nst_7)
    g.add((ilxtr['sub-7'], ilxtr.predicate, bn))

    adj_raw_8 = [
        # this produces complete nonsense
        # XXX why the, how the, heck does this produce the result ... (answer: only check equality of region)
        (('UBERON:0006450', 'UBERON:0002318'), ('UBERON:0006450', 'UBERON:0002181')),
        (('UBERON:0006450', 'UBERON:0002318'), ('UBERON:0006450', 'UBERON:0004677')),
        (('UBERON:0006450', 'UBERON:0002318'), ('UBERON:0006450', 'UBERON:0006118')),
        (('UBERON:0006450', 'UBERON:0002318'), ('UBERON:0006450', 'UBERON:0016576')),
        (('UBERON:0006450', 'UBERON:0002318'), ('UBERON:0006450', 'UBERON:0016578')),
    ]
    adj_8 = tuple(tuple(rl(*(a if a is None else a for a in _rl)) for _rl in rls) for rls in adj_raw_8)
    adj_alt_8 = tuple(tuple('-'.join(('' if a is None else a for a in _rl)) for _rl in rls) for rls in adj_raw_8)
    nst_alt_8 = adj_to_nst(adj_alt_8)  # XXX the issue is clearly in rl
    nst_raw_8 = adj_to_nst(adj_raw_8)  # XXX the issue is clearly in rl
    he = hash(adj_8[0][0]) == hash(adj_8[1][0])
    ee = adj_8[0][0] == adj_8[1][0]
    #rej_raw_8 = nst_to_adj(nst_raw_8)  # though we can't convert tuples back because of type issues
    nst_8 = adj_to_nst(adj_8)
    rej_8 = nst_to_adj(nst_8)
    pprint(('nst_8', nst_8), width=120)
    pprint(('adj_8', adj_8), width=120)
    pprint(('rej_8', rej_8), width=120)
    assert sorted(adj_8) == sorted(rej_8)
    bn = to_rdf(g, nst_8)
    g.add((ilxtr['sub-8'], ilxtr.predicate, bn))

    adj_raw_9 = [  # from keast 11 branching issue 18683 same as for adj_raw_8
        (('UBERON:0002856', None), ('UBERON:0006450', None #'UBERON:0002318'
                                    )),
        (('UBERON:0002856', None), ('UBERON:0018683', None)),
        (('UBERON:0002857', None), ('UBERON:0006448', None #'UBERON:0002318'
                                    )),
        (('UBERON:0002857', None), ('UBERON:0018683', None)),

        #(('UBERON:0018683', None), ('UBERON:0005453', None)),
    ]
    adj_9 = tuple(tuple(rl(*(a if a is None else a for a in _rl)) for _rl in rls) for rls in adj_raw_9)
    nst_9 = adj_to_nst(adj_9)
    rej_9 = nst_to_adj(nst_9)
    pprint(('nst_9', nst_9))
    pprint(('adj_9', adj_9))
    pprint(('rej_9', rej_9))
    assert sorted(adj_9) == sorted(rej_9), [a for a in adj_9 if a not in rej_9]
    bn = to_rdf(g, nst_9)
    g.add((ilxtr['sub-9'], ilxtr.predicate, bn))

    adj_10 = [
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
        (5, 2),  # long cycle not including start
        (6, 1),  # long cycle including "start"
    ]
    nst_10 = adj_to_nst(adj_10)
    rej_10 = nst_to_adj(nst_10)
    pprint(('nst_10', nst_10))
    pprint(('adj_10', adj_10))
    pprint(('rej_10', rej_10))
    assert sorted(adj_10) == sorted(rej_10), [a for a in adj_10 if a not in rej_10]
    bn = to_rdf(g, nst_10)
    g.add((ilxtr['sub-10'], ilxtr.predicate, bn))

    g.debug()

    # cycle tests
    adj_to_nst([(1, 2), (2, 3), (2, 2)])  # ok because does not include start
    adj_to_nst([(1, 2), (2, 3), (3, 3)])  # ok because does not include start
    adj_to_nst([(4, 2), (1, 2), (2, 3), (3, 1)])  # ok because does not include all starts
    adj_to_nst([(4, 2), (1, 2), (2, 3), (3, 1), (3, 4)])  # includes all start node
    adj_to_nst([(1, 2), (2, 3), (3, 1)])  # includes all start node
    adj_to_nst([(1, 2), (2, 3), (1, 1)])  # includes all start nodes


if __name__ == '__main__':
    test()
