import re
from collections import defaultdict
import rdflib
from pyontutils.sheets import Sheet
from pyontutils.namespaces import ilxtr, TEMP, rdfs, skos, owl, interlex_namespace
from neurondm.core import Config, NeuronEBM, Phenotype, log, OntId


class NeuronSparcNlp(NeuronEBM):
    owlClass = ilxtr.NeuronSparcNlp
    shortname = 'sprcnlp'


class NLP1(Sheet):
    name = 'off-nlp'


def nlp_ns(name):
    return rdflib.Namespace(interlex_namespace(f'tgbugs/uris/readable/sparc-nlp/{name}/'))


snames = {
    'MM Set 1': nlp_ns('mmset1'),
    'MM Set 2 Cranial Nerves': nlp_ns('mmset2cn'),
}


sheet_classes = [
    type(f'NLP1{sname.replace(" ", "_")}',
         (NLP1,), dict(sheet_name=sname))
    for sname in snames]


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
        'hasCircuitRolePhenotype': ilxtr.hasCircuitRolePhenotype,
    }[sheet_pred]
    return p


def main():
    cs = [c() for c in sheet_classes]
    trips = [[cl] + [c.value for c in
                     (r.id(), r.relationship(), r.identifier())]
             for cl in cs for r in cl.rows()
             if r.row_index > 0 and r.id().value
             #and (not hasattr(r, 'exclude') or not r.exclude().value)
             and r.proposed_action().value != "Don't add"
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

    for cl in cs:
        nlpns = snames[cl.sheet_name]
        for r in cl.rows():
            if (r.row_index > 0 and
                r.id().value and
                r.proposed_action().value != "Don't add"):
                # extra trips
                #print(repr(r.id()))
                s = OntId(nlpns[r.id().value])
                #print(s)
                asdf(s, ilxtr.sentenceNumber, r.sentence_number)
                asdf(s, ilxtr.curatorNote, r.different_from_existing)
                asdf(s, ilxtr.curatorNote, r.curation_notes)
                asdf(s, ilxtr.reviewNote, r.review_notes)
                asdf(s, ilxtr.reference, r.reference_pubmed_id__doi_or_text)
                asdf(s, rdfs.label, r.neuron_population_label_a_to_b_via_c)

    dd = defaultdict(list)
    for c, _s, _p, _o in trips:
        nlpns = snames[c.sheet_name]
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
        o = OntId(_o)

        if p == owl.equivalentClass:
            to_add.append((s.u, p, o.u))
            continue

        try:
            dd[s].append(Phenotype(o, p))
        except TypeError as e:
            log.error(f'bad data for {c} {s} {p} {o}')
            raise e


    config = Config('sparc-nlp')

    sigh = []
    nrns = []
    for id, phenos in dd.items():
        n = NeuronSparcNlp(*phenos, id_=id)
        if False and eff(n):
            n._sigh()  # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX FIXME figure out why this is not getting called internally
            sigh.append(n)

        nrns.append(n)

    config.write()
    labels = (
        #ilxtr.genLabel,
        ilxtr.localLabel, ilxtr.simpleLabel,
        ilxtr.simpleLocalLabel, rdfs.label, skos.prefLabel)
    to_remove = [t for t in config._written_graph if t[1] in labels]
    [config._written_graph.remove(t) for t in to_remove]
    [config._written_graph.add(t) for t in to_add]
    config._written_graph.write()
    config.write_python()
    return config,


if __name__ == '__main__':
    main()
