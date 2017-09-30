#!/usr/bin/env python3.6

import rdflib

g = rdflib.Graph().parse('/tmp/NIF-Ontology/ttl/generated/NIF-NIFSTD-mapping.ttl', format='turtle')
with open('ontology-uri-map.conf', 'wt') as f:
    for new, old_ in sorted(g.subject_objects(rdflib.OWL.sameAs), key=lambda a:f'{len(a[1]):0>5}' + a[1]):
        old = old_.split('neuinfo.org', 1)[-1].replace("#","/")
        f.writelines(f'~{old}$ {new};\n')
