#!/usr/bin/env python3
"""Given a ttl file get ILX ids for ILXREPLACE terms.

Usage:
    ilxcli [--replace --logfile=LOG] <file>...

Options:
    -l --logfile=LOG    the file mapping ILXREPLACE to ILX [default: ilx-log.json]
    -r --replace    do the replacement on the file as well
    -h --help       print this

"""
from docopt import docopt
from pyontutils import ilx_utils as iu
from IPython import embed

def test(order, recordDict):
    already_in = [None]
    for k in order:
        already_in.append(recordDict[k]['rec']['label'])
        sc = recordDict[k]['rec']['superclass']['label']
        if sc not in already_in:
            raise ValueError(sc, 'not in', already_in)

def main():
    # build complete list of ilx replace occurences for all ttl files in the ontology
    # load all relevant files into one graph and extract the info we need to insert stuff into interlex
    # {tempid:{id:'ILX:1234567',files:['1.ttl','2.ttl'],payload:{ilxstrct}}}
    # submit a batch upload and get all the ilx ids and save the updated file
    # load each individual file and do the replace

    args = docopt(__doc__, version='ilxcli 0')
    print(args)
    files = args['<file>']
    iu.setfilename(args['--logfile'])
    output = {}
    for f in files:
        iu.readFile(f, output)
    iu.superToLabel(output)
    order = iu.getSubOrder(output)
    test(order, output)
    embed()

if __name__ == '__main__':
    main()
