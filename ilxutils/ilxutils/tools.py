import json
import pickle
import re
import tabulate
from pathlib import Path as p

def degrade(var):
    def helper(s):
        return str(re.sub("\(|\)|'|\"|,|-|_|:| |;|#|>|<|`|~|@", "", s).lower().strip())
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

def ot(infilename):
    namecheck(infilename)
    if '.txt' not in infilename:
        infilename += '.txt'
    with open(infilename, 'r') as infile:
        return infile.read()
        infile.close()

def ct(data, infilename):
    namecheck(infilename)
    if '.txt' not in infilename:
        infilename += '.txt'
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
    filepath = str(filepath)
    if '.pickle' not in output:
        output += '.pickle'
    with open(output, 'wb') as outfile:
        pickle.dump(data, outfile)
    print('Complete')

def op(filepath):
    namecheck(filepath)
    filepath = str(filepath)
    if '.pickle' not in filepath:
        filepath += '.pickle'
    with open(filepath, 'rb') as infile:
        return pickle.load(infile)

def ccsv(rows, filepath):
    namecheck(filepath)
    filepath = str(filepath)
    if '.csv' not in filepath:
        filepath += '.csv'
    with open(filepath, 'wb') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for row in rows:
            filewriter.writerow(row)
