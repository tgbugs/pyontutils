#!/usr/bin/env python3.6
#!/usr/bin/env pypy3
"""
    Build lightweight slims from curie lists.
    Used for sources that don't have an owl ontology floating.
"""
#TODO consider using some of the code from scr_sync.py???

import os
import gzip
import json
from io import BytesIO
from pathlib import Path
from datetime import date
import rdflib
import requests
from lxml import etree
from rdflib.extras import infixowl
from pyontutils.core import makeGraph, createOntology, yield_recursive, build, qname
from pyontutils.core import Ont, Source
from pyontutils.utils import chunk_list, dictParse, memoryCheck
from pyontutils.ilx_utils import ILXREPLACE
from pyontutils.namespaces import makePrefixes, replacedBy, hasPart, hasRole, PREFIXES as uPREFIXES
from pyontutils.closed_namespaces import rdf, rdfs, owl, prov, oboInOwl
from IPython import embed


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
        self.g.add_trip(self.identifier, 'ilxtr:definedForTaxon', tax)  # FIXME species or taxon???

    def otheraliases(self, value):
        if value:
            for synonym in value.split(','):
                self.g.add_trip(self.identifier, 'NIFRID:synonym', synonym.strip())

    def otherdesignations(self, value):
        if value:
            for synonym in value.split('|'):
                self.g.add_trip(self.identifier, 'NIFRID:synonym', synonym)

def ncbigene_make():
    IDS_FILE = (Path(__file__).parent / 'resources/gene-subset-ids.txt').as_posix()
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
                        makePrefixes('ILXREPLACE', 'ilxtr', 'NIFRID', 'NCBIGene', 'NCBITaxon', 'skos', 'owl'),
                        'ncbigeneslim',
                        'This subset is automatically generated from the NCBI Gene database on a subset of terms listed in %s.' % IDS_FILE,
                        remote_base= 'http://ontology.neuinfo.org/NIF/')

    for k, v in base.items():
        #if k != 'uids':
        ncbi(v, ng)
    ng.write()
    #embed()


class ChebiIdsSrc(Source):
    source = (Path(__file__).parent / 'resources/chebi-subset-ids.txt').as_posix()
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


class ChebiOntSrc(Source):
    source = 'http://ftp.ebi.ac.uk/pub/databases/chebi/ontology/nightly/chebi.owl.gz'
    source_original = True
    @classmethod
    def loadData(cls):
        source = '/tmp/chebi.gz'
        if not os.path.exists(source):
            gzed = requests.get(cls.source)
            cls._gzed = gzed
            raw = BytesIO(gzip.decompress(gzed.content))
            with open(source, 'wb') as f:
                f.write(gzed.content)
        else:
            with open(source, 'rb') as f:
                raw = BytesIO(gzip.decompress(f.read()))

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
                msup, more_ids = rec(supers, done + supers)
                supers += msup
                ids_.update(more_ids)
            return supers, ids_
        more, more_ids = rec(a, a)
        all_ = set(a + more)
        r.clear()  # wipe all the stuff we don't need
        for c in all_:
            r.append(c)
        data = etree.tostring(r)
        g = rdflib.Graph()
        g.parse(data=data)  # now _this_ is stupidly slow (like 20 minutes of slow) might make more sense to do the xml directly?
        cls.iri = list(g.query('SELECT DISTINCT ?match WHERE { ?temp rdf:type owl:Ontology . ?temp owl:versionIRI ?match . }'))[0][0]
        return more, more_ids, g

    @classmethod
    def validate(cls, a, b, g):
        allids = set(e for t in g
                     for e in t if
                     isinstance(e, rdflib.URIRef) and
                     qname(e).startswith('CHEBI:'))
        classids = set(s for s in g[:rdf.type:owl.Class] if
                       isinstance(s, rdflib.URIRef) and
                       qname(s).startswith('CHEBI:'))
        assert allids == classids, f'missing! {len(allids - classids)}'
        return a, b, g


class ChebiDead(Ont):
    filename = 'chebi-dead'
    name = 'NIF ChEBI deprecated'
    shortname = 'chebidead'
    prefixes = makePrefixes('CHEBI', 'replacedBy', 'prov', 'oboInOwl')
    #'This file is generated by pyontutils/slimgen to make deprecated classes resolvablefrom the full ChEBI nightly at versionIRI %s based on the list of terms in %s.' % (src_version, IDS_FILE),


chebi_dead = ChebiDead()


