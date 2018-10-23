import difflib
import json
from pyontutils.utils import TermColors
import sys


def diff(s1, s2):
    ''' --word-diff=porcelain clone'''
    delta = difflib.Differ().compare(s1.split(), s2.split())
    difflist = []
    fullline = ''
    for line in delta:
        if line[0] == '?':
            continue
        elif line[0] == ' ':
            fullline += line.strip() + ' '
        else:
            if fullline:
                difflist.append(fullline[:-1])
                fullline = ''
            difflist.append(line)
    if fullline:
        difflist.append(fullline[:-1])
    return [l[:] for l in '\n'.join(difflist).splitlines() if l]


def diffcolor(s1, s2):
    ''' --word-diff=color clone '''
    string = ''
    for line in diff(s1, s2):
        if line[0] == '-':
            string += ' ' + TermColors.red(line[2:])
        elif line[0] == '+':
            string += ' ' + TermColors.green(line[2:])
        else:
            string += ' ' + line
    return string[1:]


def ratio(s1, s2):
    ''' ratio of likeness btw 2 strings '''
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def create_html(s1, s2, output='test.html'):
    ''' creates basic html based on the diff of 2 strings '''
    html = difflib.HtmlDiff().make_file(s1.split(), s2.split())
    with open(output, 'w') as f:
        f.write(html)


def traverse_data(obj, key_target):
    ''' will traverse nested list and dicts until key_target equals the current dict key '''
    if isinstance(obj, str) and '.json' in str(obj):
        obj = json.load(open(obj, 'r'))
    if isinstance(obj, list):
        queue = obj.copy()
    elif isinstance(obj, dict):
        queue = [obj.copy()]
    else:
        sys.exit('obj needs to be a list or dict')
    count = 0
    ''' BFS '''
    while not queue or count != 1000:
        count += 1
        curr_obj = queue.pop()
        if isinstance(curr_obj, dict):
            for key, value in curr_obj.items():
                if key == key_target:
                    return curr_obj
                else:
                    queue.append(curr_obj[key])
        elif isinstance(curr_obj, list):
            for co in curr_obj:
                queue.append(co)
    if count == 1000:
        sys.exit('traverse_data needs to be updated...')
    return False


def json_secretary(_input):
    if isinstance(_input, str) and '.json' in str(_input):
        return json.load(open(_input, 'r'))
    else:
        return _input


# reslover -> run make_config (tell where hit repo is)
def json_diff(json1, json2, key_target, get_just_diff=True, porcelain=False):
    ''' creates a (keyname + diff) key within the json of the same layer which key_target resides.
        Ex: json1={'definition':'data of key_target'}, json2={'definition':'data of key_target'}
        key_target = 'definition'

    Usage:
        json_diff (
            json_data1,             json_data1 can be both [{..}] and {[..]} or json file path
            json_data2,             json_data2 can be both [{..}] and {[..]} or json file path
            key_target,             <str> of a key within a dict that holds the string data for comparison; EX: 'definition'
            get_just_diff=True,     default=True; will return just the color diff of the 2 strings
            porcelain=False         default=False; porcelain clone as output only as optional
        )
    '''
    json1 = json_secretary(json1)
    json2 = json_secretary(json2)

    obj1 = traverse_data(json1, key_target)
    obj2 = traverse_data(json2, key_target)

    output = diffcolor(obj1[key_target], obj2[key_target])

    if porcelain:
        return diff(obj1[key_target], obj2[key_target])

    if get_just_diff:
        return output

    obj1[key_target + '_diff'] = output
    obj2[key_target + '_diff'] = output
    return json1, json2, output


def test():
    """ checking output for diff and colordiff

    >>> s1 = "the neuron's went up the tall stairs."
    >>> s2 = "the neurons went up the tall stairs again."

    >>> diff(s1, s2)
    ['the', "- neuron's", '+ neurons', 'went up the tall', '- stairs.', '+ stairs', '+ again.']

    #script is right but output has color sep. from string.
    #>>> diffcolor(s1, s2)
    #"the \x1b[91mneuron's\x1b[0m \x1b[32mneurons\x1b[0m went up the tall \x1b[91mstairs.\x1b[0m \x1b[32mstairs\x1b[0m \x1b[32magain.\x1b[0m"

    >>> ratio(s1, s2)
    0.9113924050632911

    >>> dict1 = [{'meh':'whatever', 'fields':{'definition':s1}}, 'rando']
    >>> dict2 = [{'meh':'whatever', 'fields':{'lime':'soda', 'map':{'definition':s2}}}, 'rando']
    >>> json_diff(dict1, dict2, 'definition', porcelain=True)
    ['the', "- neuron's", '+ neurons', 'went up the tall', '- stairs.', '+ stairs', '+ again.']

    #diffcolor check problem like before
    #>>> json_diff(dict1, dict2, 'definition', get_just_diff=False)
    #([{'meh': 'whatever', 'fields': {'definition': "the neuron's went up the tall stairs.", 'definition_diff': "the \x1b[91mneuron's\x1b[0m \x1b[32mneurons\x1b[0m went up the tall \x1b[91mstairs.\x1b[0m \x1b[32
    #mstairs\x1b[0m \x1b[32magain.\x1b[0m"}}, 'rando'], [{'meh': 'whatever', 'fields': {'lime': 'soda', 'map': {'definition': 'the neurons went up the tall stairs again.', 'definition_diff': "the \x1b[91mneuron'
    #s\x1b[0m \x1b[32mneurons\x1b[0m went up the tall \x1b[91mstairs.\x1b[0m \x1b[32mstairs\x1b[0m \x1b[32magain.\x1b[0m"}}}, 'rando'], "the \x1b[91mneuron's\x1b[0m \x1b[32mneurons\x1b[0m went up the tall \x1b[9
    1mstairs.\x1b[0m \x1b[32mstairs\x1b[0m \x1b[32magain.\x1b[0m")
    """


if __name__ == '__main__':
    s1 = 'I love Data'
    s2 = 'I like Data'
    print(diffcolor(s1, s2))
    print(diff(s1, s2))
    # import doctest
    # doctest.testmod()

    s1 = "the neuron's went up the tall stairs."
    s2 = "the neurons went up the tall stairs again."
    dict1 = [{'meh': 'whatever', 'fields': {'definition': s1}}, 'rando']
    dict2 = [{
        'meh': 'whatever',
        'fields': {
            'lime': 'soda',
            'map': {
                'definition': s2
            }
        }
    }, 'rando']
    # print(json_diff(dict1, dict2, 'definition', get_just_diff=False))
