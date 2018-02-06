#!/usr/bin/env python3.6
"""
    Build lightweight slims from curie lists.
    Used for sources that don't have an owl ontology floating.
"""
#TODO consider using some of the code from scr_sync.py???

import gzip
import json
from io import BytesIO
from datetime import date
import rdflib
from rdflib.extras import infixowl
import requests
from utils import makePrefixes, makeGraph, createOntology, rdf, rdfs, owl, oboInOwl
from utils import chunk_list, dictParse, memoryCheck
from ilx_utils import ILXREPLACE
from IPython import embed
from lxml import etree

memoryCheck(7300000000)

#ncbi_map = {
    #'name':,
    #'description':,
    #'uid':,
    #'organism':{''},
    #'otheraliases':,
    #'otherdesignations':,
#}

class ncbi(dictParse):
    superclass = ILXREPLACE('ilx_gene_concept')
    def __init__(self, thing, graph):
        self.g = graph
        super().__init__(thing, order=['uid'])

    def name(self, value):
        self.g.add_trip(self.identifier, rdfs.label, value)

    def description(self, value):
        #if value:
        self.g.add_trip(self.identifier, 'skos:prefLabel', value)

    def uid(self, value):
        self.identifier = 'NCBIGene:' + str(value)
        self.g.add_trip(self.identifier, rdf.type, owl.Class)
        self.g.add_trip(self.identifier, rdfs.subClassOf, self.superclass)

    def organism(self, value):
        self._next_dict(value)

    def taxid(self, value):
        tax = 'NCBITaxon:' + str(value)
        self.g.add_trip(self.identifier, 'ilx:definedForTaxon', tax)  # FIXME species or taxon???

    def otheraliases(self, value):
        if value:
            for synonym in value.split(','):
                self.g.add_trip(self.identifier, 'NIFRID:synonym', synonym.strip())

    def otherdesignations(self, value):
        if value:
            for synonym in value.split('|'):
                self.g.add_trip(self.identifier, 'NIFRID:synonym', synonym)

def ncbigene_make():
    IDS_FILE = 'resources/gene-subset-ids.txt'
    with open(IDS_FILE, 'rt') as f:  # this came from neuroNER
        ids = [l.split(':')[1].strip() for l in f.readlines()]
    
    #url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?retmode=json&retmax=5000&db=gene&id='
    #for id_ in ids:
        #data = requests.get(url + id_).json()['result'][id_]
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
    data = {
        'db':'gene',
        'retmode':'json',
        'retmax':5000,
        'id':None,
    }
    chunks = []
    for i, idset in enumerate(chunk_list(ids, 100)):
        print(i, len(idset))
        data['id'] = ','.join(idset),
        resp = requests.post(url, data=data).json()
        chunks.append(resp)
    
    base = chunks[0]['result']
    uids = base['uids']
    for more in chunks[1:]:
        data = more['result']
        uids.extend(data['uids'])
        base.update(data)
    #base['uids'] = uids  # i mean... its just the keys
    base.pop('uids')
 
    ng = createOntology('ncbigeneslim',
                        'NIF NCBI Gene subset',
                        makePrefixes('', 'ILXREPLACE', 'ilx', 'NIFRID', 'NCBIGene', 'NCBITaxon', 'skos', 'owl'),
                        'ncbigeneslim',
                        'This subset is automatically generated from the NCBI Gene database on a subset of terms listed in %s.' % IDS_FILE,
                        remote_base= 'http://ontology.neuinfo.org/NIF/')

    for k, v in base.items():
        #if k != 'uids':
        ncbi(v, ng)
    ng.write()
    #embed()

from pyontutils.parcellation import Ont, Source, uPREFIXES

def yield_recursive(s, p, o, source_graph):
    yield s, p, o
    new_s = o
    if isinstance(new_s, rdflib.BNode):
        for p, o in source_graph.predicate_objects(new_s):
            yield from class_closure(new_s, p, o, source_graph)

class SimpleSource(Source):
    @classmethod
    def processData(cls):
        return cls.raw,

    @classmethod
    def validate(cls, d):
        return d

