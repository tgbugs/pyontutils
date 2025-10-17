import csv
import rdflib
import augpathlib as aug
from pyontutils import sheets
from pyontutils.namespaces import TEMP, ilxtr, rdfs, skos, interlex_namespace
from neurondm.models.nlp import map_predicates, main as nlp_main, NeuronSparcNlp
from neurondm.models.apinat_npo import NeuronApinatSimple
from neurondm.core import log as _log, uPREFIXES, Config, Neuron

log = _log.getChild('composer')
anat_space_hack = 'http://purl.obolibrary.org/obo/UBERON_0000464'
uPREFIXES['gastint'] = 'http://uri.interlex.org/composer/uris/set/gastint/'  # run at top level to ensure is registered

ilxcr = rdflib.Namespace(interlex_namespace('composer/uris/readable/'))

def get_csv_sheet(path):
    with open(path, 'rt') as f:
        _rows = list(csv.reader(f))

    # remove rows that are missing a value since the export doesn't do
    # that and we will get missing if not provided
    # FIXME TODO take NLP-ID and promote to subject if missing
    idx = _rows[0].index('Object URI')
    sidx = _rows[0].index('Subject URI')
    pidx = _rows[0].index('Predicate URI')
    tidx = _rows[0].index('Object Text')
    ridx = _rows[0].index('Reference (pubmed ID, DOI or text)')
    cidx = _rows[0].index('Connected from uri')
    derp_idx = _rows[0].index('Object')
    _rows[0][ridx] = 'literature citation'  # XXX HACK
    sigh = 'https://uri.interlex.org/'
    sigh2 = 'https://scicrunch.org/scicrunch/interlex/view/'
    for i, _r in enumerate(_rows[1:]):  # FIXME EVEN BIGGER HACK
        if (not (_r[idx] or _r[tidx])) and _r[derp_idx]:
            _r[tidx] = _r[derp_idx]

        if _r[cidx] == anat_space_hack:
            _r[cidx] = ''

        if _r[idx] == 'http://uri.interlex.org/tgbugs/uris/readable/HasProjection':
            # something got mangled inside composer ...
            _r[idx] = 'http://uri.interlex.org/tgbugs/uris/readable/ProjectionPhenotype'
            log.error(f'bad object value for {i + 2}')

        if _r[derp_idx] == 'not specified':
            _r[sidx] = ''  # for skip the row to avoid bad triples with TEMP:MISSING
            #_r[derp_idx] = ''

        for j, c in enumerate(list(_r)):
            if c.startswith(sigh):
                _r[j] = _r[j].replace(sigh, 'http://uri.interlex.org/')
                log.error(f'bad scheme for uri.interlex.org identifier at {i + 2} {j + 1}')
            elif c.startswith(sigh2):
                _r[j] = _r[j].replace(sigh2, 'http://uri.interlex.org/base/')
                log.error(f'bad prefix for uri.interlex.org identifier at {i + 2} {j + 1}')

    # FIXME TODO maybe skip stuff flagged as invalid
    rows = [[c if c != 'http://www.notspecified.info' else ''
             for c in r] for r in _rows
            if (r[idx] or r[tidx]) and r[sidx]
            and r[idx] != anat_space_hack
            ]
    assert len(rows) > 1

    # missing due to issues with aacar-1 and pancr-2
    aacar_11 = [''] * len(rows[0])
    aacar_11[sidx], aacar_11[pidx], aacar_11[idx] = (
        'ilxtr:neuron-type-aacar-11', 'ilxtr:hasForwardConnectionPhenotype', 'ilxtr:neuron-type-aacar-1')

    pancr_1 = [''] * len(rows[0])
    pancr_1[sidx], pancr_1[pidx], pancr_1[idx] = (
        'ilxtr:neuron-type-pancr-1', 'ilxtr:hasForwardConnectionPhenotype', 'ilxtr:neuron-type-pancr-2')

    sstom_11 = [''] * len(rows[0])
    sstom_11[sidx], sstom_11[pidx], sstom_11[idx] = (
        'ilxtr:neuron-type-sstom-11', 'ilxtr:hasFunctionalCircuitRolePhenotype', 'ILX:0105486')

    sstom_12 = [''] * len(rows[0])
    sstom_12[sidx], sstom_12[pidx], sstom_12[idx] = (
        'ilxtr:neuron-type-sstom-12', 'ilxtr:hasFunctionalCircuitRolePhenotype', 'ILX:0104003')

    sdcol_l = [''] * len(rows[0])
    sdcol_l[sidx], sdcol_l[pidx], sdcol_l[idx] = (
        'ilxtr:neuron-type-sdcol-l', 'neurdf.ent:hasMolecularPhenotype', 'TEMPIND:Nos1')

    sdcol_lp = [''] * len(rows[0])
    sdcol_lp[sidx], sdcol_lp[pidx], sdcol_lp[idx] = (
        'ilxtr:neuron-type-sdcol-l-prime', 'neurdf.ent:hasMolecularPhenotype', 'TEMPIND:Nos1')

    rows.extend((
        aacar_11,
        pancr_1,
        sstom_11,
        sstom_12,
        sdcol_l,
        sdcol_lp,
    ))

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
def load_config(gitref='neurons', local=False, restore=True, load_complex=True):
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

    imports = (
        'apinat-partial-orders',
        'apinat-pops-more',
        'apinat-simple-sheet',
        'sparc-nlp',
    )

    if load_complex:
        imports += ('apinat-complex',)

    # full imports
    for f in imports:
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


