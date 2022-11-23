from copy import deepcopy
from pprint import pformat
import rdflib
import networkx as nx  # FIXME probably break this out into its own project to avoid scipy dep for deployment
from rdflib.extras import external_graph_libs as egl
from pyontutils.core import OntGraph, Edge
from pyontutils.utils import listIn, makeSimpleLogger

log = makeSimpleLogger('simplify')  # FIXME nifstd-tools might need its own hierarchy?


def cleanBad(json):
    deep = deepcopy(json)
    bads = 'fma:continuous_with',
    edges = deep['edges']
    putative_bads = [e for e in edges if e['pred'] in bads]
    skip = []
    for e in tuple(putative_bads):
        if e not in skip:
            rev = {'sub': e['obj'], 'pred': e['pred'], 'obj':e['sub'], 'meta': e['meta']}
            if rev in putative_bads:
                skip.append(rev)
                edges.remove(e)

    remed = []
    for e in skip:
        for ae in tuple(edges):
            if ae not in remed and ae != e:
                if (
                        e['sub'] == ae['sub'] or
                        e['obj'] == ae['obj'] or
                        e['obj'] == ae['sub'] or
                        e['sub'] == ae['obj']
                ):
                    # there is already another edge that pulls in one of the
                    # members of this edge so discard the bad edge
                    edges.remove(e)
                    remed.append(e)
                    break

    log.debug(len(edges))
    log.debug(len(json['edges']))
    return deep


def zap(ordered_nodes, predicates, oe2, blob):
    """ don't actually zap, wait until the end so that all
        deletions happen after all additions """

    e = Edge((ordered_nodes[0].toPython(),
            '-'.join(predicates),
            ordered_nodes[-1].toPython()))
    new_e = e.asOboGraph()
    blob['edges'].append(new_e)
    to_remove = [e.asOboGraph() for e in oe2]
    return to_remove


def simplify(collapse, blob):
    to_remove = []
    for coll in collapse:
        exclude = set(p for p in coll)
        candidates = [e for e in blob['edges'] if e['pred'] in exclude]
        for c in candidates:
            # make sure we can remove the edges later
            # if they have meta the match will fail
            if 'meta' in c:
                c.pop('meta')

        if candidates:
            edges = [Edge.fromOboGraph(c) for c in candidates]
            g = OntGraph().populate_from_triples(e.asRdf() for e in edges)
            nxg = egl.rdflib_to_networkx_multidigraph(g)
            connected = list(nx.weakly_connected_components(nxg))  # FIXME may not be minimal
            ends = [e.asRdf()[-1] for e in edges if e.p == coll[-1]]
            for c in connected:
                #log.debug('\n' + pformat(c))
                nxgt = nx.MultiDiGraph()
                nxgt.add_edges_from(nxg.edges(c, keys=True))
                ordered_nodes = list(nx.topological_sort(nxgt))
                paths = [p
                         for n in nxgt.nodes()
                         for e in ends
                         for p in list(nx.all_simple_paths(nxgt, n, e))
                         if len(p) == len(coll) + 1]

                for path in sorted(paths):
                    ordered_edges = nxgt.edges(path, keys=True)
                    oe2 = [Edge.fromNx(e) for e in ordered_edges if all([n in path for n in e[:2]])]
                    predicates = [e.p for e in oe2]
                    #log.debug('\n' + pformat(oe2))
                    if predicates == coll: #in collapse:
                        to_remove.extend(zap(path, predicates, oe2, blob))
                    else:  # have to retain this branch to handle cases where the end predicate is duplicated
                        log.error('\n' + pformat(predicates) +
                                    '\n' + pformat(coll))
                        for preds in [coll]:
                            sublist_start = listIn(predicates, preds)
                            if sublist_start is not None:
                                i = sublist_start
                                j = i + len(preds)
                                npath = path[i:j + 1]  # + 1 to include final node
                                oe2 = oe2[i:j]
                                predicates = predicates[i:j]
                                to_remove.extend(zap(npath, predicates, oe2, blob))

    for r in to_remove:
        if r in blob['edges']:
            blob['edges'].remove(r)

    #log.debug('\n' + pformat(blob['edges']))
    return blob  # note that this is in place modification so sort of supruflous


# apinatomy helpers