class ChebiIdsSrc(SimpleSource):
    source = 'resources/chebi-subset-ids.txt'
    source_original = True
    @classmethod
    def loadData(cls):
        ug = makeGraph('utilgraph', prefixes=uPREFIXES)
        with open(cls.source, 'rt') as f:
            ids_raw = set(_.strip() for _ in f.readlines())
            ids = set(ug.expand(_.strip()).toPython() for _ in ids_raw)
            return ids_raw, ids

    @classmethod
    def validate(cls, a):
        return a

class ChebiOntSrc(SimpleSource):
    source = 'http://ftp.ebi.ac.uk/pub/databases/chebi/ontology/nightly/chebi.owl.gz'
    source_original = True
    @classmethod
    def loadData(cls):
        gzed = requests.get('http://ftp.ebi.ac.uk/pub/databases/chebi/ontology/nightly/chebi.owl.gz')
        cls._gzed = gzed
        raw = BytesIO(gzip.decompress(gzed.content))
        t = etree.parse(raw)
        return t

    @classmethod
    def processData(cls):
        ids_raw, ids = ChebiIdsSrc()
        tree = cls.raw
        r = tree.getroot()
        cs = r.getchildren()
        classes = [_ for _ in cs if _.tag == '{http://www.w3.org/2002/07/owl#}Class' and _.values()[0] in ids]
        ontology = tree.xpath("/*[local-name()='RDF']/*[local-name()='Ontology']")
        ops = tree.xpath("/*[local-name()='RDF']/*[local-name()='ObjectProperty']")  # TODO
        wanted = [etree.ElementTree(_) for _ in classes]
        rpl_check = tree.xpath("/*[local-name()='RDF']/*[local-name()='Class']/*[local-name()='hasAlternativeId']")
        rpl_dict = {_.text:_.getparent() for _ in rpl_check if _.text in ids_raw} # we also need to have any new classes that have replaced old ids
        also_classes = list(rpl_dict.values())
        a = ontology + ops + classes + also_classes
        def rec(start_set, done):
            ids_ = set()
            for c in start_set:
                ids_.update([_.items()[0][1] for _ in etree.ElementTree(c).xpath("/*[local-name()='Class']/*[local-name()='subClassOf']") if _.items()])
                ids_.update([_.items()[0][1] for _ in etree.ElementTree(c).xpath("/*[local-name()='Class']/*[local-name()='subClassOf']/*[local-name()='Restriction']/*[local-name()='someValuesFrom']") if _.items()])
            supers = [_ for _ in cs if _.tag == '{http://www.w3.org/2002/07/owl#}Class' and _.values()[0] in ids_ and _ not in done]
            if supers:
                msup, mids = rec(supers, done + supers)
                supers += msup
                ids_.update(mids)
            return supers, ids_
        more, mids = rec(a, a)
        all_ = set(a + more)
        r.clear()  # wipe all the stuff we don't need
        for c in all_:
            r.append(c)
        data = etree.tostring(r)
        g = rdflib.Graph()
        g.parse(data=data)  # now _this_ is stupidly slow (like 20 minutes of slow) might make more sense to do the xml directly?
        cls.iri = list(g.query('SELECT DISTINCT ?match WHERE { ?temp rdf:type owl:Ontology . ?temp owl:versionIRI ?match . }'))[0][0]
        return more, mids, g

    @classmethod
    def validate(cls, a, b, c):
        return a, b, c

class ChebiDead(Ont):
    filename = 'chebi-dead'
    name = 'NIF ChEBI deprecated'
    shortname = 'chebidead'
    prefixes = makePrefixes('CHEBI', 'replacedBy', 'owl', 'skos')
    #'This file is generated by pyontutils/slimgen to make deprecated classes resolvablefrom the full ChEBI nightly at versionIRI %s based on the list of terms in %s.' % (src_version, IDS_FILE),

