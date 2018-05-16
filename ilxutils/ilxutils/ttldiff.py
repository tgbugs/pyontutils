#IN PROGRESS
""" Generic comparator of 2 turtle files

Usage:
    ttldiff.py [-h | --help]
    ttldiff.py [-v | -- version]
    ttldiff.py [-r REFERENCE] [-t TARGET] [-o OUTPUT]

Options:
    -r, --refernce=<path>       Path to turtle file that will be used as reference data to contruct comparison
    -t, --target=<path>         Path to target turtle file that will use the reference as a template to see
                                what this turtle file may have that is the same or different.
    -o, --output=<path>         Path to output pandas DataFrame that will house the comparitive data
"""
from docopt import docopt
import pandas as pd
import sys
import rdflib
from collections import defaultdict
from ttl2pd import get_df_from_ttl
from pathlib import Path
import pickle
VERSION = '0.0.1.beta'



class ttldiff():

    def __init__(self, reference, target, args):
        self.reference = possible_convert(refernce)
        self.target = possible_convert(target)
        self.diff_dataframe = self.diff()
        self.same_dataframe = self.same()

    def possible_convert(file):
        if Path(file).suffix == '.ttl':
            return get_df_from_ttl(file)
        elif Path(file).suffix == '.pickle':
            return pickle.load(open(file, 'wb'))
        else:
            sys.exit(file+' is not the desired pickle dataframe or ttl.')

    def diff():
        pass



def main():
    doc = docopt(__doc__, version=VERSION)
    args = pd.Series({k.replace('--',''):v for k, v in doc.items()})
    print(args)

if __name__ == '__main__':
    main()
