from pathlib import Path as p
from ilxutils.args_reader import read_args
from ilxutils.interlex_sql import IlxSql
from ilxutils.scicrunch_client import scicrunch
from ilxutils.tools import *

args = read_args(
    api_key=p.home() / 'keys/production_api_scicrunch_key.txt',
    db_url=p.home() / 'keys/production_engine_scicrunch_key.txt',
    production=True)
sql = IlxSql(db_url=args.db_url)
sci = scicrunch(
    api_key=args.api_key,
    base_path=args.base_path,
    db_url=args.db_url)

terms = sql.get_terms()
annos = sql.get_annotations()
ex = sql.get_existing_ids()

create_pickle(terms, p.home() / 'Dropbox/interlex_backups/ilx_db_terms_backup.pickle')
create_pickle(ex, p.home() / 'Dropbox/interlex_backups/ilx_db_ex_backup.pickle')
create_pickle(annos, p.home() / 'Dropbox/interlex_backups/ilx_db_annos_backup.pickle')
