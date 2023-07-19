import os
import rdflib
from pyontutils.core import OntGraph, OntResIri, OntResPath
from pyontutils.namespaces import rdfs, ilxtr
from neurondm.core import Config, graphBase, log
from neurondm.core import OntTerm, OntId, RDFL
from neurondm import orders


def multi_orig_dest(neuron):
    for dim in neuron.edges:
        if 'hasAxonPre' in dim or 'hasAxonSens' in dim or 'hasSoma' in dim:
            objs = list(neuron.getObjects(dim))
            if len(objs) > 1:
                return True


def makelpesrdf():
    collect = []
    def lpes(neuron, predicate):
        """ get predicates from python bags """
        # TODO could add expected cardinality here if needed
        return [str(o) for o in neuron.getObjects(predicate)
                if not collect.append((predicate, o))]

    def lrdf(neuron, predicate):
        """ get predicates from graph """
        return [  # XXX FIXME core_graph bad etc.
            str(o) for o in
            neuron.core_graph[neuron.identifier:predicate]]

    return lpes, lrdf, collect


def simplify(e):
    if e is None:
        return
    elif isinstance(e, rdflib.Literal):  # blank case
        return e.toPython()
    else:
        return OntTerm(e).curie


def simplify_nested(f, nested):
    for e in nested:
        if isinstance(e, list) or isinstance(e, tuple):
            yield tuple(simplify_nested(f, e))
        elif isinstance(e, orders.rl):
            yield orders.rl(f(e.region), f(e.layer))
        else:
            yield f(e)


def for_composer(n, cull=False):
    lpes, lrdf, collect = makelpesrdf()
    _po = n.partialOrder()
    fc = dict(
        id = str(n.id_),
        label = str(n.origLabel),
        origin = lpes(n, ilxtr.hasSomaLocatedIn),
        dest = (
            # XXX looking at this there seems to be a fault assumption that
            # there is only a single destination type per statement, this is
            # not the case, there is destination type per destination
            [dict(loc=l, type='AXON-T') for l in lpes(n, ilxtr.hasAxonPresynapticElementIn)] +
            # XXX I strongly reccoment renaming this to SENSORY-T so that the
            # short forms are harder to confuse A-T and S-T
            [dict(loc=l, type='AFFERENT-T') for l in lpes(n, ilxtr.hasAxonSensorySubcellularElementIn)]
        ),
        order = tuple(simplify_nested(simplify, _po)) if _po else [],
        path = (  # TODO pull ordering from partial orders (not implemented in core atm)
            [dict(loc=l, type='AXON') for l in lpes(n, ilxtr.hasAxonLocatedIn)] +
            # XXX dendrites don't really ... via ... they are all both terminal and via at the same time ...
            [dict(loc=l, type='DENDRITE') for l in lpes(n, ilxtr.hasDendriteLocatedIn)]
        ),
        #laterality = lpes(n, ilxtr.hasLaterality),  # left/rigth tricky ?
        #projection_laterality = lpes(n, ilxtr.???),  # axon located in contra ?
        species =            lpes(n, ilxtr.hasInstanceInTaxon),
        sex =                lpes(n, ilxtr.hasBiologicalSex),
        circuit_type =       lpes(n, ilxtr.hasCircuitRolePhenotype),
        phenotype =          lpes(n, ilxtr.hasAnatomicalSystemPhenotype),  # current meaning of composer phenotype
        anatomical_system =  lpes(n, ilxtr.hasAnatomicalSystemPhenotype),
        # there are a number of dimensions that we aren't converting right now
        dont_know_fcrp =     lpes(n, ilxtr.hasFunctionalCircuitRolePhenotype),
        other_phenotype = (  lpes(n, ilxtr.hasPhenotype)
                           + lpes(n, ilxtr.hasMolecularPhenotype)
                           + lpes(n, ilxtr.hasProjectionPhenotype)),
        forward_connection = lpes(n, ilxtr.hasForwardConnectionPhenotype),

        # direct references from individual individual neurons
        provenance =      lrdf(n, ilxtr.literatureCitation),
        sentence_number = lrdf(n, ilxtr.sentenceNumber),
        note_alert =      lrdf(n, ilxtr.alertNote),
        # XXX provenance from ApiNATOMY models as a whole is not ingested
        # right now because composer lacks support for 1:n from neuron to
        # prov, (or rather lacks prov collections) and because it attaches
        # prov to the sentece, which does not exist for all neurons

        # TODO more ...
        # notes = ?

        # for _ignore, hasClassificationPhenotype is used for ApiNATOMY
        # unlikely to be encountered for real neurons any time soon
        _ignore = lpes(n, ilxtr.hasClassificationPhenotype),  # used to ensure we account for all phenotypes
    )
    npo = set((p.e, p.p) for p in n.pes)
    cpo = set(collect)
    unaccounted_pos = npo - cpo
    if unaccounted_pos:
        log.warning(
            (n.id_, [[n.in_graph.namespace_manager.qname(e) for e in pos]
                     for pos in unaccounted_pos]))
    return {k:v for k, v in fc.items() if v} if cull else fc


