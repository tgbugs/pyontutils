#!/usr/bin/env python3
import rdflib
import ontquery
from neurondm.lang import *
from neurondm import *
from pyontutils.core import OntId, OntTerm
from pyontutils.utils import relative_path
from pyontutils.namespaces import makePrefixes, makeNamespaces, OntCuries
from pyontutils.namespaces import interlex_namespace, PREFIXES
from pyontutils.namespaces import NIFRID, ilxtr, hasRole, definition
from pyontutils.namespaces import rdf, rdfs, owl
from pyontutils.combinators import restriction


swanr = rdflib.Namespace(interlex_namespace('swanson/uris/readable/'))
NIFRAW, = makeNamespaces('NIFRAW')
config = Config('basic-neurons',
                prefixes={'swanr':swanr,
                          'SWAN':interlex_namespace('swanson/uris/neuroanatomical-terminology/terms/'),
                          'SWAA':interlex_namespace('swanson/uris/neuroanatomical-terminology/appendix/'),},
                source_file=relative_path(__file__))

class NeuronSWAN(NeuronEBM):
    owlClass = ilxtr.NeuronSWAN

Neuron = NeuronSWAN

Neuron.out_graph.add((next(Neuron.out_graph[:rdf.type:owl.Ontology]),
                      owl.imports,
                      # this will cause reasoner issues due to the protege bug
                      NIFRAW['dev/ttl/generated/swanson.ttl']))

class Basic(LocalNameManager):
    brain = OntId('UBERON:0000955')#, label='brain')
    #projection = Phenotype(ilxtr.ProjectionPhenotype, ilxtr.hasProjectionPhenotype)
    #intrinsic = Phenotype(ilxtr.InterneuronPhenotype, ilxtr.hasProjectionPhenotype)

    # FIXME naming
    projection = Phenotype(ilxtr.ProjectionPhenotype, ilxtr.hasCircuitRolePhenotype)
    intrinsic = Phenotype(ilxtr.IntrinsicPhenotype, ilxtr.hasCircuitRolePhenotype)

"""
http://ontology.neuinfo.org/trees/query/swanr:hasPart1/SWAN:1/ttl/generated/swanson.ttl?restriction=true&depth=40&direction=OUTGOING

human cns gray matter regions
http://ontology.neuinfo.org/trees/query/swanr:hasPart3/SWAN:1/ttl/generated/swanson.ttl?restriction=true&depth=40&direction=OUTGOING

surface features, handy to have around
http://ontology.neuinfo.org/trees/query/swanr:hasPart5/SWAN:629/ttl/generated/swanson.ttl?restriction=true&depth=40&direction=OUTGOING
"""
sgraph = rdflib.Graph().parse((Neuron.local_base / 'ttl/generated/swanson.ttl').as_posix(), format='ttl')
# restriction.parse(sgraph)  # FIXME this breaks with weird error message
OntCuries({**graphBase.prefixes, **PREFIXES})
rests = [r for r in restriction.parse(graph=sgraph) if r.p == swanr.hasPart3]
#restriction = Restriction2(rdfs.subClassOf)


class LocalGraphService(ontquery.services.BasicService):
    def __init__(self, graph):
        self.graph = graph
        super().__init__()

    def query(self, curie=None, iri=None, label=None, term=None, search=None, **kwargs):  # right now we only support exact matches to labels FIXME
        translate = {rdfs.label:'label',
                     rdfs.subClassOf:'subClassOf',
                     rdf.type:'type',
                     NIFRID.definingCitation:'definingCitation',}
        out = {}
        for p, o in super().query(OntId(curie=curie, iri=iri), label, term, search):  # FIXME should not have to URIRef at this point ...
            p = translate[p]
            if isinstance(o, rdflib.Literal):
                o = o.toPython()
            out[p] = o
        yield out


class lOntTerm(OntTerm):
    repr_arg_order = (('curie', 'label'),  # FIXME this doesn't stick?!
                      ('iri', 'label'),)
    __firsts = 'curie', 'iri'

lOntTerm.query = ontquery.OntQuery(ontquery.plugin.get('rdflib')(sgraph), instrumented=lOntTerm)


regions_unfilt = sorted(set(lOntTerm(e) for r in rests for e in (r.s, r.o)), key=lambda t:int(t.suffix))
regions = [r for r in regions_unfilt if 'gyrus' not in r.label and 'Pineal' not in r.label]
rows = [['label', 'soma located in', 'projection type']]
with Basic:  # FIXME if this is called inside a function stack_magic fails :/
    for region in regions:
        for type in (projection, intrinsic):
            n = Neuron(Phenotype(region, ilxtr.hasSomaLocatedIn, label=region.label, override=True), type)
            rows.append([n.label, region.label, type.pLabel])

Neuron.write()
Neuron.write_python()
import csv
from pathlib import Path
csvpath = Path(graphBase.ng.filename).with_suffix('.csv').as_posix()
with open(csvpath, 'wt') as f:
    csv.writer(f).writerows(rows)
