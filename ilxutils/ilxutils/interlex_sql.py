import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column
from collections import defaultdict
from pathlib import Path as p
from ilxutils.args_reader import read_args
from ilxutils.tools import *
from ilxutils.scicrunch_client import scicrunch
import re
#ELASTIC = 'https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/interlex/term/'


class IlxSql():
    def __init__(self, db_url, pre_load=False):
        self.db_url = db_url
        self.engine = create_engine(self.db_url)
        self.local_degrade = light_degrade  # current degrade of choice for sql
        self.terms = self.get_terms() if pre_load else pd.DataFrame
        self.annos = self.get_annotations() if pre_load else pd.DataFrame
        self.basic_annos = self.get_basic_annos() if pre_load else pd.DataFrame

    def fetch_terms(self):
        if self.terms.empty:
            return self.get_terms()
        return self.terms

    def fetch_annos(self):
        if self.annos.empty:
            return self.get_annotations()
        return self.annos

    def fetch_basic_annos(self):
        if self.basic_annos.empty:
            return self.get_basic_annos()
        return self.basic_annos

    def remove_duplicates(self, df):
        self.terms = self.fetch_terms()
        #check elastic?
        return df[df['tid'].isin(list(self.terms.id))]  # uses already cleaned ids as ref

    def get_terms(self):
        engine = create_engine(self.db_url)
        data = """
            SELECT t.*
            FROM terms as t
        """
        df = pd.read_sql(data, engine)
        df.drop_duplicates(keep='first', subset=['ilx'], inplace=True)
        return df

    def get_annotations(self):
        engine = create_engine(self.db_url)
        data = """
            SELECT ta.id, ta.tid,  ta.annotation_tid, ta.value, ta.orig_uid as uid, t1.label as term_label, t1.ilx as term_ilx, t2.label as annotation_label, t2.ilx as annotation_ilx
            FROM term_annotations AS ta
            JOIN terms AS t1 ON ta.tid=t1.id
            JOIN terms AS t2 ON ta.annotation_tid=t2.id
        """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df)
        return df

    def get_existing_ids(self):
        engine = create_engine(self.db_url)
        data = """
            SELECT tei.id, tei.tid, tei.curie, tei.iri, tei.preferred, t.ilx, t.type, t.label, t.definition, t.comment
            FROM terms AS t
            JOIN term_existing_ids AS tei ON t.id=tei.tid
        """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df) # takes out dead terms
        return df

    def get_relationships(self):
        engine = create_engine(self.db_url)
        data = """
           SELECT
               tr.id,
               t1.id as term1_tid, t1.ilx AS term1_ilx, t1.type as term1_type,
               t2.id as term2_tid, t2.ilx AS term2_ilx, t2.type as term2_type,
               t3.id as relationship_tid, t3.ilx AS relationship_ilx, t3.label as relationship_label
           FROM term_relationships AS tr
           JOIN terms AS t1 ON t1.id = tr.term1_id
           JOIN terms AS t2 ON t2.id = tr.term2_id
           JOIN terms AS t3 ON t3.id = tr.relationship_tid
        """
        df = pd.read_sql(data, engine)
        df.rename(columns={'relationship_tid': 'tid'}, inplace=True)
        df = self.remove_duplicates(df)
        df.rename(columns={'tid':'relationship_tid'}, inplace=True)
        return df

    def get_superclasses(self):
        engine = create_engine(self.db_url)
        data = """
            SELECT
                ts.id, ts.tid, ts.superclass_tid,
                t1.label as term_label, t1.ilx as term_ilx,
                t2.label as superclass_label, t2.ilx as superclass_ilx
            FROM term_superclasses AS ts
            JOIN terms as t1 ON t1.id = ts.tid
            JOIN terms AS t2 ON t2.id = ts.superclass_tid
        """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df)
        return df

    def get_synonyms(self):
        engine = create_engine(self.db_url)
        data = """
                SELECT ts.id, ts.tid, ts.literal, t.ilx, t.label
                FROM term_synonyms AS ts
                JOIN terms AS t
                WHERE ts.tid=t.id
                """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df)
        return df

    def get_basic_annos(self):
        engine = create_engine(self.db_url)
        data = """
                SELECT ta.*
                FROM term_annotations AS ta
                JOIN terms AS t1 ON ta.tid=t1.id
                JOIN terms AS t2 ON ta.annotation_tid=t2.id
                """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df)
        return df

    def get_client_ready_terms(self, ids):
        self.terms = self.fetch_terms()
        df_filtered = self.terms[self.terms['id'].isin(ids)]
        return {row['id']: row for row in df_filtered.to_dict('records')}

    def get_client_ready_annos(self, ids):
        self.basic_annos = self.fetch_basic_annos()
        df_filtered = self.basic_annos[self.basic_annos['id'].isin(ids)]
        return {row['id']: row for row in df_filtered.to_dict('records')}

    def get_label2id(self):
        self.terms = self.fetch_terms()
        visited = {}
        label_to_id = defaultdict(lambda: defaultdict(list))
        for row in self.terms.itertuples():
            label = self.local_degrade(row.label)
            if visited.get((label, row.type, row.uid)):
                continue
            else:
                if row.type == 'term':
                    label_to_id[label]['term'].append(int(row.id))
                    visited[(label, row.type, row.uid)] = True
                if row.type == 'cde':
                    label_to_id[label]['cde'].append(int(row.id))
                    visited[(label, row.type, row.uid)] = True
        return label_to_id

    def get_label2ilx(self):
        self.terms = self.fetch_terms()
        visited = {}
        label_to_ilx = defaultdict(list)
        for row in self.terms.itertuples():
            label = self.local_degrade(row.label)
            if visited.get((label, row.type, row.uid)):
                continue
            else:
                label_to_ilx[label].append(str(row.ilx))
                visited[(label, row.type, row.uid)] = True
        return label_to_ilx

    def get_id2label(self):
        return {row['id']: row['label'] for row in self.fetch_terms().to_dict('records')}

    def get_ilx2label(self):
        return {row['ilx']: row['label'] for row in self.fetch_terms().to_dict('records')}

    def get_id2ilx(self):
        return {row['id']: row['ilx'] for row in self.fetch_terms().to_dict('records')}

    def get_ilx2id(self):
        return {row['ilx']: row['id'] for row in self.fetch_terms().to_dict('records')}

    def get_ilx2row(self):
        return {row['ilx']: row for row in self.fetch_terms().to_dict('records')}

    def show_tables(self):
        data = """
            show tables;
        """
        return pd.read_sql(data, self.engine)

    def get_table(self, tablename, limit=1000000000):
        data = """
            SELECT *
            FROM {}
            LIMIT {}
        """.format(tablename, limit)
        return pd.read_sql(data, self.engine)

    def get_custom(self, data):
        return pd.read_sql(data, self.engine)

    def get_terms_complete(self):
        from functools import reduce

        self.terms = self.fetch_terms()
        self.annos = self.fetch_annos()
        synonyms = self.get_synonyms()
        superclasses = self.get_superclasses()
        relationships = self.get_relationships()
        existing_ids = self.get_existing_ids()

        df1 = superclasses.rename({'term_ilx': 'ilx'}, axis='columns')[['ilx', 'superclass_ilx']]
        df2 = existing_ids.rename({'curie': 'superclass_curie', 'iri': 'superclass_iri'}, axis='columns')[['ilx', 'superclass_curie', 'superclass_iri']]
        direct_superclasses = pd.merge(df1, df2, on='ilx', how='outer')

        df1 = relationships.rename({'term1_ilx': 'ilx', 'term2_ilx': 'relationship'}, axis='columns')[['ilx', 'relationship']]
        df2 = relationships.rename({'term2_ilx': 'ilx', 'term1_ilx': 'relationship'}, axis='columns')[['ilx', 'relationship']]
        direct_relationships = pd.concat([df1,df2]).drop_duplicates().reset_index(drop=True)

        dfs = [
            self.terms[['id', 'ilx', 'label']],
            direct_superclasses,
            self.annos.rename({'term_ilx': 'ilx'}, axis='columns')[['ilx', 'annotation_label', 'value']],
            synonyms.rename({'literal': 'synonym'}, axis='columns')[['ilx', 'synonym']],
            existing_ids[['ilx', 'curie', 'iri']],
            relationships.rename({'relationship_ilx': 'ilx'}, axis='columns')[['ilx', 'term1_ilx', 'term2_ilx']],
            direct_relationships,
        ]

        df_final = reduce(lambda left,right: pd.merge(left, right, on='ilx', how='outer'), dfs)

        return df_final