def location_summary(neurons, services, anatent_simple=False):
    import csv
    OntTerm.query._services = services
    locations = sorted(set(
        OntTerm(pe.p) for n in neurons for pe in n.pes
        if pe.e in n._location_predicates))
    [_.fetch() for _ in locations]

    _loc_src = sorted(set(
        (OntTerm(pe.p), n.id_) for n in neurons for pe in n.pes
        if pe.e in n._location_predicates))

    ls2 = dict()
    for _l, _s in _loc_src:
        if _l not in ls2:
            ls2[_l] = []

        ls2[_l].append(_s)

    loc_src = dict()
    for k, v in ls2.items():
        nlp = [iri for iri in v if '/sparc-nlp/' in iri]
        apinat = [iri for iri in v if '/neuron-type-' in iri]
        both = apinat and nlp
        source = 'both' if both else 'nlp' if nlp else 'apinat' if apinat else 'unknown'
        loc_src[k] = source

    def key(t):
        return (t.prefix, t.label[0].lower()
                if isinstance(t, tuple)
                else t.lower())

    if anatent_simple:
        header = 'label', 'curie', 'iri', 'source'
        rows = (
            [header] +
            [(_.label, _.curie, _.iri, loc_src[_]) for _ in sorted(locations, key=key)])
        with open('/tmp/npo-nlp-apinat-location-summary.csv', 'wt') as f:
            csv.writer(f, lineterminator='\n').writerows(rows)

    else:
        header = 'o', 'o_label', 'o_synonym'
        rows = (
            [header] +
            [(_.iri, _.label, syn) for _ in sorted(locations, key=key)
             for syn in _.synonyms])
        with open('/tmp/anatomical_entities.csv', 'wt') as f:
            csv.writer(f, lineterminator='\n').writerows(rows)


def main(local=False, anatomical_entities=False, anatent_simple=False):
    # if (local := True, anatomical_entities := True, anatent_simple := False):

    config = Config('random-merge')
    g = OntGraph()  # load and query graph

    # remove scigraph and interlex calls
    graphBase._sgv = None
    del graphBase._sgv
    if len(OntTerm.query._services) > 1:
        # backup services and avoid issues on rerun
        _old_query_services = OntTerm.query._services
        _noloc_query_services = _old_query_services[1:]

    OntTerm.query._services = (RDFL(g, OntId),)

    # base paths to ontology files
    gen_neurons_path = 'ttl/generated/neurons/'
    suffix = '.ttl'
    if local:
        from pyontutils.config import auth
        olr = auth.get_path('ontology-local-repo')
        local_base = olr / gen_neurons_path
    else:
        orr = 'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/neurons/'
        remote_base = orr + gen_neurons_path

    # full imports
    for f in ('apinat-partial-orders',
              'apinat-pops-more',
              'apinat-simple-sheet',
              'sparc-nlp'):
        if local:
            ori = OntResPath(local_base / (f + suffix))
        else:
            ori = OntResIri(remote_base + f + suffix)
        [g.add(t) for t in ori.graph]

    # label only imports
    for f in ('apinatomy-neuron-populations',
              '../../npo'):
        p = os.path.normpath(gen_neurons_path + f)
        if local:
            ori = OntResPath(olr / (p + suffix))
        else:
            ori = OntResIri(orr + p + suffix)

        [g.add((s, rdfs.label, o)) for s, o in ori.graph[:rdfs.label:]]

    config.load_existing(g)
    neurons = config.neurons()  # scigraph required here if deps not removed above

    # ingest to composer starts here
    mvp_ingest = [n for n in neurons if not multi_orig_dest(n)]

    dims = set(p for n in neurons for p in n.edges)  # for reference
    fcs = [for_composer(n) for n in mvp_ingest]
    _fcne = [for_composer(n, cull=True) for n in mvp_ingest]  # exclude empties for easier manual review

    # example neuron
    n = mvp_ingest[0]
    fc = for_composer(n)

    if anatomical_entities:
        location_summary(neurons, _noloc_query_services, anatent_simple)


if __name__ == '__main__':
    main()
