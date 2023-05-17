from pyontutils.core import OntGraph, OntResIri
from pyontutils.namespaces import rdfs, ilxtr
from neurondm.core import Config, graphBase
from neurondm.core import OntTerm, OntId, RDFL


def multi_orig_dest(neuron):
    for dim in neuron.edges:
        if 'hasAxonPre' in dim or 'hasAxonSens' in dim or 'hasSoma' in dim:
            objs = list(neuron.getObjects(dim))
            if len(objs) > 1:
                return True


def lg(neuron, predicate):
    # TODO could add expected cardinality here if needed
    return list(neuron.getObjects(predicate))


def for_composer(n):
    return dict(
        id = n.id_,
        label = n.origLabel,
        origin = lg(n, ilxtr.hasSomaLocatedIn),
        dest_presyn = lg(n, ilxtr.hasAxonPresynapticElementIn),
        dest_sens = lg(n, ilxtr.hasAxonSensorySubcellularElementIn),
        dest_dend = lg(n, ilxtr.hasDendriteLocatedIn),
        path = lg(n, ilxtr.hasAxonLocatedIn),  # TODO pull ordering from partial orders (not implemented in core atm)
        #laterality = lg(n, ilxtr.hasLaterality),  # left/rigth tricky ?
        #projection_laterality = lg(n, ilxtr.???),  # axon located in contra ?
        species = lg(n, ilxtr.hasInstanceInTaxon),
        sex = lg(n, ilxtr.hasBiologicalSex),
        circuit_type = lg(n, ilxtr.hasCircuitRolePhenotype),
        # there are a number of dimensions that we aren't converting right now
        dont_know_fcrp = lg(n, ilxtr.hasFunctionalCircuitRolePhenotype),
        phenotype = (lg(n, ilxtr.hasPhenotype)  # FIXME currently a grab bag of other types here
                     + lg(n, ilxtr.hasMolecularPhenotype)
                     + lg(n, ilxtr.hasProjectionPhenotype)),
        forward_connection = lg(n, ilxtr.hasForwardConnectionPhenotype),
        # TODO more ...
    )


def main():
    config = Config('random-merge')
    g = OntGraph()  # load and query graph

    # remove scigraph and interlex calls
    graphBase._sgv = None
    del graphBase._sgv
    OntTerm.query._services = (RDFL(g, OntId),)

    b = ('https://raw.githubusercontent.com/SciCrunch/'
         'NIF-Ontology/neurons/ttl/generated/neurons/')

    # full imports
    for f in ('apinat-partial-orders',
              'apinat-pops-more',
              'apinat-simple-sheet',
              'sparc-nlp'):
        ori = OntResIri(b + f + '.ttl')
        [g.add(t) for t in ori.graph]

    # label only imports
    for f in (
            b + 'apinatomy-neuron-populations' + '.ttl',
            ('https://raw.githubusercontent.com/SciCrunch/'
             'NIF-Ontology/neurons/ttl/npo.ttl')):
        ori = OntResIri(f)
        [g.add((s, rdfs.label, o)) for s, o in ori.graph[:rdfs.label:]]

    config.load_existing(g)
    # FIXME currently subClassOf axioms are not parsed back so we are e.g.
    # missing hasInstanceInTaxon axioms for apinatomy neurons
    neurons = config.neurons()  # scigraph required here if deps not removed above

    # ingest to composer starts here
    mvp_ingest = [n for n in neurons if not multi_orig_dest(n)]

    dims = set(p for n in neurons for p in n.edges)  # for reference
    fcs = [for_composer(n) for n in mvp_ingest]

    # example neuron
    n = mvp_ingest[0]
    fc = for_composer(n)

    breakpoint()


if __name__ == '__main__':
    main()
