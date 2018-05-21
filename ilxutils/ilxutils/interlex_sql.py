import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column
from ilxutils.args_reader import read_args
from collections import defaultdict
from pathlib import Path as p



class interlex_sql():

    def __init__(self, db_url, constraint=None):
        self.db_url = db_url
        self.constraint = constraint

    def remove_duplicates(self, df):
        terms = self.get_terms()
        df = df[df['item_id'].isin(list(terms.id))]
        return df

    def get_terms(self, records=False):
        engine = create_engine(self.db_url)
        data =  """
                SELECT t.*
                FROM terms as t
                WHERE t.type!='{0}'
                """.format(self.constraint)
        df = pd.read_sql(data, engine)
        df.drop_duplicates(keep='first', subset=['ilx'], inplace=True)
        if records:
            return df.to_dict('records')
        return df

    def get_labels_to_ids_dict(self):
        df = self.get_terms()
        visited = {}
        label_to_id = defaultdict(dict)
        for row in df.itertuples():
            label = row.label.lower().strip().replace('&#39;', "''").replace("'", '').replace('"', '')
            if visited.get((label, row.type)):
                continue
            else:
                if row.type == 'term':
                    label_to_id[label].update({'term':int(row.id)})
                    visited[(label,row.type)]=True
                if row.type == 'cde':
                    label_to_id[label].update({'cde':int(row.id)})
                    visited[(label,row.type)]=True
        return label_to_id

    def get_ids_to_labels_dict(self):
        df = self.get_terms(records=True)
        return {line['id']:line['label'] for line in df}

    def get_labels_to_ilx_dict(self):
        df = self.get_terms()
        visited = {}
        label_to_ilx = {}
        for row in df.itertuples():
            label = row.label.lower().strip()
            if visited.get(label):
                continue
            else:
                label_to_ilx[label] = str(row.ilx)
                visited[label]=True
        return label_to_ilx

    def get_ilx_to_label(self):
        df = self.get_terms(records=True)
        return {line['ilx']:line['label'] for line in df}

    def get_ilx_to_row(self):
        df = self.get_terms(records=True)
        return {line['ilx']:line for line in df}

    def get_existing_ids(self, records=False):
        #SELECT ti.curie, t.label, ti.tid, ti.iri, t.ilx
        engine = create_engine(self.db_url)
        data =  """
                SELECT t.id, tei.tid, tei.curie, tei.iri, tei.preferred, t.ilx, t.type, t.label, t.definition
                FROM terms AS t
                JOIN term_existing_ids AS tei ON t.id=tei.tid
                WHERE t.type != '{0}'
                """.format(self.constraint)
        df = pd.read_sql(data, engine)
        df.drop_duplicates(keep='first', subset=['curie','iri', 'ilx'], inplace=True)
        #df = self.remove_duplicates(df)
        if records:
            df = df.to_dict('records')
        return df

    def get_annotations(self, records=False):
        engine = create_engine(self.db_url)
        data =  """
                SELECT ta.id, t1.id as item_id, t1.label, t1.ilx, t2.id as anno_tid, t2.label as anno_label, t2.ilx as anno_ilx, ta.tid, ta.annotation_tid, ta.value
                FROM term_annotations AS ta
                JOIN terms AS t1 ON ta.tid=t1.id
                JOIN terms AS t2 ON ta.annotation_tid=t2.id
                """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df)
        if records:
            return df.to_dict('records')
        return df

    def get_annotaion_table(self, records=False):
        engine = create_engine(self.db_url)
        data =  """
                SELECT ta.*
                FROM term_annotations AS ta
                """
        if records:
            return pd.read_sql(data, engine).to_dict('records')
        return pd.read_sql(data, engine)

    def get_relationships(self, records=False):
        engine = create_engine(self.db_url)
        data = """
               SELECT t1.ilx AS term1, t3.ilx AS relationship_id, t2.ilx AS term2 FROM term_relationships AS tr
               JOIN terms AS t1 ON t1.id = tr.term1_id
               JOIN terms AS t2 ON t2.id = tr.term2_id
               JOIN terms AS t3 ON t3.id = tr.relationship_tid
               """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df)
        df.drop_duplicates(keep='first', subset=['term1', 'relationship_id', 'term2'], inplace=True) #safety measure for duplicates
        if records:
            return df.to_dict('records')
        return df

    def get_superclasses(self, records=False):
        engine = create_engine(self.db_url)
        data =  """
                SELECT ts.id, ts.tid, ts.superclass_tid, t.label, t.ilx
                FROM term_superclasses AS ts
                JOIN terms AS t
                WHERE ts.tid=t.id
                """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df)
        if records:
            return df.to_dict('records')
        return df

    def get_synonyms(self, records=False):
        engine = create_engine(self.db_url)
        data =  """
                SELECT ts.id, ts.tid, ts.literal, t.label, t.ilx
                FROM term_synonyms AS ts
                JOIN terms AS t
                WHERE ts.tid=t.id
                """
        df = pd.read_sql(data, engine)
        df = self.remove_duplicates(df)
        if records:
            return df.to_dict('records')
        return df

def main():
    args = read_args(api_key=p.home() / 'keys/production_api_scicrunch_key.txt', db_url= p.home() / 'keys/production_engine_scicrunch_key.txt',production=True)
    sql = interlex_sql(db_url=args.db_url)
    #terms_df = sql.get_terms()
    print(sql.get_existing_ids().shape)

if __name__ == '__main__':
    main()
