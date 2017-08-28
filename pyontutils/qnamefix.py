#!/usr/bin/env python3
"""
    This file should be run in NIF-Ontology/ttl
    Run at NIF-Ontology 5dd555fcbacf515a475ff1fe47aed06d93cce61e
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
        return f
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
    elif f == 'NIF-Eagle-I-Bridge.ttl':
        prefs.append('IAO')
    elif f == 'resources.ttl':
        prefs.append('IAO')
    elif f == 'NIF-Investigation.ttl':
        prefs.append('IAO')

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
    [ng.add_trip(*n) for n in graph.triples([None]*3)]
    #print(f, len(ng.g))
    ng.write()
    return f

def main():
    with ProcessPoolExecutor(8) as ppe:
        futures = [ppe.submit(convert, f) for f in glob('*/*/*.ttl') + glob('*/*.ttl') + glob('*.ttl')]
        #futures = [ppe.submit(convert, f) for f in glob('generated/parcellation/*.ttl')]
        #futures = [ppe.submit(convert, f) for f in glob('nif.ttl')]
    for f in futures:
        if f.exception():
            print(f)
    #embed()

if __name__ == '__main__':
    main()
