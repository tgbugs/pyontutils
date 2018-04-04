"""
AUTHOR: TROY SINCOMB

#BUG == There is a current problem with server or php that is being worked around.
#FIXME == Target not verbose enough for my taste. Will upgrade later.
"""
import argparse



FUNCTION_MAP = [
    'addTerms',
    'updateTerms',
    'addAnnotations',
]

""" Command Line Reader """
def read_args(**external_args):
    parser = argparse.ArgumentParser()

    ''' Required Arguments in Bash '''
    parser.add_argument("-k", "--keys", help="file path to api keys",
                            type=str, required=True)
    parser.add_argument("-f", "--file", help="file path to terms data",
                            type=str, required=False) #for convience in method call

    ''' Optional Arguments '''
    parser.add_argument("-o", "--output", help="ouput file path",
                            type=str, required=False)
    parser.add_argument("-i", "--index", help="index in file you want to start",
                            type=int, default=0, required=False)
    parser.add_argument("-s", "--sql", help="find term from sql instead of api",
                            action='store_true', default=False)

    ''' Production or Beta '''
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-p','--production', action='store_true', default=False)
    group.add_argument('-b','--beta', action='store_true', default=False)

    #parser.add_argument('command', choices=FUNCTION_MAP)

    #args = argparser.parse_args(["--keys", "/Users/tmsincomb/Desktop/interlexutils/keys.txt"])
    if external_args:
        args_list = []
        for k,v in external_args.items():
            args_list.extend(['--'+k, v])
        args = parser.parse_args(args_list)
    else:
        args = parser.parse_args()

    api_key, engine_key, base_path = extract_keys(keys=args.keys, args=args)

    return {
        'file':args.file,
        'api_key':api_key,
        'engine_key':engine_key,
        'base_path':base_path,
        'output':args.output,
        'index':args.index,
        'sql':args.sql,
        #'command':args.command,
        #I could make a facade call here
    }

""" Gets Client Version Keys """
def extract_keys(keys, args):
    pred_key = [k for k in open(keys, 'r').read().split('\n') if k]

    try:
        keys={k.split(' : ')[0].strip():k.split(' : ')[1].strip() for k in pred_key}
    except:
        sys.exit('Key file isnt created correctly.')

    if args.production:
        api_key = keys['production_scicrunch_api_key']
        engine = keys['production_scicrunch_engine_key']
        base_path = 'https://scicrunch.org'
    elif args.beta:
        api_key = keys['beta_scicrunch_api_key']
        engine = keys['beta_scicrunch_engine_key']
        base_path = 'https://test2.scicrunch.org'

    return api_key, engine, base_path

def main():
    #print(randomo)
    #print(read_args(keys='../keys.txt',beta='-b')) #file='~/Desktop/NDA/nda-cdes-second-tier-only-update-ready.json'))
    print(read_args())
if __name__ == '__main__':
    main()
