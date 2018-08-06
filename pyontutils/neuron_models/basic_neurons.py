#!/usr/bin/env python3
import ontquery
from pyontutils.neuron_lang import *
from pyontutils.neurons import *
from pyontutils.core import OntId, OntTerm, OntCuries, makePrefixes, makeNamespaces, interlex_namespace, PREFIXES
from pyontutils.core import rdf, rdfs, owl
from pyontutils.core import NIFRID, ilxtr
from pyontutils.core import hasRole, definition, restriction
import rdflib
from IPython import embed

swanr = rdflib.Namespace(interlex_namespace('swanson/uris/readable/'))
c = Config('basic-neurons',
           prefixes={'swanr':swanr,
                     'SWAN':interlex_namespace('swanson/uris/neuroanatomical-terminology/terms/'),
                     'SWAA':interlex_namespace('swanson/uris/neuroanatomical-terminology/appendix/'),})
pred = c.pred

from pyontutils.phenotype_namespaces import *  # this has to come after reconfig or it will error

Neuron.out_graph.add((next(Neuron.out_graph[:rdf.type:owl.Ontology]),
                      owl.imports,
                      rdflib.URIRef('file:///tmp/output.ttl')))
Neuron.out_graph.add((next(Neuron.out_graph[:rdf.type:owl.Ontology]),
                      owl.imports,
                      rdflib.URIRef(f'file://{Neuron.local_base.as_posix()}ttl/generated/swanson.ttl')))

class Basic(LocalNameManager):
    brain = OntId('UBERON:0000955')#, label='brain')
    #projection = Phenotype(ilxtr.ProjectionPhenotype, ilxtr.hasProjectionPhenotype)
    #intrinsic = Phenotype(ilxtr.InterneuronPhenotype, ilxtr.hasProjectionPhenotype)

    # FIXME naming
    projection = Phenotype(ilxtr.ProjectionPhenotype, ilxtr.hasCircuitRolePhenotype)
    intrinsic = Phenotype(ilxtr.InterneuronPhenotype, ilxtr.hasCircuitRolePhenotype)

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


class LocalGraphService(ontquery.BasicService):
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
    query = ontquery.OntQuery(ontquery.rdflibLocal(sgraph))

def main():
    regions_unfilt = sorted(set(lOntTerm(e) for r in rests for e in (r.s, r.o)), key=lambda t:int(t.suffix))
    regions = [r for r in regions_unfilt if 'gyrus' not in r.label and 'Pineal' not in r.label]
    rows = [['label', 'soma located in', 'projection type']]
    with Basic:
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

if __name__ == '__main__':
    main()