import unittest
import rdflib
from pyontutils.namespaces import TEMP, ilxtr, rdf, rdfs, owl
from pyontutils.core import OntGraph
from pathlib import Path
from uuid import uuid4

PAGE_BREAK = ""  # C-q C-l

utt = rdflib.Namespace('https://uilx.org/tgbugs/u/r/test/')

path_graphs = Path(__file__).parent / 'examples' / 'graphs.ttl'


def random_URIRef():
    return rdflib.URIRef(utt['uuid4hex/' + uuid4().hex])


def random_Literal():
    return rdflib.Literal(uuid4().hex)


def mkrand(e):
    if '__RANDOM' in e:
        if isinstance(e, rdflib.URIRef):
            return random_URIRef()
        elif isinstance(e, rdflib.Literal):
            return random_Literal()
        else:
            raise TypeError(f'unknown type {type(e)} {e}')
    else:
        return e


def process_command(t, base_graph):
    CMD, command, arg = t
    assert CMD == utt['__COMMAND']

    if command == utt['__INSERT']:
        if arg == utt['__BASE_META']:
            graph = base_graph
            type = utt['record-triples']
        elif arg == utt['__BASE_DATA']:
            graph = base_graph
            type = utt['record-pair']
        else:
            raise NotImplementedError(f'unknown arg {arg}')

        for s in graph[:rdf.type:type]:
            yield from graph.subjectGraph(s)  # FIXME naming should e subjectTriples?


def substitute_graph(graph, base_graph=None):
    # command triples
    # random literals
    # random urirefs
    g = OntGraph(namespace_manager=base_graph)

    trips = [[mkrand(e) for e in t]
             for t in graph
             if '__COMMAND' not in t[0]]
    g.populate_from_triples(trips)

    if base_graph is not None:
        cmd_trips = [[mkrand(e) for e in t]
                     for t_command in graph
                     if '__COMMAND' in t_command[0]
                     for t in process_command(t_command, base_graph)]
        g.populate_from_triples(cmd_trips)

    return g


def make_graphs(path):
    with open(path, 'rt') as f:
        raw_all_streams = f.read()

    (raw_local_conventions,
     helper,
     *raw_m_d_streams) = raw_all_streams.split(PAGE_BREAK)
    all_streams = [raw_local_conventions + raw_m_d_stream
                   for raw_m_d_stream in raw_m_d_streams]
    base_graph, *pre_graphs = [OntGraph().parse(data=raw_stream, format='ttl')
                               for raw_stream in all_streams]

    #_ = [g.debug() for g in (base_graph, *pre_graphs)]
    # NOTE we cannot substitute out the __RANDOM bits in base_graph
    # otherwise the templated graphs would all share the same randomness
    test_graphs = [substitute_graph(g, base_graph) for g in pre_graphs]
    _ = [g.debug() for g in test_graphs]
    return test_graphs


class TestChanges(unittest.TestCase):
    def test_graphs(self):
        test_graphs = make_graphs(path_graphs)
        #breakpoint()