class Chebi(Ont):
    sources = ChebiIdsSrc(), ChebiOntSrc()
    filename = 'chebislim'
    name = 'NIF ChEBI slim'
    shortname = 'chebislim'
    prefixes = makePrefixes('definition',
                            'hasRole',
                            'replacedBy',
                            'hasPart',
                            'termsMerged',
                            'obsReason',
                            'BFO',
                            'CHEBI',
                            'chebi',
                            'owl',
                            'skos',
                            'oboInOwl')

    #'This file is generated by pyontutils/slimgen from the full ChEBI nightly at versionIRI %s based on the list of terms in %s.' % (src_version, IDS_FILE),

    def _triples(self):
        (ids_raw, ids), (more, mids, g) = self.sources

        depwor = {'CHEBI:33243':'natural product',  # FIXME remove these?
                  'CHEBI:36809':'tricyclic antidepressant',
                 }

        #for id_ in sorted(set(ids_raw) | set((ug.g.namespace_manager.qname(_) for _ in mids))):
        for eid in sorted(ids | mids):
            id_ = self._graph.qname(eid)
            po = list(g.predicate_objects(eid))
            if not po:
                #looks for the id_ as a literal
                alts = list(g.subjects(oboInOwl.hasAlternativeId,
                                       rdflib.Literal(id_, datatype=rdflib.XSD.string)))
                if alts:
                    replaced_by = alts[0]
                    if replaced_by.toPython() not in ids:  #  we need to add any replacment classes to the bridge
                        print('REPLACED BY NEW CLASS', id_)
                        for p, o in g.predicate_objects(replaced_by):
                            yield from yield_recursive(replaced_by, p, o, g)
                    ChebiDead.addTrip(eid, rdf.type, owl.Class)
                    ChebiDead.addTrip(eid, replacedBy, replaced_by)
                    ChebiDead.addTrip(eid, owl.deprecated, Literal(True))
                else:
                    if self._graph.qname(eid) not in depwor:
                        raise BaseException('wtf error', eid)
            else:
                for p, o in po:
                    yield from class_closure(eid, p, o, g)
                    #new_graph.add_recursive(trip, g)
                    if p == replacedBy:
                        ChebiDead.addTrip(eid, rdfs.subClassOf, owl.DeprecatedClass)
                        if (o, rdf.type, owl.Class) not in g:
                            print('WARNING REPLACED BUT NOT IN THE XML SUBSET', o)
                        for p, o in g.predicate_objects(o):
                            yield from yield_recursive(eid, p, o, g)

        # https://github.com/ebi-chebi/ChEBI/issues/3294  ?? fixed?


