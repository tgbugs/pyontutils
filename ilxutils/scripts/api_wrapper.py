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
    sys.exit(args)
    data = file_opener(infile=args.file)#get labels to update
    data = data[:] #debug
    sci = scicrunch(api_key=args.api_key, base_path=args.base_path, engine_key=args.engine_key)

    FUNCTION_MAP = {
        'addTerms':sci.addTerms,
        'updateTerms':sci.updateTerms,
        'addAnnotations':sci.addAnnotations,
        'updateAnntationValues':sci.updateAnntationValues,
        'updateAnntationType':sci.updateAnntationType,
    }

    seg_length = 100 #Server times out if given too much in a single batch
    total_data = [data[x:x+seg_length] for x in range(0,len(data),seg_length)]
    total_count = m.floor(len(data) / seg_length)
    for i, data in enumerate(total_data):
        print('Batch', i, 'out of', total_count)
        FUNCTION_MAP['<argument>'](data) #, sql=args['sql'])

if __name__ == '__main__':
    main()
