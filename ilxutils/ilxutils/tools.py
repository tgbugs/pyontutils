import json
import pickle
import re
import tabulate



def degrade(var):
    def helper(s):
        return str(re.sub("\(|\)|'|\"|,", "", s).lower().strip())

    if not isinstance(var, list):
        if var:
            return helper(var)
        else:
            return var
    else:
        return [helper(v) if v else v for v in var]

def degrade_hash(mylist):
    if not isinstance(var, list):
        sys.exit('degrade_hash :: intended for lists only')
    local_hash = {}
    return {v:degraded(v) for v in mylist}

def dprint(df):
    print(tabulate(df, headers='keys', tablefmt='psql'))

def namecheck(infilename):
    if infilename == str(p.home() / 'Dropbox'):
        sys.exit('DONT OVERWRITE THE DROPBOX')

def cf(data, infilename):
    namecheck(infilename)
    with open(infilename, 'w') as infile:
        infile.write(data)
        infile.close()

def cj(data, output):
    namecheck(output)
    output = str(output)
    if '.json' not in output:
        output += '.json'
    with open(output, 'w') as outfile:
        json.dump(data, outfile, indent=4)
    print('Complete')

def oj(filepath):
    namecheck(filepath)
    filepath = str(filepath)
    if '.json' not in filepath:
        filepath += '.json'
    with open(filepath, 'r') as infile:
        return json.load(infile)

def cp(data, output):
    namecheck(output)
    with open(output+'.pickle', 'wb') as outfile:
        pickle.dump(data, outfile)
    print('Complete')

def op(filepath):
    namecheck(filepath)
    with open(filepath+'.pickle', 'rb') as infile:
        return pickle.load(infile)
