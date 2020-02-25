from .interlex_sql import IlxSql
import os

def production_sql(from_backup=True):
    return IlxSql(db_url=os.environ.get('SCICRUNCH_DB_URL_PRODUCTION'), from_backup=from_backup)

def beta_sql(from_backup=True):
    # TEST{#} should be a thing since this still relies on main sql test
    return IlxSql(db_url=os.environ.get('SCICRUNCH_DB_URL_BETA'), from_backup=from_backup)

# entities = []
# for ilx, group in ex.groupby('ilx'):
#     if not any(list(group['preferred'] == '1')):
#         entities.append(ilx)

# from ontquery.plugins.services.interlex_client import InterLexClient
