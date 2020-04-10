import unittest
from nifstd_tools.simplify import simplify


def mkt(*t):

    return [{'sub': str(s),
            'pred': p,
             'obj': str(o),} for s, p, o in t]


t1 = mkt(
    (1, 'start', 2),
    (2, 'skip1>', 3),
    (3, 'end', 4),
), mkt(
    (1, 'start', 2),
    (2, 'skip1>-end', 4),
    
)

t2 = mkt(
    (5, 'start', 6),
    (7, '<skip1', 6),
    (7, 'other', 8),
), mkt(
    (5, 'start', 6),
    (7, 'other', 8),
    (7, '<skip1', 6),  # collapsing over a single predicate is useless because single predicates collapse to themselves
)

t3 = mkt(
    (11, 'start', 12),
    (12, 'skip1>', 13),  # the first skip1> will not be removed because only full pattern matches are removed
    (13, 'skip1>', 14),  # however as it stands this breaks stuff because the first skip1 is connected
    (14, 'end', 15),
    (15, 'end', 16),
), mkt(
    (11, 'start', 12),
    (12, 'skip1>', 13),
    (15, 'end', 16),
    (13, 'skip1>-end', 15),
)

t4 = mkt(
    (16, 'start', 17),
    (17, 'skip1>', 18),  # skip1 will not skip because skip1> skip2>-end is not in the list
    (18, 'skip2>', 19),  # NOTE first one wins happens if collapses overlap at the ends
    (19, 'end', 20),     # if you encounter this you should manually extend/merge the rules
), mkt(
    (16, 'start', 17),
    (17, 'skip1>', 18),
    (18, 'skip2>-end', 20),
)

t5 = mkt(
    (21, 'start', 22),
    (22, 'skip3>', 23),
    (23, 'skip4>', 24),
    (24, 'end', 25),
), mkt(
    (21, 'start', 22),
    (22, 'skip3>-skip4>-end', 25),
)

t6 = mkt(
    (26, 'start', 27),
    (27, 'skip3>', 28),
    (28, 'skip4>', 29),
    (29, 'end', 30),
    (30, 'TO THE BYOND', 31),
), mkt(
    (26, 'start', 27),
    (30, 'TO THE BYOND', 31),
    (27, 'skip3>-skip4>-end', 30),
)

t7 = mkt(
    (32, 'start', 33),
    (34, 'skip1>', 35),  # NOTE THE SKIP
    (36, 'end', 37),
), mkt(
    (32, 'start', 33),
    (34, 'skip1>', 35),  # must avoid the infinite loop here
    (36, 'end', 37),
)

t8 = mkt(
    (38, 'start', 39),
    (39, 'skip1>', 40),
    (40, 'end', 41),
    (42, 'other', 43),
    (43, 'skip1>', 40),
), mkt(
    (38, 'start', 39),
    (42, 'other', 43),
    (39, 'skip1>-end', 41),
    (43, 'skip1>-end', 41),
)

tests = [t8, t5, t6, t1, t2, t3, t4, t7]

collapse = [
    ['<skip1'],
    ['skip1>', 'end'],
    ['skip2>', 'end'],
    ['skip3>', 'skip4>', 'end'],
]


class TestSimplify(unittest.TestCase):
    def test(self):
        for t, tv in tests:
            tb = {'nodes': [], 'edges': t}
            s = simplify(collapse, tb)
            assert s['edges'] == tv, 'oops'
