from collections import defaultdict
import os
from pathlib import Path
from typing import Union, Dict, Tuple, List

import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column

from ilxutils.tools import light_degrade, open_pickle, create_pickle


TERMSC_BACKUP = 'ilx_db_terms_complete_backup.pickle'
TERMS_BACKUP = 'ilx_db_terms_backup.pickle'
ANNOS_BACKUP = 'ilx_db_annotations_backup.pickle'
RELAS_BACKUP = 'ilx_db_relationships_backup.pickle'
SUPER_BACKUP = 'ilx_db_superclasses_backup.pickle'
SYNOS_BACKUP = 'ilx_db_synonyms_backup.pickle'
EXIDS_BACKUP = 'ilx_db_existing_ids_backup.pickle'


def pathing(path, check_path=False):
    """ Extract absolute path from shortened or relative paths.

    :param str path: path to file or folder.

    :examples:
    >>>pathing('~/shortened.filepath')
    >>>pathing('../relative.filepath')
    >>>pathing('relative.filepath')
    >>>pathing('/home/absoulte/filepath')
    """
    path = Path(path)
    if str(path).startswith('~'):
        path = path.expanduser()
    else:
        path = path.resolve()

    if check_path:
        if not path.is_file() and path.is_dir():
            raise ValueError(f'{path} does not exit')

    return path


