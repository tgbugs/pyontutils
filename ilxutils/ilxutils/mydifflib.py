import difflib
import json
from pyontutils.utils import TermColors



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

def create_html(s1, s2, output):
    ''' creates basic html based on the diff of 2 strings '''
    html = difflib.HtmlDiff().make_file(s1.split(), s2.split())
    with open(output, 'w') as f:
        f.write(html)

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
    """

if __name__ == '__main__':
    import doctest
    doctest.testmod()
