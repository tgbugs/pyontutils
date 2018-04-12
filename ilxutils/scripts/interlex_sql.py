import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column
from args_reader import read_args
from collections import defaultdict

class interlex_sql():

    def __init__(self, engine_key, constraint=None):
        self.engine_key = engine_key
        self.constraint = constraint

    def get_terms(self, records=False):
        engine = create_engine(self.engine_key)
        data =  """
                SELECT t.*
                FROM terms as t
                WHERE t.type!='{0}'
                """.format(self.constraint)
        if records:
            return pd.read_sql(data, engine).to_dict('records')
        return pd.read_sql(data, engine)

    #FIXME needs to have type as another indicator from which to get ids
    #[label] = {'term':123, 'cde':123}
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

    def get_existing_ids(self, records=False):
        #SELECT ti.curie, t.label, ti.tid, ti.iri, t.ilx
        engine = create_engine(self.engine_key)
        data =  """
                SELECT t.id, tei.tid, tei.iri, tei.preferred, t.ilx, t.type, t.label, t.definition
                FROM terms AS t
                JOIN term_existing_ids AS tei ON t.id=tei.tid
                WHERE t.type != '{0}'
                """.format(self.constraint)
        if records:
            return pd.read_sql(data, engine).to_dict('records')
        return pd.read_sql(data, engine)

    def get_annotations(self, records=False):
        engine = create_engine(self.engine_key)
        data =  """
                SELECT t1.id as item_id, t1.label, t1.ilx, t2.id as anno_tid, t2.label as anno_label, t2.ilx as anno_ilx, ta.tid, ta.annotation_tid, ta.value
                FROM term_annotations AS ta
                JOIN terms AS t1 ON ta.tid=t1.id
                JOIN terms AS t2 ON ta.annotation_tid=t2.id
                AND t1.type!='{0}'
                AND t2.type!='{1}'
                """ .format(self.constraint, self.constraint)
        if records:
            return pd.read_sql(data, engine).to_dict('records')
        return pd.read_sql(data, engine)

    def get_annotaion_table(self, records=False):
        engine = create_engine(self.engine_key)
        data =  """
                SELECT ta.*
                FROM term_annotations AS ta
                """ .format(self.constraint, self.constraint)
        if records:
            return pd.read_sql(data, engine).to_dict('records')
        return pd.read_sql(data, engine)

    def get_relationship(self, records=False):
        engine = create_engine(self.engine_key)
        data = """
               SELECT t1.ilx AS term1, t3.ilx AS relationship_id, t2.ilx AS term2 FROM term_relationships AS tr
               JOIN terms AS t1 ON t1.id = tr.term1_id
               JOIN terms AS t2 ON t2.id = tr.term2_id
               JOIN terms AS t3 ON t3.id = tr.relationship_tid
               WHERE t1.type != '{0}' AND t2.type != '{1}' AND t3.type != '{2}'
               """.format(self.constraint, self.constraint, self.constraint)
        if records:
            return pd.read_sql(data, engine).to_dict('records')
        return pd.read_sql(data, engine)

    def get_superclasses(self, records=False):
        engine = create_engine(self.engine_key)
        data =  """
                SELECT ts.*
                FROM term_superclasses AS ts
                JOIN terms AS t
                WHERE ts.tid=t.id
                AND t.type!='{0}'
                """.format(self.constraint)
        if records:
            return pd.read_sql(data, engine).to_dict('records')
        return pd.read_sql(data, engine)

    def get_synonyms(self, records=False):
        engine = create_engine(self.engine_key)
        data =  """
                SELECT ts.*
                FROM term_synonyms AS ts
                JOIN terms AS t
                WHERE ts.tid=t.id
                AND t.type!='{0}'
                """.format(self.constraint)
        if records:
            return pd.read_sql(data, engine).to_dict('records')
        return pd.read_sql(data, engine)

def main():
    args = read_args(keys='../keys.txt',beta='-b')
    sql = interlex_sql(engine_key=args['engine_key'])
    #terms_df = sql.get_terms()
    label_to_id = sql.get_labels_to_ids_dict()
    print(label_to_id['amoxicillin'])

if __name__ == '__main__':
    main()
