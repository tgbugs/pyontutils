#!/usr/bin/env python3
"""Report on overlaping triples between all pairs of ontology files.

Usage:
    overlaps [options] <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!

"""

import os
import rdflib
from docopt import docopt
from pyontutils.core import makeGraph
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint


def common(a, b):
    return sorted(tuple(map(a.qname, (s, p, str(o.toPython()) if isinstance(o, rdflib.Literal) else o)))
                  for s, p, o in set(a.g) & set(b.g)
                  if isinstance(s, rdflib.URIRef))

def g(filename):
    return makeGraph('', graph=rdflib.Graph().parse(filename, format='turtle'))

def sn(filename):
    return os.path.splitext(os.path.basename(filename))[0].split('-', 1)[-1]

def comb(members):
    return {n1 + '-' + n2 : common(g1, g2)
            for i, (n1, g1) in enumerate(sorted(members.items()))
            for n2, g2 in sorted(members.items())[i+1:]}

def extract(files, graphs):
    fn_graphs = {sn(f):g for f, g in zip(files, graphs)}
    results = comb(fn_graphs)
    overlaps = {k:v for k, v in results.items() if v}
    no_bri_inf = {k:v for k, v in overlaps.items() if '-Infe' not in k and '-Bridge' not in k}
    breakpoint()

def main():
    from joblib import Parallel, delayed
    args = docopt(__doc__, version = "overlaps 0")
    files = args['<file>']
    graphs = Parallel(n_jobs=8)(delayed(g)(f) for f in files)
    extract(files, graphs)

if __name__ == '__main__':
    main()
