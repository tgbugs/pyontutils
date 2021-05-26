"""
    Reused utilties that depend on packages outside the python standard library.
"""
import hashlib
from urllib.parse import quote as url_quote
import rdflib


rdflib.plugin.register('librdfxml', rdflib.parser.Parser,
                       'pyontutils.librdf', 'libRdfxmlParser')
rdflib.plugin.register('libttl', rdflib.parser.Parser,
                       'pyontutils.librdf', 'libTurtleParser')


def check_value(v):
    if isinstance(v, rdflib.Literal) or isinstance(v, rdflib.URIRef):
        return v
    elif isinstance(v, str) and v.startswith('http'):
        # FIXME this is dumb and dangerous but whatever
        uri = rdflib.URIRef(v)
        try:
            uri.n3()
        except:
            # dois allow ... non-url and non-identifier chars
            # that must be escaped or we have to use strings
            # FIXME this WILL induce an aliasing problem if
            # another process quotes using a different rule
            uri = rdflib.URIRef(url_quote(v, ':/;()'))

        return uri
    else:
        return rdflib.Literal(v)


class OrderInvariantHash:
    """ WARNING VERY BROKEN DO NOT USE """
    def __init__(self, cypher=hashlib.sha256, encoding='utf-8'):
        self.cypher = cypher
        self.encoding = encoding

    def convertToBytes(self, e):
        if isinstance(e, rdflib.BNode):
            raise TypeError('BNode detected, please convert bnodes to '
                            'ints in a deterministic manner first.')
        elif isinstance(e, rdflib.URIRef):
            return e.encode(self.encoding)
        elif isinstance(e, rdflib.Literal):
            return self.makeByteTuple((str(e), e.datatype, e.language))
        elif isinstance(e, int):
            return str(e).encode(self.encoding)
        elif isinstance(e, bytes):
            return e
        elif isinstance(e, str):
            return e.encode(self.encoding)
        else:
            raise TypeError(f'Unhandled type on {e!r} {type(e)}')

    def makeByteTuple(self, t):
        return b'(' + b' '.join(self.convertToBytes(e)
                                for e in t
                                if e is not None) + b')'

    def __call__(self, iterable):
        # convert all strings bytes
        # keep existing bytes as bytes
        # join as follows b'(http://s http://p http://o)'
        # join as follows b'(http://s http://p http://o)'
        # bnodes local indexes are treated as strings and converted
        # literals are treated as tuples of strings
        # if lang is not present then the tuple is only 2 elements

        # this is probably not the fastest way to do this but it works
        #bytes_ = [makeByteTuple(t) for t in sorted(tuples)]
        #embed()
        m = self.cypher()
        # when everything is replaced by an integer or a bytestring
        # it is safe to sort last because identity is ensured
        [m.update(b) for b in sorted(self.makeByteTuple(t) for t in iterable)]
        return m.digest()
