#!/usr/bin/env python3
"""
    This file should be run in NIF-Ontology/ttl
    Run at NIF-Ontology 0f1f95c25cc46b8953f115705031919485cfc42f
"""

import os
from glob import glob
import rdflib
from pyontutils.utils import makePrefixes, PREFIXES, makeGraph
from pyontutils.process_fixed import ProcessPoolExecutor
from IPython import embed

PREFIXES.pop('OIO')  # prefer oboInOwl

exclude = 'generated/swanson_hierarchies.ttl',

def convert(f):
    if f in exclude:
        print('skipping', f)
        return 
    ps = {'PROTEGE':'http://protege.stanford.edu/plugins/owl/protege#', }
    PREFIXES.update(ps)
    pi = {v:k for k, v in PREFIXES.items()}
    pi.pop(None)

    graph = rdflib.Graph()
    graph.parse(f, format='turtle')
    namespaces = [str(n) for p, n in graph.namespaces()]
    prefs = []

    if f == 'NIF-Dysfunction.ttl':
        prefs.append('OBO')


    asdf = {v:k for k, v in ps.items()}
    asdf.update(pi)

    # determine which prefixes we need
    for rn, rp in asdf.items():
        for uri in list(graph.subjects()) + list(graph.predicates()) + list(graph.objects()):
            if type(uri) == rdflib.BNode:
                continue
            elif uri.startswith(rn):
                if rp == 'OBO' or rp == 'IAO' or rp == 'NIFTTL':
                    if rp == 'IAO' and 'IAO_0000412' in uri:  # for sequence_slim
                        pass
                    else:
                        continue
                prefs.append(rp)
                break

    if prefs:
        ps = makePrefixes(*prefs)
    else:
        ps = makePrefixes('rdfs')

    if 'parcellation/' in f:
        nsl = {p:n for p, n in graph.namespaces()}
        if '' in nsl:
            ps[''] = nsl['']
        elif 'hbaslim' in f:
            ps['HBA'] = nsl['HBA']
        elif 'mbaslim' in f:
            ps['MBA'] = nsl['MBA']
        elif 'cocomac' in f:
            ps['cocomac'] = nsl['cocomac']

    ng = makeGraph(os.path.splitext(f)[0], prefixes=ps, writeloc=os.path.expanduser('~/git/NIF-Ontology/ttl/'))
    [ng.add_node(*n) for n in graph.triples([None]*3)]
    #print(f, len(ng.g))
    ng.write()

def main():
    with ProcessPoolExecutor(8) as ppe:
        futures = [ppe.submit(convert, f) for f in glob('*/*/*.ttl') + glob('*/*.ttl') + glob('*.ttl')]
        #futures = [ppe.submit(convert, f) for f in glob('generated/parcellation/*.ttl')]
    embed()

if __name__ == '__main__':
    main()
