""" Converts owl or ttl or raw rdflib graph into a pandas DataFrame. Saved in .pickle format.

Usage:  allen_cell_type.py [-h | --help]
        allen_cell_type.py [-v | --version]
        allen_cell_type.py [-i=<path>] [-o=<output_path>]

Options:
    -h --help                          Display this help message
    -v --version                       Current version of file
    -i --input=<intput_path>           Full Allen Brain Atlas meta data [default: Dropbox/neuroinformatics/dump/cell_line_data_06_26_18.json]
    -o --output=<output_path>          Output path of picklized pandas DataFrame [default: ../dump/test_graph.ttl]
"""
from docopt import docopt
from ilxutils.tools import open_json
from rdflib.namespace import *
from pyontutils.neuron_lang import *
from pyontutils.core import annotation
import rdflib
import pandas as pd
from sys import exit
import re
from IPython import embed
VERSION = '0.0.2'
doc = docopt(__doc__, version=VERSION)
ARGS = pd.Series(
    {k.replace('--', '').replace('-', '_'): v for k, v in doc.items()}
)


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

    def __init__(self,):
        self.predicates = Config(name=ARGS.output,
                                 imports=[
                                     'NIFTTL:transgenic_lines.ttl'],
                                 prefixes={'JAX': 'http://api.brain-map.org/api/v2/data/TransgenicLine/',
                                           'MMRRC': 'http://api.brain-map.org/api/v2/data/TransgenicLine/',
                                           'AIBS': 'http://api.brain-map.org/api/v2/data/TransgenicLine/', })
        self.neuron_data = open_json(ARGS.input)['msg']
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
        # embed()6
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
                    value = name + value.capitalize()
                phenotypes.append(
                    Phenotype(
                        'ilxtr:' + value,
                        mapping,
                        label=value))
        return phenotypes

    # TODO: wrong phenotype
    def structure_phenotypes(self, cell_line):
        struc = cell_line['structure']
        phenotypes = []
        acronym = self.avoid_url_conversion(struc['acronym'])
        if struc:
            phenotypes.append(
                Phenotype(
                    'ilxtr:' + acronym,
                    'ilxtr:hasMorphologicalPhenotype',
                    label='acronym'
                ),
            )
        return phenotypes

    def donor_phenotypes(self, cell_line):
        donor_mappings = {
            'sex_full_name': 'ilxtr:hasInstanceInSpecies'
        }
        phenotypes = []
        for name, value in cell_line['donor'].items():
            mapping = donor_mappings.get(name)
            if mapping and value:
                phenotypes.append(
                    Phenotype(
                        'ilxtr:' + value,
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
                        'ilxtr:hasExperimentalPhenotype',
                    )
                )
            # if name:
            #    line_names.append(
            #        Phenotype(
            #            'ilxtr:' + name,
            #            'ilxtr:hasExperimentalPhenotype',
            #            label='genotype'
            #        )
            #    )
            # if _type:
            #    line_names.append(
            #        Phenotype(
            #            'ilxtr:' + _type,
            #            'ilxtr:hasExperimentalPhenotype',
            #            label='transgenic_line_type_name'
            #        )
            #    )
            # if line_names:
                #phenotypes.append(LogicalPhenotype(AND, *line_names))

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
                label, name = tag['name'].split(' - ')
            else:
                name, label = tag['name'].split(' - ')
            name = '_'.join(name.split())
            # if phenotype == '+':
            phenotypes.append(
                Phenotype(
                    'ilxtr:' + name,
                    'ilxtr:hasDendriteMorphologicalPhenotype',
                    label=label,
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
            location = str(csl['specimen_id']
                           ) if csl['specimen_id'] else str(csl['id'])
            phenotypes.append(
                Phenotype(
                    'ilxtr:' + location,
                    'ilxtr:hasSomaLocatedIn',
                )
            )
        return phenotypes

    def build_phenotypes(self, cell_line):
        phenotype_functions = [
            self.cell_phenotypes,
            self.structure_phenotypes,
            self.donor_phenotypes,
            self.transgenic_lines_phenotypes,
            self.specimen_tags_phenotypes,
            self.cell_soma_locations_phenotypes,
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


def main():
    ex = open_json(ARGS.input)['msg'][0]
    act = AllenCellTypes()
    act.build_neurons()


if __name__ == '__main__':
    main()
