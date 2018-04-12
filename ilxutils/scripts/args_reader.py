"""
Usage:  foo.py [-h | --help]
        foo.py [-v | --version]
        foo.py [-a API_KEY] [-e ENGINE_KEY] [-p | -b]
        foo.py [-a API_KEY] [-e ENGINE_KEY] [-p | -b] [-o OUTPUT]
        foo.py [-f FILE] [-a API_KEY] [-e ENGINE_KEY] [-p | -b]
        foo.py [-f FILE] [-a API_KEY] [-e ENGINE_KEY] [-p | -b] [--index=<int>]
        foo.py <argument> [-f FILE] [-a API_KEY] [-e ENGINE_KEY] [-p | -b]
        foo.py <argument> [-f FILE] [-a API_KEY] [-e ENGINE_KEY] [-p | -b] [--index=<int>]

Arugments:
    addTerms                    Add terms|cdes|annotations|relationships to SciCrunch
    updateTerms                 Update terms|cdes|annotations|relationships in SciCrunch
    addAnnotations              Add annotations to existing elements
    updateAnntationValues       Update annotation values only
    updateAnntationType         Update annotation connector aka annotation_type via annoatation_tid

Options:
    -h, --help                  Display this help message
    -v, --version               Current version of file

    -f, --file=<path>           File that holds the data you wish to upload to Scicrunch
    -a, --api_key=<path>        Key path [default: ../production_api_scicrunch_key.txt]
    -e, --engine_key=<path>     Engine key path [default: ../production_engine_scicrunch_key.txt]
    -o, --output=<path>         Output path

    -p, --production            Production SciCrunch
    -b, --beta                  Beta SciCrunch
    -s, --sql                   Uses mysql for updating term data than default api query
    -i, --index=<int>           index of -f FILE that you which to start [default: 0]
"""
from docopt import docopt
import requests as r
from sqlalchemy import create_engine
import pandas as pd
import sys

VERSION = '0.3'
BETA = 'https://test2.scicrunch.org'
PRODUCTION = 'https://scicrunch.org'



def myopen(path):
    return open(path, 'r').read().strip()

def test(args):
    url = args['--base_path'] + '/api/1/term/view/1?key=' + args['--api_key']
    req = r.get(url)
    try:
        req.json()['data']
    except:
        sys.exit('Api key is incorrect or client choice does not match api submitted.')
    engine = create_engine(args['--engine_key'])
    data =  """
            SELECT t.*
            FROM terms as t
            LIMIT 5;
            """
    if pd.read_sql(data, engine).empty:
        sys.exit('Engine key provided does not work.')

def read_args(**args):

    doc = docopt(__doc__, version=VERSION)
    for k, v in doc.items():
        if args.get(k.replace('--', '')):
            doc[k] = args[k.replace('--', '')]
    args = doc

    if args['--engine_key']:
        args['--engine_key'] = myopen(args['--engine_key'])
    else:
        sys.exit('Need sql engine key (-e --engine_key)')

    if args['--api_key']:
        args['--api_key'] = myopen(args['--api_key'])
    else:
        sys.exit('Need api key (-a --api_key)')

    if args['--production']:
        args['--base_path'] = PRODUCTION
    elif args['--beta']:
        args['--base_path'] = BETA
    else:
        sys.exit('Need to specify the client version (-b BETA | -p PRODUCTION)')

    test(args)

    return pd.Series({k.replace('--',''):v for k, v in args.items()})



if __name__ == '__main__':
    inline = read_args(
       argument='updateTerms',
       engine_key='../production_engine_scicrunch_key.txt',
       api_key='../production_api_scicrunch_key.txt',
       production=True,)
    print(inline)
    print(read_args())
