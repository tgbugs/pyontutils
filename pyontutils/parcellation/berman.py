import collections
from PIL import Image, ImageEnhance
from pytesseract import image_to_string, image_to_data
from pathlib import Path
from glob import glob
from sys import exit
import json

SRC = Path.home()/'Dropbox/misc-work/brainmap/cropped/'
DESTINATION = str(Path.home()/'Dropbox/misc-work/brainmap/brainmap_legends.json')

def clean(string):
    ''' Begining of the string can sometimes have odd noise '''
    return string.replace('_', '').replace('-', '').replace('—', '').replace('.', '').replace('=', '').strip()

def get_legends(raw_text):
    legends = []
    for line in raw_text.splitlines():
        if not line:
            continue
        line = clean(line)
        try:
            abbrev, label = line.split(' ', 1)
        except:
            print(line)
            print(raw_text)
            exit()
        abbrev = clean(abbrev)
        label = clean(label)
        legends.append((abbrev, label))
    return legends

data = []
for foldername in glob(str(SRC/'*')):
    img_num = int(Path(foldername).stem)
    print('num', img_num)
    legends = []
    for img in glob(str(SRC/foldername/'*')):
        img = Image.open(img)
        raw_text = image_to_string(img, lang='eng', config='--psm 6') # '--psm 4 also works but 6 seems to work better'
        legends += get_legends(raw_text)
    data.append((img_num, legends))

final = collections.OrderedDict()
for key, value in sorted(data, key=lambda d: d[0]):
    final[key] = value

with open(DESTINATION, 'w') as outfile:
    json.dump(final, outfile, indent=4)