class Chebi(Ont):
    sources = ChebiIdsSrc, ChebiOntSrc
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
                            'chebi1',
                            'chebi2',
                            'chebi3',
                            'prov',
                            'skos',
                            'oboInOwl')

    #'This file is generated by pyontutils/slimgen from the full ChEBI nightly at versionIRI %s based on the list of terms in %s.' % (src_version, IDS_FILE),

    def _triples(self):
        (ids_raw, ids), (more, more_ids, g) = self.sources

        depwor = {'CHEBI:33243':'natural product',  # FIXME remove these?
                  'CHEBI:36809':'tricyclic antidepressant',
                 }
        chebiiri = next(g[:rdf.type:owl.Ontology])
        oiodate = rdflib.URIRef(str(oboInOwl) + 'date')  # this predicate doesn't actually exist...
        chebidate = next(g[chebiiri:oiodate])
        b0 = rdflib.BNode()
        yield self.iri, prov.qualifiedDerivation, b0
        yield b0, rdf.type, prov.Derivation
        yield b0, prov.atTime, chebidate

        yield from ((ss, ps, os)
                    for s in g[:rdf.type:owl.ObjectProperty]
                    if str(s) not in (str(hasRole), str(hasPart))
                    for p, o in g[s]
                    for ss, ps, os in yield_recursive(s, p, o, g))

        for s, p, o in g:
            if s == chebiiri or s == rdflib.URIRef(hasPart) or s == rdflib.URIRef(hasRole):
                continue
            if p == replacedBy:
                chebi_dead.addTrip(s, rdfs.subClassOf, owl.DeprecatedClass)
                for dead_predicate in (rdfs.label, oboInOwl.hasExactSynonym):
                    for dead_object in g[o:dead_predicate]:
                        chebi_dead.addTrip(s, dead_predicate, dead_object)

            yield s, p, o

        return  # the implementation below is a much slower equivalent that does needless checks
        # better simply to validate that there are no chebi ids that are missing an owl:Class

        #for id_ in sorted(set(ids_raw) | set((ug.g.namespace_manager.qname(_) for _ in mids))):
        print('more_ids', more_ids)
        for eid in sorted(ids | more_ids):
            #print(repr(eid))
            id_ = self._graph.qname(eid)
            s = rdflib.URIRef(eid)
            po = list(g.predicate_objects(s))
            if not po:
                print(s, 'not in xml')
                #looks for the id_ as a literal
                alts = list(g.subjects(oboInOwl.hasAlternativeId,
                                       rdflib.Literal(id_, datatype=rdflib.XSD.string)))
                if alts:
                    replaced_by = alts[0]
                    if replaced_by.toPython() not in ids:  #  we need to add any replacment classes to the bridge
                        print('REPLACED BY NEW CLASS', id_)
                        for p, o in g.predicate_objects(replaced_by):
                            yield from yield_recursive(replaced_by, p, o, g)
                    chebi_dead.addTrip(s, rdf.type, owl.Class)
                    chebi_dead.addTrip(s, replacedBy, replaced_by)
                    chebi_dead.addTrip(s, owl.deprecated, Literal(True))
                else:
                    if self._graph.qname(eid) not in depwor:
                        raise BaseException('wtf error', self._graph.qname(eid))
            else:
                for p, o in po:
                    yield from yield_recursive(s, p, o, g)
                    if p == replacedBy:
                        chebi_dead.addTrip(s, rdfs.subClassOf, owl.DeprecatedClass)
                        oqname = self._graph.qname(o)
                        if (o, rdf.type, owl.Class) not in g:
                            print('WARNING: replaced but not in the xml subset', o)
                        elif oqname not in ids and str(o) not in more_ids:
                            print('WARNING: replaced but not in ids or more_ids', o)
                            for np, no in g[o]:
                                yield from yield_recursive(o, np, no, g)
                        for ro in g[o:rdfs.label]:
                            chebi_dead.addTrip(s, rdfs.label, ro)
                            #yield from yield_recursive(s, p, o, g)

        # https://github.com/ebi-chebi/ChEBI/issues/3294  ?? fixed?


def main():
    memoryCheck(7300000000)
    ncbigene_make()
    build(Chebi, n_jobs=1)
    chebi_dead().write()

    if False:
        from pyontutils.qnamefix import cull_prefixes
        with open('/tmp/chebi-debug.xml', 'wb') as f: ChebiOntSrc.raw.write(f)
        #with open('/tmp/chebi-debug.ttl', 'wb') as f: f.write(ChebiOntSrc._data[2].serialize(format='nifttl'))
        g = cull_prefixes(ChebiOntSrc._data[2])
        g.filename = '/tmp/chebi-debug.ttl' 
        g.write()
        embed()

if __name__ == '__main__':
    main()