class IlxSql:

    def __init__(self,
                 db_url: str,
                 from_backup: bool = False,
                 pre_load: bool = False,
                 backups_folder: str = '~/.interlex_backups'):

        self.engine = create_engine(db_url)
        self.from_backup = from_backup

        self.save_folder = pathing(backups_folder)
        try:
            self.save_folder.mkdir()
        except:
            pass

        self.terms = pd.DataFrame
        self.superclasses = pd.DataFrame
        self.annotations = pd.DataFrame
        self.existing_ids = pd.DataFrame
        self.relationships = pd.DataFrame
        self.synonyms = pd.DataFrame

        # Auto load tables from backup
        if pre_load:
            self.pre_loader()


    def pre_loader(self):
        # self.terms_complete = self.get_terms_complete() if pre_load else pd.DataFrame
        self.terms = self.get_terms()
        # self.superclasses = self.get_superclasses()
        self.existing_ids = self.get_existing_ids()
        self.synonyms = self.get_synonyms()
        # self.relationships = self.get_relationships()
        # self.annotations = self.get_annotations()

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
        if self.from_backup:
            self.terms = open_pickle(self.save_folder / TERMS_BACKUP)
            return self.terms
        sql_query = """
            SELECT t.id as tid, t.ilx, t.label, t.definition, t.type, t.comment, t.version, t.uid, t.cid, t.time, t.status
            FROM terms t
            GROUP BY t.ilx
            HAVING t.status = '0'
        """
        self.terms = pd.read_sql(sql_query, self.engine)
        create_pickle(self.terms, self.save_folder / TERMS_BACKUP)
        return self.terms

    def get_annotations(self):
        if self.from_backup:
            self.annotations = open_pickle(self.save_folder / ANNOS_BACKUP)
            return self.annotations
        sql_query = """
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
                HAVING terms.status = '0'
            ) AS t1 ON ta.tid=t1.id
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
                HAVING terms.status = '0'
            ) AS t2 ON ta.annotation_tid=t2.id
        """
        self.annotations = pd.read_sql(sql_query, self.engine)
        create_pickle(self.annotations, self.save_folder / ANNOS_BACKUP)
        return self.annotations

    def get_existing_ids(self):
        if self.from_backup:
            self.existing_ids = open_pickle(self.save_folder / EXIDS_BACKUP)
            return self.existing_ids
        sql_query = """
            SELECT tei.tid, tei.curie, tei.iri, tei.preferred, t.ilx, t.label, t.definition, t.status
            FROM (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
                HAVING terms.status = '0'
            ) as t
            JOIN term_existing_ids AS tei
            ON t.id = tei.tid
        """
        self.existing_ids = pd.read_sql(sql_query, self.engine)
        create_pickle(self.existing_ids, self.save_folder / EXIDS_BACKUP)
        return self.existing_ids

    def get_relationships(self):
        if self.from_backup:
            self.relationships = open_pickle(self.save_folder / RELAS_BACKUP)
            return self.relationships
        sql_query = """
           SELECT
               t1.id as term1_tid, t1.ilx AS term1_ilx, t1.type as term1_type, t1.label as term1_label,
               t2.id as term2_tid, t2.ilx AS term2_ilx, t2.type as term2_type, t2.label as term2_label,
               t3.id as relationship_tid, t3.ilx AS relationship_ilx, t3.label as relationship_label
           FROM term_relationships AS tr
           JOIN (
               SELECT *
               FROM terms
               GROUP BY terms.ilx
               HAVING terms.status = '0'
           ) t1 ON t1.id = tr.term1_id
           JOIN (
               SELECT *
               FROM terms
               GROUP BY terms.ilx
               HAVING terms.status = '0'
           ) AS t2 ON t2.id = tr.term2_id
           JOIN (
               SELECT *
               FROM terms
               GROUP BY terms.ilx
               HAVING terms.status = '0'
           ) AS t3 ON t3.id = tr.relationship_tid
        """
        self.relationships = pd.read_sql(sql_query, self.engine)
        create_pickle(self.relationships, self.save_folder / RELAS_BACKUP)
        return self.relationships

    def get_superclasses(self):
        if self.from_backup:
            self.superclasses = open_pickle(self.save_folder / SUPER_BACKUP)
            return self.superclasses
        sql_query = """
            SELECT
                ts.tid, ts.superclass_tid,
                t1.label as term_label, t1.ilx as term_ilx,
                t2.label as superclass_label, t2.ilx as superclass_ilx
            FROM term_superclasses AS ts
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
                HAVING terms.status = '0'
            ) as t1
            ON t1.id = ts.tid
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
                HAVING terms.status = '0'
            ) AS t2
            ON t2.id = ts.superclass_tid
        """
        self.superclasses = pd.read_sql(sql_query, self.engine)
        create_pickle(self.superclasses, self.save_folder / SUPER_BACKUP)
        return self.superclasses

    def get_synonyms(self):
        if self.from_backup:
            self.synonyms = open_pickle(self.save_folder / SYNOS_BACKUP)
            return self.synonyms
        sql_query = """
            SELECT ts.tid as tid, t.ilx, ts.literal, ts.type
            FROM term_synonyms AS ts
            JOIN (
                SELECT *
                FROM terms
                GROUP BY terms.ilx
                HAVING terms.status = '0'
            ) AS t
            WHERE ts.tid=t.id
        """
        self.synonyms = pd.read_sql(sql_query, self.engine)
        create_pickle(self.synonyms, self.save_folder / SYNOS_BACKUP)
        return self.synonyms

    def get_terms_complete(self) -> pd.DataFrame:
        ''' Gets complete entity data like term/view '''
        if self.from_backup:
            self.terms_complete = open_pickle(self.save_folder / TERMSC_BACKUP)
            return self.terms_complete
        ilx2synonyms = self.get_ilx2synonyms()
        ilx2existing_ids = self.get_ilx2existing_ids()
        ilx2annotations = self.get_ilx2annotations()
        ilx2relationships = self.get_ilx2relationships()
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
        create_pickle(terms_complete, self.save_folder / TERMSC_BACKUP)
        return terms_complete

    def get_label2id(self, clean: object = None) -> Dict[str, list]:
        if not clean:
            clean = lambda string: string.lower().strip()
        label2id = defaultdict(list)
        [label2id[clean(row.label)].append(row.id) for row in self.fetch_terms().itertuples()]
        return label2id

    def get_label2ilx(self, clean: object = None) -> Dict[str, list]:
        if not clean:
            clean = lambda string: string.lower().strip()
        label2ilx = defaultdict(list)
        [label2ilx[clean(row.label)].append(row.ilx) for row in self.fetch_terms().itertuples()]
        [label2ilx[clean(row.literal)].append(row.ilx) for row in self.fetch_synonyms().itertuples()]
        return label2ilx

    # def get_label2rows(self):
    #     self.terms = self.fetch_terms()
    #     visited = {}
    #     label2rows = defaultdict(list)
    #     header = ['Index'] + list(self.terms.columns)
    #     for row in self.terms.itertuples():
    #         row = {header[i]: val for i, val in enumerate(row)}
    #         label = row['label'].lower().strip()
    #         if not visited.get((label, row['type'], row['ilx'])):
    #             label2rows[label].append(row)
    #             visited[(label, row['type'], row['ilx'])] = True
    #     return label2rows
    
    def get_label2rows(self, clean: object = None) -> Dict[str, list]:
        if not clean:
            clean = lambda string: string.lower().strip()
        label2ilx = defaultdict(list)
        [label2ilx[clean(row.label)].append(row) for row in self.fetch_terms().itertuples()]
        [label2ilx[clean(row.literal)].append(row) for row in self.fetch_synonyms().itertuples()]
        return label2ilx

    def get_ilx2synonyms(self) -> defaultdict(list):
        ilx2synonyms = defaultdict(list)
        [ilx2synonyms[row.ilx].append(row.literal) for row in self.fetch_synonyms().itertuples()]
        return ilx2synonyms

    def get_definition2rows(self):
        self.terms = self.fetch_terms()
        visited = {}
        definition2rows = defaultdict(list)
        header = ['Index'] + list(self.terms.columns)
        for row in self.terms.itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            definition = row['definition'].lower().strip()
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

    def get_ilx2relationships(self):
        ilx2relationships = defaultdict(list)
        header = ['Index'] + list(self.fetch_relationships().columns)
        for row in self.fetch_relationships().itertuples():
            row = {header[i]:val for i, val in enumerate(row)}      

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
        sql_query = "SHOW tables;"
        return pd.read_sql(sql_query, self.engine)

    def get_table(self, tablename, limit=5):
        sql_query = """
            SELECT *
            FROM {tablename}
            LIMIT {limit}
        """.format(tablename=tablename, limit=limit)
        return pd.read_sql(sql_query, self.engine)

    def get_custom(self, sql_query):
        return pd.read_sql(sql_query, self.engine)


def main():
    db_url = os.environ.get('SCICRUNCH_DB_URL_PRODUCTION')
    sql = IlxSql(db_url)
    rels = sql.get_relationships()
    print(rels.head())


if __name__ == '__main__':
    main()
