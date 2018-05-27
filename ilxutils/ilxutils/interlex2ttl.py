#!/usr/local/Cellar/python3/3.6.1/bin/python3.6
import sys
from datetime import date
from pyontutils.utils import *
from pyontutils.core import *
from sqlalchemy import create_engine, inspect, Table, Column
import pandas as pd
from datetime import date
import progressbar
import pathlib
from ilxutils.args_reader import read_args

args = read_args()
TODAY = date.isoformat(date.today())
engine = create_engine(args.db_url)
p = pathlib.PurePath(args.output)



def createBar(maxval):
    return progressbar.ProgressBar(maxval=maxval, \
        widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])

def create_graph(filename):
    g = createOntology(filename=filename,
                       name='Interlex Total',
                       prefixes={**{'Testernvs':'http://whatever.com/'},
                                    **makePrefixes('ILXREPLACE',
                                             'ilx',
                                             'NIFRID',
                                             'NCBIGene',
                                             'NCBITaxon',
                                             'skos',
                                             'owl',
                                             'definition',
                                             'ILX',
                                             'ilxtr',
                                             'oboInOwl',
                                             )},
                       shortname=str(p.stem),
                       version='0.1',
                       remote_base='http://uri.interlex.org/ontologies/',
                       path='',
                       local_base=str(p.parent))
    return g

def helper_pref_filter(iri_list, pref_list, terms_ilx):
    '''
    === if ilx exists and pref label exists ===
    >>> iri_list = ['http://uri.interlex.org/base/ilx_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213']
    >>> pref_list = [1, 0, 0]; terms_ilx = 'ilx:tmp_0'
    >>> helper_pref_filter(iri_list, pref_list, terms_ilx)
    ('http://uri.interlex.org/base/ilx_5214', ['http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213'])

    === if ilx does not exist and pref label does ===
    >>> iri_list = ['http://uri.interlex.org/base/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5214']
    >>> pref_list = [0, 0, 0]; terms_ilx = 'ilx:tmp_0'
    >>> helper_pref_filter(iri_list, pref_list, terms_ilx)
    ('ilx:tmp_0', ['http://uri.interlex.org/base/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5214'])

    === if ilx does not exist but pref label exists ===
    >>> iri_list = ['http://pref.com/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5214']
    >>> pref_list = [1, 0, 0]; terms_ilx = 'ilx:tmp_0'
    >>> helper_pref_filter(iri_list, pref_list, terms_ilx)
    ('ilx:tmp_0', ['http://pref.com/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5214'])
    '''
    if 1 in pref_list:
        pref_index = pref_list.index(1)
        if '/ilx' in iri_list[pref_index]:
            nonpref_iris = [iri for iri in iri_list if iri != iri_list[pref_index]]
            return iri_list[pref_index], nonpref_iris

    for i, iri in enumerate(iri_list):
        if 'ilx' in iri:
            index = i
    try:
        ilx_iri = iri_list[index] #ilx is auto preferred right here
    except:
        ilx_iri = 'http://uri.interlex.org/base/' + terms_ilx
        iri_list.append(ilx_iri)
    return ilx_iri, iri_list

def get_pref_unpref_iris(seg_df, terms_ilx):
    '''
    === if ilx exists and pref label exists ===
    >>> iri = {'iri':['http://uri.interlex.org/base/ilx_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213']}
    >>> preferred = {'preferred':[1,0,0]}
    >>> seg_df = pd.DataFrame({**iri, **preferred})
    >>> terms_ilx = 'ilx:tmp_0'
    >>> get_pref_unpref_iris(seg_df, terms_ilx)
    ('http://uri.interlex.org/base/ilx_5214', ['http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213'])

    === if ilx does not exit and pref label does ===
    >>> iri = {'iri':['http://uri.interlex.org/base/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213']}
    >>> preferred = {'preferred':[1,0,0]}
    >>> seg_df = pd.DataFrame({**iri, **preferred})
    >>> terms_ilx = 'ilx:tmp_0'
    >>> get_pref_unpref_iris(seg_df, terms_ilx)
    ('ilx:tmp_0', ['http://uri.interlex.org/base/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213'])

    === if ilx does not exist and pref label does not exist ===
    >>> iri = {'iri':['http://uri.interlex.org/base/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213']}
    >>> preferred = {'preferred':[0,0,0]}
    >>> seg_df = pd.DataFrame({**iri, **preferred})
    >>> terms_ilx = 'ilx:tmp_0'
    >>> get_pref_unpref_iris(seg_df, terms_ilx)
    ('ilx:tmp_0', ['http://uri.interlex.org/base/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213'])
    '''
    iri_list = list(map(str, list(seg_df.iri)))
    pref_list = list(map(int, list(seg_df.preferred)))
    return helper_pref_filter(iri_list=iri_list, pref_list=pref_list, terms_ilx=terms_ilx)

