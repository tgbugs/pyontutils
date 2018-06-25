""" Combines any number of turtle formated files into one files with all the contents.

Usage:
    combine_ttls.py [-h | --help]
    combine_ttls.py [-v | -- version]
    combine_ttls.py [--directory] [--output=<path>] [--pickle]

Options:
    -d --directory=<path>  Path to folder that containes all the turtle files to be used
    -o --output=<path>     Merged file name and path [default: ../merged.ttl]
    --pickle               If used, will make another file of the same name as --output that is a pandas dataframe of the same data.
"""
from docopt import docopt
import pandas as pd
import sys
import rdflib
from collections import defaultdict
from ttl2pd import get_df_from_ttl
from pathlib import Path
import pickle
import subprocess as sb
import glob
import os
VERSION = '0.0.1'


class combine_turtles():
    '''
    >>> python3 combine_ttls.py -d NIF-Ontology/ -o ~/destination/ --pickle
    '''

    def __init__(self, args):
        self.args = args
        self.dir = args.directory

    def get_ttl_files(self):
        avoid = []  #To add file names to avoid in merger for the future
        return [
            f for f in glob.glob(self.dir + '**/*' + '.ttl', recursive=True)
            if os.path.isfile(f) and f not in avoid
        ]

    def run(self):
        files = ' '.join(self.get_ttl_files()[:])
        output = self.args.output
        command = 'riot --time --output=Turtle %s > %s' % (files, output)
        sb.call(command, shell=True)


def main():
    doc = docopt(__doc__, version=VERSION)
    args = pd.Series({k.replace('--', ''): v for k, v in doc.items()})
    combine_turtles(args).run()
    print('=== Merge Complete ===')
    if args.pickle:
        output = args.output
        p = Path(args.output)
        args.output = p.parent / (p.stem + '.pickle')
        get_df_from_ttl(rdflib.Graph().parse(output, format='turtle'), args)


if __name__ == '__main__':
    main()
