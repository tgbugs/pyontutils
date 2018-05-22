""" Used as a master args reader for scripts that read, add, and update Interlex data through its API

Usage:  foo.py [-h | --help]
        foo.py [-v | --version]
        foo.py [-k API_KEY] [-d DB_URL] [-p | -b]
        foo.py [-k API_KEY] [-d DB_URL] [-p | -b] [-o OUTPUT]
        foo.py [-f FILE] [-k API_KEY] [-d DB_URL] [-p | -b]
        foo.py [-f FILE] [-k API_KEY] [-d DB_URL] [-p | -b] [--index=<int>]
        foo.py <argument> [-f FILE] [-k API_KEY] [-d DB_URL] [-p | -b]
        foo.py <argument> [-f FILE] [-k API_KEY] [-d DB_URL] [-p | -b] [--index=<int>]

Arugments:
    addTerms                    Add terms|cdes|annotations|relationships to SciCrunch
    updateTerms                 Update terms|cdes|annotations|relationships in SciCrunch
    addAnnotations              Add annotations to existing elements
    updateAnntationValues       Update annotation values only
    updateAnntationType         Update annotation connector aka annotation_type via annoatation_tid

Options:
    -h, --help                  Display this help message
    -v, --version               Current version of file

    -f, --file=<path>           File that holds the data you wish to upload to Scicrunch [default: None]
    -k, --api_key=<path>        Key path [default: ../keys/production_api_scicrunch_key.txt]
    -d, --db_url=<path>         Engine key path [default: ../keys/production_engine_scicrunch_key.txt]
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
#BETA = 'https://test2.scicrunch.org'
BETA = 'https://beta.scicrunch.org'
#BETA = 'https://test.scicrunch.org'
PRODUCTION = 'https://scicrunch.org'



def myopen(path):
    with open(path, 'r') as infile:
        file = infile.read().strip()
    infile.close()
    return file
    
def test(args):
    if args.api_key:
        url = args.base_path + '/api/1/term/view/10?key=' + args.api_key
        #print(url)
        req = r.get(url, auth=('scicrunch', 'perl22(query'))
        try:
            data=req.json()['data']
            #print(data)
        except:
            sys.exit('Api key is incorrect or client choice does not match api submitted.')

    if args.db_url:
        engine = create_engine(args.db_url)
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

    if args['--db_url']:
        args['--db_url'] = myopen(args['--db_url'])
    else:
        sys.exit('Need sql engine key (-d --db_url)')

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

    args = pd.Series({k.replace('--',''):v for k, v in args.items()})
    test(args)

    return args



if __name__ == '__main__':
    inline = read_args(
       argument='updateTerms',
       engine_key='../keys/production_engine_scicrunch_key.txt',
       api_key='../keys/production_api_scicrunch_key.txt',
       production=True,)
    print(inline)
    inline = read_args(
       engine_key='../keys/beta_engine_scicrunch_key.txt',
       api_key='../keys/beta_api_scicrunch_key.txt',
       beta=True,)
    print(inline)
    #print(read_args())
