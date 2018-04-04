import pandas as pd
import requests as r
import json
from sqlalchemy import create_engine, inspect, Table, Column
import numpy as np
import asyncio
import sys
import math as m
import progressbar
from aiohttp import ClientSession, TCPConnector, BasicAuth
from args_reader import read_args
from collections import defaultdict, namedtuple
import dictlib
from scicrunch_client_fast_mod import scicrunch

def file_opener(infile):
    return json.load(open(infile, 'r'))

def main():
    args = read_args()
    data = file_opener(infile=args['file'])#get labels to update
    data = data[:1] #debug
    sci = scicrunch(key=args['api_key'], base_path=args['base_path'])

    FUNCTION_MAP = {
        'addTerms':sci.addTerms,
        'updateTerms':sci.updateTerms,
        'addAnnotations':sci.addAnnotations,
    }

    seg_length = 50 #Server times out if given too much in a single batch
    total_data = [data[x:x+seg_length] for x in range(0,len(data),seg_length)]
    total_count = m.floor(len(data) / seg_length)
    for i, d in enumerate(total_data):
        print('Batch', i, 'out of', total_count)
        FUNCTION_MAP[args['command']](d, sql=args['sql'])

if __name__ == '__main__':
    main()
