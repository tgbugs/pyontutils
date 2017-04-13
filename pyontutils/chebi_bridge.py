#!/usr/bin/env python3.5

from lxml import etree
from utils import makePrefixes, makeGraph
import rdflib
from IPython import embed

# extract existing chebi classes from NIF-Chemical and NIF-Molecule and move to chebi-bridge
# run at commit?

def chebi_imp():
    PREFIXES = makePrefixes('definition',
                            'hasRole',
                            'CHEBI',
                            'owl',
                            'skos',
                            'oboInOwl')
    ug = makeGraph('utilgraph', prefixes=PREFIXES)
    with open('chebi-subset-ids.txt', 'rt') as f:
        ids_raw = set((_.strip() for _ in f.readlines()))
        ids = sorted(set((ug.expand(_.strip()) for _ in ids_raw)))

    def check_chebis(g):
        a = []
        for id_ in ids:
            l = sorted(g.triples((id_, None, None)))
            ll = len(l)
            a.append(ll)
        return a

    g = rdflib.Graph()
    cg = rdflib.Graph()
    chemg = rdflib.Graph()
    molg = rdflib.Graph()
    g.parse('/home/tom/git/NIF-Ontology/ttl/generated/chebislim.ttl', format='turtle')
    cg.parse('/home/tom/git/NIF-Ontology/ttl/generated/chebislim.ttl', format='turtle')
    a1 = check_chebis(g)
    g.parse('/home/tom/git/NIF-Ontology/ttl/generated/chebi-dead.ttl', format='turtle')
    a2 = check_chebis(g)
    g.parse('/home/tom/git/NIF-Ontology/ttl/NIF-Chemical.ttl', format='turtle')
    chemg.parse('/home/tom/git/NIF-Ontology/ttl/NIF-Chemical.ttl', format='turtle')
    a3 = check_chebis(g)
    g.parse('/home/tom/git/NIF-Ontology/ttl/NIF-Molecule.ttl', format='turtle')
    molg.parse('/home/tom/git/NIF-Ontology/ttl/NIF-Molecule.ttl', format='turtle')
    a4 = check_chebis(g)
    matches = [_ for _ in zip(a1, a2, a3, a4)]
    changed = [len(set(_)) != 1 for _ in matches] 
    review = [(id_, m) for id_, changed, m in zip(ids, changed, matches) if changed and m[0]]
    # for reasons currently lost to implementation details this returns a list of empty lists if run from ipython
    wat_c = [set([(s, str(o.toPython())) for s, p, o in cg.triples((u, None, None))]) for u, _ in review]
    wat_a = [set([(s, str(o.toPython())) for s, p, o in g.triples((u, None, None))]) for u, _ in review]
    wat_c_ = [set(cg.triples((u, None, None))) for u, _ in review]  # for reasons currently lost to implementation details this returns a list of empty lists if run from ipython
    wat_a_ = [set(g.triples((u, None, None))) for u, _ in review]  # for reasons currently lost to implementation details this returns a list of empty lists if run from ipython
    diff = [a - c for a, c in zip(wat_a, wat_c)]
    diff_ = [a - c for a, c in zip(wat_a_, wat_c_)]

    cb = makeGraph('chebi-bridge', makePrefixes('CHEBI',
                                                'owl',
                                                'skos',
                                                'dc',
                                                'hasRole',
                                                'NIFCHEM',
                                                'NIFMOL',
                                                'OBOANN',
                                                'BIRNANN'))
    out = []
    for set_ in diff:
        for sub, string in sorted(set_):
            for t in g.triples((sub, None, None)):
                py = t[-1].toPython()
                if py == string and not py.startswith('ub'):  # ignore restrictions... this is safe because nifmol and nifchem dont have any restrictions...
                    cb.add_recursive(t, g)
        cb.add_class(sub)  # only need to go at the end because sub is the same for each set

    cb.write()  # re-add only the missing edges so that we can zap them from NIF-Molecule and NIF-Chemical (recurse is needed...)
    embed()

chebi_imp()
