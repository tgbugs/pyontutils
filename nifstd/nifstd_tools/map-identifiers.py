#!/usr/bin/env python3.7

# equivalent indexed as default
# equivalent indexed in map only

from pyontutils.core import OntGraph
from pyontutils.namespaces import TEMP, ilx, rdf, owl, ilxtr, npokb, OntCuries


def main():
    from pathlib import Path
    from pyontutils.config import auth

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

if __name__ == '__main__':
    main()
