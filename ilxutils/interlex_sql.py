import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column
from args_reader import read_args

class interlex_sql():

    def __init__(self, engine_key, constraint=None):
        self.engine_key = engine_key
        self.constraint = constraint

    def get_terms(self):
        engine = create_engine(self.engine_key)
        data =  """
                SELECT t.*
                FROM terms as t
                WHERE t.type!='{0}'
                """.format(self.constraint)
        return pd.read_sql(data, engine)

    def get_labels_to_ids_dict(self):
        df = self.get_terms()
        visited = {}
        label_to_id = {}
        for row in df.itertuples():
            label = row.label.lower().strip()
            if visited.get(label):
                continue
            else:
                label_to_id[label] = row.id
                visited[label]=True
        return label_to_id

    def get_existing_ids(self):
        engine = create_engine(self.engine_key)
        data =  """
                SELECT ti.curie, t.label, ti.tid, ti.iri, t.ilx
                FROM term_existing_ids AS ti
                JOIN terms AS t
                WHERE ti.tid=t.id
                AND t.type!='{0}'
                """.format(self.constraint)
        return pd.read_sql(data, engine)

    def get_annotations(self):
        engine = create_engine(self.engine_key)
        data =  """
                SELECT t1.id as item_id, t1.label, t1.ilx, t2.id as anno_tid, t2.label as anno_label, t2.ilx as anno_ilx, ta.tid, ta.annotation_tid, ta.value
                FROM term_annotations AS ta
                JOIN terms AS t1 ON ta.tid=t1.id
                JOIN terms AS t2 ON ta.annotation_tid=t2.id
                AND t1.type!='{0}'
                AND t2.type!='{1}'
                """ .format(self.constraint, self.constraint)
        return pd.read_sql(data, engine)

    def get_relationship(self):
        engine = create_engine(self.engine_key)
        data = """
               SELECT t1.ilx AS term1, t3.ilx AS relationship_id, t2.ilx AS term2 FROM term_relationships AS tr
               JOIN terms AS t1 ON t1.id = tr.term1_id
               JOIN terms AS t2 ON t2.id = tr.term2_id
               JOIN terms AS t3 ON t3.id = tr.relationship_tid
               WHERE t1.type != '{0}' AND t2.type != '{1}' AND t3.type != '{2}'
               """.format(self.constraint, self.constraint, self.constraint)
        return pd.read_sql(data, engine)

def main():
    args = read_args(keys='../keys.txt',beta='-b')
    sql = interlex_sql(engine_key=args['engine_key'])
    terms_df = sql.get_terms()

if __name__ == '__main__':
    main()
