import re
from collections import defaultdict
import rdflib
from pyontutils.sheets import Sheet
from pyontutils.namespaces import ilxtr, TEMP, rdfs, skos, owl, interlex_namespace
from neurondm.core import Config, NeuronEBM, Phenotype, NegPhenotype, log, OntId, add_partial_orders
from neurondm import orders


class NeuronSparcNlp(NeuronEBM):
    owlClass = ilxtr.NeuronSparcNlp
    shortname = 'sprcnlp'


class NLP1(Sheet):
    name = 'off-nlp-1'


class NLP2(Sheet):
    name = 'off-nlp-2'


def nlp_ns(name):
    return rdflib.Namespace(interlex_namespace(f'tgbugs/uris/readable/sparc-nlp/{name}/'))


snames = {
    'MM Set 1': (NLP1, nlp_ns('mmset1')),
    'MM Set 2 Cranial Nerves': (NLP1, nlp_ns('mmset2cn')),
    'MM Set 4': (NLP2, nlp_ns('mmset4')),
}


sheet_classes = [
    type(f'{base.__name__}{sname.replace(" ", "_")}',
         (base,), dict(sheet_name=sname))
    for sname, (base, ns) in snames.items()]


def map_predicates(sheet_pred):
    p = {
        '': TEMP.BROKEN_EMPTY,
        'Soma': ilxtr.hasSomaLocatedIn,
        'Axon terminal': ilxtr.hasAxonPresynapticElementIn,
        'Axon': ilxtr.hasAxonLocatedIn,
        'Dendrite': ilxtr.hasDendriteLocatedIn,
        'Axon sensory terminal': ilxtr.hasAxonSensorySubcellularElementIn,
        'hasInstanceInTaxon': ilxtr.hasInstanceInTaxon,
        'hasPhenotype': ilxtr.hasPhenotype,
        'hasAnatomicalSystemPhenotype': ilxtr.hasAnatomicalSystemPhenotype,
        'hasBiologicalSex': ilxtr.hasBiologicalSex,
        'hasCircuitRolePhenotype': ilxtr.hasCircuitRolePhenotype,
        'hasForwardConnectionPhenotype': ilxtr.hasForwardConnectionPhenotype,  # FIXME this needs to be unionOf
    }[sheet_pred]
    return p


def ind_to_adj(ind_uri):
    inds = sorted(set([i for i, u in ind_uri]))
    edges = []
    for a, b in zip(inds[:-1], inds[1:]):
        for i, iu in ind_uri:
            # XXX yes this is a horribly inefficient way to do this
            # index them in a dict if it becomes an issue
            if i == a:
                for j, ju in ind_uri:
                    if j == b:
                        edge =  iu, ju
                        edges.append(edge)

    return edges


def main():
    cs = [c() for c in sheet_classes]
    trips = [[cl] + [c.value for c in
                     (r.id(), r.relationship(), r.identifier())]
             for cl in cs for r in cl.rows()
             if r.row_index > 0 and r.id().value
             #and (not hasattr(r, 'exclude') or not r.exclude().value)
             and r.proposed_action().value.lower() != "don't add"
             ]

    to_add = []

    def vl(meth):
        return rdflib.Literal(meth().value)

    def asdf(s, p, rm):
        v = vl(rm)
        if v:
            # XXX watch out for non-homogenous subject types
            # (e.g. OntId vs rdflib.URIRef)
            to_add.append((s.u, p, v))

    dd = defaultdict(list)
    ec = {}
    for cl in cs:
        _, nlpns = snames[cl.sheet_name]
        for r in cl.rows():
            if (r.row_index > 0 and
                r.id().value and
                r.proposed_action().value.lower() != "don't add"):
                # extra trips
                #print(repr(r.id()))
                s = OntId(nlpns[r.id().value])
                #print(s)
                asdf(s, ilxtr.sentenceNumber, r.sentence_number)
                asdf(s, ilxtr.curatorNote, r.different_from_existing)
                asdf(s, ilxtr.curatorNote, r.curation_notes)
                asdf(s, ilxtr.reviewNote, r.review_notes)
                asdf(s, ilxtr.reference, r.reference_pubmed_id__doi_or_text)
                asdf(s, ilxtr.literatureCitation, r.literature_citation)
                asdf(s, rdfs.label, r.neuron_population_label_a_to_b_via_c)
                if hasattr(r, 'alert_explanation'):
                    asdf(s, ilxtr.alertNote, r.alert_explanation)

                if hasattr(r, 'explicit_complement') and r.explicit_complement().value:
                    p = map_predicates(r.relationship().value)
                    o = OntId(r.explicit_complement().value)
                    ec[(s, p)] = o

                if hasattr(r, 'axonal_course_poset') and r.axonal_course_poset().value:
                    # s.u and OntId(...).u to avoid duplicate subjects/objects in the graph
                    # due to type vs instance issues for rdflib.URIRef and OntId
                    dd[s.u].append((int(r.axonal_course_poset().value), OntId(r.identifier().value).u))

    sorders = {k:sorted(v) for k, v in dd.items()}
    sadj = {k:ind_to_adj(v) for k, v in sorders.items()}
    snst = {k:orders.adj_to_nst(v) for k, v in sadj.items()}

    dd = defaultdict(list)
    for c, _s, _p, _o in trips:
        _, nlpns = snames[c.sheet_name]
        for x in (_s, _p, _o):
            if re.match(r'(^[\s]+[^\s].*|.*[^\s][\s]+$)', x):
                msg = f'leading/trailing whitespace in {c} {_s!r} {_p!r} {_o!r}'
                log.error(msg)
                raise ValueError(msg)

        s = OntId(nlpns[_s])
        try:
            p = map_predicates(_p)
        except KeyError as e:
            log.error(f'sigh {s}')
            raise e

        if p == ilxtr.hasForwardConnectionPhenotype:
            _o = nlpns[_o]

        o = OntId(_o)

        if p == owl.equivalentClass:
            to_add.append((s.u, p, o.u))
            continue

        try:
            dd[s].append(Phenotype(o, p))
        except TypeError as e:
            log.error(f'bad data for {c} {s} {p} {o}')
            raise e

        if ec and (s, p) in ec:
            dd[s].append(NegPhenotype(ec[(s, p)], p))


    config = Config('sparc-nlp')

    sigh = []
    nrns = []
    for id, phenos in dd.items():
        n = NeuronSparcNlp(*phenos, id_=id)
        if False and eff(n):
            n._sigh()  # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX FIXME figure out why this is not getting called internally
            sigh.append(n)

        nrns.append(n)

    Phenotype.in_graph.bind('mmset4', snames['MM Set 4'][-1])  # XXX FIXME UGH
    config.write()
    labels = (
        #ilxtr.genLabel,
        ilxtr.localLabel, ilxtr.simpleLabel,
        ilxtr.simpleLocalLabel, rdfs.label, skos.prefLabel)
    to_remove = [t for t in config._written_graph if t[1] in labels]
    [config._written_graph.remove(t) for t in to_remove]
    [config._written_graph.add(t) for t in to_add]
    add_partial_orders(config._written_graph, snst)
    # uncomment to debug type vs instance issues
    #sigh = sorted(set(s for s in config._written_graph.subjects() if isinstance(s, rdflib.URIRef)))
    config._written_graph.write()
    config.write_python()
    return config,


if __name__ == '__main__':
    main()
