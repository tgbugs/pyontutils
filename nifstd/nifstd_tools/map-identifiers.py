#!/usr/bin/env python3.7
"""map ids
Usage:
    map-identifiers [options] [methods npokb]

Options:
    -h --help    print this
"""

# equivalent indexed as default
# equivalent indexed in map only

import augpathlib as aug
from pyontutils import clifun as clif
from pyontutils.core import OntGraph, OntResGit
from pyontutils.namespaces import TEMP, ilx, rdf, owl, ilxtr, npokb, OntCuries
from pyontutils.config import auth


def npokb_mapping():
    index_graph = OntGraph(path=auth.get_path('ontology-local-repo') /
                           'ttl/generated/neurons/npokb-index.ttl')

    if index_graph.path.exists():
        index_graph.parse()

    # testing
    index_graph.bind('npokb', npokb)
    #[index_graph.add((npokb[str(i)], rdf.type, owl.Class)) for i in range(1, 11)]
    #[index_graph.add((npokb[str(i)], ilxtr.hasTemporaryId, TEMP[str(i)])) for i in range(1, 11)]

    ios = []
    for eff in ('cut-release-final',
                #'common-usage-types',  # excluded due to modelling changes
                'huang-2017',
                'markram-2015',
                'allen-cell-types'):
        path = auth.get_path('ontology-local-repo') / f'ttl/generated/neurons/{eff}.ttl'
        input_graph = OntGraph(path=path)
        input_graph.parse()
        output_graph = input_graph.mapTempToIndex(index_graph, npokb, TEMP)
        ios.append((input_graph, output_graph))

    input_graph, output_graph = ios[0]
    a, r, c = output_graph.subjectsChanged(input_graph)
    index_graph.write()
    [o.write() for i, o, in ios]  # when ready
    #from sparcur.paths import Path
    #Path(index_graph.path).xopen()
    breakpoint()


olr = aug.RepoPath(auth.get_path('ontology-local-repo'))
ttl = olr / 'ttl'
methods = ttl / 'methods.ttl'
helper = ttl / 'methods-helper.ttl'
core =  ttl / 'methods-core.ttl'


def methods_mapping():
    from pyontutils.namespaces import TEMP, ilxtr, tech
    from nifstd_tools import methods as m
    import rdflib

    # TODO add this to ibnode tests
    _before = OntResGit(methods, ref='8c30706cbc7ccc7443685a34dec026e8afbbedd1')
    after = OntResGit(methods, ref='860c88a574d17e0d427c1101fa1947b730b613a9')  # renaming commit
    before = OntResGit(after.path, ref=after.ref + '~1')
    assert before.graph.identity() == _before.graph.identity()

    bg = before.graph
    ag = after.graph
    _, local = next(ag[:ilxtr.indexNamespace:])
    local = rdflib.Namespace(str(local))
    T0 = TEMP['0']
    l0 = local['0']
    b = OntGraph().populate_from_triples(bg.subjectGraph(T0))
    a = OntGraph().populate_from_triples(ag.subjectGraph(l0))
    b.debug()
    a.debug()
    it = b.subjectIdentity(T0)
    il = a.subjectIdentity(l0)
    assert it == il
    assert it in (il,)
    assert il in (it,)  # (it,) ni il  # SIGH
    assert it in {il:None}
    assert il in {it:None}
    r = b.subjectsRenamed(a)
    renamed = before.graph.subjectsRenamed(after.graph)
    assert (len(renamed) -1 ==
            max([int(v.rsplit('/', 1)[-1])
                 for v in renamed.values()
                 if v != ilxtr.Something]))

    (OntGraph(namespace_manager=after.graph.namespace_manager)
     .populate_from_triples(before
                            .graph
                            .subjectsRenamedTriples(after.graph))
     .debug())
    return renamed

    index_graph = OntGraph(path=olr / 'ttl/generated/index-methods.ttl')
    # FIXME either use or record for posterity the commits where these
    # transformations were run rather than pointing to the branch name
    with org.repo.getRef('methods'):
        input_graph = org.graph
        output_graph = input_graph.mapTempToIndex(index_graph, TEMP, m.local)
        a, r, c = output_graph.subjectsChanged(input_graph)
        index_graph.write()


def methods_sneech():
    # TODO the sneech files ?
    org_m = OntResGit(methods)
    org_h = OntResGit(helper)
    org_c = OntResGit(core)

    with org.repo.getRef('methods'):
        pass


def main():
    options, args, defaults = clif.Options.setup(__doc__)
    if options.npokb:
        npokb_mapping()
    elif options.methods:
        methods_mapping()


if __name__ == '__main__':
    main()