axon = 'SAO:280355188'
dend = 'SAO:420754792'
bag = 'apinatomy:BAG'
top = 'apinatomy:topology*'
ie = 'apinatomy:inheritedExternal'
ies = 'apinatomy:inheritedExternal*'
iot = 'apinatomy:inheritedOntologyTerms'
iots = 'apinatomy:inheritedOntologyTerms*'
ext = 'apinatomy:external'
fasIn = 'apinatomy:fasciculatesIn'
endIn = 'apinatomy:endsIn'
layerIn = 'apinatomy:layerIn'
onts = 'apinatomy:ontologyTerms'


def apinat_deblob(blob, remove_converge=False, ontology_terms_predicate=onts):
    # FIXME I think we may be over or under simplifying just a bit
    # somehow getting double links at the end of the chain

    # FIXME issue here is that chain roots -> levels goes to all levels of the chain which is NOT
    # what we want, TODO need to filter out cases where the target of levels is pointed to by next
    # this is implemented downstream from here I think
    blob['edges'] = [
        e for e in blob['edges'] if not pred(e, 'apinatomy:levels') or
        (pred(e, 'apinatomy:levels') and
         not ematch(blob, (lambda ei, m: obj(ei, m) and pred(ei, 'apinatomy:next')), obj(e)))]

    #[e for e in blob['edges'] if pred(e, 'apinatomy:rootOf')]

    blob = simplify([['apinatomy:target', 'apinatomy:rootOf', 'apinatomy:levels'],
                     ['apinatomy:conveyingLyph', 'apinatomy:topology'],
                     ['apinatomy:conveys', 'apinatomy:source', 'apinatomy:sourceOf'],
                     ['apinatomy:conveys', 'apinatomy:target', 'apinatomy:sourceOf'],
                     ['apinatomy:cloneOf', 'apinatomy:inheritedOntologyTerms'],
                     ['apinatomy:conveyingLyph', 'apinatomy:inheritedOntologyTerms'],], blob)
    edges = blob['edges']
    nindex = {n['id']:n for n in blob['nodes']}  # FIXME silent errors ;_;
    for e in edges:
        if e['pred'] == 'apinatomy:nextChainStartLevels':
            e['pred'] = 'apinatomy:next'
        if e['pred'] in (
                'apinatomy:target-apinatomy:rootOf-apinatomy:levels',
                'apinatomy:conveys-apinatomy:source-apinatomy:sourceOf',
                'apinatomy:conveys-apinatomy:target-apinatomy:sourceOf',):
            e['pred'] = 'apinatomy:next*'
        if e['pred'] == 'apinatomy:conveyingLyph-apinatomy:topology':
            e['pred'] = 'apinatomy:topology*'
        if e['pred'] in (
                'apinatomy:conveyingLyph-apinatomy:inheritedOntologyTerms',
                'apinatomy:cloneOf-apinatomy:inheritedOntologyTerms',):
            e['pred'] = 'apinatomy:inheritedOntologyTerms*'
        if pred(e, top):
            # move topology to be a property not a node to make the layout cleaner
            nindex[sub(e)]['topology'] = obj(e)

    if remove_converge:
        # remove topology edges
        edges = blob['edges'] = [e for e in edges if not pred(e, top)]
        # remove process type edges
        edges = blob['edges'] = [e for e in edges if not (obj(e, axon) or obj(e, dend))]

    blob['edges'] = [dict(s) for s in set(frozenset({k:v for k, v in d.items()
                                                     if k != 'meta'}.items()) for d in blob['edges'])]

    def sekey(e):
        p = pred(e)
        iot = p != ontology_terms_predicate
        return iot, p, sub(e), obj(e)

    blob['edges'] = sorted(blob['edges'], key=sekey)
    sos = set(sov for e in blob['edges'] for sov in (e['sub'], e['obj']))
    blob['nodes'] = [n for n in blob['nodes'] if n['id'] in sos]
    somas = [e for e in edges if e['pred'] == 'apinatomy:internalIn']
    externals = [e for e in edges if e['pred'] == ontology_terms_predicate]
    ordering_edges = [e for e in edges if e['pred'] == 'apinatomy:next']
    return blob, edges, somas, externals, ordering_edges


def sub(e, match=None):
    return e['sub'] == match if match is not None else e['sub']


def pred(e, match=None):
    return e['pred'] == match if match is not None else e['pred']


def obj(e, match=None):
    return e['obj'] == match if match is not None else e['obj']


def ematch(blob, select, match, *matches, matchf=lambda ms: True):
    return [e for e in blob['edges'] if select(e, match) and matchf(matches)]
