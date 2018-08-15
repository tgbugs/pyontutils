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
import requests as r
import subprocess as sb
from pathlib import Path as p

with open('/home/troy/elastic_migration/auth.ini', 'r') as uk:
    vars = uk.read().split('\n')
    username = vars[0].split('=')[-1].strip()
    password = vars[1].split('=')[-1].strip()

args = read_args(
    api_key=p.home() / 'keys/production_api_scicrunch_key.txt',
    db_url=p.home() / 'keys/production_engine_scicrunch_key.txt',
    production=True)
#args = read_args(api_key='../production_api_scicrunch_key.txt', db_url='../production_engine_scicrunch_key.txt', production=True)
sql = interlex_sql(db_url=args.db_url)
sci = scicrunch(
    api_key=args.api_key, base_path=args.base_path, db_url=args.db_url)


def plink(ilxid):
    return "http://interlex.scicrunch.io/scicrunch/term/%s" % ilxid


def blink(ilxid):
    return "https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/interlex/term/%s" % ilxid


#8583532179
from random import choice
from string import ascii_uppercase


def get_random_words(lenghth=15, count=1):
    return [
        'troy_test_' + ''.join(choice(ascii_uppercase) for i in range(12))
        for _ in range(count)
    ]


def create_ilx_format_from_words(words):
    superclasses = [{
        'id': '146',
    }]
    return [{
        'term': w,
        'type': 'term',
        "definition": "test123",
        "superclasses": superclasses
    } for w in words]


words = get_random_words()
test_terms = create_ilx_format_from_words(words)
#print(test_terms)

#print(test_terms)
"""
ilx_data = sci.addTerms(test_terms)#, _print=True)
ilx_to_label = sql.get_ilx_to_label()

for d in ilx_data:
    if not ilx_to_label[d['ilx']] == d['label']:
        sys.exit(blink(d['ilx']))

terms_data = []
for d in ilx_data:
    terms_data.append({'id':d['id'], 'definition':'update_test'})
update_data = sci.updateTerms(terms_data)#, _print=True)

for d in update_data:
    if d['definition'] != 'update_test':
        sys.exit(blink[d['ilx']])
"""
sci.updateTerms([{'id': 15065, 'definition': 'troy_test_may_17_2018'}])


def ela_search(ilx):
    return r.get(blink(ilx), auth=(username, password))


ilx_data = [{'ilx': 'ilx_0115063'}]
results = [
    ela_search(d['ilx']).json()
    if not ela_search(d['ilx']).raise_for_status() else sys.exit(d)
    for d in ilx_data
]
#print(results)
#json.dump(results, open('../elastic_testing.json', 'w'), indent=4)
#python3 elastic_test.py  8.60s user 1.07s system 3% cpu 4:55.25 total for new elastic

#annotation_format = {'tid':'', 'annotation_tid':'', 'value':''}
#annotation_format['tid']=49552
#annotation_format['annotation_tid']=15077
#annotation_format['value']='testing value2'
#sci.addAnnotations([annotation_format])
