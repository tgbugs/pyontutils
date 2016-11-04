#!/usr/bin/env python3.5
"""Format ontology files using a uniform ttl serializer from rdflib

Usage:
    ttlfmt [-a] <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!
    -a --vanilla    use the regular rdflib turtle serializer

"""
import os
from docopt import docopt
import rdflib
from IPython import embed

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')

def main():
    args = docopt(__doc__, version = "ttlfmt 0")
    #print(args)

    if args['--vanilla']:
        outfmt = 'turtle'
    else:
        outfmt = 'nifttl'

    for file in args['<file>']:
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
    return

if __name__ == '__main__':
    main()
