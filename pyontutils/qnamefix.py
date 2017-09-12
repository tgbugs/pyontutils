#!/usr/bin/env python3
"""Set qnames based on the curies defined for a given ontology.

Usage:
    qnamefix [options] <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!
    -s --slow       do not use a process pool
    -n --nowrite    parse the file and reserialize it but do not write changes

"""

import os
from glob import glob
import rdflib
from docopt import docopt
from pyontutils.utils import makePrefixes, PREFIXES, makeGraph
from IPython import embed

PREFIXES.pop('NIFTTL')

exclude = 'generated/swanson_hierarchies.ttl',

def convert(f):
    if f in exclude:
        print('skipping', f)
        return f
    pi = {v:k for k, v in PREFIXES.items()}

    graph = rdflib.Graph()
    graph.parse(f, format='turtle')
    namespaces = [str(n) for p, n in graph.namespaces()]
    prefs = ['']

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

    ng = makeGraph(os.path.splitext(f)[0], prefixes=ps, writeloc=os.path.expanduser('~/git/NIF-Ontology/ttl/'))
    [ng.g.add(t) for t in graph]
    #[ng.add_trip(*n) for n in graph.triples([None]*3)]
    #print(f, len(ng.g))
    ng.write()
    return f

def main():
    from joblib import Parallel, delayed
    args = docopt(__doc__, version = "resurect-ids 0")
    if args['--slow'] or len(args['<file>']) == 1:
        [convert(f) for f in args['<file>']]
    else:
        Parallel(n_jobs=9)(delayed(convert)(f) for f in args['<file>'])

if __name__ == '__main__':
    main()
