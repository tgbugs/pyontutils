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
from pyontutils.utils import makePrefixes, PREFIXES, makeGraph, readFromStdIn
from pyontutils.ttlfmt import parse, prepareFile, prepareStream

PREFIXES.pop('NIFTTL')
PREFIXES = {k:v for k, v in PREFIXES.items()}

if __name__ == '__main__':
    args = docopt(__doc__, version = "qnamefix 0")
    if args['--exclude'] == ['ALL']:
        for k in list(PREFIXES):
            PREFIXES.pop(k)
    else:
        for x in args['--exclude']:
            PREFIXES.pop(x)

exclude = 'generated/swanson_hierarchies.ttl', 'generated/NIF-NIFSTD-mapping.ttl'

def cull_prefixes(graph, prefixes=PREFIXES, cleanup=lambda ps, graph: None):
    namespaces = [str(n) for p, n in graph.namespaces()]
    prefs = ['']
    pi = {v:k for k, v in prefixes.items()}
    asdf = {} #{v:k for k, v in ps.items()}
    asdf.update(pi)
    # determine which prefixes we need
    for uri in list(graph.subjects()) + list(graph.predicates()) + list(graph.objects()):
        if uri.endswith('.owl') or uri.endswith('.ttl'):
            continue  # don't prefix imports
        for rn, rp in sorted(asdf.items(), key=lambda a: -len(a[0])):  # make sure we get longest first
            lrn = len(rn)
            if type(uri) == rdflib.BNode:
                continue
            elif uri.startswith(rn) and '#' not in uri[lrn:] and '/' not in uri[lrn:]:  # prevent prefixing when there is another sep
                prefs.append(rp)
                break

    if prefs:
        ps = makePrefixes(*prefs)
    else:
        ps = makePrefixes('rdfs')

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

    print(bool(PREFIXES))
    out = graph.g.serialize(format='nifttl', gen_prefix=bool(PREFIXES))
    if not isinstance(outpath, str):  # FIXME not a good test that it is stdout
        outpath.buffer.write(out)
    else:
        with open(outpath, 'wb') as f:
            f.write(out)

def convert(file):
    if file in exclude:
        print('skipping', file)
        return file
    serialize(*parse(**prepareFile(file)))

def converts(stream):
    serialize(*parse(**prepareStream(stream)))

def main():
    if not args['<file>']:
        stdin = readFromStdIn(sys.stdin)
        if stdin is not None:
            converts(stdin)
        else:
            print(__doc__)
    else:
        from joblib import Parallel, delayed
        if args['--slow'] or len(args['<file>']) == 1:
            [convert(f, PREFIXES) for f in args['<file>']]
        else:
            Parallel(n_jobs=9)(delayed(convert)(f, PREFIXES) for f in args['<file>'])

if __name__ == '__main__':
    main()
