#!/usr/bin/env python3
#!/usr/bin/env pypy3
"""Set qnames based on the curies defined for a given ontology.

Usage:
    qnamefix [options]
    qnamefix [options] (-x <prefix>)...
    qnamefix [options] <file>...
    qnamefix [options] (-x <prefix>)... <file>...

Options:
    -h --help       print this
    -k --keep       keep only existing used prefixes
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
import ttlser.ttlfmt
from pyontutils.core import makeGraph, cull_prefixes
from ttlser.utils import readFromStdIn
from ttlser.ttlfmt import parse, prepare
from pyontutils.namespaces import PREFIXES as uPREFIXES

PREFIXES = {k:v for k, v in uPREFIXES.items() if k != 'NIFTTL'}

exclude = 'generated/swanson_hierarchies.ttl', 'generated/NIF-NIFSTD-mapping.ttl'

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
    graph = cull_prefixes(graph, cleanup=pc, prefixes=PREFIXES)

    out = graph.g.serialize(format='nifttl', gen_prefix=bool(PREFIXES), encoding='utf-8')
    if not isinstance(outpath, str):  # FIXME not a good test that it is stdout
        outpath.buffer.write(out)
    else:
        with open(outpath, 'wb') as f:
            f.write(out)

def convert(file_or_stream, stream=False, infmt=None):
    if file_or_stream in exclude:
        print('skipping', file)
        return file
    serialize(*parse(**prepare(file_or_stream, stream=stream), infmt=infmt))

def main():
    global PREFIXES
    args = docopt(__doc__, version = "qnamefix 0")
    infmt = args['--format'] = 'turtle'
    ttlser.ttlfmt.args = args
    if args['--exclude'] == ['ALL']:
        for k in list(PREFIXES):
            PREFIXES.pop(k)
    else:
        for x in args['--exclude']:
            if x in PREFIXES:
                PREFIXES.pop(x)
    if not args['<file>']:
        stdin = readFromStdIn(sys.stdin)
        if stdin is not None:
            convert(stdin, stream=True, infmt=infmt)
        else:
            print(__doc__)
    else:
        if args['--slow'] or len(args['<file>']) == 1:
            [convert(f, infmt=infmt) for f in args['<file>']]
        else:
            from joblib import Parallel, delayed
            Parallel(n_jobs=9)(delayed(convert)(f, infmt=infmt) for f in args['<file>'])

if __name__ == '__main__':
    main()
