#!/usr/bin/env python3.7

# equivalent indexed as default
# equivalent indexed in map only

import augpathlib as aug
from pyontutils.core import OntGraph, OntResGit
from pyontutils.namespaces import TEMP, ilx, rdf, owl, ilxtr, npokb, OntCuries
from pyontutils.config import auth


def npokb():
    index_graph = OntGraph(path=auth.get_path('ontology-local-repo') /
                           'ttl/generated/neurons/npokb-index.ttl')

    if index_graph.path.exists():
        index_graph.parse()

    # testing
    index_graph.bind('npokb', npokb)
    #[index_graph.add((npokb[str(i)], rdf.type, owl.Class)) for i in range(1, 11)]
    #[index_graph.add((npokb[str(i)], ilxtr.hasTemporaryId, TEMP[str(i)])) for i in range(1, 11)]

    ios = []
    for eff in ('common-usage-types', 'huang-2017', 'markram-2015', 'allen-cell-types'):
        path = auth.get_path('ontology-local-repo') / f'ttl/generated/neurons/{eff}.ttl'
        input_graph = OntGraph(path=path)
        input_graph.parse()
        output_graph = input_graph.mapTempToIndex(index_graph, npokb, TEMP)
        ios.append((input_graph, output_graph))

    input_graph, output_graph = ios[0]
    a, r, c = output_graph.subjectsChanged(input_graph)
    index_graph.write()
    # [o.write() for i, o, in ios]  # when ready
    #from sparcur.paths import Path
    #Path(index_graph.path).xopen()
    breakpoint()


olr = aug.RepoPath(auth.get_path('ontology-local-repo'))
ttl = olr / 'ttl'
methods = ttl / 'methods.ttl'
helper = ttl / 'methods-helper.ttl'
core =  ttl / 'methods-core.ttl'


def methods():
    from pyontutils.namespaces import TEMP, ilxtr, tech
    from . import methods

    org = OntResGit(methods)

    index_graph = OntGraph(path=olr / 'ttl/generated/index-methods.ttl')

    # FIXME either use or record for posterity the commits where these
    # transformations were run rather than pointing to the branch name
    with org.repo.getRef('methods'):
        input_graph = org.graph
        output_graph = input_graph.mapTempToIndex(index_graph, TEMP, methods.local)
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
    #npokb()
    methods()


if __name__ == '__main__':
    main()
