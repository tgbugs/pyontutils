#!/usr/bin/env python3
import os
from glob import glob
from pyontutils.ontload import local_imports

remote_base = 'http://ontology.neuinfo.org/NIF/ttl/'
base = '~/git/NIF-Ontology/ttl/'

#list of all nif ontologies
local_base = os.path.expanduser(base)
b = local_base
fs = glob(b + '*')
fs += glob(b + '*/*')
fs += glob(b + '*/*/*')
onts = [f for f in fs if f.endswith('.ttl') or f.endswith('.owl')]

_ = [print(f) for f in fs]

mapping = [(remote_base + file.split('/ttl/', 1)[-1], file.split('/ttl/', 1)[-1])
           for file in fs
           if file.endswith('.ttl')
           or file.endswith('.owl')]

# check for mismatched import and ontology iris
itrips = local_imports(remote_base, local_base, onts, readonly=True, dobig=True)
sa = {os.path.basename(o):s for s, p, o in itrips if 'sameAs' in p}
for f in fs:
    if '/external/' in f:
        basename = os.path.basename(f)
        if basename in sa:
            target = sa[basename]
            if 'external' not in target:
                mapping.append((target, 'external/' + basename))

print(mapping)

# make a protege catalog file to simplify life
uriline = '  <uri id="User Entered Import Resolution" name="{ontid}" uri="{filename}"/>'

xmllines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
'<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">',] + \
[uriline.format(ontid=ont, filename=file) for ont,file in sorted(mapping)] + \
['</catalog>']
xml = '\n'.join(xmllines)
with open('/tmp/nif-catalog-v001.xml','wt') as f:
    f.write(xml)
