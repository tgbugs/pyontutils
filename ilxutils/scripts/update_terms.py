import json
import sys
import math as m
from args_reader import read_args
import dictlib
from scicrunch_client import scicrunch

def file_opener(infile):
    return json.load(open(infile))

def main():
    args = read_args()
    terms = file_opener(infile=args.file)#get labels to update
    terms = terms[:] #debug
    sci = scicrunch(api_key=args.api_key, base_path=args.base_path, engine_key=args.engine_key)

    seg_length = 100 #Server times out if given too much in a single batch
    total_terms = [terms[x:x+seg_length] for x in range(0,len(terms),seg_length)]
    total_count = m.floor(len(terms) / seg_length)
    for i, ts in enumerate(total_terms):
        print('Batch', i, 'out of', total_count)
        sci.updateTerms(ts)

if __name__ == '__main__':
    main()
