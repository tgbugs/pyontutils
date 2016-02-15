#!/usr/bin/env python3

import re
from os.path import expanduser
from collections import namedtuple
import rdflib
import requests
from scigraph_client import Vocabulary, Graph
from IPython import embed

v = Vocabulary()
g = Graph()

abagraph = rdflib.Graph()
abagraph.parse(expanduser('~/git/NIF-Ontology/ttl/abaslim.ttl'), format='turtle')
abagraph.parse(expanduser('~/git/NIF-Ontology/ttl/aba-bridge.ttl'), format='turtle')
nses = {k:rdflib.Namespace(v) for k, v in abagraph.namespaces()}
#nses['ABA'] = nses['MBA']  # enable quick check against the old xrefs
syn_iri = nses['OBOANN']['synonym']
acro_iri = nses['OBOANN']['acronym']
abasyns = {}
abalabs = {}
abaacro = {}
ABA_PREFIX = 'MBA:'
#ABA_PREFIX = 'ABA:'  # all bad
for sub in abagraph.subjects(rdflib.RDF.type, rdflib.OWL.Class):
    if not sub.startswith(nses[ABA_PREFIX[:-1]]['']):
        continue
    subkey = ABA_PREFIX + sub.rsplit('/',1)[1]
    sub = rdflib.URIRef(sub)
    abalabs[subkey] = [o for o in abagraph.objects(rdflib.URIRef(sub), rdflib.RDFS.label)][0].toPython()
    syns = []
    for s in abagraph.objects(sub, syn_iri):
        syns.append(s.toPython())
    abasyns[subkey] = syns

    abaacro[subkey] = [a.toPython() for a in abagraph.objects(sub, acro_iri)]

url = 'http://api.brain-map.org/api/v2/tree_search/Structure/997.json?descendants=true'
resp = requests.get(url).json()

ids = set([ABA_PREFIX + str(r['id']) for r in resp['msg']])
Query = namedtuple('Query', ['id','relationshipType', 'direction', 'depth'])
#uberon = Query('UBERON:0000955', 'http://purl.obolibrary.org/obo/BFO_0000050', 'INCOMING', 9)
uberon = Query('UBERON:0001062', 'subClassOf', 'INCOMING', 10)  # anatomical entity
output = g.getNeighbors(**uberon.__dict__)

# TODO figure out the superclass that can actually get all the brain parts

meta_edge = 'http://www.geneontology.org/formats/oboInOwl#hasDbXref'

u_a_map = {}
a_u_map = {}
uberon_syns = {}
uberon_labs = {}
syn_types = {
    'http://www.geneontology.org/formats/oboInOwl#hasBroadSynonym':'Broad',
    'http://www.geneontology.org/formats/oboInOwl#hasExactSynonym':'Exact',
    'http://www.geneontology.org/formats/oboInOwl#hasNarrowSynonym':'Narrow',
    'http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym':'Related',
}
for node in output['nodes']:
    curie = node['id']
    uberon_labs[curie] = node['lbl']
    uberon_syns[curie] = {}
    if 'synonym' in node['meta']:
        for stype in syn_types:
            if stype in node['meta']:
                uberon_syns[curie][stype] = node['meta'][stype]

    if meta_edge in node['meta']:
        xrefs = node['meta'][meta_edge]
        mba_ref = [r for r in xrefs if r.startswith(ABA_PREFIX)]
        u_a_map[curie] = mba_ref
        if mba_ref:
            for mba in mba_ref:
                a_u_map[mba] = curie
    else:
        u_a_map[curie] = None

def make_record(uid, aid):  # edit this to change the format
    to_format = ('{uberon_id: <20}{uberon_label:}\n'
                 '{aba_id: <20}{aba_label}\n'
                 '------ABA  SYNS------\n'
                 '{aba_syns}\n'
                 '-----UBERON SYNS-----\n'
                 '{uberon_syns}\n'
                )
    uberon_syn_rec = uberon_syns[uid]
    insert_uberon = []
    for edge, syns in sorted(uberon_syn_rec.items()):
        insert_uberon.append('--{abv}--\n{syns}'.format(abv=syn_types[edge], syns='\n'.join(sorted(syns))))

    kwargs = {
        'uberon_id':uid,
        'uberon_label':uberon_labs[uid],
        'aba_id':aid,
        'aba_label':abalabs[aid],
        'aba_syns':'\n'.join(sorted(abasyns[aid] + abaacro[aid])),
        'uberon_syns':'\n'.join(insert_uberon)
    }
    return to_format.format(**kwargs)

text = '\n\n'.join([make_record(uid, aid[0]) for uid, aid in sorted(u_a_map.items()) if aid])

with open('aba_uberon_syn_review.txt', 'wt') as f:
    f.write(text)

print('total uberon terms checked:', len(uberon_labs))
print('total aba terms:           ', len(abalabs))
print('total uberon with aba xref:', len([a for a in u_a_map.values() if a]))

#embed()

