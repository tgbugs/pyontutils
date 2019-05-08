from pathlib import Path
from pyontutils.core import makeGraph, qname, OntId, OntTerm
from pyontutils.config import devconfig
from typing import Union, Dict, List
import yaml


def  convert_view_text_to_dict() -> dict:
    with open(Path(devconfig.resources, 'view.txt'), 'rt') as infile:
        rawr_yaml = ''
        for line in infile.readlines():
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
        label, *curies = normalize_term(key)
        yield (label, curies, tier_level)
        if isinstance(value, dict):
            yield from linearize_graph(value, tier_level + 1)


def main():
    view = convert_view_text_to_dict()
    view_rows = linearize_graph(view)

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

    view_text, view_text_bl = '', []
    for label, curies, tier_level in view_rows:
        view_text += ' ' * 4 * tier_level + '\t'.join([label] + curies) + '\n'
        if not curies and label.strip() not in avoid_in_bl:
            view_text_bl.append(label)

    for i, bl_term in enumerate(view_text_bl):
        neighbors = OntTerm.search(bl_term.split(' ')[0])
        for neighbor in neighbors:
            if set(neighbor.split(' ')) == set(bl_term.split(' ')):
                # if neighbor.curie.split(':')[0] in accepted_prefixes_for_bl:
                view_text_bl[i] += '\t' + neighbor.curie

    with open(Path(devconfig.resources, 'view_populated.txt', 'w'), 'w') as outfile:
        outfile.write(view_text)
    with open(Path(devconfig.resources, 'view_unpopulated_terms.txt'), 'w') as outfile:
        outfile.write('\n'.join(sorted(view_text_bl)))


if __name__ == '__main__':
    main()
