#!/usr/bin/env python3.7

import rdflib
from pathlib import Path
from lxml import etree
from pyontutils.core import makeGraph, createOntology, OntGraph
from pyontutils.config import auth
from pyontutils.scigraph import Vocabulary
from pyontutils.namespaces import makePrefixes
try:
    breakpoint
except NameError:
    from IPython import embed

# extract existing chebi classes from NIF-Chemical and NIF-Molecule
# replace identiferis that are in chebi-dead with their new id
# find edges not currently in move to chebi-bridge

# run at commit 5f02b1c5d6bd90401c386ea23f08b29cbf8f6262

sgv = Vocabulary(cache=True)


def main():
    olr = auth.get_path('ontology-local-repo')
    resources = auth.get_path('resources')
    if not olr.exists():
        raise FileNotFoundError(f'{olr} does not exist cannot continue')
    if not resources.exists():
        raise FileNotFoundError(f'{resources} does not exist cannot continue')

    PREFIXES = makePrefixes('definition',
                            'replacedBy',
                            'hasRole',
                            'oboInOwl',
                            'CHEBI',
                            'owl',
                            'skos',
                            'oboInOwl')
    ug = makeGraph('utilgraph', prefixes=PREFIXES)
    file = resources / 'chebi-subset-ids.txt'
    with open(file.as_posix(), 'rt') as f:
        ids_raw = set((_.strip() for _ in f.readlines()))
        ids = sorted(set((ug.expand(_.strip()) for _ in ids_raw)))

    def check_chebis(g):
        a = []
        for id_ in ids:
            l = sorted(g.triples((id_, None, None)))
            ll = len(l)
            a.append(ll)
        return a

    def fixIons(g):
        # there are a series of atom/ion confusions that shall be dealt with, solution is to add 'iron' as a synonym to the charged form since that is what the biologists are usually referring to...
        ng = makeGraph('', graph=g, prefixes=makePrefixes('CHEBI'))
        # atom           ion
        None, 'CHEBI:29108'  # calcium is ok
        ng.replace_uriref('CHEBI:30145', 'CHEBI:49713')  # lithium
        ng.replace_uriref('CHEBI:18248', 'CHEBI:29033')  # iron
        ng.replace_uriref('CHEBI:26216', 'CHEBI:29103')  # potassium
        ng.replace_uriref('CHEBI:26708', 'CHEBI:29101')  # sodium
        None, 'CHEBI:29105'  # zinc is ok


    g = OntGraph()
    cg = OntGraph()
    cd = OntGraph()
    chemg = OntGraph()
    molg = OntGraph()

    cg.parse(olr / 'ttl/generated/chebislim.ttl', format='turtle')
    list(g.add(t) for t in cg)
    a1 = check_chebis(g)

    cd.parse(olr / 'ttl/generated/chebi-dead.ttl', format='turtle')
    list(g.add(t) for t in cd)
    a2 = check_chebis(g)

    chemg.parse(olr / 'ttl/NIF-Chemical.ttl', format='turtle')
    chemgg = makeGraph('NIF-Chemical', graph=chemg)
    fixIons(chemg)
    list(g.add(t) for t in chemg)
    a3 = check_chebis(g)

    molg.parse(olr / 'ttl/NIF-Molecule.ttl', format='turtle')
    molgg = makeGraph('NIF-Molecule', graph=molg)
    fixIons(molg)
    list(g.add(t) for t in molg)
    a4 = check_chebis(g)

    replacedBy = ug.expand('replacedBy:')
    deads = {s:o for s, o in cd.subject_objects(replacedBy)}
    def switch_dead(g):
        ng = makeGraph('', graph=g, prefixes=makePrefixes('oboInOwl'))
        for f, r in deads.items():
            ng.replace_uriref(f, r)
            ng.add_trip(r, 'oboInOwl:hasAlternateId', rdflib.Literal(f, datatype=rdflib.XSD.string))
            g.remove((r, replacedBy, r))  # in case the replaced by was already in

    switch_dead(g)
    switch_dead(cg)
    switch_dead(chemg)
    switch_dead(molg)

    def fixHasAltId(g):
        ng = makeGraph('', graph=g, prefixes=makePrefixes('oboInOwl', 'NIFCHEM', 'NIFRID'))
        ng.replace_uriref('NIFCHEM:hasAlternativeId', 'oboInOwl:hasAlternativeId')
        # ng.replace_uriref('NIFRID:ChEBIid', 'oboInOwl:id')  # :id does not exist, do we need an alternative?

    list(map(fixHasAltId, (g, cg, chemg)))

    def fixAltIdIsURIRef(g):
        hai = ug.expand('oboInOwl:hasAlternativeId')
        # i = ug.expand('oboInOwl:id')  # :id does not exist
        makeGraph('', graph=g, prefixes=makePrefixes('CHEBI'))  # amazlingly sometimes this is missing...

        def inner(s, p, o):
            if type(o) == rdflib.URIRef:
                qn = g.namespace_manager.qname(o)
                g.add((s, p, rdflib.Literal(qn, datatype=rdflib.XSD.string)))
                if 'ns' in qn:
                    print('WARNING UNKNOWN NAMESPACE BEING SHORTENED', str(o), qn)
                g.remove((s, p, o))

        for s, o in g.subject_objects(hai):
            inner(s, hai, o)
        #for s, o in g.subject_objects(i):  # :id does not exist
            #inner(s, i, o)

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
                                     'NIFRID'),
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
    curatedOut = []
    def curateOut(*t):
        curatedOut.append(tuple(ug.expand(_) if type(_) is not rdflib.Literal else _ for _ in t))
        cb.del_trip(*t)

    curateOut('CHEBI:6887', 'rdfs:subClassOf', 'CHEBI:23367')  # defer to the chebi choice of chemical substance over molecular entity since it is classified as a racemate which doesn't quite match the mol ent def
    curateOut('CHEBI:26519', 'rdfs:subClassOf', 'CHEBI:24870')  # some ions may also be free radicals, but all free radicals are not ions!
    #natural product removal since natural product should probably be a role if anything...
    curateOut('CHEBI:18059', 'rdfs:subClassOf', 'CHEBI:33243')
    curateOut('CHEBI:24921', 'rdfs:subClassOf', 'CHEBI:33243')
    curateOut('CHEBI:37332', 'rdfs:subClassOf', 'CHEBI:33243')

    curateOut('CHEBI:50906', 'rdfs:label', rdflib.Literal('Chemical role', datatype=rdflib.XSD.string))  # chebi already has a chemical role...
    curateOut('CHEBI:22586', 'rdfs:subClassOf', 'CHEBI:24432')  # antioxidant is already modelled as a chemical role instead of a biological role, the distinction is that the biological roles affect biological processes/property, not chemical processes/property
    curateOut('CHEBI:22720', 'rdfs:subClassOf', 'CHEBI:27171')  # not all children are bicyclic
    curateOut('CHEBI:23447', 'rdfs:subClassOf', 'CHEBI:17188')  # this one seems obviously flase... all cyclic nucleotides are not nucleoside 5'-monophosphate...
    curateOut('CHEBI:24922', 'rdfs:subClassOf', 'CHEBI:27171')  # not all children are bicyclic, some may be poly, therefore removing
    curateOut('CHEBI:48706', 'rdfs:subClassOf', 'CHEBI:33232')  # removing since antagonist is more incidental and pharmacological role is more appropriate (as chebi has it)
    curateOut('CHEBI:51064', 'rdfs:subClassOf', 'CHEBI:35338')  # removing since chebi models this with has part
    curateOut('CHEBI:8247', 'rdfs:subClassOf', 'CHEBI:22720')  # the structure is 'fused to' a benzo, but it is not a benzo, chebi has the correct
    #curateOut('CHEBI:9463', 'rdfs:subClassOf', 'CHEBI:50786')  # not sure what to make of this wikipedia says one thing, but chebi says another, very strange... not an anabolic agent?!??! wat no idea

    # review hold over subClassOf statements
    intc = []
    outtc = []
    for s, o in cb.g.subject_objects(rdflib.RDFS.subClassOf):
        if str(o) == 'http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#_birnlex_retired_class' or str(o) == 'http://ontology.neuinfo.org/nif/nifstd/readable/birnlexRetiredClass':
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
        if s is None or o is None:
            print(a, '=>', s)
            print(b, '=>', o)
        else:
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

    cmc = getChebis(((((nodt(chemg) - nodt(cb.g)) - nodt(cg)) - nodt(cd)) - nodt(intc)) - nodt(curatedOut))
    cmc = sorted(t for s, o in cmc for t in chemg.triples((s, None, o)))
    mmc = getChebis(((((nodt(molg) - nodt(cb.g)) - nodt(cg)) - nodt(cd)) - nodt(intc)) - nodt(curatedOut))
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

    if __name__ == '__main__':
        breakpoint()

if __name__ == '__main__':
    main()
