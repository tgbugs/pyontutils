"""
TODO:
Fuctionality is only for label <--> rdfs:label comparison. Needs to be increased for the label
side bc rfs:label can be changed to a different coloumn.
"""

import json
from sqlalchemy import create_engine, inspect, Table, Column
import pandas as pd
from ilxutils.args_reader import read_args
from ilxutils.scicrunch_client import scicrunch
from ilxutils.mydifflib import diffcolor, diff, ratio
import sys
import time
from ilxutils.interlex_sql import interlex_sql
import re
from collections import defaultdict
from IPython.core.display import display
import subprocess as sb
import pickle
from pathlib import Path as p
import requests as r
from ilxutils.ttl2pd import *
import mydifflib
'''
Reference to repeats that may be in listself
Will delete and replace with self repeating checks
'''
toms_repeats = []
repeats = json.load(open('../dump/repeating_exids.json'))
for repeat in repeats:
    toms_repeats.append(repeat['uri'])


def degrade(var):
    def helper(s):
        return str(re.sub("\(|\)|'|,", "", s).lower().strip())

    if type(var) != list:
        if var:
            return helper(var)
        else:
            return var
    else:
        return [helper(v) if v else v for v in var]


def get(url):
    req = r.get(url)
    if req.raise_for_status():
        sys.exit('failed at ' + url)
    try:
        return req.json()
    except:
        return req.text


def cj(data, output):
    json.dump(data, open(output + '.json', 'w'), indent=4)
    print('Complete')


def oj(infile):
    try:
        return json.load(open(infile, 'r'))
    except:
        sys.exit('File does not exist')


def df2hash(df, column):
    dfhash = defaultdict(list)
    for uri, row in df.iterrows():
        labels = degrade(row[column])
        if isinstance(labels, list):
            dfhash[uri] = labels
        elif isinstance(labels, str):
            dfhash[uri] = [labels]
        if type(labels) == list:
            for label in labels:
                dfhash[label] = uri
        else:
            dfhash[labels] = uri
    return dfhash


# How I go this dict:
# for p,iri in set([(row.curie.split(':')[0].strip().lower(), row.iri.rsplit('/', 1)[0].strip()) for i, row in ex.iterrows() if row.curie]): print(p,':',iri,',')
onto_prefix = {
    'radlex': 'http://www.radlex.org/RID',
    'nlxdys': 'http://uri.neuinfo.org/nif/nifstd',
    'ilx': 'http://uri.interlex.org/base',
    't3d': 'http://t3db.org/toxins',
    'obi': 'http://purl.obolibrary.org/obo',
    'bamsn': 'https://bams1.org/bkms',
    'iao': 'http://purl.obolibrary.org/obo',
    'gbif': 'http://www.gbif.org/species',
    'itistsn': 'http://www.itis.gov/servlet/SingleRpt',
    'par': 'http://uri.interlex.org/fakeobo/uris/obo',
    'pato': 'http://purl.obolibrary.org/obo',
    'chebi': 'http://purl.obolibrary.org/obo',
    'nlxres': 'http://uri.neuinfo.org/nif/nifstd',
    'mp': 'http://purl.obolibrary.org/obo',
    'sio': 'http://semanticscience.org/resource',
    'ogms': 'http://purl.obolibrary.org/obo',
    'd': 'http://purl.bioontology.org/ontology/MESH',
    'nlxmol': 'http://uri.neuinfo.org/nif/nifstd',
    'nlxwiki': 'http://neurolex.org/wiki',
    'fbdv': 'http://purl.obolibrary.org/obo',
    'efo': 'http://www.ebi.ac.uk/efo',
    'sao': 'http://uri.neuinfo.org/nif/nifstd',
    'ma': 'http://purl.obolibrary.org/obo',
    'nlx_br': 'http://uri.neuinfo.org/nif/nifstd',
    'snomed': 'http://purl.bioontology.org/ontology/SNOMEDCT',
    'nlxcell': 'http://uri.neuinfo.org/nif/nifstd',
    'cao': 'http://www.cognitiveatlas.org/ontology',
    'bamsc': 'http://uri.neuinfo.org/nif/nifstd',
    'nlxchem': 'http://uri.neuinfo.org/nif/nifstd',
    'mesh': 'https://meshb.nlm.nih.gov/record',
    'nifext': 'http://uri.neuinfo.org/nif/nifstd',
    'ero': 'http://purl.obolibrary.org/obo',
    'nlxfunc': 'http://uri.neuinfo.org/nif/nifstd',
    'nlxsub': 'http://uri.neuinfo.org/nif/nifstd',
    'so': 'http://purl.obolibrary.org/obo',
    'sbo': 'http://purl.obolibrary.org/obo',
    'ncbitaxon': 'http://purl.obolibrary.org/obo',
    'nlxoen': 'http://uri.neuinfo.org/nif/nifstd',
    'go': 'http://purl.obolibrary.org/obo',
    'nemo': 'http://purl.bioontology.org/NEMO/ontology',
    'wbls': 'http://www.wormbase.org/species/all/life_stage',
    'c': 'https://nciterms.nci.nih.gov/ncitbrowser',
    'cogpo': 'http://www.cogpo.org/ontologies',
    'nlxqual': 'http://uri.neuinfo.org/nif/nifstd',
    'topic': 'http://edamontology.org',
    'db': 'https://www.drugbank.ca/drugs',
    'nlxorg': 'http://uri.neuinfo.org/nif/nifstd',
    'nda.cde': 'http://uri.interlex.org/NDA/uris/datadictionary/elements',
    'doid': 'http://purl.obolibrary.org/obo',
    'uberon': 'http://purl.obolibrary.org/obo',
    'hp': 'http://purl.obolibrary.org/obo',
    'cogpo1': 'http://www.cogpo.org/ontologies',
    'cl': 'http://purl.obolibrary.org/obo',
    'dicom': 'http://uri.interlex.org/dicom/uris/terms',
    'sbo': 'http://www.ebi.ac.uk/sbo/main',
    'nlxanat': 'http://uri.neuinfo.org/nif/nifstd',
    'fbbi': 'http://purl.obolibrary.org/obo',
    'nlx': 'http://uri.neuinfo.org/nif/nifstd',
    'cao': 'http://purl.obolibrary.org/obo',
    'birnlex': 'http://uri.neuinfo.org/nif/nifstd',
    'fma': 'http://purl.org/sig/ont/fma',
    'xao': 'http://purl.obolibrary.org/obo',
    'pr': 'http://purl.obolibrary.org/obo',
    'nlxinv': 'http://uri.neuinfo.org/nif/nifstd',
}


