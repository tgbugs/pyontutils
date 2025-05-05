import os
import pathlib
import textwrap
from collections import defaultdict
import rdflib
import graphviz
from pyontutils.core import OntGraph, OntResIri, OntResPath
from pyontutils.namespaces import rdfs, ilxtr
from neurondm.core import Config, graphBase, log
from neurondm.core import OntTerm, OntId, RDFL
from neurondm.models.composer import load_config
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
        return [(ph._neurdf_prefix_type, ph.p) for ph in neuron.pes
                if ph.e == predicate and not collect.append((ph._neurdf_prefix_type, predicate, ph.p))]

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
    if nested is None:
        return

    for e in nested:
        if isinstance(e, list) or isinstance(e, tuple):
            yield tuple(simplify_nested(f, e))
        elif isinstance(e, orders.rl):
            yield orders.rl(f(e.region), f(e.layer))
        else:
            yield f(e)


def filter_cycles(adj):
    out = []
    for a, b in adj:
        if a == b:
            log.warning(f'cycle removed on {a}')
            continue

        out.append((a, b))

    return out


from neurondm.models.apinat_pops_more import _genlabel
def wssn(nid):
    p, f = nid.rsplit('/', 1)
    if f.startswith('neuron-type-'):
        label, x = _genlabel(nid)
        return x
    elif 'sparc-nlp/' in nid:
        p, x, n = nid.rsplit('/', 2)
        return x
    else:
        return None


