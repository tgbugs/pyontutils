#!/usr/bin/env python3

from os.path import expanduser
import rdflib
from pyontutils.scigraph_client import Vocabulary
from IPython import embed

with open(expanduser('~/git/entity_mapping/mappings/uberon-nervous'), 'rt') as f:
    brain_only = set([l.strip() for l in f.readlines()])

v = Vocabulary('http://localhost:9000/scigraph')

g = rdflib.Graph()
g.parse(expanduser('~/git/NIF-Ontology/ttl/generated/cocomacslim.ttl'), format='turtle')
sos = [so for so in g.subject_objects(rdflib.RDFS.label)]

map_ = []
smap_ = []
for s, o in sos:
    cc_id = g.qname(s)
    cc_label = o.toPython()
    existing_id = None
    existing_label = None
    s_existing_id = None
    s_existing_label = None

    cands = v.findByTerm(o)
    if not cands:
        cands = []
        scands = v.searchByTerm(o)
        if not scands:
            scands = []
    else:
        scands = []

    for cand in cands:
        existing_id = cand['curie']
        existing_label = cand['labels'][0]
        if existing_id.startswith('UBERON'):
            if existing_id not in brain_only:
                existing_id = None
                existing_label = None
            else:
                break
        #elif cand['curie'].startswith('NIFGA'):
        #elif cand['curie'].startswith('MBA'):

    if existing_id:
        map_.append((cc_id, cc_label, existing_id, existing_label))

    for scand in scands:
        if not scand['curie']:
            print(scand)
            continue

        if scand['curie'].startswith('UBERON'):
            if scand['curie'] in brain_only:
                s_existing_id = scand['curie']
                s_existing_label = scand['labels'][0]
                smap_.append((cc_id, cc_label, s_existing_id, s_existing_label))
            #break  # FOW :/

    
_ = [print(a) for a in sorted(smap_, key=lambda a: int(a[0].split(':')[1]))]
embed()
