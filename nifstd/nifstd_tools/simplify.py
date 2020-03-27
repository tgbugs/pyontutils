from copy import deepcopy
from pprint import pformat
import rdflib
import networkx as nx
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


def simplify(path, blob):
    if 'housing-lyphs' in path or 'bundles' in path or 'soma-processes' in path:
        collapse = [
            # apparently annotates breaks this for some reason?
            #['apinatomy:annotates', 'apinatomy:conveys', 'apinatomy:source', 'apinatomy:sourceOf'],
            #['apinatomy:annotates', 'apinatomy:conveys', 'apinatomy:target', 'apinatomy:sourceOf'],
            #['apinatomy:conveys', 'apinatomy:source', 'apinatomy:sourceOf'],
            #['apinatomy:conveys', 'apinatomy:target', 'apinatomy:sourceOf'],  # FIXME apparently the 2nd round here fails ?!?!

            ['apinatomy:conveys', 'apinatomy:source'],
            ['apinatomy:conveys', 'apinatomy:target'],

            ['apinatomy:fasciculatesIn', 'apinatomy:external'],

            # FIXME should this be showing up in the query results at all?
            ['apinatomy:fasciculatesIn', 'apinatomy:supertype', 'apinatomy:external'],

            # why are some of these missing external but in the graph ?!? the answer is that the previous coll was missing
            # FIXME sub collapses happen simultaneously so those edges will still be added and you will get doubling
            #['apinatomy:fasciculatesIn', 'apinatomy:cloneOf', 'apinatomy:supertype'],
            ['apinatomy:fasciculatesIn', 'apinatomy:layerIn', 'apinatomy:external'],

            # can't include next it destroys this due to inducing everything to be weakly connected (urg)
            # since next is the linker along the tree we definitely cannot collapse that
            ['apinatomy:fasciculatesIn', 'apinatomy:cloneOf', 'apinatomy:supertype', 'apinatomy:external'],

            ['<skip1'],
            ['skip1>', 'end'],
            ['skip2>', 'end'],
            ['skip3>', 'skip4>', 'end'],

            #['apinatomy:root', 'apinatomy:internalIn', 'apinatomy:cloneOf', 'apinatomy:supertype'],
            #['apinatomy:supertype', 'apinatomy:cloneOf', 'apinatomy:internalIn', 'apinatomy:root'],
        ]

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
                        oe2 = [Edge.fromNx(e) for e in ordered_edges]
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
