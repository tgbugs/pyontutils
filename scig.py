#!/usr/bin/env python3
"""Look look up ontology terms on the command line.

Usage:
    scig v [--local --verbose] <id>...
    scig i [--local --verbose] <id>...
    scig t [--local --verbose] <term>...
    scig s [--local --verbose] <term>...
    scig g [--local --verbose --rt=RELTYPE] <id>...
    scig c

Options:
    -l --local      hit the local scigraph server
    -v --verbose    print the full uri

"""
from docopt import docopt
from pyontutils.scigraph_client import *

def main():
    args = docopt(__doc__, version='scig 0')
    print(args)
    server = None
    quiet = True
    if args['--local']:
        server = 'http://localhost:9000/scigraph'
    if args['--verbose']:
        quiet = False


    if args['i'] or args['v']:
        v = Vocabulary(server, quiet) if server else Vocabulary(quiet=quiet)
        for id_ in args['<id>']:
            out = v.findById(id_)
            if out:
                print(id_,)
                for key, value in sorted(out.items()):
                    print('\t%s:' % key, value)
    elif args['s'] or args['t']:
        v = Vocabulary(server, quiet) if server else Vocabulary(quiet=quiet)
        for term in args['<term>']:
            print(term)
            out = v.searchByTerm(term) if args['s'] else v.findByTerm(term)
            if out:
                for resp in sorted(out, key=lambda t: t['labels'][0]):
                    curie = resp.pop('curie')
                    print('\t%s' % curie)
                    for key, value in sorted(resp.items()):
                        print('\t\t%s:' % key, value)
                print()
    elif args['g']:
        g = Graph(server, quiet) if server else Graph(quiet=quiet)
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
    elif args['c']:
        c = Cypher(server, quiet) if server else Cypher(quiet=quiet)
        curies = c.getCuries()
        align = max([len(c) for c in curies]) + 2
        fmt = '{: <%s}' % align
        for curie, iri in sorted(curies.items()):
            print(fmt.format(repr(curie)), repr(iri))

if __name__ == '__main__':
    main()