def chebi_make():
    IDS_FILE = 'resources/chebi-subset-ids.txt'
    with open(IDS_FILE, 'rt') as f:
        ids_raw = set((_.strip() for _ in f.readlines()))
        ids = set((ug.expand(_.strip()).toPython() for _ in ids_raw))

    #gzed = requests.get('http://localhost:8000/chebi.owl')
    #raw = BytesIO(gzed.content)
    gzed = requests.get('http://ftp.ebi.ac.uk/pub/databases/chebi/ontology/nightly/chebi.owl.gz')
    raw = BytesIO(gzip.decompress(gzed.content))
    t = etree.parse(raw)
    r = t.getroot()
    cs = r.getchildren()
    classes = [_ for _ in cs if _.tag == '{http://www.w3.org/2002/07/owl#}Class' and _.values()[0] in ids]
    ontology = t.xpath("/*[local-name()='RDF']/*[local-name()='Ontology']")
    ops = t.xpath("/*[local-name()='RDF']/*[local-name()='ObjectProperty']")  # TODO
    wanted = [etree.ElementTree(_) for _ in classes]
    rpl_check = t.xpath("/*[local-name()='RDF']/*[local-name()='Class']/*[local-name()='hasAlternativeId']")
    rpl_dict = {_.text:_.getparent() for _ in rpl_check if _.text in ids_raw } # we also need to have any new classes that have replaced old ids
    also_classes = list(rpl_dict.values())
    def rec(start_set, done):
        ids_ = set()
        for c in start_set:
            ids_.update([_.items()[0][1] for _ in etree.ElementTree(c).xpath("/*[local-name()='Class']/*[local-name()='subClassOf']") if _.items()])
            ids_.update([_.items()[0][1] for _ in etree.ElementTree(c).xpath("/*[local-name()='Class']/*[local-name()='subClassOf']/*[local-name()='Restriction']/*[local-name()='someValuesFrom']") if _.items()])
        supers = [_ for _ in cs if _.tag == '{http://www.w3.org/2002/07/owl#}Class' and _.values()[0] in ids_ and _ not in done]
        if supers:
            msup, mids = rec(supers, done + supers)
            supers += msup
            ids_.update(mids)
        return supers, ids_
    a = ontology + ops + classes + also_classes
    more, mids = rec(a, a)
    all_ = set(a + more)
    r.clear()  # wipe all the stuff we don't need
    for c in all_:
        r.append(c)
    data = etree.tostring(r)

    g = rdflib.Graph()
    g.parse(data=data)  # now _this_ is stupidly slow (like 20 minutes of slow) might make more sense to do the xml directly?

    src_version = list(g.query('SELECT DISTINCT ?match WHERE { ?temp rdf:type owl:Ontology . ?temp owl:versionIRI ?match . }'))[0][0]

    new_graph = createOntology('chebislim',
                               'NIF ChEBI slim',
                               PREFIXES,
                               'chebislim',
                               'This file is generated by pyontutils/slimgen from the full ChEBI nightly at versionIRI %s based on the list of terms in %s.' % (src_version, IDS_FILE),
                               remote_base='http://ontology.neuinfo.org/NIF/')

    chebi_dead = createOntology('chebi-dead',
                                'NIF ChEBI deprecated',
                                dPREFIXES,
                                'chebidead',
                                'This file is generated by pyontutils/slimgen to make deprecated classes resolvablefrom the full ChEBI nightly at versionIRI %s based on the list of terms in %s.' % (src_version, IDS_FILE),
                                remote_base='http://ontology.neuinfo.org/NIF/')

    depwor = {'CHEBI:33243':'natural product',  # FIXME remove these?
              'CHEBI:36809':'tricyclic antidepressant',
             }

    for id_ in sorted(set(ids_raw) | set((ug.g.namespace_manager.qname(_) for _ in mids))):
        eid = ug.expand(id_)
        trips = list(g.triples((eid, None, None)))
        if not trips:
            #looks for the id_ as a literal
            alts = list(g.subjects(oboInOwl.hasAlternativeId,
                                   rdflib.Literal(id_, datatype=rdflib.XSD.string)))
            if alts:
                replaced_by = alts[0]
                if replaced_by.toPython() not in ids:  #  we need to add any replacment classes to the bridge
                    print('REPLACED BY NEW CLASS', id_)
                    for p, o in g.predicate_objects(replaced_by):
                        new_graph.add_recursive((replaced_by, p, o), g)
                chebi_dead.add_class(id_)
                chebi_dead.add_trip(id_, 'replacedBy:', replaced_by)
                chebi_dead.add_trip(id_, owl.deprecated, True)
            else:
                if id_ not in depwor:
                    raise BaseException('wtf error', id_)
        else:
            for trip in trips:
                new_graph.add_recursive(trip, g)
                if trip[1] == ug.expand('replacedBy:'):
                    chebi_dead.add_trip(trip[0], rdfs.subClassOf, owl.DeprecatedClass)
                    if (trip[-1], rdf.type, owl.Class) not in g:
                        print('WARNING REPLACED BUT NOT IN THE XML SUBSET', trip[-1])
                    for t in g.triples((trip[-1], None, None)):
                        new_graph.add_recursive(t, g)

    # https://github.com/ebi-chebi/ChEBI/issues/3294
    def doNotWant(o):
        if o[-1].isdigit:
            return o.strip('-').replace('.','').isdigit()
        else:
            return False

    for s, o in new_graph.g.subject_objects(oboInOwl.hasRelatedSynonym):
        if doNotWant(o):
            new_graph.g.remove((s, oboInOwl.hasRelatedSynonym, o))

    new_graph.write()
    chebi_dead.write()
    embed()

def main():
    #ncbigene_make()
    #chebi_make()
    embed()

if __name__ == '__main__':
    main()