def make_preferred_iris_dict(g=None, test_df=None):
    '''
    === if ilx exists and pref label exists ===
    >>> iri = {'iri':['http://uri.interlex.org/base/ilx_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213']}
    >>> preferred = {'preferred':[1,0,0]}
    >>> ilx = {'ilx':['tmp_0', 'tmp_0', 'tmp_0']}
    >>> id = {'id':1}
    >>> seg_df = pd.DataFrame({**iri, **preferred, **ilx, **id})
    >>> make_preferred_iris_dict(test_df=seg_df)
    ({1: 'ILX:5214'}, {'tmp_0': 'ILX:5214'})

    === if ilx does not exit and pref label does ===
    >>> iri = {'iri':['http://uri.interlex.org/base/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213']}
    >>> preferred = {'preferred':[1,0,0]}
    >>> ilx = {'ilx':['tmp_0', 'tmp_0', 'tmp_0']}
    >>> id = {'id':1}
    >>> seg_df = pd.DataFrame({**iri, **preferred, **ilx, **id})
    >>> make_preferred_iris_dict(test_df=seg_df)
    ({1: 'ilx:tmp_0'}, {'tmp_0': 'ilx:tmp_0'})

    === if ilx does not exist and pref label does not exist ===
    >>> iri = {'iri':['http://uri.interlex.org/base/nifext_5214', 'http://notpref1.com/nifext_5214', 'http://notpref2.com/nifext_5213']}
    >>> preferred = {'preferred':[0,0,0]}
    >>> ilx = {'ilx':['tmp_0', 'tmp_0', 'tmp_0']}
    >>> id = {'id':1}
    >>> seg_df = pd.DataFrame({**iri, **preferred, **ilx, **id})
    >>> make_preferred_iris_dict(test_df=seg_df)
    ({1: 'ilx:tmp_0'}, {'tmp_0': 'ilx:tmp_0'})
    '''
    data =  '''
            SELECT t.id, tei.tid, tei.iri, tei.preferred, t.ilx, t.type, t.label, t.definition
            FROM terms AS t
            JOIN term_existing_ids AS tei ON t.id=tei.tid
            WHERE t.type != 'cde'
            '''
    try:
        test_df.empty
        df = test_df
        g = create_graph('test')
    except:
        df = pd.read_sql(data, engine)

    df_ids = list(set(df.id))

    pref_dict = {}
    ilx_to_pref = {}
    unpref_dict = {}
    bar=createBar(len(df_ids)); bar.start()
    for i, curr_id in enumerate(df_ids):

        seg_df = df.loc[df.id == (curr_id)]
        pref_iri, unpref_iris = get_pref_unpref_iris(seg_df=seg_df, terms_ilx=list(seg_df.ilx)[0])
        pref_dict[curr_id] = pref_iri#g.qname(pref_iri) #FIXME tom must have changed qname
        unpref_dict[curr_id] = unpref_iris
        ilx_to_pref[list(seg_df.ilx)[0]] = pref_iri#g.qname(pref_iri)

        bar.update(i)
    bar.finish()
    try:
        test_df.empty
    except:
        print('=== PREFERRED IRI COMPLETE ===')

    return pref_dict, ilx_to_pref, unpref_dict

def label_def_prefix(g=None, pref_dict=None, unpref_dict=None):
    data = '''
           SELECT t.id, t.ilx, t.type, t.label, t.definition
           FROM terms AS t
           WHERE t.type != 'cde'
           '''
    df = pd.read_sql(data, engine)
    df_ids = list(set(df.id))

    bar=createBar(len(df_ids)); bar.start()
    for i, curr_id in enumerate(df_ids):

        seg_df = df.loc[df.id == (curr_id)]
        pref_iri = pref_dict[curr_id]
        unpref_iris = unpref_dict[curr_id]
        for row in seg_df.itertuples():

            if row.type == 'relationship':
                g.add_op(g.qname(pref_iri), row.label)
            elif row.type == 'annotation':
                g.add_ap(g.qname(pref_iri), row.label)
            else:
                g.add_class(pref_iri, label=row.label)

            g.add_trip(pref_iri, 'rdfs:isDefinedBy', row.definition)
            #http://www.geneontology.org/formats/oboInOwl#DbXref
            for unpref_iri in unpref_iris:
                if 'ilx' in unpref_iri.lower():
                    continue
                #if 'neurolex.' in unpref_iri:
                #    g.add_trip(pref_iri, oboInOwl.DbXref, unpref_iri)
                else:
                    g.add_trip(pref_iri, 'ilxtr:existingId', unpref_iri)
                    #g.add_trip(pref_iri, oboInOwl.hasDbXref, unpref_iri)
                    #g.add_trip(pref_iri, owl.equivalentClass, unpref_iri)

        bar.update(i)
    bar.finish()

    print('=== LABEL COMPLETE ===')
    print('=== DEFINITION COMPLETE ===')
    print('=== PREFIXES COMPLETE ===')
    return g

