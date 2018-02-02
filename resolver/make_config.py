#!/usr/bin/env python3.6

import rdflib
from pyontutils.utils import PREFIXES as uPREFIXES

ilxtr = rdflib.Namespace(uPREFIXES['ilxtr'])

prefix = '/tmp'

g = rdflib.Graph().parse(f'{prefix}/NIF-Ontology/ttl/generated/NIF-NIFSTD-mapping.ttl', format='turtle')
with open('ontology-uri-map.conf', 'wt') as f:
    for new, old_ in sorted(g.subject_objects(rdflib.OWL.sameAs), key=lambda a:f'{len(a[1]):0>5}' + a[1]):
        old = old_.split('neuinfo.org', 1)[-1].replace("#","/")
        f.writelines(f'~{old}$ {new};\n')

ig = rdflib.Graph().parse(f'{prefix}/NIF-Ontology/ttl/generated/NIFSTD-ILX-mapping.ttl', format='turtle')
with open('uri-ilx-map.conf', 'wt') as f:
    for nif_, ilx in sorted(ig.subject_objects(ilxtr.hasIlxId), key=lambda a:f'{len(a[1]):0>5}' + a[0]):
        nif = nif_.split('neuinfo.org', 1)[-1]
        f.writelines(f'~{nif}$ {ilx};\n')

sg = rdflib.Graph().parse(f'{prefix}/NIF-Ontology/ttl/generated/NIFSTD-SCR-mapping.ttl', format='turtle')
with open('uri-scr-map.conf', 'wt') as f:
    for nif_, scr in sorted(sg.subject_objects(ilxtr.hasScrId), key=lambda a:f'{len(a[1]):0>5}' + a[0]):
        nif = nif_.split('neuinfo.org', 1)[-1]
        f.writelines(f'~{nif}$ {scr};\n')
