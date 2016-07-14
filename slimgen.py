#!/usr/bin/env python3
"""
    Build lightweight slims from curie lists.
    Used for sources that don't have an owl ontology floating.
"""
#TODO consider using some of the code from scr_sync.py???

import json
from datetime import date
import rdflib
from rdflib.extras import infixowl
import requests
from utils import makeGraph, add_hierarchy, chunk_list, dictParse
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
    superclass = rdflib.URIRef('http://uri.interlex.org/base/ilx_gene_concept')
    def __init__(self, thing, graph):
        self.g = graph
        super().__init__(thing, order=['uid'])

    def name(self, value):
        self.g.add_node(self.identifier, rdflib.RDFS.label, value)

    def description(self, value):
        #if value:
        self.g.add_node(self.identifier, 'ilx:display_label', value)

    def uid(self, value):
        self.identifier = 'NCBIGene:' + str(value)
        self.g.add_node(self.identifier, rdflib.RDF.type, rdflib.OWL.Class)
        self.g.add_node(self.identifier, rdflib.RDFS.subClassOf, self.superclass)

    def organism(self, value):
        self._next_dict(value)

    def taxid(self, value):
        tax = 'NCBITaxon:' + str(value)
        self.g.add_node(self.identifier, 'ilx:has_taxon', tax)

    def otheraliases(self, value):
        if value:
            for synonym in value.split(','):
                self.g.add_node(self.identifier, 'OBOANN:synonym', synonym.strip())

    def otherdesignations(self, value):
        if value:
            for synonym in value.split('|'):
                self.g.add_node(self.identifier, 'OBOANN:synonym', synonym)

def ncbigene_make():
    with open('gene-subset-ids.txt', 'rt') as f:  # this came from neuroNER
        ids = [l.split(':')[1].strip() for l in f.readlines()]
    
    #url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?retmode=json&retmax=5000&db=gene&id='
    #for id_ in ids:
        #data = requests.get(url + id_).json()['result'][id_]
    url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
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
 
    prefixes = {
        'ilx':'http://uri.interlex.org/base/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'NCBIGene':'http://www.ncbi.nlm.nih.gov/gene/',
        'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
    }
    ng = makeGraph('ncbigeneslim', prefixes)

    for k, v in base.items():
        #if k != 'uids':
        ncbi(v, ng)

    ontid = 'http://ontology.neuinfo.org/NIF/ttl/generated/ncbigeneslim.ttl'
    ng.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    ng.add_node(ontid, rdflib.RDFS.label, 'NIF NCBI Gene subset')
    ng.add_node(ontid, rdflib.RDFS.comment, 'This subset is automatically generated from the NCBI Gene database on a subset of terms.')
    ng.add_node(ontid, rdflib.OWL.versionInfo, date.isoformat(date.today()))
    ng.write()
    #embed()

def main():
    ncbigene_make()

if __name__ == '__main__':
    main()
