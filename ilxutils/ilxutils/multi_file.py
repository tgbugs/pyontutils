""" Intended use is to compare owl or ttl to the ttl created from interlx.

Usage:  multi_file.py [-h | --help]
        multi_file.py [-v | --version]
        multi_file.py [-f <filenames>...]

Options:
    -h, --help                      Display this help message
    -v, --version                   Current version of file
    -o, --output=<path>             Output path [default: /home/troy/Dropbox/compare_graphs_example.json]
    -f <filename>...
"""
from docopt import docopt
import pandas as pd
from compare_graphs import GraphComparator

VERSION = '0.1'
doc = docopt(__doc__, version=VERSION)
args = pd.Series({k.replace('--', ''): v for k, v in doc.items()})

#diffcolor for terminal and html use
#terminal -> <f> <f> <diff-pred>
#html -> tables
def main():
    pass

if __name__ == '__main__':
    main()
