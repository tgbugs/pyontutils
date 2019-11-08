from argparse import Namespace
import json
from pathlib import Path
from pyontutils.core import makeGraph, qname, OntId, OntTerm
from pyontutils.config import auth
from typing import Union, Dict, List
import yaml
from IPython import embed

resources = auth.get_path('resources')


def  convert_view_text_to_dict() -> dict:
    with open(resources / 'sparc_terms3.txt', 'rt') as infile:
        rawr_yaml = ''
        for line in infile.readlines()[:]:
            rawr_yaml += line.replace('\n', '').replace('\t', '\u1F4A9') + ':\n'
    return yaml.load(rawr_yaml)


def get_curies_from_scigraph_label_query(label: str, prefixes:List[str] = ['UBERON', 'ILX', 'PAXRAT']) -> list:
    curies = set()
    for prefix in prefixes:
        # TODO: if not stipped the label will return nothing. Seems to be trailing spaces
        neighbors = [v.OntTerm for v in OntTerm.query(label=label.strip(), prefix=prefix)]
        if not neighbors:
            continue
        for neighbor in neighbors:
            curies.add(OntId(neighbor).curie)
    return list(curies)


def normalize_term(term, prefix=''):
    term, *curie = term.split('\u1F4A9')
    #print(repr(term))
    if curie:
        curie, = curie
        oid = OntId(curie)
        curie = oid.curie
        row = [prefix + term, curie]
    else:
        curies = get_curies_from_scigraph_label_query(term)
        row = [prefix + term] + curies
    return row


def linearize_graph(dict_: dict, tier_level: int = 0) -> tuple:
    """ Recursively pull nested dictionaries out of print order"""
    for key, value in dict_.items():
        term, *curies = key.split('\u1F4A9')
        yield Namespace(**dict(label=term, curies=curies, tier_level=tier_level))
        if isinstance(value, dict):
            yield from linearize_graph(value, tier_level + 1)


def pair_terms(terms):
    new_terms = []
    for term in terms:
        label = term.label
        curies = term.curies
        if not term.curies:
            label, *curies = normalize_term(term.label)
        new_terms.append(Namespace(**dict(label=label, curies=curies, tier_level=term.tier_level)))
    return new_terms


def main():
    sparc_terms = convert_view_text_to_dict()
    print('Linearizing graph')
    sparc_terms_unpaired = list(linearize_graph(sparc_terms))
    print('Adding ids to terms list')
    sparc_terms_paired = pair_terms(sparc_terms_unpaired)
    # embed()
    avoid_in_bl = [
        'Gross anatomy',
        'Internal anatomy',
        'Segmental Anatomy',
        'Atlas Nomenclature',
        'Allen Mouse Brainstem',
        'Paxinos Rar Brainstem'
        'Berman Cat Brainstem',
        'Nerves (also includes Cranial)',
        'UBERON',
    ]

    accepted_prefixes_for_bl = [
        'UBERON',
        'PAXRAT',
    ]

    print('Building sparc terms list txt')
    sparc_terms_text, sparc_terms_bl = '', []
    for term in sparc_terms_paired:
        sparc_terms_text += ' ' * 4 * term.tier_level + '\t'.join([term.label] + term.curies) + '\n'
        if not term.curies and term.label.strip() not in avoid_in_bl:
            sparc_terms_bl.append(term.label)

    # Labels with no ID
    # Slow as heck
    print(f'Building list for terms with no IDs with len:{len(sparc_terms_bl)}')
    for i, bl_term in enumerate(sparc_terms_bl):
        neighbors = OntTerm.search(bl_term.split(' ')[0])
        for neighbor in neighbors:
            if set(neighbor.split(' ')) == set(bl_term.split(' ')):
                # if neighbor.curie.split(':')[0] in accepted_prefixes_for_bl:
                view_text_bl[i] += '\t' + neighbor.curie

    # Original IDs with wrong label
    print('Building list for terms with wrong IDs')
    sparc_terms_with_bad_ids = []
    for term in sparc_terms_unpaired:
        for curie in term.curies:
            onts = OntTerm.query(curie=curie)
            if not onts:
                continue
            for ont in onts:
                if term.label.lower().strip() != ont.label.lower().strip():
                    sparc_terms_with_bad_ids.append({**vars(term), 'searched_label':ont.label})

    # embed()
    with open(resources / 'sparc_terms_populated3.txt', 'w') as outfile:
        outfile.write(sparc_terms_text)
    with open(resources / 'sparc_terms_unpopulated_terms3.txt', 'w') as outfile:
        outfile.write('\n'.join(sorted(sparc_terms_bl)))
    with open(resources / 'sparc_terms_with_bad_ids3.json', 'w') as outfile:
        json.dump(sparc_terms_with_bad_ids, outfile, indent=4)

if __name__ == '__main__':
    main()
