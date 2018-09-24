#!/usr/bin/env python3.6
from pathlib import Path
import rdflib
from pyontutils.core import makeGraph
from pyontutils.utils import relative_path
from pyontutils.config import devconfig
from pyontutils.namespaces import makePrefixes, TEMP
from pyontutils.neurons.lang import *
from pyontutils.neurons import *
from pyontutils.neurons.core import MeasuredNeuron
from pyontutils.closed_namespaces import rdf, rdfs, owl
from IPython import embed


def main():
    # load in our existing graph
    # note: while it would be nice to allow specification of phenotypes to be decoupled
    # from insertion into the graph... maybe we could enable this, but it definitely seems
    # to break a number of nice features... and we would need the phenotype graph anyway
    Config('temporary-graph')
    EXISTING_GRAPH = graphBase.in_graph
    #EXISTING_GRAPH = rdflib.Graph()
    #graphBase.in_graph = EXISTING_GRAPH
    #graphBase.core_graph = EXISTING_GRAPH
    local_prefix = Path(devconfig.ontology_local_repo, 'ttl')
    sources = (f'{local_prefix}/NIF-Neuron-Defined.ttl',
               f'{local_prefix}/NIF-Neuron.ttl',
               f'{local_prefix}/NIF-Neuron-Phenotype.ttl',
               f'{local_prefix}/phenotype-core.ttl',
               f'{local_prefix}/phenotypes.ttl',
               f'{local_prefix}/hbp-special.ttl')
    for file in sources:
            EXISTING_GRAPH.parse(file, format='turtle')
    EXISTING_GRAPH.namespace_manager.bind('ILXREPLACE', makePrefixes('ILXREPLACE')['ILXREPLACE'])
    #EXISTING_GRAPH.namespace_manager.bind('PR', makePrefixes('PR')['PR'])

    #graphBase.core_graph = EXISTING_GRAPH
    #graphBase.out_graph = rdflib.Graph()
    graphBase.__import_name__ = 'pyontutils.neurons'
    graphBase._predicates = getPhenotypePredicates(EXISTING_GRAPH)

    g = makeGraph('merged', prefixes={k:str(v) for k, v in EXISTING_GRAPH.namespaces()}, graph=EXISTING_GRAPH)
    reg_neurons = list(g.g.subjects(rdfs.subClassOf, g.expand(_NEURON_CLASS)))
    tc_neurons = [_ for (_,) in g.g.query('SELECT DISTINCT ?match WHERE {?match rdfs:subClassOf+ %s}' % _NEURON_CLASS)]
    def_neurons = g.get_equiv_inter(_NEURON_CLASS)

    nodef = sorted(set(tc_neurons) - set(def_neurons))
    og1 = MeasuredNeuron.out_graph = rdflib.Graph()  # there is only 1 out_graph at a time, load and switch

    mns = [MeasuredNeuron(id_=n) for n in nodef]
    mnsp = [n for n in mns if n.pes]
    Neuron.out_graph = rdflib.Graph()  # XXX NEVER DO THIS IT IS EVIL ZALGO WILL EAT YOUR FACE
    dns = [Neuron(id_=n) for n in sorted(def_neurons)]
    #dns += [Neuron(*m.pes) if m.pes else m.id_ for m in mns]
    dns += [Neuron(*m.pes) for m in mns if m.pes]

    # reset everything for export
    Config('phenotype-direct', source_file=relative_path(__file__))
    Neuron.out_graph = graphBase.out_graph  # each subclass of graphBase has a distinct out graph IF it was set manually
    #Neuron.out_graph = rdflib.Graph()
    #ng = makeGraph('', prefixes={}, graph=Neuron.out_graph)
    #ng.filename = Neuron.ng.filename
    Neuron.existing_pes = {}  # reset this as well because the old Class references have vanished
    dns = [Neuron(*d.pes) for d in set(dns)]  # TODO remove the set and use this to test existing bags?
    #from neurons.lang import WRITEPYTHON
    #WRITEPYTHON(sorted(dns))
    Neuron.write_python()
    #ng.add_ont(TEMP['defined-neurons'], 'Defined Neurons', 'NIFDEFNEU',
               #'VERY EXPERIMENTAL', '0.0.0.1a')
    #ng.add_trip(TEMP['defined-neurons'], owl.imports, rdflib.URIRef('file:///home/tom/git/NIF-Ontology/ttl/phenotype-core.ttl'))
    #ng.add_trip(TEMP['defined-neurons'], owl.imports, rdflib.URIRef('file:///home/tom/git/NIF-Ontology/ttl/phenotypes.ttl'))
    #ng.write()
    ontinfo = (
        (Neuron.ng.ontid, rdf.type, owl.Ontology),
        (Neuron.ng.ontid, rdfs.label, rdflib.Literal('phenotype direct neurons')),
        (Neuron.ng.ontid, rdfs.comment, rdflib.Literal('Neurons derived directly from phenotype definitions')),
    )
    [Neuron.out_graph.add(t) for t in ontinfo]
    Neuron.write()
    bads = [n for n in Neuron.ng.g.subjects(rdf.type, owl.Class)
            if len(list(Neuron.ng.g.predicate_objects(n))) == 1]
    if __name__ == '__main__':
        embed()


main()
