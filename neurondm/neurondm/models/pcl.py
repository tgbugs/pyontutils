import rdflib
from pyontutils.core import OntGraph
from pyontutils.config import auth
from pyontutils.namespaces import ilxtr, UBERON, CL, NCBITaxon, skos
from neurondm.core import OntId, log

pCL = rdflib.Namespace('http://uri.interlex.org/fakeobo/uris/obo/pCL_')
HGNC = rdflib.Namespace('https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/')
LOC = rdflib.Namespace('https://www.ncbi.nlm.nih.gov/gene'
                       '?cmd=Retrieve&dopt=full_report&list_uids=')

def fixns(g):
    ns = rdflib.Namespace(dict(g.namespace_manager)[''])
    nsb = ns + 'pCL_'
    nsu = ns + 'UBERON_'
    nsc = ns + 'CL_'

    ng = OntGraph()
    ng.namespace_manager.populate_from(g)
    ng.bind('ilxtr', ilxtr)
    ng.bind('CL', CL)
    ng.bind('pCL', pCL)
    ng.bind('UBERON', UBERON)
    ng.bind('NCBITaxon', NCBITaxon)
    ng.bind('HGNC', HGNC)
    ng.bind('LOC', LOC)
    ng.populate_from_triples((rdflib.URIRef(str(e.replace(nsb, pCL)))
                              if e.startswith(nsb) else
                              (rdflib.URIRef(str(e.replace(nsu, UBERON)))
                               if e.startswith(nsu) else
                               (rdflib.URIRef(str(e.replace(nsc, CL)))
                                if e.startswith(nsc) else
                                e))
                              for e in t)
                             for t in g)

    return ng


def hsli(s, p, os):
    rep = {
        "cortical_layer1": OntId('UBERON:0005390').u,
        "cortical_layer2": OntId('UBERON:0005391').u,
        "cortical_layer3": OntId('UBERON:0005392').u,
        "cortical_layer4": OntId('UBERON:0005393').u,
        "cortical_layer5": OntId('UBERON:0005394').u,
        "cortical_layer6": OntId('UBERON:0005395').u,
    }
    return s, ilxtr.hasSomaLocatedInLayer, rep[str(os)]


def def_to_trips(s, definition):
    if 'selectively expresses' in definition:
        prefix, suffix_mRNAs = definition.split('selectively expresses', 1)
        suffix, *_ = suffix_mRNAs.rsplit(' mRNAs')
        elements = suffix.split(',')
        for e in elements:
            e = e.strip()
            if '|' in e:
                for id in e.split('|'):
                    #log.debug(id)
                    if 'HGNC_' in id:
                        _, suffix = id.split('_', 1)
                        yield s, ilxtr.hasExpressionPhenotype, HGNC[suffix]  # FIXME mRNA
                        break
                else:
                    log.warning(f'failure to convert {e} for {s}')
                    yield s, ilxtr.fdsa, rdflib.Literal(e)
            else:
                if e.startswith('LOC'):
                    yield s, ilxtr.hasExpressionPhenotype, LOC[e[3:]]  # FIXME
                else:
                    log.warning(f'failure to convert {e} for {s}')
                    yield s, ilxtr.asdf, rdflib.Literal(e)
    else:
        # right now none of these are neurons or
        # lack additional expression information in the description
        #log.error(definition)
        #yield s, ilxtr.wtf, definition
        pass


def to_ebm(g):
    ns = rdflib.Namespace(dict(g.namespace_manager)[''])
    for s, p, o in g:
        if p == skos.definition:
            yield s, p, o
            yield from def_to_trips(s, o)

        elif p == ns.id:
            yield s, p, o
        elif p == ns.neuron_type:
            yield s, p, o
        elif p == ns.part_of:
            yield s, ilxtr.hasSomaLocatedIn, o
        elif p == ns.preferred_name:
            yield s, p, o
        elif p == ns.prefixIRI:
            yield s, p, o
        elif p == ns.species_id:
            yield s, ilxtr.hasInstanceInTaxon, NCBITaxon[o.split(':txid')[-1]]
        elif p == ns.species_source:
            yield s, p, o
        elif p == ns.has_soma_location_in:
            yield hsli(s, p, o)
        elif p == ns.tdc_id:
            yield s, p, o
        else:
            yield s, p, o


def main():
    url = ('http://data.bioontology.org/ontologies/'
           f'PCL/submissions/7/download?apikey={auth.user_config.secrets("bioportal")}')
    g = OntGraph().parse(url, format='application/rdf+xml')
    g = fixns(g)
    og = OntGraph()
    g.namespace_manager.populate(og)
    og.populate_from_triples(to_ebm(g))
    og.write('/tmp/pCL.ttl')
    #og.debug()


if __name__ == '__main__':
    main()
