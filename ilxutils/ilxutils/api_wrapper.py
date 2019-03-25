""" Used as a master args reader for scripts that read, add, and update Interlex data through its API

Usage:  api_wrapper.py [-h | --help]
        api_wrapper.py [-v | --version]
        api_wrapper.py <argument> [-f=<path>] [-o=<path>] [-p | -b]

Arugments:
    addTerms                        Add terms|cdes|annotations|relationships to SciCrunch
    updateTerms                     Update terms|cdes|annotations|relationships in SciCrunch
    addAnnotations                  Add annotations to existing elements
    updateAnnotations               Update annotations

Options:
    -h --help                      Display this help message
    -v --version                   Current version of file
    -f --file=<path>               File that holds the data you wish to upload to Scicrunch
    -p --production                Production SciCrunch
    -b --beta                      Beta SciCrunch
    -o --output=<path>             saved outputed data location
"""
import datetime
from docopt import docopt
import json
import math as m
from pathlib import Path
import time
from sys import exit
from ilxutils.scicrunch_client import scicrunch
from ilxutils.tools import open_json, create_json
import os
VERSION = '0.0.5'


def batch(data, seg_length, start_batch, end_batch, func, **kwargs):
    if start_batch != 0: print("Warning: Start Batch isn't 0")

    total_data = [data[x:x + seg_length] for x in range(0, len(data), seg_length)]
    total_count = m.floor(len(data) / seg_length)
    output = []

    for i, _data in enumerate(total_data[start_batch:end_batch], start_batch):
        print('Batch', i, 'out of', total_count)
        output.extend(func(_data, **kwargs))

    return output


def main():
    doc = docopt(__doc__, version=VERSION)
    if doc['--production']:
        base_url = os.environ.get('SCICRUNCH_BASEURL_PRODUCTION')
    elif doc['--beta']:
        base_url = os.environ.get('SCICRUNCH_BASEURL_BETA')
    else:
        exit('Need to specify SciCrunch client version.')

    if doc['--output']:
        output_path = doc['--output']
    else:
        now = datetime.datetime.now().strftime('%Y-%m-%d')
        output_path = Path.home()/('Dropbox/tmp/api_wrapper_output_on_'+str(now)+'.json')

    api_key = os.environ.get('SCICRUNCH_API_KEY')

    data = open_json(infile=doc['--file'])
    data = data[:]  # for debuging
    sci = scicrunch(
        api_key = api_key,
        base_url = base_url,
    )

    FUNCTION_MAP = {
        'addTerms': sci.addTerms,
        'updateTerms': sci.updateTerms,
        'addAnnotations': sci.addAnnotations,
        'updateAnnotations': sci.updateAnnotations,
        'deleteAnnotations': sci.deleteAnnotations,
        'addRelationships': sci.addRelationships,
    }

    resp = batch(
        data = data,
        seg_length = 100,
        start_batch = 0,  # WHAT?! -> 2340, regarding meshdump
        end_batch = None,  #
        func = FUNCTION_MAP[doc['<argument>']],
        _print = True,
        crawl = False,
        LIMIT = 25,
    )
    #create_json(resp, output_path)


if __name__ == '__main__':
    main()
