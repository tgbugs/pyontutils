import difflib
import json
from pyontutils.utils import TermColors



''' --word-diff=porcelain clone'''
def diff(s1, s2):
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

''' --word-diff=color clone '''
def diffcolor(s1, s2):
    string = ''
    for line in diff(s1, s2):
        if line[0] == '-':
            string += ' ' + TermColors.red(line[2:])
        elif line[0] == '+':
            string += ' ' + TermColors.green(line[2:])
        else:
            string += ' ' + line
    return string[1:]

''' ratio of likeness btw 2 strings '''
def ratio(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()

''' creates basic html based on the diff of 2 strings '''
def create_html(s1, s2, output):
    html = difflib.HtmlDiff().make_file(s1.split(), s2.split())
    with open(output, 'w') as f:
        f.write(html)

def main():
    s1 = "the neuron's went up the tall stairs."
    s2 = "the neurons went up the tall stairs."
    s1 = open('../dum1.txt', 'r').read().strip()
    s2 = open('../dum2.txt', 'r').read().strip()
    dif = diff(s1, s2)
    json.dump({'id':1234, 'term':'neuron', 'difflib':dif, 'ratio':ratio(s1, s2)}, open('mydifftest.json', 'w'), indent=4)
    for i,l in enumerate(dif):
        if l[0] == '-':
            print(TermColors.red(l))
        elif l[0] == '+':
            print(TermColors.green(l))
        else:
            print(l)
    print(diffcolor(s1, s2))

if __name__ == '__main__':
    main()
