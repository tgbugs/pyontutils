#!/usr/bin/env python3
"""Set qnames based on the curies defined for a given ontology.

Usage:
    qnamefix [options] <file>...
    qnamefix [options] (-x <prefix>)... <file>...

Options:
    -h --help       print this
    -x --exclude=X  do not include the prefix when rewriting
    -v --verbose    do something fun!
    -s --slow       do not use a process pool
    -n --nowrite    parse the file and reserialize it but do not write changes

"""

import os
from glob import glob
import rdflib
from docopt import docopt
from pyontutils.utils import makePrefixes, PREFIXES, makeGraph

exclude = 'generated/swanson_hierarchies.ttl', 'generated/NIF-NIFSTD-mapping.ttl'
PREFIXES.pop('NIFTTL')


def convert(f, prefixes):
    if f in exclude:
        print('skipping', f)
        return f

    graph = rdflib.Graph()
    graph.parse(f, format='turtle')

    def prefix_cleanup(ps, graph):
        if 'parcellation/' in f:
            nsl = {p:n for p, n in graph.namespaces()}
            if '' in nsl:
                ps[''] = nsl['']
            elif 'hbaslim' in f:
                ps['HBA'] = nsl['HBA']
            elif 'mbaslim' in f:
                ps['MBA'] = nsl['MBA']
            elif 'cocomac' in f:
                ps['cocomac'] = nsl['cocomac']

        # special cases for NIFORG, NIFINV, NIFRET where there identifiers in
        # annotation properties that share the prefix, so we warn incase
        # at some point in the future for some reason want them again...
        if f == 'NIF-Organism.ttl':
            print('WARNING: special case for NIFORG')
            ps.pop('NIFORG')
        elif f == 'NIF-Investigation.ttl':
            print('WARNING: special case for NIFINV')
            ps.pop('NIFINV')
        elif f == 'unused/NIF-Retired.ttl':
            print('WARNING: special case for NIFRET')
            ps.pop('NIFGA')

    ng = cull_prefixes(graph, cleanup=prefix_cleanup)
    ng.filename = f
    #[ng.add_trip(*n) for n in graph.triples([None]*3)]
    #print(f, len(ng.g))
    ng.write()
    return f

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

def main():
    from joblib import Parallel, delayed
    args = docopt(__doc__, version = "qnamefix 0")
    for x in args['--exclude']:
        PREFIXES.pop(x)
    if args['--slow'] or len(args['<file>']) == 1:
        [convert(f, PREFIXES) for f in args['<file>']]
    else:
        Parallel(n_jobs=9)(delayed(convert)(f, PREFIXES) for f in args['<file>'])

if __name__ == '__main__':
    main()
