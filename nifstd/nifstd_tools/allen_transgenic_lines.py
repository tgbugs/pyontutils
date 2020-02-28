""" Converts owl or ttl or raw rdflib graph into a pandas DataFrame. Saved in .pickle format.

Usage:
    allen_transgenic_lines [options]

Options:
    -h --help                   Display this help message
    -v --version                Current version of file
    -r --refresh                Update local copy
    -i --input=<path>           Local copy of Allen Brain Atlas meta data [default: /tmp/allen-cell-types.json]
    -o --output=<path>          Output path in ttl format [default: allen-cell-types]
"""
import re
import json
from pathlib import Path
import rdflib
import requests
from pyontutils.core import makeGraph, makePrefixes
from pyontutils.combinators import annotation
from docopt import docopt


class AllenTransgenicLines:

    def __init__(self, input):
        prefixes = {**{'JAX': 'http://jaxmice.jax.org/strain/',
                    'MMRRC': 'http://www.mmrrc.org/catalog/getSDS.jsp?mmrrc_id=',
                    'AIBS': 'http://api.brain-map.org/api/v2/data/TransgenicLine/'},
                    **makePrefixes('definition', 'ilxtr', 'owl')}
        self.g = makeGraph('transgenic-lines', prefixes=prefixes)
        self.neuron_data = input

    def build_transgenic_lines(self):
        """
        init class     |  "transgenic_line_source_name":"stock_number" a Class
        add superClass |  rdfs:subClassOf ilxtr:transgenicLine
        add *order*    |  ilxtr:useObjectProperty ilxtr:<order>
        add name       |  rdfs:label "name"
        add def        |  definition: "description"
        add transtype  |  rdfs:hasTransgenicType "transgenic_line_type_name"
        """
        allen_namespaces = {
            'JAX': 'http://jaxmice.jax.org/strain/',
            'MMRRC': 'http://www.mmrrc.org/catalog/getSDS.jsp?mmrrc_id=',
            'AIBS': 'http://api.brain-map.org/api/v2/data/TransgenicLine/',
        }
        for prefix, iri in allen_namespaces.items():
            self.g.add_namespace(prefix, iri)
        for cell_line in self.neuron_data[:]:
            for tl in cell_line['donor']['transgenic_lines']:
                _id = tl['stock_number'] if tl['stock_number'] else tl['id']
                prefix = tl['transgenic_line_source_name']
                line_type = tl['transgenic_line_type_name']
                if prefix not in ['JAX', 'MMRRC', 'AIBS']:
                    continue
                _class = prefix + ':' + str(_id)
                self.g.add_class(_class)
                self.g.add_trip(_class, 'rdfs:label', tl['name'])
                self.g.add_trip(_class, 'definition:', tl['description'])
                self.g.add_trip(_class, 'rdfs:subClassOf', 'ilxtr:transgenicLine')
                self.g.add_trip(_class, 'ilxtr:hasTransgenicType', 'ilxtr:' + line_type + 'Line')
        self.g.write()

def main():
    args = docopt(__doc__, version='0.0.0')
    #print(args)
    if not args['--refresh'] and args['--input'] and Path(args['--input']).exists():
        with open(args['--input'], 'rt') as f:
            input = json.load(f)
    else:
        response = requests.get('http://api.brain-map.org/api/v2/data/query.json?criteria='
                                'model::Specimen,rma::criteria,[is_cell_specimen$eq%27true%27],'
                                'products[name$eq%27Mouse%20Cell%20Types%27],'
                                'rma::include,structure,donor(transgenic_lines),'
                                'specimen_tags,cell_soma_locations,rma::options[num_rows$eqall]')
        input = response.json()['msg']
        with open(args['--input'], 'wt') as f:
            json.dump(input, f, indent=4)

    act = AllenTransgenicLines(input=input)
    act.build_transgenic_lines()

if __name__ == '__main__':
    main()
