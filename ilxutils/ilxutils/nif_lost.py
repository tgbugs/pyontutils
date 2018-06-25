import json
from sqlalchemy import create_engine, inspect, Table, Column
import pandas as pd
from ilxutils.args_reader import read_args
from ilxutils.scicrunch_client import scicrunch
import sys
import time
from ilxutils.interlex_sql import interlex_sql
import re
from collections import defaultdict
from pyontutils.utils import *
from pyontutils.core import *
from pyontutils.closed_namespaces import *
import rdflib
import pickle

args = read_args(
    api_key='../keys/production_api_scicrunch_key.txt',
    db_url='../keys/production_engine_scicrunch_key.txt',
    production=True)
sql = interlex_sql(engine_key=args.db_url)
sci = scicrunch(
    api_key=args.api_key, base_path=args.base_path, engine_key=args.db_url)

g_nif = makeGraph(
    '', graph=pickle.load(open('../nif-ilx-versions/NIF-ALL.pickle', 'rb')))


#total-sub   261096
#total-lists 167238
#sub          33508
#lists        63154
def check_restrictions(graph):

    r = Restriction(rdfs.subClassOf)
    sub = r.parse(graph=graph.g)

    r = Restriction(rdf.first)
    lists = r.parse(graph=graph.g)

    return sub, lists


sub, lists = check_restrictions(g_nif)


def wj(data, name):
    json.dump(data, open(name + '.json', 'w'), indent=4)


wj(sub, 'sub')
wj(lists, 'lists')

print('sub', len(sub))
print('lists', len(lists))
