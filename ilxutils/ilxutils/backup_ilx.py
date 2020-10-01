from pathlib import Path as p
from ilxutils.interlex_sql import IlxSql
from ilxutils.tools import create_pickle
import os


sql = IlxSql(db_url=os.environ.get('SCICRUNCH_DB_URL_PRODUCTION'))


terms = sql.get_terms()
create_pickle(terms, p.home() / 'Dropbox/interlex_backups/ilx_db_terms_backup.pickle')
print('=== terms backup complete ===')
del terms


annos = sql.get_annotations()
create_pickle(annos, p.home() / 'Dropbox/interlex_backups/ilx_db_annos_backup.pickle')
print('=== annotations backup complete ===')
del annos


ex = sql.get_existing_ids()
create_pickle(ex, p.home() / 'Dropbox/interlex_backups/ilx_db_ex_backup.pickle')
print('=== existing ids backup complete ===')
del ex


synonyms = sql.get_synonyms()
create_pickle(synonyms, p.home() / 'Dropbox/interlex_backups/ilx_db_synonyms_backup.pickle')
print('=== synonyms backup complete ===')
del synonyms


superclasses = sql.get_superclasses()
create_pickle(superclasses, p.home() / 'Dropbox/interlex_backups/ilx_db_superclasses_backup.pickle')
print('=== superclasses backup complete ===')
del superclasses

relationships = sql.get_relationships()
create_pickle(relationships, p.home() / 'Dropbox/interlex_backups/ilx_db_relationships_backup.pickle')
print('=== relationships backup complete ===')
del relationships
