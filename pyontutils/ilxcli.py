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

def main():
    args = docopt(__doc__, version='ilxcli 0')
    print(args)
    files = args['<file>']
    iu.setfilename(args['--logfile'])
    for f in files:
        iu.readFile(f)
    embed()

if __name__ == '__main__':
    main()
