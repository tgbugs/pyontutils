#!/usr/bin/env python3.7

from pathlib import Path
import rdflib
from pyontutils.core import Ont, OntGraph
from pyontutils.config import devconfig
from pyontutils.sheets import Sheet
from pyontutils.namespaces import owl, rdf, rdfs, ilxtr, NIFRID, OntCuries, skos, makeNamespaces
from neurondm import OntTerm, OntId
from neurondm.models.allen_cell_types import AllenCellTypes

OntCuries(AllenCellTypes.prefixes)  # FIXME BAD
OntCuries({'TEMPIND': 'http://uri.interlex.org/temp/uris/phenotype-indicators/'})
NIFRAW, NIFTTL = makeNamespaces('NIFRAW', 'NIFTTL')
a = rdf.type


# TODO the proper way to do this in the future will be to write a populateIndicators
# for Neuron and Phenotype


class PhenotypeIndicators(Sheet):
    name = 'phenotype-indicators'
    sheet_name = 'Sheet1'

    @property
    def things(self):
        def process(k, v):
            if ',' in v:
                return [rdflib.Literal(_.strip()) for _ in v.split(',')]
            elif k == 'synonyms':
                return [rdflib.Literal(v)]
            else:
                return rdflib.Literal(v)

        lexical = 'synonyms', 'molecule', 'comments'
        for row in self.byCol.rows:
            if not any(row):
                continue
            idents = {k:OntTerm(v) for k, v in row._asdict().items() if v and k not in lexical}
            lex = {k:process(k, v) for k, v in row._asdict().items() if v and k in lexical}
            members = set(idents.values())
            mol = lex['molecule']
            label = f'{mol} (indicator)'
            id = OntId('TEMPIND:' + mol)
            thing = {'id': id,
                     'label': rdflib.Literal(label),
                     'hiddenLabel': mol,
                     'synonyms': lex['synonyms'],
                     'members': members,}
            yield thing
        
    def indicator(self, thing):
        s = thing['id'].u
        yield s, rdf.type, owl.Class
        yield s, rdfs.subClassOf, ilxtr.PhenotypeIndicator
        for m in thing['members']:
            # yield from m.triples_simple
            yield m.u, rdfs.subClassOf, s
            # TODO more synonyms etc

        yield s, rdfs.label, thing['label']
        yield s, skos.hiddenLabel, thing['hiddenLabel']  # FIXME choice of predicate
        for lit in thing['synonyms']:
            yield s, NIFRID.synonym, lit

    @property
    def triples_metadata(self):
        # aka triples_header aka triples_bound_metadata

        # FIXME replace this
        class PhenotypeIndicators(Ont):
            remote_base = str(NIFRAW['neurons/'])
            path = 'ttl/'  # FIXME should be ttl/utility/ but would need the catalog file working
            filename = self.name
            name = 'Phenotype indicators'
            #imports = 
            #prefixes = oq.OntCuries._dict

        yield from PhenotypeIndicators()._graph.g  # OOF very much replace this

    @property
    def triples_data(self):
        for thing in self.things:
            yield from self.indicator(thing)

        sst = OntId('PTHR:10558').u
        yield sst, a, owl.Class
        yield sst, rdfs.subClassOf, ilxtr.PhenotypeIndicator
        yield sst, rdfs.label, rdflib.Literal('somatostatin (indicator)')
        yield sst, NIFRID.synonym, rdflib.Literal('Sst')
        yield sst, NIFRID.synonym, rdflib.Literal('SOM')
        yield sst, NIFRID.synonym, rdflib.Literal('somatostatin')
        sst_members = (OntId('ilxtr:SST-flp'),
                       OntId('NCBIGene:20604'),
                       OntId('PR:000015665'),
                       OntId('JAX:013044'),
                       OntId('JAX:028579'),)
        for i in sst_members:
            yield i.u, rdfs.subClassOf, sst

        # pv fix
        pheno = rdflib.Namespace(ilxtr[''] + 'Phenotype/')
        pv = OntId('PTHR:11653').u
        yield pv, rdfs.label, rdflib.Literal('parvalbumin (indicator)')
        yield pv, NIFRID.synonym, rdflib.Literal('PV')
        yield pv, NIFRID.synonym, rdflib.Literal('Pvalb')
        yield pv, NIFRID.synonym, rdflib.Literal('parvalbumin')
        #yield pv, ilxtr.indicatesDisplayOfPhenotype, pheno.parvalbumin  # as restriction ...
        yield from ((pv, rdf.type, owl.Class),
                    (pv, rdfs.subClassOf, ilxtr.PhenotypeIndicator),)
        pv_members = (OntId('JAX:008069'),
                      OntId('JAX:021189'),
                      OntId('JAX:021190'),
                      OntId('JAX:022730'),
                      OntId('JAX:017320'),
                      ilxtr.Pvalb,
                      ilxtr['PV-cre'],
                      OntId('PR:000013502'),
                      OntId('NCBIGene:19293'),
                      OntId('NIFEXT:6'),)

        for i in pv_members:
            s = i.u if isinstance(i, OntId) else i
            yield s, rdfs.subClassOf, pv

    @property
    def triples(self):
        yield from self.triples_metadata
        yield from self.triples_data

    def asGraph(self):
        return self.populate()

    def populate(self, graph=None):
        """ Populate a graph, or if no graph is provided
            populate a new empty graph from the current
            content. (Also useful for debug) """

        if graph is None:
            graph = OntGraph()

        [graph.add(t) for t in self.triples]
        OntCuries.populate(graph)
        return graph


def main():
    pi = PhenotypeIndicators()
    trips = list(pi.triples)

    #yield from PhenotypeIndicators().triples
    g = pi.asGraph()
    g.write(Path(devconfig.ontology_local_repo, f'ttl/{pi.name}.ttl'))


if __name__ == '__main__':
    main()