class EzIlxSql(IlxSql):
    def __init__(self, db_url):
        IlxSql.__init__(self, db_url, pre_load=True)
        self.label2id_dict = self.get_label2id()
        self.id2label_dict = self.get_id2label()
        self.label2ilx_dict = self.get_label2ilx()
        self.ilx2label_dict = self.get_ilx2label()

    def label2ilx(self, label):
        return self.label2ilx_dict.get(self.local_degrade(label))

    def label2id(self, label):
        return self.label2id_dict.get(self.local_degrade(label))

    def id2label(self, id):
        return self.id2label_dict.get(int(id))

    def ilx2label(self, ilx_id):
        ilx_id = str(ilx_id)
        ilx_id = ilx_id if 'ilx_' in ilx_id else ('ilx_' + ilx_id)
        return self.ilx2label_dict.get(ilx_id)


def main():
    args = read_args(
        api_key=p.home() / 'keys/production_api_scicrunch_key.txt',
        db_url=p.home() / 'keys/production_engine_scicrunch_key.txt',
        production=True)
    sql = IlxSql(api_key=args.api_key,
                 base_path=args.base_path,
                 db_url=args.db_url)
    # terms_df = sql.get_terms()
    ex2row = sql.get_existing_id2row()
    print(ex2row['http://uri.interlex.org/dicom/uris/terms/0018_0029'])
    # print(list(label2ilx)[0])

# engine = create_engine('mysql+mysqlconnector://root:water@localhost/umls2018ab', pool_size=10, max_overflow=2)
# data = """
#     select m.code, m.str, s.atv, d.def
#     from MRCONSO m
#     left outer join MRSAT s ON m.AUI=s.METAUI
#     left outer join MRDEF d on m.AUI=d.AUI ;
# """
# umls = pd.read_sql(data, engine)
# umls.to_pickle(p.home()/'Dropbox/SciCrunchDumps/umls/umls.pickle')

# psql -U interlex-admin -h localhost -d interlex_test;

if __name__ == '__main__':
    main()
