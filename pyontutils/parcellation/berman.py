import subprocess
import collections
from pathlib import Path
import json
from pyontutils.config import devconfig

source_images = Path('~/files/cropped').expanduser()
output = Path(devconfig.resources, 'berman_legends.json')


def clean(string):
    ''' Begining of the string can sometimes have odd noise '''
    # manual fixes in the source
    # 24/1.png
    # 9/1.png
    # 3/1.png
    #if ')' in string:  # fix in the source data
        #string = string.split(')')[0] + ')'  # remove trailing garbage
    return (string
            .replace('_', '')
            .replace('-', '')
            .replace('—', '')
            .replace('.', '')
            .replace('=', '')
            .replace('\u2018',"'")  # LEFT SINGLE QUOTATION MARK
            .replace('\u2019', "'")  # RIGHT SINGLE QUOTATION MARK
            .strip())


def get_legends(raw_text):
    legends = []
    for line in raw_text.splitlines():
        line = clean(line)
        if not line:
            continue
        try:
            abbrev, label = line.split(' ', 1)
        except ValueError as e:
            print(repr(line))
            print(repr(raw_text))
            raise e
            continue
        abbrev = clean(abbrev)
        label = clean(label)
        legends.append((abbrev, label))
    return legends


redo = False
data = []
for folder in source_images.glob('*'):
    raw = folder / 'raw.txt'
    img_num = int(folder.stem)
    if not raw.exists() or redo:
        legends = []
        raw_text = ''
        for img in folder.glob('*.png'):
            print('num', img_num, img.stem)
            p = subprocess.Popen(('tesseract', img.as_posix(), 'stdout', '-l', 'eng', '--oem', '2', '--psm', '6'),
                                 stdout=subprocess.PIPE)
            bytes_text, err = p.communicate()
            raw_text += bytes_text.decode() + '\n'

        with open(raw, 'wt') as f:
            f.write(raw_text)
    else:
        with open(raw, 'rt') as f:
            raw_text = f.read()

    legends = get_legends(raw_text)
    data.append((img_num, legends))


# in theory could use the most frequent if > .75 are the same ...
cor_l = {
    'abducens nerve': {'GN': '6N'},
    'alaminar spinal trigeminal nucleus, magnocellular division (14)': {'5SM': 'SSM'},
    'alaminar spinal trigeminal nucleus, parvocellular division (6)': {'5SP': 'SSP'},
    'central nucleus of the inferior colliculus (21)': {'1CC': 'ICC'},
    'cerebral cortex': {'¢': 'C'},
    'commissure of the inferior colliculi': {'1CO': 'ICO', 'I1CO': 'ICO'},
    'corpus callosum': {'198': 'CC'},
    'inferior central nucleus (13)': {'C': 'CI', 'Cl': 'CI'},
    'lateral tegmental field (3)': {'FIL': 'FTL'},
    'mesencephalic trigeminal nucleus (19)': {'SME': '5ME'},
    'motor trigeminal tract': {'SMT': '5MT'},
    'nucleus of the trapezoid body (15)': {'J': 'T'},
    'solitary tract': {'$': 'S'},
    'spinal trigeminal tract': {'SST': '5ST'},
    'statoacoustic nerve': {'BN': 'SN'},
    'superior central nucleus (22)': {'s': 'CS'},
    'trigeminal nerve': {'SN': '5N'},
}

cor_a = {
    #'1': {'ependymal layer', 'superficial layer'},
    #'2': {'intermediate layer', 'molecular layer'},
    #'3': {'deep layer', 'oculomotor nucleus (27)', 'pyramidal layer'},
    #'4': {'polymorph layer', 'trochlear nucleus (23)'},
    'KF': {'KollikerFuse nucleus (17)': 'KéllikerFuse nucleus (17)'},
    'SCS': {'superior colliculus, supertficial layer (25)':
            'superior colliculus, superficial layer (25)'},
}


by_abbrev = collections.defaultdict(list)
by_label = collections.defaultdict(list)
abbrev_index = collections.defaultdict(list)
label_index = collections.defaultdict(list)
for n, legends in sorted(data):
    for abbrev, label in legends:
        if label in cor_l and abbrev in cor_l[label]:
            abbrev = cor_l[label][abbrev]
        if abbrev in cor_a and label in cor_a[abbrev]:
            label = cor_a[abbrev][label]
        by_abbrev[abbrev].append(label)
        by_label[label].append(abbrev)
        abbrev_index[abbrev].append(n)
        label_index[label].append(n)


def dorder(thing, type=lambda v:v):
    return  {k:type(v) for k, v in sorted(thing.items())}

by_abbrev = dorder(by_abbrev, collections.Counter)
by_label = dorder(by_label, collections.Counter)
index_abbrev = dorder(abbrev_index)
index_label = dorder(label_index)

prob_a = {k:v for k, v in by_abbrev.items() if len(v) > 1}
prob_l = {k:v for k, v in by_label.items() if len(v) > 1}


from IPython import embed
embed()


def out():
    final = collections.OrderedDict()
    for key, value in sorted(data, key=lambda d: d[0]):
        final[key] = value

    with open(output, 'wt') as f:
        json.dump(final, f, indent=2)
