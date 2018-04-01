#!/usr/bin/env python3
import os
from glob import glob
from pathlib import Path
from pyontutils.utils import anyMembers
from pyontutils.config import devconfig
from pyontutils.ontload import local_imports

remote_base = 'http://ontology.neuinfo.org/NIF/ttl/'
local_base = Path(devconfig.git_local_base, 'NIF-Ontology/ttl/').as_posix() + '/'

#list of all nif ontologies
b = local_base
fs = glob(b + '*')
fs += glob(b + '*/*')
fs += glob(b + '*/*/*')
onts = [f for f in fs if f.endswith('.ttl') or f.endswith('.owl') and 'NEMO_' not in f]

_ = [print(f) for f in fs]

mapping = [(remote_base + file.split('/ttl/', 1)[-1], file.split('/ttl/', 1)[-1])
           for file in fs
           if file.endswith('.ttl')
           or file.endswith('.owl')]

# check for mismatched import and ontology iris
itrips = local_imports(remote_base, local_base, onts, readonly=True, dobig=False)  # XXX these files are big and slow, run at own peril
sa = {os.path.basename(o):s for s, p, o in itrips if 'sameAs' in p}

# FIXME should be able to do this by checking what is tracked by git...
externals = ('CogPO.owl', 'NEMO_vv2.98.owl', 'cogat_v0.3.owl', 'doid.owl',
             'ero.owl', 'pato.owl', 'pr.owl', 'ro_bfo1-1_bridge.owl', 'uberon.owl')

for f in fs:
    if '/external/' in f and anyMembers(f, *externals):
        basename = os.path.basename(f)
        if basename in sa:
            target = sa[basename]
            if 'external' not in target:
                mapping.append((target, 'external/' + basename))

# make a protege catalog file to simplify life
uriline = '    <uri id="User Entered Import Resolution" name="{ontid}" uri="{filename}"/>'

xmllines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
'<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">',] + \
[uriline.format(ontid=ont, filename=file) for ont,file in sorted(mapping)] + \
['</catalog>']
xml = '\n'.join(xmllines)
with open('/tmp/nif-catalog-v001.xml','wt') as f:
    f.write(xml)
