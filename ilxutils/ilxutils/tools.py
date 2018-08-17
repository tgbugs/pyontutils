import json
import pickle
import re
import tabulate
import pandas as pd
from pathlib import Path as p
from subprocess import call
from sys import exit
import csv

''' Custom encoder to allow json to convert any sets in nested data to become lists '''
class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(list(obj))
        return json.JSONEncoder.default(self, obj)

def is_file(path):
    if p(path).is_file():
        return True
    return False


def is_dict(path):
    if p(path).is_dir():
        return True
    return False


def tilda(obj):
    if isinstance(obj, list):
        return [str(p(o).expanduser()) if isinstance(o, str) else o for o in obj]
    elif isinstance(obj, str):
        return str(p(obj).expanduser())
    else:
        return obj


def fix_path(path):

    def __fix_path(path):
        if not isinstance(path, str):
            return path
        elif '~' == path[0]:
            tilda_fixed_path = tilda(path)
            if is_file(tilda_fixed_path):
                return tilda_fixed_path
            else:
                exit(path, ': does not exit.')
        elif is_file(p.home() / path):
            return str(p().home() / path)
        elif is_dict(p.home() / path):
            return str(p().home() / path)
        else:
            return path

    if isinstance(path, str):
        return __fix_path(path)
    elif isinstance(path, list):
        return [__fix_path(p) for p in path]
    else:
        return path


def compare_strings(s1, s2):
    s1, s2 = degrade(s1), degrade(s2)
    if s1 != s2:
        return False
    return True


def mydecoder(string):
    try:
        string.encode('ascii')
        return string
    except:
        ustring = string.encode('utf-8')
        string = re.sub(b"\xe2\x80\x90", b"-", ustring)
        return string.decode('utf-8')


def __degrade(sub, var):
    def helper(s):
        s = str(s)
        s = mydecoder(s)
        s = re.sub(sub, "", s).lower().strip()
        if not s:
            return None
        return s

    if isinstance(var, list):
        return [helper(v) if v else v for v in var]
    else:
        if var:
            return helper(var)
        else:
            return None


def light_degrade(var):
    sub = "\(|\)|&#39;|&#34;|\'|\"|-"
    return __degrade(sub=sub, var=var)


def degrade(var):
    sub = "\(|\)|&#39;|&#34;|\'|\"|-|,|_|:|\.| |;|#|>|<|`|~|@"
    return __degrade(sub=sub, var=var)


def degrade_hash(mylist):
    if not isinstance(var, list):
        sys.exit('degrade_hash :: intended for lists only')
    local_hash = {}
    return {v: degraded(v) for v in mylist}


def df_print(df):
    print(tabulate(df, headers='keys', tablefmt='psql'))


def namecheck(infilename):
    if infilename == str(p.home() / 'Dropbox'):
        sys.exit('DONT OVERWRITE THE DROPBOX')


def open_txt(infilename):
    namecheck(infilename)
    infilename = str(infilename)
    if '.txt' not in infilename:
        infilename += '.txt'
    infilename = fix_path(infilename)
    with open(infilename, 'r') as infile:
        output = infile.read().strip()
        infile.close()
        return output


def create_txt(data, output):
    namecheck(output)
    output = str(output)
    if '.txt' not in output:
        output += '.txt'
    output = fix_path(output)
    with open(output, 'w') as outfile:
        outfile.write(data)
        outfile.close()


def create_json(data, output):
    namecheck(output)
    output = str(output)
    if '.json' not in output:
        output += '.json'
    output = fix_path(output)
    with open(output, 'w') as outfile:
        json.dump(data, outfile, indent=4, cls=SetEncoder)
        outfile.close()

def open_json(infile):
    namecheck(infile)
    infile = str(infile)
    if '.json' not in infile:
        infile += '.json'
    infile = fix_path(infile)
    with open(infile, 'r') as _infile:
        return json.load(_infile)


def create_pickle(data, output):
    namecheck(output)
    output = str(output)
    if '.pickle' not in output:
        output += '.pickle'
    output = fix_path(output)
    with open(output, 'wb') as outfile:
        pickle.dump(data, outfile)
        outfile.close()


def open_pickle(infile):
    namecheck(infile)
    infile = str(infile)
    if '.pickle' not in infile:
        infile += '.pickle'
    infile = fix_path(infile)
    with open(infile, 'rb') as _infile:
        output = pickle.load(_infile)
        _infile.close()
        return output


def create_csv(rows, infile):
    namecheck(infile)
    infile = str(infile)
    if '.csv' not in infile:
        infile += '.csv'
    infile = fix_path(infile)
    with open(infile, 'wb') as csvfile:
        filewriter = csv.writer(csvfile,
                                delimiter=',',
                                quotechar='|',
                                quoting=csv.QUOTE_MINIMAL,)
        for row in rows:
            filewriter.writerow(row)
        csvfile.close()


def prettify_ontodiff_json(output):
    namecheck(output)
    output = str(output)  # shell fixes output path itself
    if '.json' not in output:
        output += '.json'
    shellcommand = 'ex -s +\'g/\[[\ \\n]\+"/j4\' -cwq ' + output
    if call(shellcommand, shell=True) == 1:
        print('Could not prettify the json file')
    else:
        print('Prettify Complete For:', output)
