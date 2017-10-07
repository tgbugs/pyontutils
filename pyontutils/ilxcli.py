#!/usr/bin/env python3.6
"""Given a ttl file get ILX ids for ILXREPLACE terms.

Usage:
    ilxcli [options] <file>...

Options:
    -l --logfile=LOG    the file mapping ILXREPLACE to ILX [default: ilx-records.json]
    -o --ontology=ONT   manually set the ontology where ILX identifiers will live
    -g --get            actually get the ILX ids instead of just building records
    -r --replace        do the replacement on the file as well
    -x --overwrite      overwrite the logfile
    -u --user=USER      user to get session cookie
    -p --password=PASS  password to get sessions cookie
    -h --help           print this

"""
import os
import json
from docopt import docopt
from pyontutils import ilx_utils as iu
from IPython import embed

def test(order, recordDict):
    already_in = [None]
    for k in order:
        already_in.append(recordDict[k]['rec']['label'])
        scl = recordDict[k]['rec']['superclass']['label']
        if scl not in already_in and recordDict[k]['sc'].startswith('ILXREPLACE'):  # dont check cases where super already exists
            raise ValueError(scl, 'not in', already_in)

def main():
    # build complete list of ilx replace occurences for all ttl files in the ontology
    # load all relevant files into one graph and extract the info we need to insert stuff into interlex
    # {tempid:{id:'ILX:1234567',files:['1.ttl','2.ttl'],payload:{ilxstrct}}}
    # submit a batch upload and get all the ilx ids and save the updated file
    # load each individual file and do the replace

    args = docopt(__doc__, version='ilxcli 0')
    print(args)
    SC_EM = args['--user']
    SC_PASS = args['--password']
    iu.SESS_COOKIE = iu.getSessionCookie(SC_EM, SC_PASS)
    embed()
    return

    files = args['<file>']
    target_file = args['--ontology']  # target ontology file where the 'real' classes will be inserted
    #iu.setfilename(args['--logfile'])
    # if the logfile already exists read from it XXX THIS DOES NOT SUPPORT CONCURRENT MODIFICATION!
    if os.path.exists(args['--logfile']) and not args['--overwrite']:
        with open(args['--logfile'], 'rt') as f:
            existing = json.load(f)
    else:
        existing = {}
    iu.wholeProcess(files, existing, target_file, args['--logfile'], args['--get'])

if __name__ == '__main__':
    main()
