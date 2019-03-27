#!/usr/bin/env python3.6
from pyontutils.config import devconfig

import sys
import csv
import json
import pickle
import socket
from pathlib import Path
from itertools import chain
from collections import Counter, defaultdict
from rdflib import Graph, URIRef, Namespace, Literal
from sqlalchemy import create_engine, inspect
from pyontutils.core import createOntology
from pyontutils.utils import Async, deferred, noneMembers, anyMembers, mysql_conn_helper, TermColors as tc
from pyontutils.qnamefix import cull_prefixes
from pyontutils.scigraph import Vocabulary, Graph as sGraph
from pyontutils.namespaces import makePrefixes, PREFIXES as uPREFIXES, ilxtr, NIFRID, NIFSTD, ilxb
from pyontutils.closed_namespaces import rdf, rdfs, owl, oboInOwl
from IPython import embed

gitf = Path(devconfig.git_local_base)

def _check_dupes(thing, known=tuple()):
    test = [t for t in thing if t not in known]
    assert len(test) == len(set(test)), f'duplicate mappings to same ilx! {Counter(test).most_common()[:5]}'

def main():
    DB_URI = 'mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db}'
    if socket.gethostname() != 'orpheus':
        config = mysql_conn_helper('localhost', 'nif_eelg', 'nif_eelg_secure', 33060)  # see .ssh/config
    else:
        config = mysql_conn_helper('nif-mysql.crbs.ucsd.edu', 'nif_eelg', 'nif_eelg_secure')
    engine = create_engine(DB_URI.format(**config), echo=True)
    config = None
    del(config)

    insp = inspect(engine)
    terms = [c['name'] for c in insp.get_columns('terms')]
    term_existing_ids = [c['name'] for c in insp.get_columns('term_existing_ids')]
    #embed()
    #sys.exit()

    query = engine.execute('SELECT * FROM term_existing_ids as teid JOIN terms as t ON t.id = teid.tid WHERE t.type != "cde"')
    header = term_existing_ids + terms

    data = query.fetchall()
    cdata = list(zip(*data))

    def datal(head):
        return cdata[header.index(head)]

    ilx_labels = {ilxb[ilx_fragment]:label for ilx_fragment, label in zip(datal('ilx'), datal('label'))}

    mapping_no_sao = [p for p in zip(datal('iri'), datal('ilx')) if 'neuinfo' in p[0]]  # 9446
    mapping = [p for p in zip(datal('iri'), datal('ilx')) if 'neuinfo' in p[0] or '/sao' in p[0]]  # 9883
    done = [ilx for iri, ilx in mapping]
    obo_mapping = [p for p in zip(datal('iri'), datal('ilx')) if 'obolibrary' in p[0] and p[1] not in done]
    done = done + [ilx for iri, ilx in obo_mapping]
    db_mapping = [p for p in zip(datal('iri'), datal('ilx')) if 'drugbank' in p[0] and p[1] not in done]
    done = done + [ilx for iri, ilx in db_mapping]
    t3db_mapping = [p for p in zip(datal('iri'), datal('ilx')) if 't3db' in p[0] and p[1] not in done]
    done = done + [ilx for iri, ilx in t3db_mapping]

    wiki_mapping = [p for p in zip(datal('iri'), datal('ilx')) if 'neurolex' in p[0] and p[1] not in done]

    sao_mapping = {o.toPython():s for s, o in Graph().parse((gitf / 'nlxeol/sao-nlxwiki-fixes.ttl').as_posix(), format='ttl').subject_objects(oboInOwl.hasAlternativeId)}

    scr = Graph().parse((gitf / 'NIF-Ontology/scicrunch-registry.ttl').as_posix(), format='turtle')
    moved_to_scr = {}
    #PROBLEM = set()
    for s, o in scr.subject_objects(oboInOwl.hasDbXref):
        if 'SCR_' in o:
            print(f'WARNING Registry identifier listed as alt id! {s} hasDbXref {o}')
            continue
        uri = NIFSTD[o]
        #try:
        assert uri not in moved_to_scr, f'utoh {uri} was mapped to more than one registry entry! {s} {moved_to_scr[uri]}'
        #except AssertionError:
            #PROBLEM.add(uri)

        moved_to_scr[uri] = s

    to_scr = [(k, v) for k, v in moved_to_scr.items()
           if noneMembers(k, 'SciEx_', 'OMICS_', 'rid_', 'SciRes_',
                          'biodbcore-', 'C0085410', 'doi.org', 'C43960',
                          'doi:10.', 'GAZ:',
                          # 'birnlex_', 'nlx_', 'nif-'
                         )]

    replacement_graph = createOntology(filename='NIFSTD-ILX-mapping',
                        name='NLX* to ILX equivalents',
                        prefixes=makePrefixes('ILX'),)

    scr_rep_graph = createOntology(filename='NIFSTD-SCR-mapping',
                                   name='NLX* to SCR equivalents',
                                   prefixes=makePrefixes('SCR'),)

    _existing = {}
    def dupes(this, other, set_, dupes_):
        if this not in set_:
            set_.add(this)
            _existing[this] = other
        elif _existing[this] != other:
            dupes_[this].add(_existing[this])
            dupes_[this].add(other)

    iri_done = set()
    ilx_done = set()
    iri_dupes = defaultdict(set)
    ilx_dupes = defaultdict(set)
    def check_dupes(iri, ilx):
        dupes(iri, ilx, iri_done, iri_dupes)
        dupes(ilx, iri, ilx_done, ilx_dupes)

    BIRNLEX = Namespace(uPREFIXES['BIRNLEX'])
    trouble = [  # some are _2 issues :/
               # in interlex -- YES WE KNOW THEY DONT MATCH SOME IDIOT DID THIS IN THE PAST
               BIRNLEX['1006'],  # this one appears to be entirely novel despite a note that it was created in 2006...
               BIRNLEX['1152'],  # this was used in uberon ;_;
               BIRNLEX['2476'],  # can be owl:sameAs ed -> _2 version
               BIRNLEX['2477'],  # can be owl:sameAs ed -> _2 version
               BIRNLEX['2478'],  # can be owl:sameAs ed -> _2 version
               BIRNLEX['2479'],  # can be owl:sameAs ed -> _2 version
               BIRNLEX['2480'],  # can be owl:sameAs ed -> _2 version
               BIRNLEX['2533'],  # This is in interlex as a wiki id http://uri.interlex.org/base/ilx_0109349 since never used in the ontology, we could add it to the list of 'same as' for cosmetic purposes which will probably happen...
               BIRNLEX['3074'],  # -> CHEBI:26848  # add to slim and bridge...
               BIRNLEX['3076'],  # -> CHEBI:26195  # XXX when we go to load chebi make sure we don't dupe this...
    ]

    aaaaaaaaaaaaaaaaaaaaaaaaaaaaa = [t + '_2' for t in trouble]  # _never_ do this

    # TODO check for cases where there is an ilx and scr for the same id >_<

    sao_help = set()
    for iri, ilx_fragment in chain(mapping, to_scr):  # XXX core loop
        if iri in sao_mapping:
            uri = sao_mapping[iri]
            sao_help.add(uri)
        else:
            uri = URIRef(iri)

        if uri in trouble:
            #print('TROUBLE', iri, ilxb[ilx_fragment])
            print('TROUBLE', ilxb[ilx_fragment])

        if uri in moved_to_scr:  # TODO I think we need to have _all_ the SCR redirects here...
            s, p, o = uri, ilxtr.hasScrId, moved_to_scr[uri]
            scr_rep_graph.g.add((s, p, o))
        else:
            s, p, o = uri, ilxtr.hasIlxId, ilxb[ilx_fragment]
            #s, p, o = o, ilxtr.ilxIdFor, s
            replacement_graph.g.add((s, p, o))

        check_dupes(s, o)

    dupes = {k:v for k, v in iri_dupes.items()}
    idupes = {k:v for k, v in ilx_dupes.items()}
    assert not dupes, f'there are duplicate mappings for an external id {dupes}'
    #print(ilx_dupes)  # there are none yet

    ng = cull_prefixes(replacement_graph.g, prefixes=uPREFIXES)
    ng.filename = replacement_graph.filename

    sng = cull_prefixes(scr_rep_graph.g, prefixes=uPREFIXES)
    sng.filename = scr_rep_graph.filename


    _ = [print(k.toPython(), ' '.join(sorted(ng.qname(_.toPython()) for _ in v))) for k, v in idupes.items()]

    # run `resolver_uris = sorted(set(e for t in graph for e in t if 'uri.neuinfo.org' in e))` on a graph with everything loaded to get this file...
    resources = Path(__file__).resolve().absolute().parent / 'resources'
    with open((resources / 'all-uri.neuinfo.org-uris.pickle').as_posix(), 'rb') as f:
        all_uris = pickle.load(f)  # come in as URIRefs...
    with open((resources / 'all-uri.neuinfo.org-uris-old.pickle').as_posix(), 'rb') as f:
        all_uris_old = pickle.load(f)  # come in as URIRefs...
    with open((resources / 'all-uri.neuinfo.org-uris-old2.pickle').as_posix(), 'rb') as f:
        all_uris_old2 = pickle.load(f)  # come in as URIRefs...

    resolver_uris = set(e for t in chain(ng.g, sng.g) for e in t if 'uri.neuinfo.org' in e)
    ilx_only = resolver_uris - all_uris  # aka nlxonly
    resolver_not_ilx_only = resolver_uris - ilx_only
    problem_uris = all_uris - resolver_uris
    old_uris = all_uris_old - all_uris
    old_uris2 = all_uris_old2 - all_uris
    dold_uris = all_uris_old - all_uris_old2

    #idold_uris = all_uris_old2 - all_uris_old  # empty as expected
    #nxrefs = Graph().parse((gitf / 'NIF-Ontology/ttl/generated/nlx-xrefs.ttl').as_posix(), format='turtle')
    nxrefs = Graph().parse((gitf / 'nlxeol/nlx-xrefs.ttl').as_posix(), format='turtle')
    xrefs_uris = set(e for t in nxrefs for e in t if 'uri.neuinfo.org' in e)
    test_old_uris = old_uris2 - xrefs_uris

    diff_uris = test_old_uris - ilx_only
    #diff_uris.remove(URIRef('http://uri.neuinfo.org/nif/nifstd/nlx_149160'))  # ORNL was included in an old bad version of the xrefs file and was pulled in in the old all-uris  # now dealt with by the scr mapping
    diff_uris.remove(URIRef('http://uri.neuinfo.org/nif/nifstd/nlx_40280,birnlex_1731'))  # one of the doubled neurolex ids
    diff_uris.remove(URIRef('http://uri.neuinfo.org/nif/nifstd'))  # i have zero idea how this snuck in
    assert not diff_uris, 'old uris and problem uris should be identical'

    _ilx = set(e for t in ng.g for e in t)
    _scr = set(e for t in sng.g for e in t)
    for uri in ilx_only:
        if uri in _ilx and uri in _scr:
            raise BaseException('AAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
        elif uri in _ilx:
            g = ng.g
        elif uri in _scr:
            g = sng.g
        else:
            raise BaseException('????????????')
        g.add((uri, ilxtr.isDefinedBy, URIRef('http://neurolex.org')))

    # XXX write the graphs
    ng.write()
    sng.write()

    nsuris = set(uri for uri, ilx in mapping_no_sao)
    auris = set(_.toPython() for _ in all_uris)
    iuris = set(_.toPython() for _ in resolver_uris)
    #sao_missing = iuris - nsuris  # now fixed and cannot run due to addition of scr ids to resolver_uris
    #assert not sao_missing, f'whoops {sao_missing}'
    ilx_missing = auris - iuris
    all_missing = iuris - auris
    #assert not all_missing, f'all is not all! {all_missing}'  # XXX have to deal with ilx_only separately as NLX-ILX or something

    # fixed
    #sao_add = {o.toPython():s.toPython() for s, p, o in ng.g if s.toPython() in sao_missing}
    #assert len(sao_add) == len(sao_missing), 'EEEEEEEEEEEEEEE'
    #with open('/tmp/please-add-these-sao-ids-as-existing-ids-to-the-listed-interlex-record.json', 'wt') as f:
        #json.dump(sao_add, f, indent=2)

    to_review = sorted(ilx_missing)

    # not relevant anymore
    #with open('thought-to-be-missing.json', 'rt') as f:
        #thought_to_be_missing = json.load(f)

    # from troy has issues
    #with open('nifext-duplicates-and-new.json', 'rt') as f:
        #nifext_data = json.load(f)

    #nifext_dupes = {v['current_nifext_id']:v['dropped_nifext_ids'][-1] if v['dropped_nifext_ids'] else None for v in nifext_data.values()}

    sgv = Vocabulary(cache=True)
    trts = [(v, (sgv.findById(v)['labels'][0]
                 if sgv.findById(v)['labels']
                 else '<--NO-LABEL-->')
             if sgv.findById(v)
             else '<------>')
            for v in to_review]

    sgg = sGraph(cache=True)
    SGG = Namespace(sgg._basePath.rstrip('/') + '/graph/')
    rg = Graph().parse((gitf / 'NIF-Ontology/ttl/unused/NIF-Retired.ttl').as_posix(), format='turtle')
    retired = set(e.toPython() for t in rg for e in t if 'uri.neuinfo.org' in e)
    retfile = '<ttl/unused/NIF-Retired.ttl>'
    help_graph = createOntology(filename='NIFSTD-BLACKHOLE-mapping',
                        name='HELPPPPPPPP!!!!',
                        prefixes=uPREFIXES,)
    def make_rt(to_review_tuples, retired=retired):
        def inner(u, l, retired=retired):
            ne = sgg.getNeighbors(u, relationshipType="isDefinedBy", depth=1)
            if ne:
                curie = help_graph.qname(u)
                help_graph.g.add((URIRef(u), ilxtr.SciGraphLookup, URIRef(f'http://scigraph.olympiangods.org/scigraph/graph/{curie}')))
            if ne and ne['edges']:
                src = ' '.join([f'<{e["obj"]}>' for e in ne["edges"]])
            elif u in retired:
                src = retfile
            else:
                src = '<>'
            return f'{u:<70} {l:<50} {src}'
        out = Async(rate=3000)(deferred(inner)(u, l) for u, l in sorted(to_review_tuples, key=lambda a:a[-1]))
        return '\n'.join(out)

    review_text = make_rt(trts)
    trts2 = [(u, l) for u, l in trts if 'nifext' not in u]
    not_nifext = make_rt(trts2)

    hng = cull_prefixes(help_graph.g, prefixes=uPREFIXES)
    hng.filename = help_graph.filename
    hng.write()

    ###
    #   Accounting of uri.neuinfo.org ids that do not resolve
    ###

    not_in_interlex = set(s for s, o in hng.g.subject_objects(ilxtr.SciGraphLookup))
    bh_deprecated = set(s for s in hng.g.subjects() if sgv.findById(s) and sgv.findById(s)['deprecated'])
    bh_not_deprecated = set(s for s in hng.g.subjects() if sgv.findById(s) and not sgv.findById(s)['deprecated'])
    bh_nifexts = set(s for s in bh_not_deprecated if 'nifext' in s)
    bh_readable = set(s for s in bh_not_deprecated if 'readable' in s)
    unaccounted = not_in_interlex - bh_readable - bh_nifexts - bh_deprecated
    namedinds = set(s for s in unaccounted
                    if sgv.findById(s) and
                    sgg.getNode(s)['nodes'][0]['meta']['types'] and
                    sgg.getNode(s)['nodes'][0]['meta']['types'][0] == 'NamedIndividual')
    unaccounted = unaccounted - namedinds
    ual = sorted(o for s in unaccounted for o in hng.g.objects(s, ilxtr.SciGraphLookup))
    report = (
        f'Total       {len(not_in_interlex)}\n'
        f'deprecated  {len(bh_deprecated)}\n'
        f'nd nifext   {len(bh_nifexts)}\n'
        f'nd readable {len(bh_readable)}\n'
        f'nd namedind {len(namedinds)}\n'
        f'unaccounted {len(unaccounted)}\n'
             )
    print(report)

    def reverse_report():
        ilx = Graph()
        ilx.parse('/tmp/interlex.ttl', format='turtle')
        not_in_ontology = set()
        annotations = set()
        relations = set()
        drugbank = set()
        t3db = set()
        for subject in ilx.subjects(rdf.type, owl.Class):
            ok = False
            for object in ilx.objects(subject, oboInOwl.hasDbXref):
                if anyMembers(object, 'uri.neuinfo.org', 'GO_', 'CHEBI_', 'PR_',
                              'PATO_', 'HP_', 'OBI_', 'DOID_', 'COGPO_', 'CAO_',
                              'UBERON_', 'NCBITaxon_', 'SO_', 'IAO_'):
                    # FIXME doe we areally import HP?
                    ok = True
                
                if (subject, rdf.type, owl.AnnotationProperty) in ilx:  # FIXME for troy these need to be cleared up
                    annotations.add(subject)
                elif (subject, rdf.type, owl.ObjectProperty) in ilx:
                    relations.add(subject)
                elif 'drugbank' in object:
                    drugbank.add(subject)
                elif 't3db.org' in object:
                    t3db.add(subject)

            if not ok:
                not_in_ontology.add(subject)


        drugbank = drugbank & not_in_ontology
        t3db = t3db & not_in_ontology
        annotations = annotations & not_in_ontology
        relations = relations & not_in_ontology
        unaccounted = not_in_ontology - drugbank - t3db - annotations - relations
        report = (
            f'Total       {len(not_in_ontology)}\n'
            f'annotations {len(annotations)}\n'
            f'relations   {len(relations)}\n'
            f'drugbank    {len(drugbank)}\n'
            f't3db        {len(t3db)}\n'
            f'unaccounted {len(unaccounted)}\n'
        )
        print(report)
        return (not_in_ontology, drugbank, unaccounted)

    _, _, un = reverse_report()

    h_uris = set(e for t in hng.g for e in t if 'uri.neuinfo.org' in e)
    real_problems = problem_uris - h_uris

    ###
    #   Missing neurons
    ###

    with open((gitf / 'nlxeol/neuron_data_curated.csv').as_posix()) as f:
        r = csv.reader(f)
        nheader = next(r)
        rows = list(r)

    ndata = list(zip(*rows))

    def datan(head):
        return ndata[nheader.index(head)]

    if __name__ == '__main__':
        embed()

###
#   ============================ crazy curation below seek no reason here
###

def would_you_like_to_know_more_question_mark():

    # resolving differences between classes
    more_ids = set((
        'http://uri.neuinfo.org/nif/nifstd/readable/ChEBIid',
        'http://uri.neuinfo.org/nif/nifstd/readable/GOid',
        'http://uri.neuinfo.org/nif/nifstd/readable/MeshUid',
        'http://uri.neuinfo.org/nif/nifstd/readable/PMID',
        'http://uri.neuinfo.org/nif/nifstd/readable/UmlsCui',
        'http://uri.neuinfo.org/nif/nifstd/readable/bamsID',
        'http://uri.neuinfo.org/nif/nifstd/readable/bonfireID',
        'http://uri.neuinfo.org/nif/nifstd/readable/cell_ontology_ID',
        'http://uri.neuinfo.org/nif/nifstd/readable/definingCitationID',
        'http://uri.neuinfo.org/nif/nifstd/readable/definingCitationURI',
        'http://uri.neuinfo.org/nif/nifstd/readable/emapMouseStageDataID',
        'http://uri.neuinfo.org/nif/nifstd/readable/emapMouseStageDiagramID',
        'http://uri.neuinfo.org/nif/nifstd/readable/externalSourceId',
        'http://uri.neuinfo.org/nif/nifstd/readable/externalSourceURI',
        'http://uri.neuinfo.org/nif/nifstd/readable/gbifID',
        'http://uri.neuinfo.org/nif/nifstd/readable/gbifTaxonKeyID',
        'http://uri.neuinfo.org/nif/nifstd/readable/gene_Ontology_ID',
        #'http://uri.neuinfo.org/nif/nifstd/readable/hasExternalSource',
        'http://uri.neuinfo.org/nif/nifstd/readable/hasGenbankAccessionNumber',
        'http://uri.neuinfo.org/nif/nifstd/readable/imsrStandardStrainName',
        'http://uri.neuinfo.org/nif/nifstd/readable/isReplacedByClass',
        'http://uri.neuinfo.org/nif/nifstd/readable/jaxMiceID',
        'http://uri.neuinfo.org/nif/nifstd/readable/ncbiTaxID',
        'http://uri.neuinfo.org/nif/nifstd/readable/neuronamesID',
        'http://uri.neuinfo.org/nif/nifstd/readable/nifID',
        'http://uri.neuinfo.org/nif/nifstd/readable/sao_ID',
        'http://uri.neuinfo.org/nif/nifstd/readable/umls_ID',
        'http://www.geneontology.org/formats/oboInOwl#id',
    ))

    outside = []
    eee = {}
    resolver_not_ilx_only_but_not_in_scigraph = set()  # resources.ttl
    _res = Graph().parse((gitf / 'NIF-Ontology/ttl/resources.ttl').as_posix(), format='turtle')
    reslookup = {uri:[l] for uri, l in _res.subject_objects(rdfs.label)}
    for uri in chain(h_uris, resolver_not_ilx_only):
        if 'uri.neuinfo.org' in uri:
            try:
                meta = sgg.getNode(uri.toPython())['nodes'][0]['meta']
                asdf = {hng.qname(k):v for k, v in meta.items() if k in more_ids}
            except TypeError:
                resolver_not_ilx_only_but_not_in_scigraph.add(uri)  # resources.ttl ;)
                if uri in reslookup:  # no differentia
                    asdf = False
                else:
                    asdf = False
                    print('WTF', uri)
            if asdf:
                #print(uri, asdf)
                eee[uri] = asdf
                for l in asdf.values():
                    for e in l:
                        outside.append(e)

    outside_dupes = [v for v, c in Counter(outside).most_common() if c > 1]
    eee_dupes = {k:v for k, v in eee.items() if anyMembers(outside_dupes, *(e for l in v.values() for e in l))}

    #for uri, meta in sorted(eee_dupes.items(), key=lambda a:sorted(a[1].values())):
        #print(uri.toPython(), sorted((e.replace('PMID: ', 'PMID:'), k) for k, l in meta.items() for e in l))


    # attempt to deal with label mappings
    iexisting = defaultdict(set)
    iiexisting = {}
    for i, existing in zip(datal('ilx'), datal('iri')):
        #if 'uri.neuinfo.org' in existing:
        if 'interlex.org' not in existing and 'neurolex.org' not in existing:
            iexisting[i].add(URIRef(existing))
            iiexisting[URIRef(existing)] = i
    iexisting = {**iexisting}

    _ilabs = {k:l for k, l in zip(datal('ilx'), datal('label'))}
    def inner(iri):
        resp = sgv.findById(iri)
        if resp is not None:
            l = resp['labels']
        else:
            l = [] #_ilabs[iiexisting[iri]] + '** already in ilx **']
            #print('trouble?', iri)  # ilx only
        return iri, l

    #labs = {k:v[0] if v else '<--NO-LABEL-->' for k, v in Async()(deferred(inner)(id_) for id_ in chain(h_uris, (e for s in iexisting.values() for e in s)))}
    labs = {k:v[0] if v else '<--NO-LABEL-->' for k, v in Async()(deferred(inner)(id_) for id_ in h_uris)}
    ilabs = {k:l.lower() for k, l in zip(datal('ilx'), datal('label'))}
    iilabs = {v:k for k, v in ilabs.items()}
    assert len(ilabs) == len(iilabs)
    missing_map = {k:iilabs[v.lower()] for k, v in labs.items() if v and v.lower() in iilabs}  # XXX this is not valid

    missing_existing = {i:[m, *iexisting[i]] for m, i in missing_map.items() if i in iexisting}

    missing_equivs = {next(iter(iexisting[i])):i for m, i in missing_map.items() if i in iexisting}

    eid = NIFRID.externalSourceId.toPython()
    ded = owl.deprecated.toPython()
    # SP: -> swissprot vs uniprot
    mmr = []
    proto_mmr_1_to_1 = {}
    arrr = defaultdict(set)
    uniprot_iuphar = set()
    for uri, ilx_frag in {**missing_equivs, **missing_map}.items():
        uri = URIRef(uri)
        try:
            meta = sgg.getNode(uri.toPython())['nodes'][0]['meta']
        except TypeError:
            # just ignore these, they are ilx only :/
            meta = {}
        if eid in meta:
            src = meta[eid][0]
            if src.startswith('SP:'):
                src = tc.yellow(src.replace('SP:', 'http://www.uniprot.org/uniprot/'))
            #elif src.startswith('IUPHAR:'):
                #pass
            #else:
                #src = 'TODO'
        elif ded in meta and meta[ded]:
            src = tc.red('ded ')
        else:
            src = 'TODO'
        val = labs[uri] if uri in labs else _ilabs[ilx_frag] + ' **'
        if uri in eee:
            differentia = str(eee[uri])
            for v in eee[uri].values():
                for e in v:
                    arrr[e].add(uri)
                    if 'SP:' in e or 'IUPHAR:' in e:
                        uniprot_iuphar.add(uri)
        else:
            differentia = ''

        if uri in _ilx and uri in all_uris:
            ruri = SGG[hng.qname(uri)]
            ruri = tc.blue(f'{ruri:<60}')
        else:
            ruri = uri
            ruri = f'{ruri:<60}'

        v = ' '.join((f'{val:<60}',
                      src,
                      ruri,
                      ilxb[ilx_frag],
                      differentia))
        mmr.append(v)
        proto_mmr_1_to_1[uri] = v
        src = None

    arrr = {**arrr}
    arrr_not_1_to_1 = {k:v for k, v in arrr.items() if len(v) > 1}
    #arrr_n11_uris = set((u.toPython() for v in arrr_not_1_to_1.values() for u in v))
    arrr_n11_uris = set.union(*arrr_not_1_to_1.values())
    mmr_1_to_1 = {k:v for k, v in proto_mmr_1_to_1.items() if k not in arrr_n11_uris}
    no_uniprot = {k:v for k, v in proto_mmr_1_to_1.items() if k not in uniprot_iuphar}
    arrr_n11_text = '\n'.join(f'{k:<15} {sorted(_.toPython() for _ in v)}' for k, v in arrr_not_1_to_1.items())
    mmr.sort()
    mmr_text = '\n'.join(mmr)

    mmr_1_to_1_text = '\n'.join(sorted(mmr_1_to_1.values()))

    no_uniprot_text = '\n'.join(sorted(no_uniprot.values()))

    # XXX run these manually
    #print(review_text)
    #print(not_nifext)
    #print(mmr_text)

    # nifext is a major source here, they need to be mapped in, but probably ok
    #  many of the nifext 'identical' case are where we had used an iuphar id as the
    #  generic id and then had uniprot as the variants *screaming* makes sense but
    #  not clear why it was ever done this way :/
    #  http://pharmrev.aspetjournals.org/content/50/2/271.long  IUPHAR receptor codes were dumped WTF
    #  no one seems to be using them WHY DO WE HAVE THEM IN THE ONTOLOGY *screaming*

    #embed()

# would_you_like_to_know_more_question_mark()


if __name__ == '__main__':
    main()
