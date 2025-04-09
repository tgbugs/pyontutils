from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column
from collections import defaultdict
from .tools import light_degrade, open_pickle, create_pickle
import os

HOME = Path.home() / "DropboxPersonal"
# ELASTIC = 'https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/interlex/term/'
TERMS_COMPLETE_BACKUP_PATH = HOME / ".interlex_backups/ilx_db_terms_complete_backup.pickle"
USERS_BACKUP_PATH = HOME / ".interlex_backups/ilx_db_users_backup.pickle"
TERMS_BACKUP_PATH = HOME / ".interlex_backups/ilx_db_terms_backup.pickle"
ANNOS_BACKUP_PATH = HOME / ".interlex_backups/ilx_db_annotations_backup.pickle"
RELAS_BACKUP_PATH = HOME / ".interlex_backups/ilx_db_relationships_backup.pickle"
SUPER_BACKUP_PATH = HOME / ".interlex_backups/ilx_db_superclasses_backup.pickle"
SYNOS_BACKUP_PATH = HOME / ".interlex_backups/ilx_db_synonyms_backup.pickle"
EXIDS_BACKUP_PATH = HOME / ".interlex_backups/ilx_db_ex_backup.pickle"


class IlxSql:
    def __init__(self, db_url, pre_load=False, from_backup=False):
        self.db_url = db_url
        self.engine = create_engine(self.db_url)
        # current degrade of choice for sql
        self.local_degrade = lambda string: string.lower().strip()
        self.from_backup = from_backup
        # self.terms_complete = self.get_terms_complete() if pre_load else pd.DataFrame
        self.users = pd.DataFrame
        self.terms = pd.DataFrame
        self.superclasses = pd.DataFrame
        self.annotations = pd.DataFrame
        self.existing_ids = pd.DataFrame
        self.relationships = pd.DataFrame
        self.synonyms = pd.DataFrame
        if pre_load:
            self.__pre_load_db()

    def __pre_load_db(self):
        self.users = self.get_users()
        self.terms = self.get_terms()
        self.superclasses = self.get_superclasses()
        self.annotations = self.get_annotations()
        self.existing_ids = self.get_existing_ids()
        self.relationships = self.get_relationships()
        self.synonyms = self.get_synonyms()

    def fix_df_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert Float Columns to Int with 0 for NaN while converting the rest of the NaNs to None.

        Parameters
        ----------
        df : dataframe

        Returns
        -------
        dataframe
            0 and None in place of nans
        """
        float_col = df.select_dtypes(include=["float64"])
        for col in float_col:
            df[col] = df[col].replace({np.nan: 0}).astype(int)
        df = df.replace({np.nan: None})
        return df

    def fetch_terms_complete(self):
        if self.terms_complete.empty:
            return self.get_terms_complete()
        return self.terms_complete

    def fetch_users(self):
        if self.users.empty:
            return self.get_users()
        return self.users

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

    def get_users(self, refresh=False) -> pd.DataFrame:
        """GROUP BY is a shortcut to only getting the first in every list of group"""
        if not self.users.empty and not refresh:
            return self.users
        if self.from_backup:
            self.users = open_pickle(USERS_BACKUP_PATH)
            self.users.name = "users"
            return self.users
        engine = create_engine(self.db_url)
        data = f"""
            SELECT u.*
            FROM users u
        """
        self.users = pd.read_sql(data, engine)
        self.users = self.fix_df_types(self.users)
        self.users.name = "users"
        create_pickle(self.users, USERS_BACKUP_PATH)
        return self.users

    def get_terms(self, status=0, refresh=False):
        """GROUP BY is a shortcut to only getting the first in every list of group"""
        if not self.terms.empty and not refresh:
            return self.terms
        if self.from_backup:
            self.terms = open_pickle(TERMS_BACKUP_PATH)
            self.terms.name = "terms"
            return self.terms
        engine = create_engine(self.db_url)
        data = f"""
            SELECT t.*, u.*
            FROM terms t
            JOIN users u
            ON t.orig_uid = u.guid
            WHERE t.status = '{status}'
        """
        self.terms = pd.read_sql(data, engine)
        self.terms = self.fix_df_types(self.terms)
        self.terms.name = "terms"
        create_pickle(self.terms, TERMS_BACKUP_PATH)
        return self.terms

    def get_annotations(self, status=0, withdrawn=0, refresh=False):
        if not self.annotations.empty and not refresh:
            return self.fetch_annotations()
        if self.from_backup:
            self.annotations = open_pickle(ANNOS_BACKUP_PATH)
            self.annotations.name = "annotations"
            return self.annotations
        engine = create_engine(self.db_url)
        data = f"""
            SELECT
                t1.ilx as term_ilx, t1.label as term_label, t1.type as term_type, t1.orig_cid as term_orig_cid,
                t2.ilx as annotation_type_ilx, t2.label as annotation_type_label,
                ta.*
            FROM term_annotations AS ta
            JOIN (
                SELECT *
                FROM terms
                WHERE status = '{status}'
            ) AS t1 ON ta.tid=t1.id
            JOIN (
                SELECT *
                FROM terms
                WHERE status = '{status}'
            ) AS t2 ON ta.annotation_tid=t2.id
           WHERE ta.withdrawn = '{withdrawn}'
        """
        self.annotations = pd.read_sql(data, engine)
        self.annotations = self.fix_df_types(self.annotations)
        self.annotations.name = "annotations"
        create_pickle(self.annotations, ANNOS_BACKUP_PATH)
        return self.annotations

    def get_existing_ids(self, status=0, refresh=False):
        if not self.existing_ids.empty and not refresh:
            return self.existing_ids
        if self.from_backup:
            self.existing_ids = open_pickle(EXIDS_BACKUP_PATH)
            self.existing_ids.name = "existing_ids"
            return self.existing_ids
        engine = create_engine(self.db_url)
        data = f"""
            SELECT tei.*, t.ilx, t.label, t.type, t.orig_cid
            FROM (
                SELECT *
                FROM terms
                WHERE status = '{status}'
            ) as t
            JOIN term_existing_ids AS tei
            ON t.id = tei.tid
        """
        self.existing_ids = pd.read_sql(data, engine)
        self.existing_ids = self.fix_df_types(self.existing_ids)
        self.existing_ids.name = "existing_ids"
        create_pickle(self.existing_ids, EXIDS_BACKUP_PATH)
        return self.existing_ids

    def get_relationships(self, status=0, withdrawn=0, refresh=False):
        if not self.relationships.empty and not refresh:
            return self.relationships
        if self.from_backup:
            self.relationships = open_pickle(RELAS_BACKUP_PATH)
            self.relationships.name = "relationships"
            return self.relationships
        engine = create_engine(self.db_url)
        data = f"""
           SELECT
               t1.ilx AS term1_ilx, t1.type as term1_type, t1.label as term1_label, t1.orig_cid as term1_orig_cid,
               t2.ilx AS term2_ilx, t2.type as term2_type, t2.label as term2_label, t2.orig_cid as term2_orig_cid,
               t3.ilx AS relationship_ilx, t3.label as relationship_label, 
               tr.*
           FROM term_relationships AS tr
           JOIN (
               SELECT *
               FROM terms
               WHERE status = '{status}'
           ) t1 ON t1.id = tr.term1_id
           JOIN (
               SELECT *
               FROM terms
               WHERE status = '{status}'
           ) AS t2 ON t2.id = tr.term2_id
           JOIN (
               SELECT *
               FROM terms
               WHERE status = '{status}'
           ) AS t3 ON t3.id = tr.relationship_tid
           WHERE tr.withdrawn = '{withdrawn}'
        """
        self.relationships = pd.read_sql(data, engine)
        self.relationships = self.fix_df_types(self.relationships)
        self.relationships.name = "relationships"
        create_pickle(self.relationships, RELAS_BACKUP_PATH)
        return self.relationships

    def get_superclasses(self, status=0, withdrawn=0, refresh=False):
        if not self.superclasses.empty and not refresh:
            return self.superclasses
        if self.from_backup:
            self.superclasses = open_pickle(SUPER_BACKUP_PATH)
            self.superclasses.name = "superclasses"
            return self.superclasses
        engine = create_engine(self.db_url)
        data = f"""
            SELECT
                t1.ilx as term_ilx, t1.label as term_label,
                t2.ilx as superclass_ilx, t2.label as superclass_label,
                ts.*
            FROM term_superclasses AS ts
            JOIN (
                SELECT *
                FROM terms
                WHERE status = '{status}'
            ) as t1
            ON t1.id = ts.tid
            JOIN (
                SELECT *
                FROM terms
                WHERE status = '{status}'
            ) AS t2
            ON t2.id = ts.superclass_tid
        """
        self.superclasses = pd.read_sql(data, engine)
        self.superclasses = self.fix_df_types(self.superclasses)
        self.superclasses.name = "superclasses"
        create_pickle(self.superclasses, SUPER_BACKUP_PATH)
        return self.superclasses

    def get_synonyms(self, status=0, refresh=False):
        if not self.synonyms.empty and not refresh:
            return self.synonyms
        if self.from_backup:
            self.synonyms = open_pickle(SYNOS_BACKUP_PATH)
            self.synonyms.name = "synonyms"
            return self.synonyms
        engine = create_engine(self.db_url)
        data = f"""
            SELECT t.ilx, t.type as term_type, t.label, ts.*
            FROM term_synonyms AS ts
            JOIN (
                SELECT *
                FROM terms
                WHERE status = '{status}'
            ) AS t
            WHERE ts.tid=t.id
        """
        self.synonyms = pd.read_sql(data, engine)
        self.synonyms = self.fix_df_types(self.synonyms)
        self.synonyms.name = "synonyms"
        create_pickle(self.synonyms, SYNOS_BACKUP_PATH)
        return self.synonyms

    # def get_terms_complete(self, status=0, withdrawn=0, refresh=False) -> pd.DataFrame:
    #     ''' Gets complete entity data like term/view '''
    #     if not self.terms_complete.empty and not refresh:
    #         return self.terms_complete
    #     if self.from_backup:
    #         self.terms_complete = open_pickle(TERMS_COMPLETE_BACKUP_PATH)
    #         return self.terms_complete
    #     ilx2synonyms = self.get_ilx2synonyms()
    #     ilx2existing_ids = self.get_ilx2existing_ids()
    #     ilx2annotations = self.get_ilx2annotations()
    #     ilx2superclass = self.get_ilx2superclass()
    #     ilx_complete = []
    #     header = ['Index'] + list(self.fetch_terms().columns)
    #     for row in self.fetch_terms().itertuples():
    #         row = {header[i]: val for i, val in enumerate(row)}
    #         row['synonyms'] = ilx2synonyms.get(row['ilx'])
    #         # if breaks we have worse problems
    #         row['existing_ids'] = ilx2existing_ids[row['ilx']]
    #         row['annotations'] = ilx2annotations.get(row['ilx'])
    #         row['superclass'] = ilx2superclass.get(row['ilx'])
    #         ilx_complete.append(row)
    #     terms_complete = pd.DataFrame(ilx_complete)
    #     create_pickle(terms_complete, TERMS_COMPLETE_BACKUP_PATH)
    #     return terms_complete

    def get_label2id(self):
        self.terms = self.fetch_terms()
        visited = {}
        label_to_id = defaultdict(lambda: defaultdict(list))
        for row in self.terms.itertuples():
            label = self.local_degrade(row.label)
            if not visited.get((label, row.type, row.ilx)):
                if row.type == "term":
                    label_to_id[label]["term"].append(int(row.id))
                    visited[(label, row.type, row.ilx)] = True
                elif row.type == "cde":
                    label_to_id[label]["cde"].append(int(row.id))
                    visited[(label, row.type, row.ilx)] = True
                elif row.type == "fde":
                    label_to_id[label]["fde"].append(int(row.id))
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
        header = ["Index"] + list(self.terms_complete.columns)
        for row in self.terms_complete.itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            label = self.local_degrade(row["label"])
            if not visited.get((label, row["type"], row["ilx"])):
                label2rows[label].append(row)
                visited[(label, row["type"], row["ilx"])] = True
        return label2rows

    def get_definition2rows(self):
        self.terms = self.fetch_terms()
        visited = {}
        definition2rows = defaultdict(list)
        header = ["Index"] + list(self.terms.columns)
        for row in self.terms.itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            definition = self.local_degrade(row["definition"])
            if not definition or definition == " ":
                continue
            if not visited.get((definition, row["type"], row["ilx"])):
                definition2rows[definition].append(row)
                visited[(definition, row["type"], row["ilx"])] = True
        return definition2rows

    def get_tid2row(self):
        tid2row = {}
        header = ["Index"] + list(self.fetch_terms().columns)
        for row in self.fetch_terms().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            tid2row[row["tid"]] = row
        return tid2row

    def get_ilx2row(self):
        ilx2row = {}
        header = ["Index"] + list(self.fetch_terms().columns)
        for row in self.fetch_terms().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            ilx2row[row["ilx"]] = row
        return ilx2row

    def get_ilx2superclass(self, clean: bool = True):
        """clean: for list of literals only"""
        ilx2superclass = defaultdict(list)
        header = ["Index"] + list(self.fetch_superclasses().columns)
        for row in self.fetch_superclasses().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            if clean:
                superclass = {
                    "tid": row["superclass_tid"],
                    "ilx": row["superclass_ilx"],
                }
                ilx2superclass[row["term_ilx"]].append(superclass)
            elif not clean:
                ilx2superclass[row["term_ilx"]].append(row)
        return ilx2superclass

    def get_tid2annotations(self, clean: bool = True):
        """clean: for list of literals only"""
        tid2annotations = defaultdict(list)
        header = ["Index"] + list(self.fetch_annotations().columns)
        for row in self.fetch_annotations().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            if clean:
                annotation = {
                    "tid": row["tid"],
                    "annotation_type_tid": row["annotation_type_tid"],
                    "value": row["value"],
                    "annotation_type_label": row["annotation_type_label"],
                }
                tid2annotations[row["tid"]].append(annotation)
            elif not clean:
                tid2annotations[row["tid"]].append(row)
        return tid2annotations

    def get_ilx2annotations(self, clean: bool = True):
        """clean: for list of literals only"""
        ilx2annotations = defaultdict(list)
        header = ["Index"] + list(self.fetch_annotations().columns)
        for row in self.fetch_annotations().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            if clean:
                annotation = {
                    "tid": row["tid"],
                    "annotation_type_tid": row["annotation_type_tid"],
                    "value": row["value"],
                    "annotation_type_label": row["annotation_type_label"],
                }
                ilx2annotations[row["term_ilx"]].append(annotation)
            elif not clean:
                ilx2annotations[row["term_ilx"]].append(row)
        return ilx2annotations

    def get_tid2synonyms(self, clean: bool = True):
        """clean: for list of literals only"""
        tid2synonyms = {}
        header = ["Index"] + list(self.fetch_synonyms().columns)
        for row in self.fetch_synonyms().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            if clean:
                synonym = {"literal": row["literal"], "type": row["type"]}
                tid2synonyms[row["tid"]].append(synonym)
            elif not clean:
                tid2synonyms[row["tid"]].append(row)
        return tid2synonyms

    def get_ilx2synonyms(self, clean: bool = True):
        """clean: for list of literals only"""
        ilx2synonyms = defaultdict(list)
        header = ["Index"] + list(self.fetch_synonyms().columns)
        for row in self.fetch_synonyms().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            if clean:
                synonym = {"literal": row["literal"], "type": row["type"]}
                ilx2synonyms[row["ilx"]].append(synonym)
            elif not clean:
                ilx2synonyms[row["ilx"]].append(row)
        return ilx2synonyms

    def get_iri2row(self):
        iri2row = {}
        header = ["Index"] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            iri2row[row["iri"]] = row
        return iri2row

    def get_tid2existing_ids(self, clean=True):
        tid2existing_ids = defaultdict(list)
        header = ["Index"] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            if clean:
                existing_id = {"iri": row["iri"], "curie": row["curie"]}
                tid2existing_ids[row["tid"]].append(existing_id)
            elif not clean:
                tid2existing_ids[row["tid"]].append(row)
        return tid2existing_ids

    def get_ilx2existing_ids(self, clean=True):
        ilx2existing_ids = defaultdict(list)
        header = ["Index"] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            if clean:
                existing_id = {"iri": row["iri"], "curie": row["curie"]}
                ilx2existing_ids[row["ilx"]].append(existing_id)
            elif not clean:
                ilx2existing_ids[row["ilx"]].append(row)
        return ilx2existing_ids

    def get_curie2row(self):
        curie2row = {}
        header = ["Index"] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            curie2row[row["curie"]] = row
        return curie2row

    def get_fragment2rows(self):
        fragement2rows = defaultdict(list)
        header = ["Index"] + list(self.fetch_existing_ids().columns)
        for row in self.fetch_existing_ids().itertuples():
            row = {header[i]: val for i, val in enumerate(row)}
            if not row["curie"]:  # there are a few with no curies that will cause a false positive
                continue
            fragment = row["curie"].split(":")[-1]
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
        """.format(
            tablename=tablename, limit=limit
        )
        return pd.read_sql(data, self.engine)

    def get_custom(self, data):
        return pd.read_sql(data, self.engine)


def main():
    db_url = os.environ.get("SCICRUNCH_DB_URL_PRODUCTION")
    sql = IlxSql(db_url)
    rels = sql.get_relationships()
    print(rels.head())


if __name__ == "__main__":
    main()
