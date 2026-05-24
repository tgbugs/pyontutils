import json
import pickle
import re
import pandas as pd
from pathlib import Path as p
import pprint
from subprocess import call
from sys import exit
import csv
from typing import Union, Dict, List
import networkx as nx

def sort_list_of_tuples_by_string(list_of_tuples:List[tuple], string_index:int) -> List[tuple]:
    return sorted(list_of_tuples, key=lambda x: (str(x[string_index]).strip() in ['None', ''], x[string_index].lower()))

def class_hierarchy(dag:List[tuple], descending=True) -> list:
    ''' Topological Sorting
    Args:
        dag: directed acyclic graph that is a mappings of list of tuples with len of 2
    Returns:
        Ordered list of single entities in topological ordering of choice
    Examples:
        >>> class_hierarchy([(1, 2), (2, 3)])
        [3, 2, 1]
    '''
    dag = nx.DiGraph(dag)
    dag = list(nx.topological_sort(dag))
    if descending:
        dag = list(reversed(dag))
    return dag

def clean(self, string, clean_scale:int=0):
    if clean_scale == 0:
        return string
    elif clean_scale == 1:
        return string.lower().strip()
    elif clean_scale == 2:
        return ' '.join(string_profiler(string))
    elif clean_scale == 3:
        return ' '.join(string_profiler(string)).replace('obsolete', '').strip()


def string_profiler(
        string: str,
        start_delimiter: str='(',
        end_delimiter: str=')',
        remove: bool=True,
        keep_delimiter: bool = True,
    ) -> List[str]:
    '''
    Seperates strings fragements into list based on the start and end delimiters
    Args:
        string: complete string you want to be broken up based on start and stop delimiters given
        start_delimiter: delimiter element to start
        end_delimiter: delimiter elemtent to end
        remove: decide whether or not to keep strings inside the delimiters
    Returns:
        List[str]: list of strings that are split at start and end delimiters given and whether
            or not you want to remove the string inside the delimiters
    Tests:
        long = '(life is is good) love world "(blah) blah" "here I am" once again "yes" blah '
        print(string_profiler(long))
        null = ''
        print(string_profiler(null))
        short = '(life love) yes(and much more)'
        print(string_profiler(short))
        short = 'yes "life love"'
        print(string_profiler(short))
    '''
    outer_index  = 0  # stepper for outer delimier string elements
    inner_index  = 0  # stepper for inner delimier string elements
    curr_index   = 0  # actual index of the current element in the string
    string_list  = [] # string broken up into individual elements whenever a start and end delimiter is hit
    outer_string = '' # string tracked while outside the delimiters
    inner_string = '' # string tracked while inside the delimiters

    for outer_index in range(len(string)):
        # Actual pointer position (inner delimiter counter + outer delimiter counter)
        curr_index = inner_index + outer_index
        # Close once acutal index is at the end
        # NOTE: outer_index will keep going till end regardless of hitting a delimiter and adding to inner stepper.
        if curr_index == len(string): break
        ### DELIMITER HIT ###
        if string[curr_index] == start_delimiter:
            # If we his a delimiter, collect the string previous to that as an element; flush
            if outer_string:
                # Option: .extend(outer_string.strip().split()) | If you want every word seperate. Maybe an option?
                string_list.append(outer_string.strip())
                outer_string = ''
            for j in range(curr_index+1, len(string)):
                # Stepper that is pushed while in inner delimiter string.
                inner_index += 1
                # Once we his the end delimiter, stop iterating through the inner delimiter string
                if string[j] == end_delimiter: break
                # String inside delimiters
                inner_string += string[j]
            # If you want the string inside the delimiters
            if not remove:
                if keep_delimiter:
                    inner_string = start_delimiter + inner_string + end_delimiter
                string_list.append(inner_string)
            # inner delimiter string restart
            inner_string = ''
        # String outside of the delimiters
        else: outer_string += string[curr_index]
        # End delimiter is either nested or not the real target; should ignore
        if string[curr_index] == end_delimiter:
            if string_list and outer_string:
                string_list[-1] += outer_string
                outer_string = ''
    # In case of not hiting a delimiter at the end of the string, collect the remaining outer delimiter string
    # Option: .extend(outer_string.strip().split()) | If you want every word seperate. Maybe an option?
    if outer_string: string_list.append(outer_string.strip())
    return string_list


pp = pprint.PrettyPrinter(indent=4).pprint


class SetEncoder(json.JSONEncoder):
    ''' Custom encoder to allow json to convert any sets in nested data to become lists '''
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
    sub = "\(|\)|&#39;|&#34;|\'|\""
    return __degrade(sub=sub, var=var)


def degrade(var):
    sub = "\(|\)|&#39;|&#34;|\'|\"|-|,|_|:|\.| |;|#|>|<|`|~|@"
    return __degrade(sub=sub, var=var)


def degrade_hash(mylist):
    if not isinstance(var, list):
        sys.exit('degrade_hash :: intended for lists only')
    local_hash = {}
    return {v: degraded(v) for v in mylist}


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
