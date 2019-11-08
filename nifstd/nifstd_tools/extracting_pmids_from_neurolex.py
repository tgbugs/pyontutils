from collections import defaultdict
import csv
from pathlib import Path
import os
from rdflib import Graph, URIRef, Literal, BNode, RDF, RDFS, OWL
from sqlalchemy import create_engine, inspect, Table, Column
from sqlalchemy.orm.session import sessionmaker
from pyontutils import utils
from pyontutils.config import auth
from typing import Dict, Tuple, List, Union


db_url = os.environ.get('SCICRUNCH_DB_URL_PRODUCTION')
ilx_uri_base = 'http://uri.interlex.org/base'
triple2annotation_bnode = {}
g = Graph()

olr = auth.get_path('ontology-local-repo')
output = olr / 'ttl/generated/neurolex_to_interlex_pmids.ttl'

namespaces = {
    'ILX': 'http://uri.interlex.org/base/ilx_',
    'definition': 'http://purl.obolibrary.org/obo/IAO_0000115',
    'ilxtr': 'http://uri.interlex.org/tgbugs/uris/readable/',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'PMID': 'https://www.ncbi.nlm.nih.gov/pubmed/',
    'NIFSTD': 'http://uri.neuinfo.org/nif/nifstd/',
    'BIRNLEX': 'http://uri.neuinfo.org/nif/nifstd/birnlex_',
    'UBERON': 'http://purl.obolibrary.org/obo/UBERON_',
    'PR': 'http://purl.obolibrary.org/obo/PR_',
}

for prefix, uri in namespaces.items():
    g.bind(prefix, uri)


def add_annotation(
        subj: URIRef,
        pred: URIRef,
        obj: Union[Literal, URIRef],
        a_p: URIRef ,
        a_o: Union[Literal, URIRef],
    ) -> BNode:
    """ Adds annotation to rdflib graph.

    The annotation axiom will filled in if this is a new annotation for the triple.

    Args:
        subj: Entity subject to be annotated
        pref: Entities Predicate Anchor to be annotated
        obj: Entities Object Anchor to be annotated
        a_p: Annotation predicate
        a_o: Annotation object

    Returns:
        A BNode which is an address to the location in the RDF graph that is storing the
        annotation information.
    """
    bnode: BNode = triple2annotation_bnode.get( (subj, pred, obj) )
    if not bnode:
        a_s: BNode = BNode()
        triple2annotation_bnode[ (subj, pred, obj) ]: BNode = a_s
        g.add((a_s, RDF.type, OWL.Axiom))
        g.add((a_s, OWL.annotatedSource, subj))
        g.add((a_s, OWL.annotatedProperty, pred))
        g.add((a_s, OWL.annotatedTarget, obj))
    else:
        a_s: BNode = bnode
    g.add( (a_s, a_p, a_o) )
    return bnode # In case you have more triples to add


def get_existing_ids():
    Session = sessionmaker()
    engine = create_engine(db_url)
    Session.configure(bind=engine)
    session = Session()
    sql = f"""
        SELECT
            tei.id, tei.tid, tei.curie, tei.iri, tei.preferred,
            t.ilx, t.type, t.label, t.definition, t.comment
        FROM (
            SELECT *
            FROM terms
            GROUP BY terms.ilx
        ) as t
        JOIN term_existing_ids AS tei
        ON t.id = tei.tid
    """ # groub by will just take the first occurance and drop the rest
    sqlobj = session.execute(sql)
    return sqlobj


def get_suffix2row():
    suffix2row = {}
    for row in get_existing_ids():
         suffix2row[row.iri.rsplit('/', 1)[-1]] = {
            'ilx': row.ilx, 'curie': row.curie, 'iri': row.iri, 'definition':row.definition,
        }
    return suffix2row


def pmid_fix(string):
    def uni_strip(s):
        return s.replace('PMID=', '').replace('PMID:', '').replace('.', '').strip()
    if ',' in string:
        obj = [uni_strip(s) for s in string.split(',')]
    elif ';' in string:
        obj = [uni_strip(s) for s in string.split(';')]
    else:
        obj = [uni_strip(string)]
    new_obj = []
    for o in obj:
        if 'PMID' in o:
            new_obj.append(o.split('PMID')[-1].strip())
        else:
            new_obj.append(o)
    obj = new_obj
    new_obj = []
    for o in obj:
        try:
            if 'pmc' not in o.lower():
                int(o)
            new_obj.append(o)
        except:
            count = 0
            for e in o:
                try:
                    int(e)
                    count += 1
                except:
                    pass
            if count > 0:
                print(o) #p357, D011919 D-- is a literal ID of the mesh annotation
    return new_obj