def annotation(g, pref_dict):
    data =  '''
            SELECT t1.id, t1.ilx, t2.ilx AS annotation_ilx, ta.value FROM term_annotations AS ta
            INNER JOIN terms AS t1 ON t1.id = ta.tid
            INNER JOIN terms AS t2 ON t2.id = ta.annotation_tid
            WHERE t1.type != 'cde'
            AND t2.type != 'cde'
            '''
    df = pd.read_sql(data, engine)
    df_ids = list(set(df.id))

    bar=createBar(len(set(df.id))); bar.start()
    for i, curr_id in enumerate(df_ids):

        seg_df = df.loc[df.id == (curr_id)]
        pref_iri = pref_dict[curr_id]

        for row in seg_df.itertuples():
            g.add_trip(pref_iri, 'ilx:'+row.annotation_ilx, row.value)

        bar.update(i)
    bar.finish()

    print('=== ANNOTATION COMPLETE ===')
    return g

def synonym(g, pref_dict):
    data =  '''
            SELECT t.id, t.ilx, t.label, t.definition, ts.type, ts.literal AS syn_abbrev
            FROM terms AS t
            INNER JOIN term_synonyms AS ts
            ON ts.tid = t.id
            WHERE t.type != 'cde'
            '''
    df = pd.read_sql(data, engine)
    df_ids = list(set(df.id))

    bar=createBar(len(set(df.id))); bar.start()
    for i, curr_id in enumerate(df_ids):

        seg_df = df.loc[df.id == (curr_id)]
        pref_iri = pref_dict[curr_id]

        for row in seg_df.itertuples():
            if row.type == 'abbrev':
                g.add_trip(pref_iri, "NIFRID:abbrev", row.syn_abbrev)
            else:
                g.add_trip(pref_iri, "NIFRID:synonym", row.syn_abbrev)

        bar.update(i)
    bar.finish()

    print('=== SYNONYM COMPLETE ===')
    return g

def relationship(g, ilx_to_pref):
    data = '''
           SELECT t1.ilx AS term1, t3.ilx AS relationship_id, t2.ilx AS term2 FROM term_relationships AS tr
           JOIN terms AS t1 ON t1.id = tr.term1_id
           JOIN terms AS t2 ON t2.id = tr.term2_id
           JOIN terms AS t3 ON t3.id = tr.relationship_tid
           WHERE t1.type != 'cde' AND t2.type != 'cde' AND t3.type != 'cde'
           '''
    df = pd.read_sql(data, engine)
    #add sys.exit test
    df_ids = df.term1

    bar=createBar(len(df_ids)); bar.start()

    for i, row in enumerate(df.itertuples()):

        try:
            front = ilx_to_pref[row.term1]
            mid = ilx_to_pref[row.relationship_id]
            back = ilx_to_pref[row.term2]
            g.add_trip(front, mid, back)
        except:
            pass

        bar.update(i)
    bar.finish()

    print('=== RELATIONSHIP COMPLETE ===')
    return g

def superclasses(g, pref_dict):
    data =  '''
            SELECT ts.*, t1.id as curr_id, t2.id as superclass_id
            FROM term_superclasses as ts
            JOIN terms as t1 ON ts.tid = t1.id
            JOIN terms as t2 ON ts.superclass_tid = t2.id
            WHERE t1.type != 'cde' AND t2.type != 'cde'
            '''
    df = pd.read_sql(data, engine)

    df_ids = df.curr_id

    bar=createBar(len(df_ids)); bar.start()
    for i, row in enumerate(df.itertuples()):
        g.add_trip(pref_dict[row.curr_id], 'rdfs:subClassOf', pref_dict[row.superclass_id])

        bar.update(i)
    bar.finish()

    print('=== SUPERCLASSES COMPLETE ===')
    return g

if __name__ == '__main__':
    g = create_graph('Interlex')
    pref_dict, ilx_to_pref, unpref_dict = make_preferred_iris_dict(g)
    g = label_def_prefix(g, pref_dict, unpref_dict)
    g = annotation(g, pref_dict)
    g = synonym(g, pref_dict)
    g = relationship(g, ilx_to_pref)
    g = superclasses(g, pref_dict)
    g.g.serialize(destination=args.output, format='turtle') #g.write() broken
    print('COMPLETE')
