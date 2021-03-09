#!/usr/bin/env python3
"""
    Build lightweight slims from curie lists.
    Used for sources that don't have an owl ontology floating.
"""
#TODO consider using some of the code from scr_sync.py???

from pathlib import Path
import requests
from pyontutils.core import createOntology
from pyontutils.utils import chunk_list, dictParse
from pyontutils.config import auth
from pyontutils.namespaces import SO, makePrefixes
from pyontutils.namespaces import rdf, rdfs, owl

#ncbi_map = {
    #'name':,
    #'description':,
    #'uid':,
    #'organism':{''},
    #'otheraliases':,
    #'otherdesignations':,
#}


class ncbi(dictParse):
    superclass = SO['0000110']  # sequence feature
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
    IDS_FILE = auth.get_path('resources') / 'gene-subset-ids.txt'
    with open(IDS_FILE.as_posix(), 'rt') as f:  # this came from neuroNER
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
                        makePrefixes('ilxtr', 'NIFRID', 'NCBIGene',
                                     'NCBITaxon', 'skos', 'owl', 'SO'),
                        'ncbigeneslim',
                        f'This subset is automatically generated from the NCBI Gene database on a subset of terms listed in {IDS_FILE}.',
                        remote_base= 'http://ontology.neuinfo.org/NIF/')

    for k, v in base.items():
        #if k != 'uids':
        ncbi(v, ng)
    ng.write()


def main():
    ncbigene_make()


if __name__ == '__main__':
    main()
