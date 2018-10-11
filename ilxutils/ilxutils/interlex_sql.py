import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column
from collections import defaultdict
from ilxutils.tools import light_degrade
import os
#ELASTIC = 'https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/interlex/term/'


class IlxSql():
    
    def __init__(self, db_url, pre_load=False):
        self.db_url = db_url
        self.engine = create_engine(self.db_url)
        self.local_degrade = light_degrade  # current degrade of choice for sql
        self.terms = self.get_terms() if pre_load else pd.DataFrame
        self.annos = self.get_annotations() if pre_load else pd.DataFrame

    def fetch_terms(self):
        if self.terms.empty:
            return self.get_terms()
        return self.terms

    def fetch_annos(self):
        if self.annos.empty:
            return self.get_annotations()
        return self.annos

    def get_terms(self):
        engine = create_engine(self.db_url)
        data = """
            SELECT *
            FROM terms
            GROUP BY terms.ilx
        """
        df = pd.read_sql(data, engine)
        return df

    def get_annotations(self):
        engine = create_engine(self.db_url)
        data = """
            SELECT
                ta.id, ta.tid,  ta.annotation_tid, ta.value, ta.orig_uid as uid,
                t1.label as term_label, t1.ilx as term_ilx,
                t2.label as annotation_label, t2.ilx as annotation_ilx
            FROM term_annotations AS ta
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
            ) AS t1 ON ta.tid=t1.id
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
            ) AS t2 ON ta.annotation_tid=t2.id
        """
        df = pd.read_sql(data, engine)
        return df

    def get_existing_ids(self):
        engine = create_engine(self.db_url)
        data = """
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
        """
        df = pd.read_sql(data, engine)
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
           JOIN (
               SELECT *
               FROM terms
               GROUP BY terms.ilx
           ) t1 ON t1.id = tr.term1_id
           JOIN (
               SELECT *
               FROM terms
               GROUP BY terms.ilx
           ) AS t2 ON t2.id = tr.term2_id
           JOIN (
               SELECT *
               FROM terms
               GROUP BY terms.ilx
           ) AS t3 ON t3.id = tr.relationship_tid
        """
        df = pd.read_sql(data, engine)
        return df

    def get_superclasses(self):
        engine = create_engine(self.db_url)
        data = """
            SELECT
                ts.id, ts.tid, ts.superclass_tid,
                t1.label as term_label, t1.ilx as term_ilx,
                t2.label as superclass_label, t2.ilx as superclass_ilx
            FROM term_superclasses AS ts
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
            ) as t1
            ON t1.id = ts.tid
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
            ) AS t2
            ON t2.id = ts.superclass_tid
        """
        df = pd.read_sql(data, engine)
        return df

    def get_synonyms(self):
        engine = create_engine(self.db_url)
        data = """
            SELECT ts.id, ts.tid, ts.literal, t.ilx, t.label
            FROM term_synonyms AS ts
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
            ) AS t
            WHERE ts.tid=t.id
        """
        df = pd.read_sql(data, engine)
        return df

    def get_label2id(self):
        self.terms = self.fetch_terms()
        visited = {}
        label_to_id = defaultdict(lambda: defaultdict(list))
        for row in self.terms.itertuples():
            label = self.local_degrade(row.label)
            if not visited.get((label, row.type, row.uid)):
                if row.type == 'term':
                    label_to_id[label]['term'].append(int(row.id))
                    visited[(label, row.type, row.uid)] = True
                elif row.type == 'cde':
                    label_to_id[label]['cde'].append(int(row.id))
                    visited[(label, row.type, row.uid)] = True
                elif row.type == 'fde':
                    label_to_id[label]['fde'].append(int(row.id))
                    visited[(label, row.type, row.uid)] = True
        return label_to_id

    def get_label2ilx(self):
        self.terms = self.fetch_terms()
        visited = {}
        label_to_ilx = defaultdict(list)
        for row in self.terms.itertuples():
            label = self.local_degrade(row.label)
            if not visited.get((label, row.type, row.uid)):
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
        data = "SHOW tables;"
        return pd.read_sql(data, self.engine)

    def get_table(self, tablename, limit=5):
        data = """
            SELECT *
            FROM {}
            LIMIT {}
        """.format(tablename, limit)
        return pd.read_sql(data, self.engine)

    def get_custom(self, data):
        return pd.read_sql(data, self.engine)


def main():
    db_url = os.environ.get('SCICRUNCH_DB_URL_PRODUCTION')
    sql = IlxSql(db_url)
    rels = sql.get_relationships()
    print(rels.head())


if __name__ == '__main__':
    main()
