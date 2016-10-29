#!/usr/bin/env python3.5
"""Format ontology files using a uniform ttl serializer from rdflib

Usage:
    ttlfmt <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!

"""
import os
from docopt import docopt
import rdflib
from IPython import embed

rdflib.plugin.register('nifttl', rdflib.serializer.Serializer, 'pyontutils.ttlser', 'CustomTurtleSerializer')

def main():
    args = docopt(__doc__, version = "ttlfmt 0")
    print(args)

    for file in args['<file>']:
        filepath = os.path.expanduser(file)
        _, ext = os.path.splitext(filepath)
        filetype = ext.strip('.')
        if filetype == 'ttl':
            infmt = 'turtle'
        else:
            infmt = None
        graph = rdflib.Graph()
        graph.parse(filepath, format=infmt)
        with open(filepath, 'wb') as f:
            f.write(graph.serialize(format='nifttl'))
    #embed()
    return

if __name__ == '__main__':
    main()