def add_uri(ID):
    if 'nlx_' in ID or 'birnlex_' in ID or 'sao' in ID or 'BAMSC' in ID:
        return 'http://uri.neuinfo.org/nif/nifstd/' + ID
    elif 'UBERON' in ID:
        return 'http://purl.obolibrary.org/obo/UBERON_' + ID.split('_')[-1]
    else:
        print('Warning: ', ID, 'does not have a stored prefix')
        return 'http://uri.neuinfo.org/nif/nifstd/' + ID


def main():
    with open('/home/tmsincomb/Dropbox/PMID/pmid-dump.tsv', 'r') as csvFile:  # FIXME what is this file? where did it come from?
        reader = csv.reader(csvFile, delimiter='\t')
        old_text = []
        for i, row in enumerate(reader):
            if i == 0:
                header = {colname: col_indx for col_indx, colname in enumerate(row)}
                continue
            old_text.append(row[header['old_text']])

    data = [text for text in old_text
        if 'SuperCategory=Resource' not in text and 'Id=\\n' not in text and 'PMID=\\n' not in text]

    ### PRIMER
    id_count, pmid_count, definition_count = 0, 0, 0
    total_data = {}
    id2def = {}
    for d in data:
        local_data = {'id':None, 'pmids':set(), 'definition':None}
        for segment in d.split('|'):
            if 'Id=' == segment[:3]:
                id_count += 1
                local_data['id'] = segment
            if 'PMID=' == segment[:5]:
                if 'nlx_12' in segment:
                    print(segment)
                pmid_count += 1
                local_data['pmids'].add(segment)
            if 'Definition=' == segment[:11]:
                definition_count += 1
                local_data['definition'] = segment.split('Definition=')[-1].replace('\\n', '')
        if local_data['id'] and local_data['pmids'] and local_data['definition']:
            total_data[local_data['id']] = local_data['pmids']
            id2def[local_data['id']] = local_data['definition']
    print(id_count, pmid_count, definition_count)

    ### Nuances
    raw_id2pmids = total_data
    total_data = defaultdict(list)
    clean_id2def = {}
    for exid, pmids in raw_id2pmids.items():
        curr_def = id2def[exid]
        for hit in exid.split('\\n'):
            if 'Id=' in hit:
                clean_id = hit.replace('Id=', '').strip()

        clean_pmids = []
        for hit in [pmid.split('\\n') for pmid in pmids]:
            for h in hit:
                if 'PMID=' in h:
                    h = pmid_fix(h)
                    clean_pmids.extend(h)
        if clean_pmids:
            total_data[clean_id].extend(clean_pmids)
            clean_id2def[clean_id] = curr_def
    suffix2pmids = total_data

    ### Annotation Creation
    suffix2row = get_suffix2row()
    for _id, pmids in suffix2pmids.items():
        row = suffix2row.get(_id)
        definition = Literal(clean_id2def[_id])
        if row:
            for pmid in pmids:
                ilx_uri = URIRef('/'.join([ilx_uri_base, row['ilx']]))
                g.add((
                    URIRef(row['iri']),
                    URIRef('http://uri.interlex.org/tgbugs/uris/readable/literatureCitation'),
                    URIRef('https://www.ncbi.nlm.nih.gov/pubmed/'+pmid),
                ))
                add_annotation(
                    URIRef(row['iri']),
                    URIRef('http://purl.obolibrary.org/obo/IAO_0000115'),
                    definition,
                    URIRef('http://uri.interlex.org/tgbugs/uris/readable/literatureCitation'),
                    URIRef('https://www.ncbi.nlm.nih.gov/pubmed/'+pmid),
                )
        else:
            for pmid in pmids:
                add_annotation(
                    URIRef(add_uri(str(_id))),
                    URIRef('http://purl.obolibrary.org/obo/IAO_0000115'),
                    definition,
                    URIRef('http://uri.interlex.org/tgbugs/uris/readable/literatureCitation'),
                    URIRef('https://www.ncbi.nlm.nih.gov/pubmed/'+pmid),
                )

    g.serialize(output, format='nifttl')


if __name__ == '__main__':
    main()
