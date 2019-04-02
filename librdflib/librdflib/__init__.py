"""librdf parser for rdflib"""

__version__ = '0.0.1'

try:
    import RDF
except ImportError as e:
    print('WARNING: librdf bindings not found. You will have runtime errors.')
import rdflib
from pathlib import Path


def Literal(string, language=None, datatype=None):
    datatype = datatype if datatype is None else rdflib.URIRef(str(datatype))
    return rdflib.Literal(string, lang=language, datatype=datatype)


def statement_to_tuple(statement):
    def get_value(element):
        if element.type == 1:
            return str(element.uri)
        elif element.type == 2:
            return (element.literal_value['string'],
                    element.literal_value['language'],
                    element.literal_value['datatype'])
        elif element.type == 4:
            return str(element.blank_identifier)
        else:
            embed()
            raise TypeError

    return (get_value(statement.subject),
            get_value(statement.predicate),
            get_value(statement.object))


def statement_to_triple(statement):
    def get_value(element):
        if element.type == 1:
            return rdflib.URIRef(str(element.uri))
        elif element.type == 2:
            return Literal(**element.literal_value)
        elif element.type == 4:
            return rdflib.BNode(element.blank_identifier)
        else:
            from IPython import embed
            embed()
            raise TypeError

    return (get_value(statement.subject),
            get_value(statement.predicate),
            get_value(statement.object))


class librdfParser(rdflib.parser.Parser):
    format = None
    def __init__(self):
        pass

    def parse(self, source, sink, **args):
        source.close()
        file_uri = source.getPublicId()
        parser = RDF.Parser(name=self.format)
        stream = parser.parse_as_stream(file_uri)
        [sink.add(statement_to_triple(statement)) for statement in stream]


class libRdfxmlParser(librdfParser):
    format = 'rdfxml'


class libTurtleParser(librdfParser):
    format = 'turtle'


class Stream:
    def __init__(self, iterable):
        self._stream = True
        self._iter = iterable

    def end(self):
        return not self._stream

    def __next__(self):
        try:
            return next(self._iter)
        except StopIteration:
            self._stream = False
            return 1

    next = __next__

def serialize(graph, format='turtle'):
    # TODO this is not quite so simple ...
    # it would see that we can't just give it a list of statements ...
    def r_to_l(element):
        if isinstance(element, rdflib.URIRef):
            RDF.Uri(element)
        elif isinstance(element, rdflib.Literal):
            if element.datatype:
                kwargs = dict(datatype=RDF.Uri(element.datatype))
            else:
                kwargs = dict(language=element.language)
            RDF.Node(literal=str(element),
                     **kwargs)
        elif isinstance(element, rdflib.BNode):
            RDF.Node(blank=str(element))

    gen = (RDF.Statement(*(r_to_l(e) for e in t)) for t in graph)
    stream = Stream(gen)
    ser = RDF.Serializer(name=format)
    string = ser.serialize_stream_to_string(stream)
    return string

def modeltest():
    from IPython import embed
    # this hardlocks 
    ms = RDF.MemoryStorage('test')
    m = RDF.Model(ms)
    p1 = Path('~/git/NIF-Ontology/ttl/NIF-Molecule.ttl').expanduser()
    p = RDF.Parser(name='turtle')
    p.parse_into_model(m, p1.as_uri())
    embed()

def main():
    from IPython import embed
    """ Python 3.6.6
    ibttl 2.605194091796875
    ttl 3.8316309452056885
    diff lt - ttl -1.2264368534088135
    librdfxml 31.267616748809814
    rdfxml 58.25124502182007
    diff lr - rl -26.983628273010254
    simple time 17.405116319656372
    """

    """ Python 3.5.3 (pypy3)
    libttl 2.387338638305664
    ttl 1.3430471420288086
    diff lt - ttl 1.0442914962768555
    librdfxml 24.70371127128601
    rdfxml 17.85916304588318
    diff lr - rl 6.844548225402832
    simple time 18.32300615310669
    """

    # well I guess that answers that question ...
    # librdf much faster for cpython, not for pypy3

    from time import time
    rdflib.plugin.register('librdfxml', rdflib.parser.Parser,
                        'librdflib', 'libRdfxmlParser')
    rdflib.plugin.register('libttl', rdflib.parser.Parser,
                        'librdflib', 'libTurtleParser')

    p1 = Path('~/git/NIF-Ontology/ttl/NIF-Molecule.ttl').expanduser()
    start = time()
    graph = rdflib.Graph().parse(p1.as_posix(), format='libttl')
    stop = time()
    lttime = stop - start
    print('libttl', lttime)
    #serialize(graph)

    start = time()
    graph = rdflib.Graph().parse(p1.as_posix(), format='turtle')
    stop = time()
    ttltime = stop - start
    print('ttl', ttltime)
    print('diff lt - ttl', lttime - ttltime)

    p2 = Path('~/git/NIF-Ontology/ttl/external/uberon.owl').expanduser()
    start = time()
    graph2 = rdflib.Graph().parse(p2.as_posix(), format='librdfxml')
    stop = time()
    lrtime = stop - start
    print('librdfxml', lrtime)
    if True:
        start = time()
        graph2 = rdflib.Graph().parse(p2.as_posix(), format='xml')
        stop = time()
        rltime = stop - start
        print('rdfxml', rltime)
        print('diff lr - rl', lrtime - rltime)

    if True:
        file_uri = p2.as_uri()
        parser = RDF.Parser(name='rdfxml')
        stream = parser.parse_as_stream(file_uri)
        start = time()
        # t = list(stream)
        t = tuple(statement_to_tuple(statement) for statement in stream)
        stop = time()
        stime = stop - start
        print('simple time', stime)

    embed()

if __name__ == "__main__":
    main()
