#!/usr/bin/env python3.5
"""Format ontology files using a uniform ttl serializer from rdflib

Usage:
    ttlfmt [options] <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!
    -a --vanilla    use the regular rdflib turtle serializer
    -s --slow       do not use a process pool

"""
import os
from docopt import docopt
import rdflib
from concurrent.futures import ProcessPoolExecutor
args = docopt(__doc__, version = "ttlfmt 0")

if args['--vanilla']:
    outfmt = 'turtle'
else:
    outfmt = 'nifttl'


rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')

def convert(file):
    filepath = os.path.expanduser(file)
    _, ext = os.path.splitext(filepath)
    filetype = ext.strip('.')
    if filetype == 'ttl':
        infmt = 'turtle'
    else:
        infmt = None
    print(filepath)
    graph = rdflib.Graph()
    graph.parse(filepath, format=infmt)
    out = graph.serialize(format=outfmt)
    with open(filepath, 'wb') as f:
        f.write(out)

def main():
    if args['--slow'] or len(args['<file>']) == 1:
        [convert(f) for f in args['<file>']]
    else:
        with ProcessPoolExecutor(4) as ppe:
            futures = [ppe.submit(convert, _) for _ in args['<file>']]

if __name__ == '__main__':
    main()
