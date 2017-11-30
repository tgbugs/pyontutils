#!/usr/bin/env python3.6
"""Format ontology files using a uniform ttl serializer from rdflib

Usage:
    ttlfmt [options]
    ttlfmt [options] <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!
    -a --vanilla    use the regular rdflib turtle serializer
    -s --slow       do not use a process pool
    -n --nowrite    parse the file and reserialize it but do not write changes
    -d --debug      embed after parsing and before serialization

"""
import os
import sys
from docopt import docopt
import rdflib
from rdflib.plugins.parsers.notation3 import BadSyntax
from concurrent.futures import ProcessPoolExecutor
from pyontutils.utils import readFromStdIn

if __name__ == '__main__':
    args = docopt(__doc__, version="ttlfmt 0")

    if args['--vanilla']:
        outfmt = 'turtle'
    else:
        outfmt = 'nifttl'
    if args['--debug']:
        from IPython import embed

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')

def prepareFile(file):
    filepath = os.path.expanduser(file)
    _, ext = os.path.splitext(filepath)
    filetype = ext.strip('.')
    if filetype == 'ttl':
        infmt = 'turtle'
    else:
        infmt = None
    print(filepath)
    return dict(source=filepath, format=infmt, outpath=filepath)

def prepareStream(stream):
    infmt = 'turtle'  # FIXME detect or try/except?
    return dict(source=stream, format=infmt, outpath=sys.stdout)

def parse(source, format, outpath):
    graph = rdflib.Graph()
    filepath = source
    try:
        graph.parse(source=source, format=format)
    except BadSyntax as e:
        print('PARSING FAILED', source)
        raise e
    return graph, outpath

def serialize(graph, outpath):
    if args['--debug']:
        from IPython import embed
        embed()
    out = graph.serialize(format=outfmt)
    if args['--nowrite']:
        print('PARSING Success', outpath)
    elif not isinstance(outpath, str):  # FIXME not a good test that it is stdout
        outpath.buffer.write(out)
    else:
        with open(outpath, 'wb') as f:
            f.write(out)

def convert(file):
    serialize(*parse(**prepareFile(file)))

def converts(stream):
    serialize(*parse(**prepareStream(stream)))

def main():
    if not args['<file>']:
        stdin = readFromStdIn(sys.stdin)
        if stdin is not None:
            converts(stdin)
            #fn = sys.stdout.fileno()
            #tty = os.ttyname(fn)
            #with open(tty) as sys.stdin:
                #from IPython import embed
                #embed()
        else:
            print(__doc__)
    else:
        from joblib import Parallel, delayed
        if args['--slow'] or len(args['<file>']) == 1:
            [convert(f) for f in args['<file>']]
        else:
            Parallel(n_jobs=9)(delayed(convert)(f) for f in args['<file>'])

if __name__ == '__main__':
    main()
