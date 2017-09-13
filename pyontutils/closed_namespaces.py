#!/usr/bin/env python3

from rdflib import Graph, URIRef
from rdflib.namespace import ClosedNamespace

__all__ = [
    'owl',
    'skos',
    'dc',
    'dcterms',
]

###
###

def main():
    # use to populate terms
    uris = {
        'owl':'http://www.w3.org/2002/07/owl#',
        'skos':'http://www.w3.org/2004/02/skos/core#',
        'dc':'http://purl.org/dc/elements/1.1/',
        'dcterms':'http://purl.org/dc/terms/',
    }
    tw = 4
    functions = ''
    for name, uri in sorted(uris.items()):
        sep = uri[-1]
        globals().update(locals())
        terms = sorted(set(s.rsplit(sep, 1)[-1]
                       for s in Graph().parse(uri).subjects()
                       if uri in s and sep in s))
        tab = ' ' * tw
        ind = ' ' * (tw + len('terms=['))
        block = (''
                '{name} = ClosedNamespaces(\n'
                '{tab}uri=URIRef({uri})\n'
                "{tab}terms=['{terms0}',\n"
                '{ind}'
                ',\n{ind}'.join("'{t}'".format(t=t)
                                for t in terms[1:]) + ']\n'
                ')\n')
        functions += block.format(name=name,
                           uri=uri,
                           tab=tab,
                           ind=ind,
                           terms0=terms[0])

    with open(__file__, 'rt') as f:
        text = f.read()

    sep = '###\n'
    start, mid, end = text.split(sep)
    code = sep.join((start, functions, end))
    with open(__file__, 'wt') as f:
        f.write(code)

if __name__ == '__main__':
    main()
