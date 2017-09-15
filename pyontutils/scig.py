#!/usr/bin/env python3.6
"""Look look up ontology terms on the command line.

Usage:
    scig v [--local --verbose] <id>...
    scig i [--local --verbose] <id>...
    scig t [--local --verbose --limit=LIMIT] <term>...
    scig s [--local --verbose --limit=LIMIT] <term>...
    scig g [--local --verbose --rt=RELTYPE] <id>...
    scig e [--local --verbose] <p> <s> <o>
    scig c [--local --verbose]
    scig cy <query>

Options:
    -l --local          hit the local scigraph server
    -v --verbose        print the full uri
    -t --limit=LIMIT    limit number of results [default: 10]

"""
from docopt import docopt
from pyontutils.scigraph_client import *
from pyontutils.utils import scigPrint


def main():
    args = docopt(__doc__, version='scig 0')
    #print(args)
    server = None
    verbose = False
    if args['--local']:
        server = 'http://localhost:9000/scigraph'
    if args['--verbose']:
        verbose = True


    if args['i'] or args['v']:
        v = Vocabulary(server, verbose) if server else Vocabulary(verbose=verbose)
        for id_ in args['<id>']:
            out = v.findById(id_)
            if out:
                print(id_,)
                for key, value in sorted(out.items()):
                    print('\t%s:' % key, value)
    elif args['s'] or args['t']:
        v = Vocabulary(server, verbose) if server else Vocabulary(verbose=verbose)
        for term in args['<term>']:
            print(term)
            limit = args['--limit']
            out = v.searchByTerm(term, limit=limit) if args['s'] else v.findByTerm(term, limit=limit)
            if out:
                for resp in sorted(out, key=lambda t: t['labels'][0] if t['labels'] else 'zzzzzzzzz'):
                    try:
                        curie = resp.pop('curie')
                    except KeyError:
                        curie = resp.pop('iri')  # GRRRRRRRRRRRRRR
                    print('\t%s' % curie)
                    for key, value in sorted(resp.items()):
                        print('\t\t%s:' % key, value)
                print()
    elif args['g']:
        g = Graph(server, verbose) if server else Graph(verbose=verbose)
        for id_ in args['<id>']:
            out = g.getNeighbors(id_, relationshipType=args['--rt'])
            if out:
                print(id_,)
                scigPrint.pprint_neighbors(out)
    elif args['e']:
        v = Vocabulary(server, verbose) if server else Vocabulary(verbose=verbose)
        p, s, o = args['<p>'], args['<s>'], args['<o>']
        if ':' in p:
            p = v.findById(p)['labels'][0]
        if ':' in s:
            s = v.findById(s)['labels'][0]
        if ':' in o:
            o = v.findById(o)['labels'][0]
        print('(%s %s %s)' % tuple([_.replace(' ', '-') for _ in (p, s, o)]))
    elif args['c']:
        c = Cypher(server, verbose) if server else Cypher(verbose=verbose)
        curies = c.getCuries()
        align = max([len(c) for c in curies]) + 2
        fmt = '{: <%s}' % align
        for curie, iri in sorted(curies.items()):
            print(fmt.format(repr(curie)), repr(iri))
    elif args['cy']:
        c = Cypher(server, verbose) if server else Cypher(verbose=verbose)
        out = c.execute(args['<query>'], 10)
        if out:
            out = '\n'.join([_.strip() for _ in out.split('|')[3:-1]])
            print(out)
        else:
            print('Error?')

if __name__ == '__main__':
    main()
