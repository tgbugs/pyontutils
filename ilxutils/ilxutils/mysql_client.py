import os
import pandas as pd
from sqlalchemy import create_engine, inspect, Table, Column
from sys import exit


class MysqlClient:

    def __init__(
        self,
        user,
        password,
        hostname,
    ):
        self.db_url = 'mysql+mysqlconnector://{user}:{password}@{hostname}'.format(
            user = user,
            password = password,
            hostname = hostname,
        )
        self.db_engine = create_engine(self.db_url)
        print(self.db_url)

    def show_databases(self):
        sqlquery = """ SHOW DATABASES; """
        print(pd.read_sql(sqlquery, self.db_engine))

    def show_tables(self, db_name):
        sqlquery = """ SHOW TABLES; """
        engine = create_engine('/'.join([self.db_url, db_name]))
        print(pd.read_sql(sqlquery, engine))

    def get_db_engine(self, db_name):
        return create_engine('/'.join([self.db_url, db_name]))
        

def main():
    sqlc = MysqlClient(
        user = 'root',
        password = os.environ.get('MYSQL_ROOT_PASSWORD'),
        hostname = 'localhost'
    )
    sqlc.show_databases()
    sqlc.show_tables('umls2018ab')


if __name__ == '__main__':
    main()
