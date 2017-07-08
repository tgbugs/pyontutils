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
    with open('resources/chebi-subset-ids.txt', 'rt') as f:
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
    cd = rdflib.Graph()
    chemg = rdflib.Graph()
    molg = rdflib.Graph()
    g.parse('/home/tom/git/NIF-Ontology/ttl/generated/chebislim.ttl', format='turtle')
    cg.parse('/home/tom/git/NIF-Ontology/ttl/generated/chebislim.ttl', format='turtle')
    a1 = check_chebis(g)
    g.parse('/home/tom/git/NIF-Ontology/ttl/generated/chebi-dead.ttl', format='turtle')
    cd.parse('/home/tom/git/NIF-Ontology/ttl/generated/chebi-dead.ttl', format='turtle')
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
                # please not that this process will do things like remove hasStreenName ectasy from CHEBI:1391 since chebislim has it listed as a synonym
                py = t[-1].toPython()
                if py == string and not py.startswith('ub'):  # ignore restrictions... this is safe because nifmol and nifchem dont have any restrictions...
                    cb.add_recursive(t, g)
        cb.add_class(sub)  # only need to go at the end because sub is the same for each set

    cb.write()  # re-add only the missing edges so that we can zap them from NIF-Molecule and NIF-Chemical (recurse is needed...)

    # validation
    diff2 = set(cb.g) - set(cg)
    diff3 = set(cb.g) - diff2  # should just be all the owl:Class entries
    diff4 = set(cb.g) - set(chemg) | set(cb.g) - set(molg)  # not informative
    diff5 = set(cb.g) - diff4  # not informative
    both = set(chemg) & set(molg)  # there is no overlap beyond the owl:Class declarations

    def getChebis(set_):
        return set(t for t in set_ if 'CHEBI_' in t[0])

    def nodt(graph):
        return set((s, str(o) if type(o) is rdflib.Literal else o) for s, p, o in graph)

    cmc = getChebis(((nodt(chemg) - nodt(cb.g)) - nodt(cg)) - nodt(cd))
    cmc = sorted(t for s, o in cmc for t in chemg.triples((s, None, o)))
    mmc = getChebis(((nodt(molg) - nodt(cb.g)) - nodt(cg)) - nodt(cd))
    mmc = sorted(t for s, o in mmc for t in molg.triples((s, None, o)))

    def qname(trips):
        return tuple(tuple(cb.g.namespace_manager.qname(_) for _ in t) for t in trips)

    # TODO deal with edges on dead classes and all the subclassing madness that ensues

    embed()

chebi_imp()
