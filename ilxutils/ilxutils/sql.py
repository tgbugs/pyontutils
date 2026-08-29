from .interlex_sql import IlxSql
import os

def production_sql(from_backup=True):
    return IlxSql(db_url=os.environ.get('SCICRUNCH_DB_URL_PRODUCTION'), from_backup=from_backup)

def test_sql(db_url=None, schema=None, from_backup=True):
    db_url = os.environ.get('SCICRUNCH_DB_URL_TEST') if not db_url else  db_url
    # Default test schema is nif_test3
    if schema:
        db_url = '/'.join(db_url.split('/')[:-1] + [schema])
    return IlxSql(db_url=db_url, from_backup=from_backup)
