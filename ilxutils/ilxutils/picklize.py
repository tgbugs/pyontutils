"""Intended purpose it to convert every ontology in NIF-Ontology and picklize it in a new folder

Usage:
    picklize.py [-h | --help]
    picklize.py [-v | --version]
    picklize.py [-f=<paths>...] [-o=<path>]

Options:
    -h --help               Display this help message
    -v --version            Current version of file
    -o --output=<path>      [default: ~/Dropbox/NIF-Ontology-Picklized/]
    -f --files=<paths>...   [default: ~/Dropbox/NIF-Ontology/]
"""
from glob import glob
import pandas as pd
from pathlib import Path as p
import subprocess as sb
from ilxutils.graph2pandas import Graph2Pandas
from ilxutils.tools import create_pickle
from ilxutils.args_reader import doc2args
VERSION = '0.0.1'


class Picklize:

    def __init__(self, wildcard, output):
        self.wildcard = wildcard
        self.output = output
        self.files = self.__find_ontologies()
        self.pickles = self.__create_pickles()

    def __find_ontologies(self):
        files = []
        for wc in self.wildcard:
            if p(wc).is_dir():
                files.extend(glob(wc + '/**/*.ttl', recursive=True))
            elif p(wc).is_file() and p(wc).suffix in ['.owl', '.ttl', '.pickle']:
                files.append(wc)
        return files

    def __create_pickles(self):
        sb.call('mkdir '+self.output, shell=True)
        for i, f in enumerate(self.files, 1):
            print(i, len(self.files), f)
            name = p(f).stem
            output = p(self.output)/name
            create_pickle(Graph2Pandas(f).df, p(self.output)/name)


def main():
    from docopt import docopt
    doc = docopt(__doc__, version=VERSION)
    args = doc2args(doc)
    Picklize(wildcard=args.files, output=args.output)


if __name__ == '__main__':
    main()
