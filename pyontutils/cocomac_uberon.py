#!/usr/bin/env python3

import csv
from os.path import expanduser
import rdflib
from pyontutils.scigraph import Vocabulary, Graph
from IPython import embed

dbx = 'http://www.geneontology.org/formats/oboInOwl#hasDbXref'

with open(expanduser('~/git/entity_mapping/mappings/uberon-nervous'), 'rt') as f:
    brain_only = set([l.strip() for l in f.readlines()])

v = Vocabulary('http://localhost:9000/scigraph')
sg = Graph('http://localhost:9000/scigraph')

g = rdflib.Graph()
g.parse(expanduser('~/git/NIF-Ontology/ttl/generated/cocomacslim.ttl'), format='turtle')
sos = [so for so in g.subject_objects(rdflib.RDFS.label)]

map_ = []
smap_ = []
fma_lookup = {}
for s, o in sos:
    cc_id = g.qname(s)
    cc_label = o.toPython()
    existing_id = None
    existing_label = None
    existing_fma = ''
    s_existing_id = None
    s_existing_label = None
    s_existing_fma = ''

    cands = v.findByTerm(o)
    if not cands:
        cands = []
        scands = v.searchByTerm(o)
        if not scands:
            scands = []
    else:
        scands = []

    for cand in cands:
        existing_fma = ''
        existing_id = cand['curie']
        existing_label = cand['labels'][0]
        if existing_id.startswith('UBERON'):
            if existing_id not in brain_only:
                existing_id = None
                existing_label = None
                existing_fma = ''
            else:
                if existing_id in fma_lookup:
                    existing_fma = fma_lookup[existing_id]
                else:
                    meta = sg.getNode(existing_id)['nodes'][0]['meta']
                    if dbx in meta:
                        xrefs = meta[dbx]
                        for ref in xrefs:
                            if ref.startswith('FMA:'):
                                existing_fma += ref
                    fma_lookup[existing_id] = existing_fma
                break
        #elif cand['curie'].startswith('NIFGA'):
        #elif cand['curie'].startswith('MBA'):

    if existing_id:
        map_.append((cc_label, cc_id, existing_label, existing_id, existing_fma))

    for scand in scands:
        if not scand['curie']:
            print(scand)
            continue

        s_existing_fma = ''
        if scand['curie'].startswith('UBERON'):
            if scand['curie'] in brain_only:
                s_existing_id = scand['curie']
                s_existing_label = scand['labels'][0]
                if not s_existing_id:
                    print(scand)
                    continue
                asdf = sg.getNode(s_existing_id)
                #print(asdf, s_existing_id, s_existing_label)
                if s_existing_id in fma_lookup:
                    s_existing_fma = fma_lookup[s_existing_id]
                else:
                    meta = asdf['nodes'][0]['meta']
                    if dbx in meta:
                        xrefs = meta[dbx]
                        for ref in xrefs:
                            if ref.startswith('FMA:'):
                                s_existing_fma += ref
                    fma_lookup[s_existing_id] = s_existing_fma
                smap_.append((cc_label, cc_id, s_existing_label, s_existing_id, s_existing_fma))
            #break  # FOW :/


_ = [print(a) for a in sorted(smap_, key=lambda a: int(a[1].split(':')[1]))]
with open('/tmp/coco_uber_match.csv', 'wt') as f:
    writer = csv.writer(f)
    writer.writerows(map_)
with open('/tmp/coco_uber_search.csv', 'wt') as f:
    writer = csv.writer(f)
    writer.writerows(smap_)

# cocomac -> integrated connectivity terminiology mapping

def lnc(string):
    return string.lower().replace(',',' ')  # matches the conv in NIF_conn

ccslim = rdflib.Graph().parse(expanduser('~/git/NIF-Ontology/ttl/generated/cocomacslim.ttl'), format='turtle')
coco_all = [l for l in ccslim.objects(None, rdflib.RDFS.label)]

with open(expanduser('~/files/disco/NIF_conn_allcols_minimal_clean_filtered2.csv'), 'rt') as f:
    ber_rows = [r for r in csv.reader(f)]

ber_set = set([c for c in zip(*[r for r in ber_rows if r[0] == 'CoCoMac'])][1])
coco_match_lower_no_comma = set([lnc(t) for t in [c for c in zip(*map_)][0]])
coco_search_lower_no_comma = set([lnc(t) for t in [c for c in zip(*smap_)][0]])
coco_all_lower_no_comma = set([lnc(t) for t in coco_all])
matched = ber_set.intersection(coco_match_lower_no_comma)
searched = ber_set.intersection(coco_search_lower_no_comma)
alled = ber_set.intersection(coco_all_lower_no_comma)
unmapped = alled.difference(matched.union(searched))
missing = ber_set.difference(alled)

nmatch = len(matched)
nsearch = len(searched)
nall = len(alled)
nunmapped = len(unmapped)
nmissing = len(missing)

print('# matched =', nmatch)
print('# searched =', nsearch)
print('# alled =', nall)
print('# unmatched =', nunmapped)
print('# missing =', nmissing)

print('missing')
for m in sorted(missing):
    print(m)

print('unmapped')
for m in sorted(unmapped):
    print(m)

#embed()

