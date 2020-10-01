from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column
from collections import defaultdict
from ilxutils.tools import light_degrade, open_pickle, create_pickle
import os
#ELASTIC = 'https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/interlex/term/'
TERMS_COMPLETE_BACKUP_PATH = Path.home()/'Dropbox/interlex_backups/ilx_db_terms_complete_backup.pickle'
TERMS_BACKUP_PATH = Path.home()/'Dropbox/interlex_backups/ilx_db_terms_backup.pickle'
ANNOS_BACKUP_PATH = Path.home()/'Dropbox/interlex_backups/ilx_db_annotations_backup.pickle'
RELAS_BACKUP_PATH = Path.home()/'Dropbox/interlex_backups/ilx_db_relationships_backup.pickle'
SUPER_BACKUP_PATH = Path.home()/'Dropbox/interlex_backups/ilx_db_superclasses_backup.pickle'
SYNOS_BACKUP_PATH = Path.home()/'Dropbox/interlex_backups/ilx_db_synonyms_backup.pickle'
EXIDS_BACKUP_PATH = Path.home()/'Dropbox/interlex_backups/ilx_db_ex_backup.pickle'


class IlxSql():

    def __init__(self, db_url, pre_load=False, from_backup=False):
        self.db_url = db_url
        self.engine = create_engine(self.db_url)
        self.local_degrade = lambda string: string.lower().strip()  # current degrade of choice for sql
        self.from_backup = from_backup
        self.terms_complete = self.get_terms_complete() if pre_load else pd.DataFrame
        self.terms = self.get_terms() if pre_load else pd.DataFrame
        self.superclasses = self.get_superclasses if pre_load else pd.DataFrame
        self.annotations = self.get_annotations() if pre_load else pd.DataFrame
        self.existing_ids = self.get_existing_ids() if pre_load else pd.DataFrame
        self.relationships = self.get_relationships() if pre_load else pd.DataFrame
        self.synonyms = self.get_synonyms() if pre_load else pd.DataFrame

    def fetch_terms_complete(self):
        if self.terms_complete.empty:
            return self.get_terms_complete()
        return self.terms_complete

    def fetch_terms(self):
        if self.terms.empty:
            return self.get_terms()
        return self.terms

    def fetch_annotations(self):
        if self.annotations.empty:
            return self.get_annotations()
        return self.annotations

    def fetch_existing_ids(self):
        if self.existing_ids.empty:
            return self.get_existing_ids()
        return self.existing_ids

    def fetch_relationships(self):
        if self.relationships.empty:
            return self.get_relationships()
        return self.relationships

    def fetch_synonyms(self):
        if self.synonyms.empty:
            return self.get_synonyms()
        return self.synonyms

    def fetch_superclasses(self):
        if self.superclasses.empty:
            return self.get_superclasses()
        return self.superclasses

    def get_terms(self):
        ''' GROUP BY is a shortcut to only getting the first in every list of group '''
        if not self.terms.empty:
            return self.terms
        if self.from_backup:
            self.terms = open_pickle(TERMS_BACKUP_PATH)
            return self.terms
        engine = create_engine(self.db_url)
        data = """
            SELECT t.id as tid, t.ilx, t.label, t.definition, t.type, t.comment, t.version, t.uid, t.time
            FROM terms t
            GROUP BY t.ilx
        """
        self.terms = pd.read_sql(data, engine)
        create_pickle(self.terms, TERMS_BACKUP_PATH)
        return self.terms

    def get_annotations(self):
        if not self.annotations:
            return self.fetch_annotations()
        if self.from_backup:
            self.annotations = open_pickle(ANNOS_BACKUP_PATH)
            return self.annotations
        engine = create_engine(self.db_url)
        data = """
            SELECT
                ta.tid, ta.annotation_tid as annotation_type_tid,
                t1.ilx as term_ilx, t2.ilx as annotation_type_ilx,
                t2.label as annotation_type_label,
                ta.value
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
        self.annotations = pd.read_sql(data, engine)
        create_pickle(self.annotations, ANNOS_BACKUP_PATH)
        return self.annotations

    def get_existing_ids(self):
        if not self.existing_ids.empty:
            return self.existing_ids
        if self.from_backup:
            self.existing_ids = open_pickle(EXIDS_BACKUP_PATH)
            return self.existing_ids
        engine = create_engine(self.db_url)
        data = """
            SELECT tei.tid, tei.curie, tei.iri, tei.preferred, t.ilx, t.label, t.definition
            FROM (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
            ) as t
            JOIN term_existing_ids AS tei
            ON t.id = tei.tid
        """
        self.existing_ids = pd.read_sql(data, engine)
        create_pickle(self.existing_ids, EXIDS_BACKUP_PATH)
        return self.existing_ids

    def get_relationships(self):
        if not self.relationships.empty:
            return self.relationships
        if self.from_backup:
            self.relationships = open_pickle(RELAS_BACKUP_PATH)
            return self.relationships
        engine = create_engine(self.db_url)
        data = """
           SELECT
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
        self.relationships = pd.read_sql(data, engine)
        create_pickle(self.relationships, RELAS_BACKUP_PATH)
        return self.relationships

    def get_superclasses(self):
        if not self.superclasses.empty:
            return self.superclasses
        if self.from_backup:
            self.superclasses = open_pickle(SUPER_BACKUP_PATH)
            return self.superclasses
        engine = create_engine(self.db_url)
        data = """
            SELECT
                ts.tid, ts.superclass_tid,
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
        self.superclasses = pd.read_sql(data, engine)
        create_pickle(self.superclasses, SUPER_BACKUP_PATH)
        return self.superclasses

    def get_synonyms(self):
        if not self.synonyms.empty:
            return self.synonyms
        if self.from_backup:
            self.synonyms = open_pickle(SYNOS_BACKUP_PATH)
            return self.synonyms
        engine = create_engine(self.db_url)
        data = """
            SELECT ts.tid as tid, t.ilx, ts.literal, ts.type
            FROM term_synonyms AS ts
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
            ) AS t
            WHERE ts.tid=t.id
        """
        self.synonyms = pd.read_sql(data, engine)
        create_pickle(self.synonyms, SYNOS_BACKUP_PATH)
        return self.synonyms

    def get_terms_complete(self) -> pd.DataFrame:
        ''' Gets complete entity data like term/view '''
        if not self.terms_complete.empty:
            return self.terms_complete
        if self.from_backup:
            self.terms_complete = open_pickle(TERMS_COMPLETE_BACKUP_PATH)
            return self.terms_complete
        ilx2synonyms = self.get_ilx2synonyms()
        ilx2existing_ids = self.get_ilx2existing_ids()
        ilx2annotations = self.get_ilx2annotations()
        ilx2superclass = self.get_ilx2superclass()
        ilx_complete = []
        header = ['Index'] + list(self.fetch_terms().columns)
        for row in self.fetch_terms().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            row['synonyms'] = ilx2synonyms.get(row['ilx'])
            row['existing_ids'] = ilx2existing_ids[row['ilx']] # if breaks we have worse problems
            row['annotations'] = ilx2annotations.get(row['ilx'])
            row['superclass'] = ilx2superclass.get(row['ilx'])
            ilx_complete.append(row)
        terms_complete = pd.DataFrame(ilx_complete)
        create_pickle(terms_complete, TERMS_COMPLETE_BACKUP_PATH)
        return terms_complete

    def get_label2id(self):
        self.terms = self.fetch_terms()
        visited = {}
        label_to_id = defaultdict(lambda: defaultdict(list))
        for row in self.terms.itertuples():
            label = self.local_degrade(row.label)
            if not visited.get((label, row.type, row.ilx)):
                if row.type == 'term':
                    label_to_id[label]['term'].append(int(row.id))
                    visited[(label, row.type, row.ilx)] = True
                elif row.type == 'cde':
                    label_to_id[label]['cde'].append(int(row.id))
                    visited[(label, row.type, row.ilx)] = True
                elif row.type == 'fde':
                    label_to_id[label]['fde'].append(int(row.id))
                    visited[(label, row.type, row.ilx)] = True
        return label_to_id

    def get_label2ilxs(self):
        self.terms = self.fetch_terms()
        visited = {}
        label_to_ilx = defaultdict(list)
        for row in self.terms.itertuples():
            label = self.local_degrade(row.label)
            if not visited.get((label, row.type, row.ilx)):
                label_to_ilx[label].append(str(row.ilx))
                visited[(label, row.type, row.ilx)] = True
        return label_to_ilx

    def get_label2rows(self):
        self.terms_complete = self.fetch_terms_complete()
        visited = {}
        label2rows = defaultdict(list)
        header = ['Index'] + list(self.terms_complete.columns)
        for row in self.terms_complete.itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            label = self.local_degrade(row['label'])
            if not visited.get((label, row['type'], row['ilx'])):
                label2rows[label].append(row)
                visited[(label, row['type'], row['ilx'])] = True
        return label2rows

    def get_definition2rows(self):
        self.terms = self.fetch_terms()
        visited = {}
        definition2rows = defaultdict(list)
        header = ['Index'] + list(self.terms.columns)
        for row in self.terms.itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            definition = self.local_degrade(row['definition'])
            if not definition or definition == ' ':
                continue
            if not visited.get((definition, row['type'], row['ilx'])):
                definition2rows[definition].append(row)
                visited[(definition, row['type'], row['ilx'])] = True
        return definition2rows

    def get_tid2row(self):
        tid2row = {}
        header = ['Index'] + list(self.fetch_terms().columns)
        for row in self.fetch_terms().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            tid2row[row['tid']] = row
        return tid2row

    def get_ilx2row(self):
        ilx2row = {}
        header = ['Index'] + list(self.fetch_terms().columns)
        for row in self.fetch_terms().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            ilx2row[row['ilx']] = row
        return ilx2row

    def get_ilx2superclass(self, clean:bool=True):
        ''' clean: for list of literals only '''
        ilx2superclass = defaultdict(list)
        header = ['Index'] + list(self.fetch_superclasses().columns)
        for row in self.fetch_superclasses().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            if clean:
                superclass = {
                    'tid': row['superclass_tid'],
                    'ilx': row['superclass_ilx'],
                }
                ilx2superclass[row['term_ilx']].append(superclass)
            elif not clean:
                ilx2superclass[row['term_ilx']].append(row)
        return ilx2superclass

    def get_tid2annotations(self, clean:bool=True):
        ''' clean: for list of literals only '''
        tid2annotations = defaultdict(list)
        header = ['Index'] + list(self.fetch_annotations().columns)
        for row in self.fetch_annotations().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            if clean:
                annotation = {
                    'tid': row['tid'],
                    'annotation_type_tid': row['annotation_type_tid'],
                    'value': row['value'],
                    'annotation_type_label': row['annotation_type_label'],
                }
                tid2annotations[row['tid']].append(annotation)
            elif not clean:
                tid2annotations[row['tid']].append(row)
        return tid2annotations

    def get_ilx2annotations(self, clean:bool=True):
        ''' clean: for list of literals only '''
        ilx2annotations = defaultdict(list)
        header = ['Index'] + list(self.fetch_annotations().columns)
        for row in self.fetch_annotations().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            if clean:
                annotation = {
                    'tid': row['tid'],
                    'annotation_type_tid': row['annotation_type_tid'],
                    'value': row['value'],
                    'annotation_type_label': row['annotation_type_label'],
                }
                ilx2annotations[row['term_ilx']].append(annotation)
            elif not clean:
                ilx2annotations[row['term_ilx']].append(row)
        return ilx2annotations


    def get_tid2synonyms(self, clean:bool=True):
        ''' clean: for list of literals only '''
        tid2synonyms = {}
        header = ['Index'] + list(self.fetch_synonyms().columns)
        for row in self.fetch_synonyms().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            if clean:
                synonym = {'literal':row['literal'], 'type':row['type']}
                tid2synonyms[row['tid']].append(synonym)
            elif not clean:
                tid2synonyms[row['tid']].append(row)
        return tid2synonyms

    def get_ilx2synonyms(self, clean:bool=True):
        ''' clean: for list of literals only '''
        ilx2synonyms = defaultdict(list)
        header = ['Index'] + list(self.fetch_synonyms().columns)
        for row in self.fetch_synonyms().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            if clean:
                synonym = {'literal':row['literal'], 'type':row['type']}
                ilx2synonyms[row['ilx']].append(synonym)
            elif not clean:
                ilx2synonyms[row['ilx']].append(row)
        return ilx2synonyms

    def get_iri2row(self):
        iri2row = {}
        header = ['Index'] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            iri2row[row['iri']] = row
        return iri2row

    def get_tid2existing_ids(self, clean=True):
        tid2existing_ids = defaultdict(list)
        header = ['Index'] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            if clean:
                existing_id = {'iri':row['iri'], 'curie':row['curie']}
                tid2existing_ids[row['tid']].append(existing_id)
            elif not clean:
                tid2existing_ids[row['tid']].append(row)
        return tid2existing_ids

    def get_ilx2existing_ids(self, clean=True):
        ilx2existing_ids = defaultdict(list)
        header = ['Index'] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            if clean:
                existing_id = {'iri':row['iri'], 'curie':row['curie']}
                ilx2existing_ids[row['ilx']].append(existing_id)
            elif not clean:
                ilx2existing_ids[row['ilx']].append(row)
        return ilx2existing_ids

    def get_curie2row(self):
        curie2row = {}
        header = ['Index'] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            curie2row[row['curie']] = row
        return curie2row

    def get_fragment2rows(self):
        fragement2rows = defaultdict(list)
        header = ['Index'] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}
            if not row['curie']: # there are a few with no curies that will cause a false positive
                continue
            fragment = row['curie'].split(':')[-1]
            fragement2rows[fragment].append(row)
        return fragement2rows

    def show_tables(self):
        data = "SHOW tables;"
        return pd.read_sql(data, self.engine)

    def get_table(self, tablename, limit=5):
        data = """
            SELECT *
            FROM {tablename}
            LIMIT {limit}
        """.format(tablename=tablename, limit=limit)
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