class NeuronApinatComplex(NeuronApinatSimple):
    owlClass = ilxtr.NeuronApinatComplex
    shortname = 'apinat'


def remlabs_write(config, keep=tuple()):
    config.write()
    labels = tuple(
        l for l in (#ilxtr.genLabel,
            rdfs.label,
            ilxtr.origLabel,
            ilxtr.localLabel, ilxtr.simpleLabel,
            ilxtr.simpleLocalLabel, skos.prefLabel)
        if l not in keep)
    to_remove = [t for t in config._written_graph if t[1] in labels]
    [config._written_graph.remove(t) for t in to_remove]
    #[config._written_graph.add(t) for t in to_add]
    # TODO figure out about partial orders being roundtripped or not?
    config._written_graph.write()


def ncfun_roundtrip(id):
    if '/neuron-type-' in id:
        return NeuronApinatComplex
    elif '/sparc-nlp/' in id:
        return NeuronSparcNlp
    else:
        return Neuron


def main(report=True):
    exp = aug.LocalPath('~/downloads/export_v5-1-1_2025-09-12_04-50-39.csv').expanduser()

    sht = get_csv_sheet(exp)
    cs = [sht]
    config = Config('composer-and-roundtrip')
    nlp_main(cs=cs, config=config, neuron_class=Neuron, neuron_class_fun=ncfun_roundtrip)  # FIXME neuron_class is incorrect and changes per model
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
        # composer only
        ilxcr.hasComposerURI,

        # composer export derived
        skos.prefLabel,
        #ilxtr.curatorNote,
        #ilxtr.inNLPWorkingSet,  # XXX there is no explicit field in the export for this right now?
        #ilxtr.reference,  # XXX this is not present from composer so leave out to reduce noise
        #ilxtr.reviewNote,
        #ilxtr.sentenceNumber,

        # ontology derived extra
        #ilxtr.alertNote,
        #ilxtr.hasOrganTarget,  # currently not ingested into composer
        #ilxtr.literatureCitation,  # leave this out for now because it is composer only

             )
    def anncop(n, g):
        s = n.id_
        for p in acops:
            for o in g[s:p]:
                graphBase.out_graph.add((s, p, o))

        return n

    from neurondm import orders as nord

    def _key(v):
        if isinstance(v, nord.rl):
            return v
        else:
            return nord.rl(v)

    def pos(nst):
        # XXX temporary hack to normalize all edges for comparison
        _adj = nord.nst_to_adj(nst)
        adj = [tuple(sorted(ab, key=_key)) for ab in _adj]
        return nord.adj_to_nst(adj)

    def pos(nst): return nst

    # skos no longer in rdflib default so not restored after cull_prefixes
    config._written_graph.namespace_manager.bind('skos', str(skos))
    config_composer_only = Config('composer')
    cco_nrns = [
        anncop(NeuronComposer(
            *n.pes, id_=n.id_, label=n._origLabel, override=True, partialOrder=pos(n.partialOrder())),
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
        anncop((ncfun_roundtrip(n.id_))(
            *n.pes, id_=n.id_, label=n._origLabel, override=True, partialOrder=pos(n.partialOrder())),
               config._written_graph)
        for n in nrns if 'sparc-nlp/composer' not in n.id_
        and 'composer/uris/set' not in n.id_
    ]
    remlabs_write(config_composer_roundtrip)
    config_composer_roundtrip.write_python()
    rtids = set(n.id_ for n in ccr_nrns)

    config_composer_apinat = Config('apinat-complex')
    cca_nrns = [
        anncop((ncfun_roundtrip(n.id_))(
            *n.pes, id_=n.id_, label=n._origLabel, override=True,
            #partialOrder=pos(n.partialOrder())
        ),
               config._written_graph)
        for n in nrns if '/neuron-type-' in n.id_
    ]
    remlabs_write(config_composer_apinat)
    config_composer_apinat.write_python()

    # TODO remove all the gen labels like we do in nlp
    # TODO move ex before composer rt so we can look up the existing parent class
    ex_nrns, ex_config, ex_g = load_config(local=True)
    #ex_nrns = ex_config.neurons()
    config_existing = Config('composer-existing')
    cex_nrns = [
        anncop(n.__class__(
            *n.pes, id_=n.id_, label=n._origLabel, override=True, partialOrder=pos(n.partialOrder())),
               ex_g)
        for n in ex_nrns if n.id_ in rtids]
    remlabs_write(config_existing)
    config_existing.write_python()

    if not report:
        return

    ok_for_reason = {
        ilxtr['neuron-type-pancr-2']: 'apinat contains loops which composer cannot represent, also dendrite edges go in opposite order because composer cannot currently start distally and always starts at soma (see anat space hack)',
        ilxtr['neuron-type-pancr-4']: 'apinat contains a loop which npo skips',
        ilxtr['neuron-type-bolew-unbranched-24']: 'addition of fiber does not change overall order',
    }

    apinat_cases = [i for i in rtids if 'neuron-type' in i]
    crin = {n.id_:n for n in ccr_nrns}
    exin = {n.id_:n for n in cex_nrns}
    todiff = []
    for a in apinat_cases:
        if a not in crin or a not in exin:
            log.debug(f'one side missing {a}')
            continue

        t = crin[a], exin[a]
        todiff.append(t)

    report_both = {}
    report_cm = {}
    for c, e in todiff:
        ca = tuple(tuple(e.region if e.layer is None else e for e in ab) for ab in nord.nst_to_adj(c.partialOrder()))
        ea = nord.nst_to_adj(e.partialOrder())
        sca, sea = set(ca), set(ea)
        sca_only, sea_only = sca - sea, sea - sca
        # loops
        #sea_maybe_loops = set((b, a) for a, b in sea_only)
        #sea_loops = sca & sea_maybe_loops
        # node diff
        nsca = set(e for es in ca for e in es)
        nsea = set(e for es in ea for e in es)
        nsca_only, nsea_only = nsca - nsea, nsea - nsca
        if sea_only and sca_only:
            msg = f'{c.id_} both different'
            rep = c, e, sca, sea, sca_only, sea_only, nsca_only, nsea_only
            #if len(sea_loops) == len(sea_maybe_loops):
                #msg = f'{c.id_} all composer missing cases are loops so ok'
                #log.debug(msg)
                #continue

            if c.id_ not in ok_for_reason:
                report_both[c.id_] = rep
        elif sea_only:
            msg = f'{c.id_} composer missing'
            rep = c, e, sca, sea, sca_only, sea_only, nsca_only, nsea_only
            report_cm[c.id_] = rep
        elif sca_only:
            msg = f'{c.id_} only difference is new nodes in composer'
        else:
            msg = None

        if msg:
            log.debug(msg)

    ({k:[sorted(_, key=_key) for _ in v[-2:]] for k, v in report_both.items()},
     {k:[sorted(_, key=_key) for _ in v[-2:]] for k, v in report_cm.items()},)

    ({k:[_ for _ in v[-4:-2]] for k, v in report_both.items()},
     {k:[_ for _ in v[-4:-2]] for k, v in report_cm.items()},)

    breakpoint()
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
