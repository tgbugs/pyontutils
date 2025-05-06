import csv
import rdflib
import augpathlib as aug
from pyontutils import sheets
from pyontutils.namespaces import TEMP, ilxtr, rdfs, skos
from neurondm.models.nlp import map_predicates, main as nlp_main, NeuronSparcNlp
from neurondm.core import log as _log, uPREFIXES, Config, Neuron

log = _log.getChild('composer')


def get_csv_sheet(path):
    with open(path, 'rt') as f:
        _rows = list(csv.reader(f))

    # remove rows that are missing a value since the export doesn't do
    # that and we will get missing if not provided
    idx = _rows[0].index('Object URI')
    sidx = _rows[0].index('Subject URI')
    tidx = _rows[0].index('Object Text')
    ridx = _rows[0].index('Reference (pubmed ID, DOI or text)')
    derp_idx = _rows[0].index('Object')
    _rows[0][ridx] = 'literature citation'  # XXX HACK
    for _r in _rows[1:]:  # FIXME EVEN BIGGER HACK
        if (not (_r[idx] or _r[tidx])) and _r[derp_idx]:
            _r[tidx] = _r[derp_idx]

    rows = [[c if c != 'http://www.notspecified.info' else ''
             for c in r] for r in _rows if (r[idx] or r[tidx]) and r[sidx]]
    assert len(rows) > 1

    s = sheets.Sheet(fetch=False)
    s.sheet_name = 'comprt'
    s._values = []
    s.update(rows)
    s._uncommitted_appends = {}
    assert len(s.values) > 1
    return s


import os
from pyontutils.core import OntGraph, OntResIri, OntResPath
from neurondm.core import graphBase, OntTerm, OntId, RDFL
from . import apinat_npo  # populate Neuron subclasses
from . import apinat_pops_more  # populate Neuron subclasses
def load_config(gitref='neurons', local=False, restore=True):
    # FIXME naming ... really load_config_neurons ...
    # FIXME from ../../docs/compoers.py

    config = Config('random-merge')
    g = OntGraph()  # load and query graph

    # remove scigraph and interlex calls
    _old_vocab = graphBase._sgv
    graphBase._sgv = None
    del graphBase._sgv
    if len(OntTerm.query._services) > 1:
        # backup services and avoid issues on rerun
        _old_query_services = OntTerm.query._services
        # noloc excludes the rdflib local service for graphBase.core_graph
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
        orr = f'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/{gitref}/'
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
            ori = OntResIri(orr + gen_neurons_path + f + suffix)

        [g.add((s, rdfs.label, o)) for s, o in ori.graph[:rdfs.label:]]

    config.load_existing(g)
    neurons = config.neurons()  # scigraph required here if deps not removed above

    if restore:
        # restore old
        graphBase._sgv = _old_vocab
        OntTerm.query._services = _noloc_query_services

    return neurons, config, g


class NeuronComposer(Neuron):
    owlClass = ilxtr.NeuronComposer
    shortname = 'cmpsr'


def remlabs_write(config, keep=tuple()):
    config.write()
    labels = tuple(
        l for l in (#ilxtr.genLabel,
            ilxtr.origLabel,
            ilxtr.localLabel, ilxtr.simpleLabel,
            ilxtr.simpleLocalLabel, rdfs.label, skos.prefLabel)
        if l not in keep)
    to_remove = [t for t in config._written_graph if t[1] in labels]
    [config._written_graph.remove(t) for t in to_remove]
    #[config._written_graph.add(t) for t in to_add]
    # TODO figure out about partial orders being roundtripped or not?
    config._written_graph.write()


