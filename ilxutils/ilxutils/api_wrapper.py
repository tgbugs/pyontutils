import json
import sys
import math as m
from pathlib import Path as p
from ilxutils.args_reader import read_args
from ilxutils.scicrunch_client import scicrunch
from ilxutils.tools import cj, oj

def main():
    args = read_args(VERSION='0.3')
    data = oj(filepath=args.file)
    data = data[:] #for debuging
    sci = scicrunch(api_key=args.api_key, base_path=args.base_path, db_url=args.db_url)

    FUNCTION_MAP = {
        'addTerms':sci.addTerms,
        'updateTerms':sci.updateTerms,
        'addAnnotations':sci.addAnnotations,
        'updateAnnotations':sci.updateAnnotations,
        'deleteAnnotations':sci.deleteAnnotations,
    }

    seg_length = 25 #Server times out if given too much in a single batch
    total_data = [data[x:x+seg_length] for x in range(0,len(data),seg_length)]
    total_count = m.floor(len(data) / seg_length)
    start = 7315 #4way update stop
    for i, data in enumerate(total_data[start:], start):
        print('Batch', i, 'out of', total_count)
        FUNCTION_MAP[args['<argument>']](data, LIMIT=25) #limit should be 25 > x > 10

if __name__ == '__main__':
    main()
