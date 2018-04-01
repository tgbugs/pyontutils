#!/usr/bin/env python3

import re
from pathlib import Path
from collections import namedtuple, OrderedDict
import rdflib
import requests
from pyontutils.scigraph import Vocabulary, Graph
from pyontutils.obo_io import OboFile, Header, Term, TVPair
from pyontutils.core import makePrefixes, createOntology
from IPython import embed

current_file = Path(__file__).absolute()
gitf = current_file.parent.parent.parent

v = Vocabulary(cache=True)
g = Graph(cache=True)

def main():
    abagraph = rdflib.Graph()
    abagraph.parse((gitf / 'NIF-Ontology/ttl/generated/parcellation/mbaslim.ttl').as_posix(), format='turtle')
    abagraph.parse((gitf / 'NIF-Ontology/ttl/bridge/aba-bridge.ttl').as_posix(), format='turtle')
    nses = {k:rdflib.Namespace(v) for k, v in abagraph.namespaces()}
    #nses['ABA'] = nses['MBA']  # enable quick check against the old xrefs
    syn_iri = nses['NIFRID']['synonym']
    acro_iri = nses['NIFRID']['acronym']
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
    output = g.getNeighbors(**uberon._asdict())

    # TODO figure out the superclass that can actually get all the brain parts

    meta_edge = 'http://www.geneontology.org/formats/oboInOwl#hasDbXref'

    u_a_map = {}
    a_u_map = {}
    uberon_syns = {}
    uberon_labs = {}
    syn_types = {
        'http://www.geneontology.org/formats/oboInOwl#hasExactSynonym':'Exact',
        'http://www.geneontology.org/formats/oboInOwl#hasNarrowSynonym':'Narrow',
        'http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym':'Related',
        'http://www.geneontology.org/formats/oboInOwl#hasBroadSynonym':'Broad',
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

    def obo_output():  # oh man obo_io is a terrible interface for writing obofiles :/
        for aid in abalabs:  # set aids not in uberon to none
            if aid not in a_u_map:
                a_u_map[aid] = None

        e = OboFile()
        n = OboFile()
        r = OboFile()
        b = OboFile()
        name_order = 'Exact', 'Narrow', 'Related', 'Broad'
        rev = {v:k for k, v in syn_types.items()}  # sillyness
        syn_order = [rev[n] for n in name_order]

        files_ = {rev['Broad']:b, rev['Exact']:e, rev['Narrow']:n, rev['Related']:r}
        for aid, uid in sorted(a_u_map.items()):
            id_line = 'id: ' + aid
            lines = []
            lines.append(id_line)
            lines.append('name: ' + abalabs[aid])
            if uid in uberon_syns:
                syns = uberon_syns[uid]
            else:
                syns = {}

            for syn_type in syn_order:
                f = files_[syn_type]
                if syn_types[syn_type] == 'Exact' and uid is not None:
                    syn_line = 'synonym: "' + uberon_labs[uid] + '" ' + syn_types[syn_type].upper() + ' [from label]'
                    lines.append(syn_line)
                if syn_type in syns:
                    for syn in sorted(syns[syn_type]):
                        syn_line = 'synonym: "' + syn + '" ' + syn_types[syn_type].upper() + ' []'
                        lines.append(syn_line)
                block = '\n'.join(lines)
                term = Term(block, f)

        e.filename = 'e-syns.obo'
        n.filename = 'en-syns.obo'
        r.filename = 'enr-syns.obo'
        b.filename = 'enrb-syns.obo'
        for f in files_.values():
            h = Header('format-version: 1.2\nontology: %s\n' % f.filename)
            h.append_to_obofile(f)
            f.write(f.filename)
        #embed()

    #obo_output()

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

    #text = '\n\n'.join([make_record(uid, aid[0]) for uid, aid in sorted(u_a_map.items()) if aid])

    #with open('aba_uberon_syn_review.txt', 'wt') as f:
        #f.write(text)

    print('total uberon terms checked:', len(uberon_labs))
    print('total aba terms:           ', len(abalabs))
    print('total uberon with aba xref:', len([a for a in u_a_map.values() if a]))

    ubridge = createOntology('uberon-parcellation-mappings', 'Uberon Parcellation Mappings',
                             makePrefixes('owl', 'ilx', 'UBERON', 'MBA'))
    for u, arefs in u_a_map.items():
        if arefs:
            # TODO check for bad assumptions here
            ubridge.add_trip(u, 'ilx:delineatedBy', arefs[0])
            ubridge.add_trip(arefs[0], 'ilx:delineates', u)

    ubridge.write()
    if __name__ == '__main__':
        embed()

if __name__ == '__main__':
    main()
