from collections import defaultdict
import pandas as pd
import pickle
from sqlalchemy import create_engine, inspect, Table, Column
from sqlalchemy.engine.url import make_url
from sys import exit


class DatabaseClient:

    """ Takes care of the database pass opening to find the url and can query
        the respected database.

        Input:
            dbpass_path     path to the text file with the list of database urls
            dbname          database name so we know which database to query from the list
    """

    def __init__(self, dbpass_path, dbname):
        self.dbpass_path = dbpass_path
        self.dbname = dbname
        self.db_url = self.get_db_url()
        self.engine = create_engine(self.db_url)

    def get_db_url(self):
        with open(self.dbpass_path, 'r') as infile:
            db_names = []
            for raw_url in infile.read().splitlines():
                url_obj = make_url(raw_url)
                if url_obj.database == self.dbname:
                    infile.close()
                    return raw_url
                db_names.append(url_obj.database)
        infile.close()
        exit('database name does not exist in dbpass given:' + ', '.join(db_names))

    def get_df_with_query(self, query):
        """ WARNING :: Will crash if too large. If so, you should just create the df file
            first via create_df_file(query=).

        load example:
            with open(input, 'rb') as infile:
                objs = []
                while True:
                    try:
                        obj = pickle.load(infile)
                    except EOFError:
                        break
                    ...
        """
        return pd.read_sql(query, self.engine)

    def create_df_file_with_query(self, query, output):
        """ Dumps in df in chunks to avoid crashes.
        """
        chunk_size = 100000
        offset = 0
        data = defaultdict(lambda : defaultdict(list))

        with open(output, 'wb') as outfile:
            query = query.replace(';', '')
            query += """ LIMIT {chunk_size} OFFSET {offset};"""
            while True:
                print(offset)
                query = query.format(
                    chunk_size=chunk_size,
                    offset=offset
                )
                df = pd.read_sql(query, self.engine)
                pickle.dump(df, outfile)
                offset += chunk_size
                if len(df) < chunk_size:
                    break
            outfile.close()