def main():
    #exp = aug.LocalPath('~/downloads/export_2024-09-17_15-03-20.csv').expanduser()
    #exp = aug.LocalPath('~/downloads/export_2024-10-06_00-31-18.csv').expanduser()  # contains no data?
    #exp = aug.LocalPath('~/downloads/export_2024-12-20_23-40-50.csv').expanduser()
    #exp = aug.LocalPath('~/downloads/export_2025-01-27_15-14-55.csv').expanduser()
    exp = aug.LocalPath('~/downloads/export_v3-2-1_2025-02-12_21-31-31.csv').expanduser()
    #exp = aug.LocalPath('~/downloads/export_v4-0-1_2025-03-13_15-31-17.csv').expanduser()
    # XXX FIXME the only time you can actually say that something has been exported is when you detect it on the next load from the ontology
    #exp = aug.LocalPath('~/downloads/export_v4-1-0_2025-04-11_19-22-42.csv').expanduser()  # wat
    sht = get_csv_sheet(exp)
    cs = [sht]
    config = Config('composer-and-roundtrip')
    nlp_main(cs=cs, config=config, neuron_class=Neuron)  # FIXME neuron_class is incorrect and changes per model
    nrns = config.neurons()
    # FIXME partial order is lost when config changes it seems :/
    # but it sighed was called??? yes, but we add the partial orders
    # in bulk at the end ...

    # TODO
    # use the ids from nrns
    # to create 3 files
    # 1. composer only
    # 2. composer existing only
    # 3. existing from ontology

    acops = (
        # composer export derived
        skos.prefLabel,
        ilxtr.curatorNote,
        ilxtr.inNLPWorkingSet,
        #ilxtr.reference,  # XXX this is not present from composer so leave out to reduce noise
        ilxtr.reviewNote,
        ilxtr.sentenceNumber,

        # ontology derived extra
        ilxtr.alertNote,
        ilxtr.hasOrganTarget,
        ilxtr.literatureCitation,

             )
    def anncop(n, g):
        s = n.id_
        for p in acops:
            for o in g[s:p]:
                graphBase.out_graph.add((s, p, o))

        return n

    config_composer_only = Config('composer')
    cco_nrns = [
        anncop(NeuronComposer(
            *n.pes, id_=n.id_, label=n._origLabel, override=True, partialOrder=n.partialOrder()),
               config._written_graph)
        for n in nrns if 'sparc-nlp/composer' in n.id_
        or 'composer/uris/set' in n.id_
    ]
    remlabs_write(config_composer_only, keep=(rdfs.label, skos.prefLabel))
    config_composer_only.write_python()

    # FIXME TODO likely need to use OntGraph.subjectGraph to copy these correctly
    config_composer_roundtrip = Config('composer-roundtrip')
    # FIXME TODO use ex_nrns to create a lookup for these
    ccr_nrns = [
        anncop((NeuronSparcNlp if 'sparc-nlp' in n.id_ else Neuron)(
            *n.pes, id_=n.id_, label=n._origLabel, override=True, partialOrder=n.partialOrder()),
               config._written_graph)
        for n in nrns if 'sparc-nlp/composer' not in n.id_
        and 'composer/uris/set' not in n.id_
    ]
    remlabs_write(config_composer_roundtrip)
    config_composer_roundtrip.write_python()
    rtids = set(n.id_ for n in ccr_nrns)
    # TODO remove all the gen labels like we do in nlp

    # TODO move ex before composer rt so we can look up the existing parent class
    ex_nrns, ex_config, ex_g = load_config(local=True)
    #ex_nrns = ex_config.neurons()
    config_existing = Config('composer-existing')
    cex_nrns = [
        anncop(n.__class__(
            *n.pes, id_=n.id_, label=n._origLabel, override=True, partialOrder=n.partialOrder()),
               ex_g)
        for n in ex_nrns if n.id_ in rtids]
    remlabs_write(config_existing)
    config_existing.write_python()

    return config,


def _oldmain():
    r1 = sht.rows()[1]
    trips = [t for t in [row_to_triple(r) for r in sht.rows()[1:]] if t is not None]
    bund = {}
    for s, p, o in trips:
        if s not in bund:
            bund[s] = []

        bund[s].append((p, o))

def row_to_triple(row):  # XXX old before reuse of nlp code
    skip = ilxtr.hasSomaPhenotype,
    s = rdflib.URIRef(row.uri().value)

    p = map_predicates(row.predicate().value)
    if p in skip:
        return
        
    v = row.identifier().value
    if v:
        if ',' in v:
            r, l = v.split(',')
            o = rdflib.URIRef(r)  # TODO region + layer
        else:
            o = rdflib.URIRef(v)
    else:
        # looks like the export contains rows even when there is no value for that phenotype
        # which is annoying because you can't tell if you screwed up or whether the data
        # actually did not contain that value
        msg = f'where value for {p}?'
        #raise NotImplementedError(msg)
        log.error(msg)
        o = TEMP.FIXME_MISSING
        return

    row.connected_from_uris()  # used for partial order probably
    row.axonal_course_poset()
    #row.relationship()
    #s.rows()[1].cells[0]
    #s.raw_values = rows
    #s._values = rows
    return s, p, o


if __name__ == '__main__':
    main()
