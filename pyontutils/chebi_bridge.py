#!/usr/bin/env python3.5

from lxml import etree
from utils import makePrefixes, makeGraph, createOntology
from scigraph_client import Vocabulary
import rdflib
from IPython import embed

# extract existing chebi classes from NIF-Chemical and NIF-Molecule
# replace identiferis that are in chebi-dead with their new id
# find edges not currently in move to chebi-bridge

# run at commit?

sgv = Vocabulary(cache=True)


def chebi_imp():
    PREFIXES = makePrefixes('definition',
                            'replacedBy',
                            'hasRole',
                            'oboInOwl',
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
    chemgg = makeGraph('NIF-Chemical', graph=chemg)
    a3 = check_chebis(g)

    g.parse('/home/tom/git/NIF-Ontology/ttl/NIF-Molecule.ttl', format='turtle')
    molg.parse('/home/tom/git/NIF-Ontology/ttl/NIF-Molecule.ttl', format='turtle')
    molgg = makeGraph('NIF-Molecule', graph=molg)
    a4 = check_chebis(g)

    replacedBy = ug.expand('replacedBy:')
    deads = {s:o for s, o in cd.subject_objects(replacedBy)}
    def switch_dead(g):
        ng = makeGraph('', graph=g, prefixes=makePrefixes('oboInOwl'))
        for f, r in deads.items():
            ng.replace_uriref(f, r)
            ng.add_node(r, 'oboInOwl:hasAlternateId', rdflib.Literal(f, datatype=rdflib.namespace.XSD.string))
            g.remove((r, replacedBy, r))  # in case the replaced by was already in
    
    switch_dead(g)
    switch_dead(cg)
    switch_dead(chemg)
    switch_dead(molg)

    def fixHasAltId(g):
        ng = makeGraph('', graph=g, prefixes=makePrefixes('oboInOwl', 'NIFCHEM'))
        ng.replace_uriref('NIFCHEM:hasAlternativeId', 'oboInOwl:hasAlternativeId')

    list(map(fixHasAltId, (g, cg, chemg)))

    def fixAltIdIsURIRef(g):
        hai = ug.expand('oboInOwl:hasAlternativeId')
        for s, o in g.subject_objects(hai):
            if type(o) == rdflib.URIRef:
                g.add((s, hai, rdflib.Literal(g.namespace_manager.qname(o), datatype=rdflib.namespace.XSD.string)))
                g.remove((s, hai, o))

    list(map(fixAltIdIsURIRef, (g, cg, chemg)))

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

    cb = createOntology('chebi-bridge',
                        'NIF ChEBI bridge',
                        makePrefixes('CHEBI',
                                     'BFO1SNAP',
                                     'owl',
                                     'skos',
                                     'dc',
                                     'hasRole',
                                     'NIFCHEM',
                                     'oboInOwl',
                                     'NIFMOL',
                                     'OBOANN',
                                     'BIRNANN'),
                        'chebibridge',
                        ('This bridge file contains additional annotations'
                         ' on top of CHEBI identifiers that were originally'
                         ' included in NIF-Chemical or NIF-Molecule that have'
                         ' not since been added to CHEBI upstream'),
                        path='ttl/bridge/',
                        #imports=('https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/master/ttl/generated/chebislim.ttl',
                                 #'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/master/ttl/generated/chebi-dead.ttl'))
                        imports=('http://ontology.neuinfo.org/NIF/ttl/generated/chebislim.ttl',
                                 'http://ontology.neuinfo.org/NIF/ttl/generated/chebi-dead.ttl'))

    out = []
    for set_ in diff:
        for sub, string in sorted(set_):
            for t in g.triples((sub, None, None)):
                # please not that this process will do things like remove hasStreenName ectasy from CHEBI:1391 since chebislim has it listed as a synonym
                py = t[-1].toPython()
                if py == string and not py.startswith('ub'):  # ignore restrictions... this is safe because nifmol and nifchem dont have any restrictions...
                    cb.add_recursive(t, g)
        cb.add_class(sub)  # only need to go at the end because sub is the same for each set


    def hasImplicitSuperclass(s, o):
        for super_ in cg.objects(s, rdflib.RDFS.subClassOf):
            if super_ == o:
                return True
            elif hasImplicitSuperclass(super_, o):
                return True

    # curation decisions after review (see outtc for full list)
    cb.del_trip('CHEBI:6887', 'rdfs:subClassOf', 'CHEBI:23367')  # defer to the chebi choice of chemical substance over molecular entity since it is classified as a racemate which doesn't quite match the mol ent def
    'CHEBI:18248'  # edges currently attached to this wrt Iron (2+) should be on 'CHEBI:29033' (!)



    # review hold over subClassOf statements
    intc = []
    outtc = []
    for s, o in cb.g.subject_objects(rdflib.RDFS.subClassOf):
        if str(o) == 'http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#_birnlex_retired_class':
            # we need to remove any of the cases where deprecation was misused
            cb.g.remove((s, rdflib.RDFS.subClassOf, o))
        elif hasImplicitSuperclass(s, o):
            cb.g.remove((s, rdflib.RDFS.subClassOf, o))
            intc.append((s, rdflib.RDFS.subClassOf, o))
        else:
            outtc.append((s, rdflib.RDFS.subClassOf, o))

    def qname(trips):
        return tuple(tuple(cb.g.namespace_manager.qname(_) for _ in t) for t in trips)

    for a, p, b in sorted(qname(outtc)):
        if 'NIFMOL' in b:
            continue  # not considering cases where NIFMOL/NIFCHEM ids are used, that can come later
        s = sgv.findById(a)
        o = sgv.findById(b)
        print(s['labels'], s['curie'])
        print('subClassOf')
        print(o['labels'], o['curie'])
        print((a, p, b))
        print('---------------------')



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

    cmc = getChebis((((nodt(chemg) - nodt(cb.g)) - nodt(cg)) - nodt(cd)) - nodt(intc))
    cmc = sorted(t for s, o in cmc for t in chemg.triples((s, None, o)))
    mmc = getChebis((((nodt(molg) - nodt(cb.g)) - nodt(cg)) - nodt(cd)) - nodt(intc))
    mmc = sorted(t for s, o in mmc for t in molg.triples((s, None, o)))

    # remove chebi classes from nifchem and nifmol
    def remstuff(sources, targets):
        for source in sources:
            for id_ in source.subjects(rdflib.RDF.type, rdflib.OWL.Class):
                for target in targets:
                    target.del_class(id_)

    remstuff((cg, cd), (chemgg, molgg))


    chemgg.write()
    molgg.write()

    embed()

chebi_imp()
