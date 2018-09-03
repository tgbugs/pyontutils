#!/usr/bin/env python3
"""Set qnames based on the curies defined for a given ontology.

Usage:
    qnamefix [options]
    qnamefix [options] (-x <prefix>)...
    qnamefix [options] <file>...
    qnamefix [options] (-x <prefix>)... <file>...

Options:
    -h --help       print this
    -x --exclude=X  do not include the prefix when rewriting, ALL will strip
    -v --verbose    do something fun!
    -s --slow       do not use a process pool
    -n --nowrite    parse the file and reserialize it but do not write changes

"""

import os
import sys
from glob import glob
import rdflib
from docopt import docopt
import pyontutils.ttlfmt
from pyontutils.core import makeGraph
from pyontutils.utils import readFromStdIn
from pyontutils.ttlfmt import parse, prepare
from pyontutils.namespaces import makePrefixes, PREFIXES

PREFIXES = {k:v for k, v in PREFIXES.items()}
PREFIXES.pop('NIFTTL')

exclude = 'generated/swanson_hierarchies.ttl', 'generated/NIF-NIFSTD-mapping.ttl'

def cull_prefixes(graph, prefixes=PREFIXES, cleanup=lambda ps, graph: None):
    namespaces = [str(n) for p, n in graph.namespaces()]
    prefs = ['']
    pi = {v:k for k, v in prefixes.items()}
    asdf = {} #{v:k for k, v in ps.items()}
    asdf.update(pi)
    # determine which prefixes we need
    for uri in set((e for t in graph for e in t)):
        if uri.endswith('.owl') or uri.endswith('.ttl') or uri.endswith('$$ID$$'):
            continue  # don't prefix imports or templates
        for rn, rp in sorted(asdf.items(), key=lambda a: -len(a[0])):  # make sure we get longest first
            lrn = len(rn)
            if type(uri) == rdflib.BNode:
                continue
            elif uri.startswith(rn) and '#' not in uri[lrn:] and '/' not in uri[lrn:]:  # prevent prefixing when there is another sep
                prefs.append(rp)
                break

    ps = {p:prefixes[p] for p in prefs}

    cleanup(ps, graph)

    ng = makeGraph('', prefixes=ps)
    [ng.g.add(t) for t in graph]
    return ng

def serialize(graph, outpath):
    def prefix_cleanup(ps, graph):
        if 'parcellation/' in outpath:
            nsl = {p:n for p, n in graph.namespaces()}
            if '' in nsl:
                ps[''] = nsl['']
            elif 'hbaslim' in outpath:
                ps['HBA'] = nsl['HBA']
            elif 'mbaslim' in outpath:
                ps['MBA'] = nsl['MBA']
            elif 'cocomac' in outpath:
                ps['cocomac'] = nsl['cocomac']

        # special cases for NIFORG, NIFINV, NIFRET where there identifiers in
        # annotation properties that share the prefix, so we warn incase
        # at some point in the future for some reason want them again...
        if outpath == 'NIF-Organism.ttl':
            print('WARNING: special case for NIFORG')
            ps.pop('NIFORG')
        elif outpath == 'NIF-Investigation.ttl':
            print('WARNING: special case for NIFINV')
            ps.pop('NIFINV')
        elif outpath == 'unused/NIF-Retired.ttl':
            print('WARNING: special case for NIFRET')
            ps.pop('NIFGA')

    pc = prefix_cleanup if isinstance(outpath, str) else lambda a, b: None
    graph = cull_prefixes(graph, cleanup=pc)

    #print(bool(PREFIXES))
    out = graph.g.serialize(format='nifttl', gen_prefix=bool(PREFIXES))
    if not isinstance(outpath, str):  # FIXME not a good test that it is stdout
        outpath.buffer.write(out)
    else:
        with open(outpath, 'wb') as f:
            f.write(out)

def convert(file_or_stream, stream=False):
    if file_or_stream in exclude:
        print('skipping', file)
        return file
    serialize(*parse(**prepare(file_or_stream, stream=stream)))

def main():
    global PREFIXES
    args = docopt(__doc__, version = "qnamefix 0")
    args['--format'] = 'turtle'
    pyontutils.ttlfmt.args = args
    if args['--exclude'] == ['ALL']:
        for k in list(PREFIXES):
            PREFIXES.pop(k)
    else:
        for x in args['--exclude'] and x in PREFIXES:
            PREFIXES.pop(x)
    if not args['<file>']:
        stdin = readFromStdIn(sys.stdin)
        if stdin is not None:
            convert(stdin, stream=True)
        else:
            print(__doc__)
    else:
        if args['--slow'] or len(args['<file>']) == 1:
            [convert(f) for f in args['<file>']]
        else:
            from joblib import Parallel, delayed
            Parallel(n_jobs=9)(delayed(convert)(f) for f in args['<file>'])

if __name__ == '__main__':
    main()
