#!/usr/bin/env python3

from rdflib import Graph, URIRef
from rdflib.namespace import ClosedNamespace

__all__ = [
    'dc',
    'dcterms',
    'owl',
    'skos',
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
    tab = ' ' * tw
    ind = ' ' * (tw + len('terms=['))
    functions = ''
    for name, uri in sorted(uris.items()):
        sep = uri[-1]
        globals().update(locals())
        terms = sorted(set(s.rsplit(sep, 1)[-1]
                           for s in Graph().parse(uri.rstrip('#')).subjects()
                           if uri in s and uri != s.toPython() and sep in s))
        block = ('\n'
                 '{name} = ClosedNamespace(\n'
                 "{tab}uri=URIRef('{uri}'),\n"
                 '{tab}' + "terms=['{t}',\n".format(t=terms[0]) + ''
                 '{ind}' + ',\n{ind}'.join("'{t}'".format(t=t)  # watch out for order of operations issues
                                           for t in terms[1:]) + ']\n'
                 ')\n')
        function = block.format(name=name,
                                uri=uri,
                                tab=tab,
                                ind=ind)
        functions += function

    functions += '\n'

    with open(__file__, 'rt') as f:
        text = f.read()

    sep = '###\n'
    start, mid, end = text.split(sep)
    code = sep.join((start, functions, end))
    with open(__file__, 'wt') as f:
        f.write(code)

if __name__ == '__main__':
    main()
