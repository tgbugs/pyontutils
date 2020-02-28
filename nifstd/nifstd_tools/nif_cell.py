#!/usr/bin/env python3
import rdflib
import yaml
from pyontutils.config import auth
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint


def main():
    with open(auth.get_path('curies'), 'rt') as f:
        curie_map = yaml.safe_load(f)

    curie_map['nlx_only'] = curie_map['']  # map nlx_only to 'http://uri.neuinfo.org/nif/nifstd/'

    g = rdflib.Graph()
    g.parse('http://ontology.neuinfo.org/NIF/ttl/NIF-Cell.ttl', format='turtle')

    curiespaces = {k:rdflib.Namespace(v) for k, v in curie_map.items()}
    namespaces = {c_prefix:rdflib.Namespace(iri_prefix) for c_prefix, iri_prefix in g.namespaces()}

    subject = curiespaces['NIFCELL']['nifext_75']
    predicate = None
    object_ = None
    matches = [t for t in g.triples((subject, predicate, object_))]
    print(matches)
    if matches:
        predicate = matches[0][1].toPython()
        print(predicate)

    if __name__ == '__main__':
        breakpoint()

if __name__ == '__main__':
    main()
