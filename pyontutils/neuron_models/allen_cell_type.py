""" Converts owl or ttl or raw rdflib graph into a pandas DataFrame. Saved in .pickle format.

Usage:
    allen_cell_type [options]

Options:
    -h --help                   Display this help message
    -v --version                Current version of file
    -r --refresh                Update local copy
    -i --input=<path>           Local copy of Allen Brain Atlas meta data [default: /tmp/allen-cell-types.json]
    -o --output=<path>          Output path of picklized pandas DataFrame [default: allen-cell-types]
"""
import re
import json
from pathlib import Path
import rdflib
import requests
from rdflib import RDF, OWL
from rdflib.namespace import *
from pyontutils.core import annotation, makeGraph, makePrefixes
from pyontutils.neuron_lang import *
from docopt import docopt
from IPython import embed
args = docopt(__doc__, version='0.0.4')


class AllenCellTypes:

    phenotype_preds = [
        'hasSomaLocatedIn',
        'hasCircuitRolePhenotype',
        'hasNeurotransmitterPhenotype',
        'hasInstanceInSpecies',
        'hasExperimentalPhenotype',
        'hasDendriteLocatedIn',
        'hasNucleicAcidExpressionPhenotype',
        'hasLayerLocationPhenotype',
        'hasExpressionPhenotype',
        'hasSmallMoleculeExpressionPhenotype',
        'hasPresynapticTerminalsIn',
        'hasPhenotype',
        'hasTaxonRank',
        'hasProteinExpressionPhenotype',
        'hasMorphologicalPhenotype',
        'hasDendriteMorphologicalPhenotype',
        'hasAxonLocatedIn',
        'hasDevelopmentalOrigin',
        'hasElectrophysiologicalPhenotype',
        'hasProjectionPhenotype',
        'hasLocationPhenotype'
    ]

    def __init__(self, input):
        prefixes = {**{'JAX': 'http://jaxmice.jax.org/strain/',
                    'MMRRC': 'http://www.mmrrc.org/catalog/getSDS.jsp?mmrrc_id=',
                    'AIBS': 'http://api.brain-map.org/api/v2/data/TransgenicLine/'},
                    **makePrefixes('definition', 'ilxtr', 'owl')}
        self.predicates = Config(
            name=args['--output'],
            imports=['NIFTTL:transgenic_lines.ttl'],
            prefixes=prefixes)
        self.g = makeGraph('transgenic-lines', prefixes=prefixes)
        self.neuron_data = input
        # self.sample_neuron()

    def avoid_url_conversion(self, string):
        if not string:
            return string
        return re.sub("/| |\(", '_', string).replace(')', '')

    def sample_neuron(self,):
        Neuron(
            Phenotype('ilxtr:apical',
                      'ilxtr:hasPhenotype',
                      label='apical - truncated'),
            Phenotype('JAX:12345',
                      'ilxtr:hasExperimentalPhenotype',
                      label='prefix+stock_number'),
        )
        # embed()
        print(graphBase.ttl())

    def cell_phenotypes(self, cell_line):
        cell_mappings = {
            'hemisphere': 'ilxtr:hasLocationPhenotype',
            # 'name': 'ilxtr:hasPhenotype',
        }
        phenotypes = []
        for name, value in cell_line.items():
            mapping = cell_mappings.get(name)
            if mapping and value:
                if name == 'hemisphere':
                    if value.lower() == 'left':
                        curie = 'UBERON:0002812'
                    elif value.lower() == 'right':
                        curie = 'UBERON:0002813'
                    else:
                        raise ValueError('got stuck with unkown hemisphere ' + value)
                phenotypes.append(
                    Phenotype(
                        curie,
                        mapping,
                        label=value
                    )
                )
        return phenotypes

    # TODO: wrong phenotype
    def structure_phenotypes(self, cell_line):
        struc = cell_line['structure']
        phenotypes = []
        acronym = self.avoid_url_conversion(struc['acronym'])
        curie = 'MBA:' + str(struc['id'])
        if struc:
            phenotypes.append(
                Phenotype(
                    curie,
                    'ilxtr:hasSomaLocatedIn',
                    label=acronym
                ),
            )
        return phenotypes

    def donor_phenotypes(self, cell_line):
        donor_mappings = {
            'sex_full_name': 'ilxtr:hasPhenotype'
        }
        phenotypes = []
        for name, value in cell_line['donor'].items():
            mapping = donor_mappings.get(name)
            if mapping and value:
                if name == 'sex_full_name':
                    if value.lower() == 'male':
                        curie = 'PATO:0000383'
                    elif value.lower() == 'female':
                        curie = 'PATO:0000384'
                    else:
                        raise ValueError('unkown sex ' + str(value))
                phenotypes.append(
                    Phenotype(
                        curie,
                        mapping,
                        label='name'
                    ),
                )
        return phenotypes

    # TODO: Figure how to add: description, name and type
    def transgenic_lines_phenotypes(self, cell_line):
        transgenic_mappings = {
        }
        phenotypes = []
        for tl in cell_line['donor']['transgenic_lines']:
            prefix = tl['transgenic_line_source_name']
            suffix = tl['stock_number'] if tl['stock_number'] else str(tl['id'])
            name = self.avoid_url_conversion(tl['name'])
            _type = tl['transgenic_line_type_name']
            line_names = []
            if prefix and suffix and prefix in ['AIBS', 'MMRRC', 'JAX']:
                curie = prefix + ':' + suffix
                # line_names.append(
                phenotypes.append(
                    Phenotype(
                        curie,
                        'ilxtr:hasExpressionPhenotype',
                    )
                )
        return phenotypes

    # TODO: search if description exists
    # TODO: Create mapping for all possible types
    # TODO: Fork negatives to NegPhenotype
    def specimen_tags_phenotypes(self, cell_line):
        specimen_tag_mappings = {
            # 'spiny':'+',
            # 'aspiny':'-'
        }
        phenotypes = []
        for tag in cell_line['specimen_tags']:
            if 'dendrite type' in tag['name']:
                name = tag['name'].split(' - ')[1].replace(' ','_')
            else:
                name = tag['name'].replace(' - ', '_')
            # if phenotype == '+':
            phenotypes.append(
                Phenotype(
                    'ilxtr:' + name,
                    'ilxtr:hasDendriteMorphologicalPhenotype',
                    #label=label,
                )
            )
            # elif phenotype == '-': phenotypes.append(NegPhenotype(...))
        return phenotypes

    # TODO: check to see if specimen_id is really the priority
    def cell_soma_locations_phenotypes(self, cell_line):
        cell_soma_mappings = {
        }
        phenotypes = []
        for csl in cell_line['cell_soma_locations']:
            location = csl['id']
            phenotypes.append(
                Phenotype(
                    'ilxtr:' + str(location),
                    'ilxtr:hasSomaLocatedIn',
                )
            )
        return phenotypes

    def add_mouse_lineage(self, cell_line):
        phenotypes = [Phenotype('NCBITaxon:10090', 'ilxtr:hasInstanceInSpecies')]
        return phenotypes

    def build_phenotypes(self, cell_line):
        phenotype_functions = [
            self.cell_phenotypes,
            self.structure_phenotypes,
            self.donor_phenotypes,
            self.transgenic_lines_phenotypes,
            self.specimen_tags_phenotypes,
            self.add_mouse_lineage,
            # self.cell_soma_locations_phenotypes, # deprecated
        ]
        phenotypes = []
        for func in phenotype_functions:
            phenotypes.extend(func(cell_line))
        return phenotypes

    def build_neurons(self):
        for cell_line in self.neuron_data[:]:
            Neuron(*self.build_phenotypes(cell_line))
        # print(graphBase.ttl())
        Neuron.write()

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
                #phenotype = self.get_phenotype()
                self.g.add_class(_class)
                self.g.add_trip(_class, 'rdfs:label', tl['name'])
                self.g.add_trip(_class, 'definition:', tl['description'])
                self.g.add_trip(_class, 'rdfs:subClassOf', 'ilxtr:transgenicLine')
                self.g.add_trip(_class, 'ilxtr:hasTransgenicType', 'ilxtr:' + line_type + 'Line')
        self.g.write()

def main():
    print(args)
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

    act = AllenCellTypes(input=input)
    act.build_neurons()
    act.build_transgenic_lines()


if __name__ == '__main__':
    main()
