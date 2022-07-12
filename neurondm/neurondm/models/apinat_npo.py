import re
from collections import defaultdict
from pyontutils.sheets import Sheet
from pyontutils.namespaces import ilxtr, TEMP, rdfs, skos
from neurondm.core import Config, NeuronEBM, Phenotype, log, OntId


class NeuronApinatSimple(NeuronEBM):
    owlClass = ilxtr.NeuronApinatSimple
    shortname = 'apinat'


class AtN(Sheet):
    name = 'apinat-to-npo-sue'


sheet_classes = [
    type(f'AtN{sname.replace(" ", "_")}',
         (AtN,), dict(sheet_name=sname))
    for sname in (
            'aacar',
            'spleen',
            'bromo',
            'sstom',
            # 'keast-jun7',  # bad schema
            # 'new colon',  # too many empty predicates
    )]


def map_predicates(sheet_pred):
    p = {
        '': TEMP.BROKEN_EMPTY,
        'Soma-Location': ilxtr.hasSomaLocatedIn,
        'Axon-Terminal-Location': ilxtr.hasAxonPresynapticElementIn,
        'Axon-Location': ilxtr.hasAxonLocatedIn,
        'Dendrite-Location': ilxtr.hasDendriteLocatedIn,
        'Dendrite-Terminal-Location': ilxtr.hasDendriteSensorySubcellularElementIn,
    }[sheet_pred]
    return p


def main():
    cs = [c() for c in sheet_classes]
    trips = [[cl] + [c.value for c in
                     (r.neuron_id(), r.exact_location(), r.location_id())]
             for cl in cs for r in cl.rows()
             if r.row_index > 0 and r.neuron_id().value]

    dd = defaultdict(list)
    for c, _s, _p, _o in trips:
        for x in (_s, _p, _o):
            if re.match(x, r'(^[\s]+[^\s].*|.*[^\s][\s]+$)'):
                msg = 'leading/trailing whitespace in {c} {s} {p} {o}'
                log.error(msg)
                raise ValueError(msg)

        s = OntId(_s)
        try:
            p = map_predicates(_p)
        except KeyError as e:
            log.error(f'sigh {s}')
            raise e
        o = OntId(_o)
        try:
            dd[s].append(Phenotype(o, p))
        except TypeError as e:
            log.error(f'bad data for {c} {s} {p} {o}')
            raise e

    config = Config('apinat-simple-sheet')
    nrns = []
    for id, phenos in dd.items():
        n = NeuronApinatSimple(*phenos, id_=id)
        nrns.append(n)

    config.write()
    labels = (
        ilxtr.genLabel, ilxtr.localLabel, ilxtr.simpleLabel,
        ilxtr.simpleLocalLabel, rdfs.label, skos.prefLabel)
    to_remove = [t for t in config._written_graph if t[1] in labels]
    [config._written_graph.remove(t) for t in to_remove]
    config._written_graph.write()
    config.write_python()
    return config,


if __name__ == '__main__':
    main()
