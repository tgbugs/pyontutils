import json
import sys
import math as m
from ilxutils.args_reader import read_args
import dictlib
from ilxutils.scicrunch_client import scicrunch



def file_opener(infile):
    return json.load(open(infile))

def main():
    args = read_args(VERSION='0.3')
    data = file_opener(infile=args.file)#get labels to update
    data = data[:] #debug
    sci = scicrunch(api_key=args.api_key, base_path=args.base_path, db_url=args.db_url)

    FUNCTION_MAP = {
        'addTerms':sci.addTerms,
        'updateTerms':sci.updateTerms,
        'addAnnotations':sci.addAnnotations,
        'updateAnnotations':sci.updateAnnotations,
        'deleteAnnotations':sci.deleteAnnotations,
    }

    seg_length = 100 #Server times out if given too much in a single batch
    total_data = [data[x:x+seg_length] for x in range(0,len(data),seg_length)]
    total_count = m.floor(len(data) / seg_length)
    start = 572 #stopped here for update
    #start = 23
    #ys.exit(total_data[0])
    for i, data in enumerate(total_data[start:], start):
        print('Batch', i, 'out of', total_count)
        FUNCTION_MAP[args['<argument>']](data, LIMIT=10)

if __name__ == '__main__':
    main()