class ontology_check():
    def __init__(self, ontology, column_to_hash, sql, cj=False):
        self.cj = cj
        self.ontoname = p(ontology).stem
        self.onto = local_ttl2pd(ontology)
        self.ontohash = df2hash(self.onto[self.onto[column_to_hash].notnull()],
                                column_to_hash)  # hashes index to column
        self.ex = sql.get_existing_ids()
        self.ilxdiffdata = self.ilx_label_diff()

    def ilx_label_diff(
            self
    ):  #FIXME should be renamed label something bc thats all it checks right now
        data = []
        if not onto_prefix.get(self.ontoname):  #dont have iri prefix
            ex = self.ex
        else:
            ex = self.ex[self.ex.iri.str.contains(
                onto_prefix[self.ontoname]
            )]  #sign cuts time if you have iri prefix of the onto
        for i, row in ex.iterrows():
            local_data = {}
            label = degrade(row.label)
            if self.ontohash.get(row.iri):
                if not label in self.ontohash.get(row.iri):  #do check here
                    local_data.update({
                        'ilx_uri':
                        row.iri,
                        'ilx_label':
                        label,
                        'onto_labels':
                        self.ontohash.get(row.iri),
                        'ilx_id':
                        row.ilx
                    })
                    if self.ontohash.get(label):
                        if row.iri != self.ontohash.get(label):
                            local_data.update({
                                'onto_uri_from_ilx_label':
                                self.ontohash.get(label)
                            })
                    if row.iri in toms_repeats:
                        local_data.update({'repeating_in_ilx': True})  #FIXME
                    local_data.update({
                        'label_diffs': [
                            diff(label, onto_label)
                            for onto_label in self.ontohash.get(row.iri)
                        ]
                    })
                    ratios = [
                        ratio(label, onto_label)
                        for onto_label in self.ontohash.get(row.iri)
                    ]
                    notes = []
                    for _ratio in ratios:
                        if float(_ratio) >= .95:
                            notes.append('Syntax difference')
                        else:
                            notes.append('Need futher action')
                    local_data.update({'label_diff_notes': notes})
                    local_data.update({'label_diff_ratios': ratios})
            if local_data:
                data.append(local_data)
        if self.cj:
            cj(data, '../dump/' + self.ontoname + '-ilx-diff')


def main():
    args = read_args(
        api_key=p.home() / 'keys/production_api_scicrunch_key.txt',
        db_url=p.home() / 'keys/production_engine_scicrunch_key.txt',
        VERSION='0.1',
        production=True)
    sql = interlex_sql(db_url=args.db_url)
    ontoc = ontology_check(
        ontology='/home/troy/Desktop/uberon.owl',
        column_to_hash='rdfs:label',
        sql=sql,
        cj=True)


if __name__ == '__main__':
    main()
