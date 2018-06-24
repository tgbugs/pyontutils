""" Intended use is to compare owl or ttl to the ttl created from interlx.

Usage:  compare_graphs.py [-h | --help]
        compare_graphs.py [-v | --version]
        compare_graphs.py [-r reference_graph] [-t target_graph] [-o output]
        compare_graphs.py [-r reference_graph] [-t target_graph] [-o output]
                            [--ilx] [-s shorten_names] [--html] [--save] [--pred-diff=<args>]

Options:
    -h, --help                      Display this help message
    -v, --version                   Current version of file
    -o, --output=<path>             Output path [default: /home/troy/Dropbox/compare_graphs_example.json]
    -r, --reference_graph=<path>    [default: /home/troy/Dropbox/interlex.pickle]
    -t, --target_graph=<path>       [default: /home/troy/Dropbox/uberon.pickle]
    --pred-diff=<args>              only considering differences in specified predicates
    --ilx                           treat reference like its ilx bc it has uniqueness
    --html                          creates html output from the json diff
    -s, --shorten_names             qnames the reference iri and target iri
    --save                          saves both picklized graphs into seperate files next to their source
"""
from docopt import docopt
import pandas as pd
VERSION = '0.1'
doc = docopt(__doc__, version=VERSION)
args = pd.Series({k.replace('--', ''): v for k, v in doc.items()})
print(args)


#diffcolor for terminal and html use
#terminal -> <f> <f> <diff-pred>
#html -> tables
def main():
    pass


if __name__ == '__main__':
    main()
