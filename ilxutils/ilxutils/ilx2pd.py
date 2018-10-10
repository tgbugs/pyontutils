from collections import defaultdict
from ilxutils.interlex_sql import IlxSql
from ilxutils.mydifflib import ratio
from ilxutils.tools import open_pickle, create_pickle
import os
import pandas as pd
from pathlib import Path
from sys import exit


sql = IlxSql(db_url=os.environ.get('SCICRUNCH_DB_URL_PRODUCTION'))
data = {}
output = Path.home()/'Dropbox/ilx-df.pickle'
doc = {'--local':True}


if doc['--local']:
    terms = open_pickle(Path.home()/'Dropbox/interlex_backups/ilx_db_terms_backup.pickle')
    annos = open_pickle(Path.home() / 'Dropbox/interlex_backups/ilx_db_annos_backup.pickle')
    synonyms = open_pickle(Path.home() / 'Dropbox/interlex_backups/ilx_db_synonyms_backup.pickle')
    superclasses = open_pickle(Path.home() / 'Dropbox/interlex_backups/ilx_db_superclasses_backup.pickle')
    relationships = open_pickle(Path.home() / 'Dropbox/interlex_backups/ilx_db_relationships_backup.pickle')
    existing_ids = open_pickle(Path.home()/'Dropbox/interlex_backups/ilx_db_ex_backup.pickle')
elif doc['--src']:
    terms = sql.get_terms()
    annos = sql.get_annotations()
    synonyms = sql.get_synonyms()
    superclasses = sql.get_superclasses()
    relationships = sql.get_relationships()
    existing_ids = sql.get_existing_ids()


for row in terms.itertuples():
    if not data.get(row.ilx):
        data[row.ilx] = defaultdict(set)
    data[row.ilx]['label'].add(row.label)
    data[row.ilx]['ilx'].add(row.ilx)
    data[row.ilx]['definition'].add(row.definition)


for row in annos.itertuples():
    data[row.term_ilx]['annotation'].add((row.annotation_label, row.value))


for row in synonyms.itertuples():
    if row.literal:
        data[row.ilx]['synonym'].add(row.literal)


for row in existing_ids.itertuples():
    data[row.ilx]['existing_ids'].add((row.curie, row.iri))


for row in superclasses.itertuples():
    data[row.term_ilx]['superclass_ilx'].add(row.superclass_ilx)
    superclass_exs = data[row.superclass_ilx]['existing_ids']
    for superclass_ex in superclass_exs:
        data[row.term_ilx]['superclass_existing_ids'].add(superclass_ex)


for row in relationships.itertuples():
    data[row.term1_ilx]['relationship'].add((row.term1_ilx, row.relationship_ilx, row.term2_ilx))
    data[row.term2_ilx]['relationship'].add((row.term2_ilx, row.relationship_ilx, row.term1_ilx))


df = pd.DataFrame.from_records([record for record in data.values()])
create_pickle(df, output)
