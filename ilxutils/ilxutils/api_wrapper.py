""" Used as a master args reader for scripts that read, add, and update Interlex data through its API

Usage:  api_wrapper.py [-h | --help]
        api_wrapper.py [-v | --version]
        api_wrapper.py <argument> [-f=<path>] [-k=<path>] [-d=<path>] [-p | -b]

Arugments:
    addTerms                        Add terms|cdes|annotations|relationships to SciCrunch
    updateTerms                     Update terms|cdes|annotations|relationships in SciCrunch
    addAnnotations                  Add annotations to existing elements
    updateAnnotations               Update annotations

Options:
    -h --help                      Display this help message
    -v --version                   Current version of file
    -f --file=<path>               File that holds the data you wish to upload to Scicrunch
    -k --api_key=<path>            Key path [default: keys/production_api_scicrunch_key.txt]
    -d --db_url=<path>             Engine key path [default: keys/production_engine_scicrunch_key.txt]
    -p --production                Production SciCrunch
    -b --beta                      Beta SciCrunch
"""
from docopt import docopt
import json
import math as m
from pathlib import Path as p
import time
from sys import exit
from ilxutils.args_reader import ilx_doc2args
from ilxutils.scicrunch_client import scicrunch
from ilxutils.tools import open_json
VERSION = '0.0.5'


def batch(data, seg_length, start_batch, end_batch, func, **kwargs):
    if start_batch != 0:
        print("Warning: Start Batch isn't 0")
    total_data = [data[x:x + seg_length]
                  for x in range(0, len(data), seg_length)]
    total_count = m.floor(len(data) / seg_length)
    output = []
    for i, _data in enumerate(total_data[start_batch:end_batch], start_batch):
        print('Batch', i, 'out of', total_count)
        output.extend(func(_data, **kwargs))
    return output


def main():
    doc = docopt(__doc__, version=VERSION)
    args = ilx_doc2args(doc)
    print(args)
    data = open_json(infile=args.file)
    data = data[:]  # for debuging
    sci = scicrunch(api_key=args.api_key,
                    base_path=args.base_path,
                    db_url=args.db_url)

    FUNCTION_MAP = {
        'addTerms': sci.addTerms,
        'updateTerms': sci.updateTerms,
        'addAnnotations': sci.addAnnotations,
        'updateAnnotations': sci.updateAnnotations,
        'deleteAnnotations': sci.deleteAnnotations,
        'addRelationships': sci.addRelationships,
    }

    output = batch(data=data,
                   seg_length=10,
                   start_batch=0,  # 1408, # regarding uids
                   end_batch=None,  # 1410,
                   func=FUNCTION_MAP[args['<argument>']],
                   _print=True,
                   crawl=False,
                   LIMIT=10,)


if __name__ == '__main__':
    main()