def for_composer(n, cull=False):
    lpes, lrdf, collect = makelpesrdf()
    _po = n.partialOrder()
    idwssn = wssn(n.id_)
    fc = dict(
        id = str(n.id_),
        label = str(n.origLabel),  # this is our rdfs label not prefLabel
        # prefLabel = ???,  # TODO I don't think we roundtrip this normally
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
        #phenotype =          lpes(n, ilxtr.hasAnatomicalSystemPhenotype),  # no longer current
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
        working_set =     lrdf(n, ilxtr.inNLPWorkingSet),
        ws_short =        idwssn,  # lrdf(n, ilxtr.workingSetShortName),  # XXX TODO materialize probably

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
    npo = set((p._neurdf_prefix_type, p.e, p.p) for p in n.pes)
    cpo = set(collect)
    unaccounted_pos = npo - cpo
    if unaccounted_pos:
        log.warning(
            (n.id_, [[n.in_graph.namespace_manager.qname(e) for e in pos]
                     for npt, *pos in unaccounted_pos]))
    return {k:v for k, v in fc.items() if v} if cull else fc


def location_summary(neurons, anatent_simple=False):
    import csv
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

        preds = sorted(set(e for n in neurons for e in n.edges))
        header = ['id'] + [OntId(p).curie for p in preds]
        _rows = [[n.id_, *[','.join(sorted([OntId(o).curie  for o in n.getObjects(p)])) for p in preds]] for n in neurons]
        rows = [header] + _rows
        with open('/tmp/npo-by-predicates.csv', 'wt') as f:
            csv.writer(f, lineterminator='\n').writerows(rows)

    else:
        header = 'o', 'o_label', 'o_synonym'
        rows = (
            [header] +
            [(_.iri, _.label, syn) for _ in sorted(locations, key=key)
             for syn in _.synonyms])
        with open('/tmp/anatomical_entities.csv', 'wt') as f:
            csv.writer(f, lineterminator='\n').writerows(rows)


def reconcile(n):
    lobjs = set(o for p in n._location_predicates._litmap.values() for o in n.getObjects(p))
    po_rl = set(e for pair in orders.nst_to_adj(n.partialOrder()) for e in pair)
    po_r = set(t.region if isinstance(t, orders.rl) else t for t in po_rl)
    po_l = set(t.layer for t in po_rl if isinstance(t, orders.rl))
    po_rl.difference_update({rdflib.Literal('blank')})
    po_r.difference_update({rdflib.Literal('blank')})
    po_l.difference_update({rdflib.Literal('blank')})
    #[if isinstance(e, orders.rl) else ]
    both = po_r & lobjs
    either = po_r | lobjs
    missing_axioms = po_r - lobjs
    missing_orders = lobjs - po_r
    missing_orders_rl =  lobjs - ( po_r | po_l )
    withl_missing_axioms = po_rl - lobjs
    withl_missing_orders = lobjs - po_rl
    ok_reg_l = not (missing_axioms or missing_orders_rl)
    ok_reg = not (missing_axioms or missing_orders)
    ok_rl = not (withl_missing_axioms or withl_missing_orders)
    return {
        'ok_reg': ok_reg,
        'ok_rl': ok_rl,
        'ok_reg_l': ok_reg_l,
        'withl_missing_axioms': withl_missing_axioms,
        'withl_missing_orders': withl_missing_orders,
        'missing_axioms': missing_axioms,
        'missing_orders': missing_orders,
        'missing_orders_rl': missing_orders_rl,
    }


def lgen(u):
    l = OntTerm(u).label
    if isinstance(l, tuple):
        log.warning(f'sigh {u} {l}')
        l = l[0]
    if l is None:
        c = OntId(u).curie
        log.warning(f'no label for {c}')
        return c,
    else:
        return textwrap.wrap(l, 30)


def synviz(neurons):
    index = {n.id_:n for n in neurons}
    idstrs = ('keast', 'aacar', 'sstom', 'pancr', 'bolew', 'sdcol', 'splen', 'bromo',  # XXX hack :/
              # FIXME mmset1 and 2 need ccomp to be easily visualized (ccomp is better for layout anyway)
              'semves', 'prostate', 'mmset1', 'mmset2', 'mmset4',)
    done = set()
    subsets = []
    for idstr in idstrs:
        subset = set(n for n in neurons if idstr in n.identifier)
        done.update(subset)
        subsets.append((subset, idstr))

    missed = set(neurons) - done
    if missed:
        subsets.append((missed, 'missed'))

    for subset, idstr in subsets:
        edges = [
            (pre, index[post])
            for pre in subset
            for post in pre.getObjects(ilxtr.hasForwardConnectionPhenotype)]

        dot = graphviz.Digraph(comment='forward connection')

        for ne in set(ne for nene in edges for ne in nene):
            dot.node(OntId(ne.id_).curie.replace(":", "-"),
                     label=OntId(ne.id_).curie,
                     #label=ne.origLabel
                     )

        for pre, post in edges:
            dot.edge(OntId(pre.id_).curie.replace(":", "-"), OntId(post.id_).curie.replace(":", "-"))

        base = pathlib.Path('/tmp/syntaptic/')
        if not base.exists():
            base.mkdir()

        dot.render(base / f'neurons-synaptic-connectivity-{idstr}', format='svg')


def gviz(n):
    nid = OntId(n.id_).curie
    dot = graphviz.Digraph(comment=nid)
    dot.attr('graph', labelloc='t')
    dot.attr('graph', label=n.origLabel)
    dot.attr('node', fontname='DejaVu Sans Mono')
    _bl = rdflib.Literal('blank')
    adj = [e for e in orders.nst_to_adj(n.partialOrder()) if e[0] != _bl]
    # FIXME labels need to be done once or it will be insanely slow
    nl = '\n'
    labels = {v: ((f'{v.hash_thing()}\n'
                   f'{nl.join(lgen(v.region))}\nx\n'
                   f'{nl.join(lgen(v.layer))}')
              if isinstance(v, orders.rl) else f'{OntId(v).curie}\n{nl.join(lgen(v))}')
              for v in set(v for e in adj for v in e)}
    for ab in adj:
        a, b = ab
        c, d = [n.hash_thing().replace(":", "-") if isinstance(n, orders.rl) else OntId(n).curie.replace(":", "-") for n in ab]
        dot.edge(c, d)
        # XXX dupes
        dot.node(c, label=labels[a])
        dot.node(d, label=labels[b])

    #print(dot.source)
    base = pathlib.Path('/tmp/partial-orders/')
    if not base.exists():
        base.mkdir()

    dot.render(base / f'neuron-po-{nid.replace(":", "-")}', format='svg')


def apinat_ontology_to_internal(blob):
    fixes = {
        # white matter issues, cns white matter layer is not a parent class of the spinal cord layer
        # the proliferation of terms for white matter in uberon without consistent modelling is a problem
        'UBERON:0016549': 'UBERON:0002318',
        # epicardium -> epicardial fat, issue is in the NPO representation I think? cause layer mismatch
        'UBERON:0002348': 'UBERON:0015129',
    }
    exclude = (
        # lingering old id not used anywhere (hopefully)
        'lyph-cardiovascular-heart-fat-layer',  # -> mat-tissue-cardiovascular-epicardial-fat
        'lyph-cardiovascular-heart-epicardium',  # related to the fix for 2348 -> 15129 above FIXME this won't work will it ... double replace
        #'mat-peritoneal-serosa-of-esophagus',  # XXX mismatch between wbcrm and sstom modelling I think?

    )
    out = {}
    lc = blob['localConventions']  # FIXME TODO use these to expand to OntId
    for d in (*blob['lyphs'], *blob['materials']):
        if 'ontologyTerms' not in d:
            log.warning(f'missing ontologyTerms: {d}')
            continue
        ots = d['ontologyTerms']
        id = d['id']
        if id in exclude:
            continue
        if len(ots) > 1 or not ots:
            log.error(ots)
            continue
        else:
            # FIXME use localConventions first
            ots0 = ots[0]
            if ots0 in fixes:
                log.info(f'replaced {ots0} -> {fixes[ots0]}')
                ots0 = fixes[ots0]

            oid = OntId(ots0)
            if oid.u in out:
                log.critical(f'DOUBLE ID FOR {oid}: {out[oid.u]} {id}')
                continue
            else:
                out[oid.u] = id

    return out


def npo_to_apinat(neurons):
    import requests
    wbrcm = "https://raw.githubusercontent.com/open-physiology/apinatomy-models/master/models/wbrcm/source/wbrcm.json"
    blob = requests.get(wbrcm).json()
    lookup = apinat_ontology_to_internal(blob)
    all_segments = [seggen(n, blob, lookup) for n in neurons]
    _ok_segs = [(i, segs) for i, segs in enumerate(all_segments) if segs and all([v[0] and v[1] for v_all in segs.values() for v in v_all])]
    globals().update(locals())
    ok = [i for i, s in _ok_segs]
    ok_segs = [s for i, s in _ok_segs]
    log.info(f'ok/all: {len(ok_segs)}/{len(all_segments)}')
    globals().update(locals())
    all_chains = [c for i, n in enumerate(neurons) for c in chaingen(n, blob, lookup, i)]
    ok_chains = [c for i, n in enumerate(neurons) if i in ok for c in chaingen(n, blob, lookup, i)]  # TODO group probably ...
    for c in all_chains:
        c['ok'] = c in ok_chains

    localConventions = {  # TODO derive from somewhere more sensible
        'too': 'https://apinatomy.org/uris/models/too-map/ids/',
        'wbkg': 'https://apinatomy.org/uris/models/wbrcm/ids/',
    }
    out = {
        'id': 'npo-neurons',
        'name': 'NPO neuron types as ApiNATOMY neuron populations',
        'imports': [wbrcm],
        'namespace': 'npo-apinat',
        'localConventions': [{'prefix': k, 'namespace': v} for k, v in localConventions.items()],
        'chains': all_chains,
     }
    return out


def get_layer_index(r_id, l_id, blob):
    things = [l for l in blob['lyphs'] + blob['materials'] if l['id'] == r_id]
    if not things:
        msg = f'sigh? {r_id}'
        raise ValueError(msg)

    l = things[0]
    if 'layers' in l:
        layers = l['layers']
        if l_id not in layers:
            log.error(f'sigh: {r_id} {l_id} {layers}')
        return layers.index(l_id)
    elif 'supertype' in l:
        return get_layer_index(l['supertype'], l_id, blob)
    else:
        raise ValueError('uhoh')


def seggen(n, blob, lookup):
    segments, dis = _seggen(n, blob, lookup)
    return segments


process_types = {
    ilxtr.hasAxonLocatedIn: 'wbkg:lt-axon-tube',
    ilxtr.hasDendriteLocatedIn: 'wbkg:lt-dend-bag',
    ilxtr.hasSomaLocatedIn: ('wbkg:lt-soma-of-neuron', 'wbkg:lt-axon-tube'),  # FIXME see what to do about inferred dendrites
    # FIXME also issue with inferring dendrite bag because we don't know whether the might be an explicit dendrite
    ilxtr.hasAxonPresynapticElementIn: 'wbkg:lt-axon-bag',
    ilxtr.hasAxonSensorySubcellularElementIn: 'lt-axon-sens-bag',
    ilxtr.hasAxonLeadingToSensorySubcellularElementIn: 'lt-axon-sens-tube',
}


def _seggen(n, blob, lookup):
    _blank = rdflib.Literal('blank')
    adj = [edge for edge in orders.nst_to_adj(n.partialOrder()) if edge[0] != _blank]
    try:
        dis, lin = orders.adj_to_lin(adj)
    except Exception as e:
        log.exception(e)
        return {}, None

    starts = [seq[0] for seq in dis]
    int_dis = [seq[-1] for seq in dis if len(seq) > 1 and seq[-1] in starts]
    assert not int_dis, 'derp'
    in_linkers = set(v for edge in lin for v in edge)
    tar_linkers = {}
    src_linkers = {}
    dd = defaultdict(set)
    idp = OntId(n.identifier).curie.replace(":", "-")
    for i, edge in enumerate(lin):
        node_id = f'node-{idp}-{i}'
        a, b = edge
        if a in tar_linkers and b in src_linkers and tar_linkers[a] != src_linkers[b]:
            # this is the case where we have to rewrite nodes because we discover that
            # they converge at some later point because a vertex is present in multiple
            # linkers, in this case we prefer and thus use the lowest existing node id
            tla = tar_linkers[a]
            slb = src_linkers[b]
            node_id, rewrite = (tla, slb) if tla < slb else (slb, tla)
            to_rewrite = dd[rewrite]
            dd[rewrite] = None
            for identifier in to_rewrite:
                for _linkers in (tar_linkers, src_linkers):
                    if identifier in _linkers and _linkers[identifier] == rewrite:
                        # must also check that the identifier matches rewrite otherwise we overwrite
                        # a regions target with its source or source with its target
                        _linkers[identifier] = node_id

        elif a in tar_linkers:
            node_id = tar_linkers[a]
        elif b in src_linkers:
            node_id = src_linkers[b]

        tar_linkers[a] = node_id
        src_linkers[b] = node_id
        dd[node_id].update((a, b))

    lindex = dict(dd)

    # axiom lookup
    alu = {o:p for p in n._location_predicates._litmap.values() for o in n.getObjects(p)}
    po_rl = set(v for edge in adj for v in edge)

    segments = {}
    for vertex in po_rl:
        all_segs = []
        seg = []
        for e in ((vertex.region, vertex.layer) if isinstance(vertex, orders.rl) else (vertex, None)):
            if e in lookup:
                i = lookup[e]
            else:
                i = None

            if e in alu:
                t = alu[e]
            else:
                t = None

            seg.append(i)
            seg.append(t)

            if e in tar_linkers:
                ta = tar_linkers[e]
            else:
                ta = None

            if e in src_linkers:
                sr = src_linkers[e]
            else:
                sr = None

            seg.append(ta)
            seg.append(sr)

        r_id, r_type, r_tar, r_src, l_id, l_type, l_tar, l_src = seg
        if r_type and l_type and r_type != l_type:
            msg = f'error rendring {n}: {r_type} != {l_type}'
            log.error(msg)
            return {}, dis
        elif r_type:
            # FIXME soma -> + axon
            actual_type = process_types[r_type]
        elif l_type:
            log.critical(f'uhoh {r_id} {l_id} {l_type}')
            actual_type = process_types[l_type]
        else:
            actual_type = None

        try:
            layer_index = None if r_id is None or l_id is None else get_layer_index(r_id, l_id, blob)
        except ValueError as e:
            log.exception(e)
            msg = f'error rendring {n}'
            log.error(msg)
            return {}, dis

        if isinstance(actual_type, tuple):
            # soma implied axon case
            if len(actual_type) < 2:
                raise ValueError('need at least two')

            at0, *atd, atn = actual_type
            s0 = r_id, r_type, None, r_src, l_id, l_type, None, l_src, at0, layer_index
            all_segs.append(s0)
            for at in atd:
                nseg = r_id, r_type, None, None, l_id, l_type, None, None, at, layer_index
                all_segs.append(nseg)

            sn = r_id, r_type, r_tar, None, l_id, l_type, l_tar, None, atn, layer_index
            all_segs.append(sn)
        else:
            seg.append(actual_type)
            seg.append(layer_index)
            all_segs.append(seg)

        segments[vertex] = all_segs  # FIXME needs to be a list because a single soma segment can expand into multiple chain segments

    #if int_dis or src_linkers or tar_linkers:
        #breakpoint()

    return segments, dis


def chaingen(n, blob, lookup, index=0):
    segments, dis = _seggen(n, blob, lookup)
    if not segments:
        return []

    chains = []
    for i, seq in enumerate(dis):
        lyphTemplates = []
        housingLyphs = []
        housingLayers = []
        levels = []
        root = None
        #leaf = None
        for j, vertex in enumerate(seq):  # XXX FIXME have to split chains by type because they can only have a single template :/
            all_segs = segments[vertex]
            for k, seg in enumerate(all_segs):
                r_id, r_type, r_tar, r_src, l_id, l_type, l_tar, l_src, actual_type, layer_index = seg

                lyphTemplates.append(actual_type)
                housingLyphs.append(None if r_id is None else 'wbkg:' + r_id)
                housingLayers.append(layer_index)  # XXX looking at housingLayers in pancreas it is clearly wrong

                # either nil or empty object if we don't need any explicit information
                link = {}

                if j == 0 and r_src and k == 0:
                    root = r_src  # FIXME there is no way there are 8 that share a root for mmset1/11
                elif r_src:
                    # XXX shouldn't need this even in multiply branched cases
                    # because it should be matched correctly by apinatomy ???
                    # but there could be a bug in the chaingen code for levels?
                    #link['source'] = r_src
                    #breakpoint()
                    pass

                if actual_type is not None:
                    link['conveyingLyph'] = actual_type #'lyph-template-type',
                if r_tar is not None:
                    # FIXME mmset1-11 everything has the same target, the 0th node which is also the root ???
                    link['target'] = r_tar

                if link:
                    # FIXME seems like there is a bug where if the link structure is missing and id
                    # the expansion code will incorrectly match it with other identical link objects
                    # resulting in links appearing to be shared between many neurons
                    # adding the id here is a workaround
                    link['id'] = f'link-for-chains-{index}-{i}-{j}-{k}'

                levels.append(link)  # TODO vs None

        chain = {
            'id': f'chain-{OntId(n.id_).curie.replace(":", "-")}-{i}',
            #'leaf': '',
            # 'lyphTemplates': lyphTemplates,  # not useful for branched structures
            'housingLyphs': housingLyphs,
            'housingLayers': housingLayers,
            'levels': levels,  # these are links so have to provide {'id': 'link-id', 'source': }
         }

        if root is not None:
            chain['root'] = root

        chains.append(chain)

    return chains


def main(local=False, anatomical_entities=False, anatent_simple=False, do_reconcile=False, viz=False, chains=False):
    # if (local := True, anatomical_entities := True, anatent_simple := False, do_reconcile := False, viz := False, chains := False):
    restore = do_reconcile or viz or anatomical_entities
    neurons, ex_config, ex_g = load_config(local=local, restore=restore)
    new_neurons = [n for n in neurons if 'neuron-type-' not in n.id_]  # filter out existing apinatomy populations

    # ingest to composer starts here
    mvp_ingest = [n for n in neurons if not multi_orig_dest(n)]

    dims = set(p for n in neurons for p in n.edges)  # for reference
    fcs = [for_composer(n) for n in mvp_ingest]
    _fcne = [for_composer(n, cull=True) for n in mvp_ingest]  # exclude empties for easier manual review

    # example neuron
    n = mvp_ingest[0]
    fc = for_composer(n)

    # example partial orders
    view_partial_orders = [tuple(simplify_nested(simplify, n.partialOrder())) for n in neurons]

    # example linearized orders
    def linearize(n):
        def key(d):
            return tuple((n.region, n.layer) if isinstance(n, orders.rl) else (n, '') for n in d)
            # FIXME somehow the caste to orders.rl here results in a different sort order than
            # the version above !?!??!
            #return tuple(n if isinstance(n, orders.rl) else orders.rl(n) for n in d)

        try:
            adj = filter_cycles(orders.nst_to_adj(tuple(simplify_nested(simplify, n.partialOrder()))))
            dis, lin = orders.adj_to_lin(adj)
            rej = orders.lin_to_adj(dis, lin)
            sa, sj = sorted(adj, key=key), sorted(rej, key=key)
            assert set(sa) == set(sj), breakpoint()  # XXX if this passes be the below fails we are in big trouble
            assert sa == sj, breakpoint()
            return dis, lin
        except Exception as e:
            log.exception(e)
            log.error(f'cycle in\n{n}')
            return [], []

    def _rend(dislin):
        dis, lin = dislin
        return [' '.join([n.hash_thing() if isinstance(n, orders.rl) else n for n in d])
                for d in sorted(dis, key=len, reverse=True)], [[n.hash_thing() if isinstance(n, orders.rl) else n for n in d] for d in lin]

    linear_orders = sorted([(n.id_, linearize(n)) for n in neurons])
    view_linear_orders = [(i, _rend(dislin)) for i, dislin in linear_orders]

    if do_reconcile:
        _recs = [(n, reconcile(n)) for n in neurons]
        recs_reg = [(n, r) for n, r in _recs if not r['ok_reg']]
        recs_rl = [(n, r) for n, r in _recs if not r['ok_rl']]
        recs_reg_l = [(n, r) for n, r in _recs if not r['ok_reg_l']]
        msg = f'{len(recs_reg)} pops with reg issues, {len(recs_rl)} pops with rl issues, {len(recs_reg_l)} pops with reg_l'
        log.info(msg)
        sigh_reg = sorted([(len(r["missing_axioms"]), len(r["missing_orders"]), n, r) for n, r in recs_reg],
                          key=lambda t: (t[0] + t[1], t[0], t[1]), reverse=True)
        sigh_how = [s[:2] + tuple(OntId(_.id_).curie for _ in s[2:3]) for s in sigh_reg]
        rep_reg = 'a  o  i\n' + '\n'.join(f'{a: >2} {o: >2} {i}' for a, o, i in sigh_how)
        missing_orders = sorted(set([e for n, r in _recs for e in r['missing_orders']]))
        missing_orders_rl = sorted(set([e for n, r in _recs for e in r['missing_orders_rl']]))

        # missing orders populations where neither region nor layer are accounted for
        morl = [(n, r) for n, r in _recs if r['missing_orders_rl']]

        import pprint
        from pyontutils.core import IlxTerm
        from neurondm.orders import rl
        from collections import Counter
        derp = defaultdict(list)
        for n, r in _recs:
            if r['missing_orders_rl']:
                for mo in r['missing_orders_rl']:
                    derp[mo].append(n)
        dderp = {OntTerm(k): v for k, v in derp.items()}
        mcmorl_issues = Counter([_.id_ for k, v in dderp.items() for _ in v]).most_common()

        derps = set([_ for k, v in dderp.items() for _ in v])
        lderps = len(derps)  # 63 for mo, 25 for

        _report = ''
        for k, v in dderp.items():
            _report += '\n--------------------------------------\n'
            _report += repr(k)
            for _ in v:
                _report += '\n'
                _report += str(_)
                _report += pprint.pformat(_.partialOrder())

        log.debug(_report)

        lu_mo = [OntTerm(t) for t in missing_orders]
        lu_mo_rl = [OntTerm(t) for t in missing_orders_rl]

        ilu_mo = [IlxTerm(t) for t in missing_orders]
        ilu_mo_rl = [IlxTerm(t) for t in missing_orders_rl]

        def sigh(t, pred):
            if not t.validated:
                # FIXME this is where query services wants RDFL
                # for things like ilxtr:cardiac-interganglionic-nerve
                # but the bug is really in OntTerm which should still
                # be able to answer predicates when not validated ...
                return tuple()

            if pred in t.predicates:
                v = t.predicates[pred]
                if not isinstance(v, tuple):
                    return v,

                return v

            return tuple()

        # XXX cases where region/layer were modelled as subClassOf/partOf pairs  # XXX probably need to fix modeling of these in interlex
        ilu_scopo = [(t, sigh(t, 'rdfs:subClassOf'), sigh(t, 'ilx.partOf:')) for t in ilu_mo_rl]
        ilu = [(a, rl(b[0].u, c[0].u)) for a, b, c in ilu_scopo if b and c if len(b) == 1 and len(c) == 1]

        _manual_lookup_table = {
            '': rl('', ''),
        }

        # XXX cases where region/layer/layer were modelled as part part vessles in layer of colon mostly
        # sdcol-f is not actually the issue here it seems
        #f = [n for n in neurons if 'sdcol-f' in n.id_][0]
        #f.pes()
        #f.partialOrder()

        # XXX cases where an axiom appears as a layer in a partial order because the layer is already a direct part of the region e.g. bromo-1 case
        # TODO try to automate detection of these cases during conversion from apinatomy to partial orders
        #b = [n for n in neurons if 'bromo-1' in n.id_][0]
        #b.pes()
        #b.partialOrder()

        # XXX cases where a super class was used (e.g. toracic instead of T1-T5)
        # TODO could try to add a subClassOf check if other matches fail? but doesn't resolve the desire for an exact match
        # e.g. bromo-1

        # XXX cases where the partial order split a structure into two parts e.g. proximal and distal stomach but axioms use the parent part
        # e.g. sstom-5

        #reg_missing_orders = [r['missing_orders'] for n, r in recs_reg]
        #rl_missing_orders = [r['missing_orders'] for n, r in recs_rl]
        breakpoint()

    if anatomical_entities:
        location_summary(neurons, anatent_simple)

    if viz:
        synviz(neurons)
        [gviz(n) for n in neurons]

    if chains:
        import json
        chains = npo_to_apinat(neurons)
        #chains = npo_to_apinat([n for n in neurons if 'mmset1/11' in n.id_])
        ok = [c for c in chains['chains'] if c['ok']]
        wl = [c for c in chains['chains'] if [_ for _ in c['levels'] if _]]
        wr = [c for c in chains['chains'] if 'root' in c and c['root']]
        wlr = [c for c in chains['chains'] if 'root' in c and c['root'] and [_ for _ in c['levels'] if _]]
        with open('/tmp/test-npo-apinat-chains.json', 'wt') as f:
            json.dump(chains, f, indent=2)


if __name__ == '__main__':
    main()
