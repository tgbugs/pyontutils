#!/usr/bin/env python3

from collections import namedtuple
import rdflib
from pyontutils.utils import makeGraph

ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/'

PScheme = namedtuple('PScheme', ['curie', 'name', 'species', 'devstage', 'citation'])
schemes = [
PScheme('ILX:','','','',''),
PScheme('ILX:','CoCoMac parcellation concept','NCBITaxon:9544','various','problem'),  # problems detected :/
PScheme('ILX:','Allen Mouse Brain Atlas parcellation concept','NCBITaxon:10090','adult P56','http://help.brain-map.org/download/attachments/2818169/AllenReferenceAtlas_v2_2011.pdf?version=1&modificationDate=1319667383440'),  # yay no doi! wat
]

root = ('ILX:', 'Brain parcellation scheme concept')


def make_scheme(parent, scheme):  # ick...
    out = [
        (scheme.curie, rdflib.RDF.type, rdflib.OWL.Class),
        (scheme.curie, rdflib.RDFS.label, scheme.name)
        (scheme.curie, 'OBOANN:', scheme.species)
        (scheme.curie, 'OBOANN', scheme.devstage)
        (scheme.curie, 'OBOANN:definingCitation', scheme.citation)
    ]
    return out

def main():
    filename = 'parcellation'
    ontid = ONT_PATH + filename + 'ttl'
    PREFIXES = {
        'skos':'http://www.w3.org/2004/02/skos/core#',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
               }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    new_graph.add_node(ontid, rdflib.RDFS.label, filename)
    new_graph.add_node(ontid, rdflib.RDFS.comment, 'Brain parcellation schemes as represented by root concepts.')
    for scheme in schemes:
        s = make_scheme(parent, scheme)
        [new_graph.add_node(t) for t in s]

    new_graph.write()

if __name__ == '__main__':
    main()

