import json
import sys
import math as m
from ilxutils.args_reader import read_args
import dictlib
from ilxutils.scicrunch_client import scicrunch


def file_opener(infile):
    return json.load(open(infile))


def main():
    args = read_args()
    annotations = file_opener(infile=args.file)  #get labels to update
    annotations = annotations[:]  #debug
    sci = scicrunch(
        api_key=args.api_key,
        base_path=args.base_path,
        engine_key=args.engine_key)

    seg_length = 100  #Server times out if given too much in a single batch
    total_annotations = [
        annotations[x:x + seg_length]
        for x in range(0, len(annotations), seg_length)
    ]
    total_count = m.floor(len(annotations) / seg_length)
    for i, annos in enumerate(total_annotations):
        print('Batch', i, 'out of', total_count)
        #print(annos)
        sci.addAnnotations(annos)


if __name__ == '__main__':
    main()
