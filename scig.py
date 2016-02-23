#!/usr/bin/env python3
"""Look look up ontology terms on the command line.

Usage:
    scig vi [--local] <id>...
    scig vt [--local] <term>
    scig vs [--local] <term>
    scig g [--rt=RELTYPE] <id>...

Options:
    -l --local      hit the local scigraph server

"""
from docopt import docopt
from pyontutils.scigraph_client import *

def main():
    args = docopt(__doc__, version='scig 0')
    print(args)
    server = None
    if args['--local']:
        server = 'http://localhost:9000/scigraph'

    if args['vi']:
        v = Vocabulary() if server else Vocabulary()
        for id_ in args['<id>']:
            out = v.findById(id_)
            if out:
                print(id_,)
                for key, value in sorted(out.items()):
                    print('\t%s:' % key, value)
                #print(id_, out)
    elif args['vt']:
        v = Vocabulary(server) if server else Vocabulary()
        out = sorted(v.findByTerm(args['<term>']), key=lambda t: t['labels'][0])
        print(args['<term>'])
        for resp in out:
            for key, value in sorted(resp.items()):
                print('\t%s:' % key, value)
    elif args['vs']:
        v = Vocabulary(server) if server else Vocabulary()
        out = sorted(v.searchByTerm(args['<term>']), key=lambda t: t['labels'][0])
        print(out)
    elif args['g']:
        g = Graph(server) if server else Graph()
        for id_ in args['<id>']:
            out = g.getNeighbors(id_, relationshipType=args['--rt'])
            if out:
                print(id_,)
                print('\tnodes')
                for node in out['nodes']:
                    for key, value in sorted(node.items()):
                        if key == 'meta':
                            print('\t\tmeta:')
                            for mk, mv in value.items():
                                print('\t\t\t%s:' % mk, mv)
                        else:
                            print('\t\t%s:' % key, value)
                print('\tedges')
                for edge in out['edges']:
                    for key, value in sorted(edge.items()):
                        print('\t\t%s:' % key, value)

if __name__ == '__main__':
    main()
