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
from rdflib.namespace import *
from pyontutils.core import makePrefixes, ilxtr
from pyontutils.neuron_lang import *
from pyontutils.neurons import LocalNameManager
from docopt import docopt
from IPython import embed
args = docopt(__doc__, version='0.0.4')


prefixes = {**{'JAX': 'http://jaxmice.jax.org/strain/',
            'MMRRC': 'http://www.mmrrc.org/catalog/getSDS.jsp?mmrrc_id=',
            'AIBS': 'http://api.brain-map.org/api/v2/data/TransgenicLine/'},
            **makePrefixes('definition', 'ilxtr', 'owl')}
predicates = Config(
    name=args['--output'],
    imports=['NIFTTL:transgenic_lines.ttl'],
    prefixes=prefixes)


class NeuronACT(Neuron):
    owlClass = ilxtr.NeuronACT
    shortname = 'AllenCT'

class AllenNames(LocalNameManager):
    Mouse = Phenotype('NCBITaxon:10090', 'ilxtr:hasInstanceInSpecies')

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
        self.neurons_data = input
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
        print(graphBase.ttl())

    def get_cell_phenotypes(self, cell_data):
        hemisphere_side = cell_data.get('hemisphere')
        if not hemisphere_side:
            return []
        if hemisphere_side.lower() == 'left':
            curie = 'UBERON:0002812'
        elif hemisphere_side.lower() == 'right':
            curie = 'UBERON:0002813'
        phenotypes=[Phenotype(curie, 'ilxtr:hasLocationPhenotype', label=hemisphere_side)]
        return phenotypes

    def get_structure_phenotypes(self, structure_data):
        acronym = structure_data['acronym']
        curie = 'MBA:' + str(structure_data['id'])
        phenotypes=[Phenotype(curie, 'ilxtr:hasSomaLocatedIn', label=acronym)]
        return phenotypes

    def get_donor_phenotypes(self, donor_data):
        sex = donor_data['sex_full_name']
        if sex.lower() == 'male':
            curie = 'PATO:0000383'
        elif sex.lower() == 'female':
            curie = 'PATO:0000384'
        phenotypes=[Phenotype(curie, 'ilxtr:hasPhenotype', label=sex)]
        return phenotypes

    def get_transgenic_lines_phenotypes(self, transgenic_lines_data):
        phenotypes = []
        for tl in transgenic_lines_data:
            name = tl['transgenic_line_source_name']
            if not name:
                continue
            elif name.lower() == 'other':
                continue
            _id = tl['stock_number'] if tl['stock_number'] else str(tl['id'])
            curie = name + ':' + _id
            phenotypes.append(Phenotype(curie, 'ilxtr:hasExpressionPhenotype'))
        return phenotypes

    # TODO: Fork negatives to NegPhenotype
    def get_specimen_tags_phenotypes(self, specimen_tags_data):
        specimen_tag_mappings = {
            # 'spiny':'+',
            # 'aspiny':'-'
        }
        phenotypes = []
        for tag in specimen_tags_data:
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

    def compartmentalize_neuron_data(self, neuron_data):
        cell_data = neuron_data
        cell_phenotypes = self.get_cell_phenotypes(cell_data)

        structure_data = neuron_data['structure']
        structure_phenotypes = self.get_structure_phenotypes(structure_data)

        donor_data = neuron_data['donor']
        donor_phenotypes = self.get_donor_phenotypes(donor_data)

        transgenic_lines = neuron_data['donor']['transgenic_lines']
        transgenic_lines_phenotypes = self.get_transgenic_lines_phenotypes(transgenic_lines)

        specimen_tags = neuron_data['specimen_tags']
        specimen_tags_phenotypes = self.get_specimen_tags_phenotypes(specimen_tags)

        return (cell_phenotypes,
                structure_phenotypes,
                donor_phenotypes,
                transgenic_lines_phenotypes,
                specimen_tags_phenotypes)

    def build_neurons(self):
        with AllenNames:
            for neuron_data in self.neurons_data:
                phenotype_bundle = self.compartmentalize_neuron_data(neuron_data)
                cell, structure, donor, transgenic_lines, specimen_tags = phenotype_bundle
                NeuronACT(*(cell + structure + donor + transgenic_lines + specimen_tags))

        # print(graphBase.ttl())
        NeuronACT.write()
        NeuronACT.write_python()

def main():
    print(args)
    if not args['--refresh'] and args['--input'] and Path(args['--input']).exists():
        with open(args['--input'], 'rt') as f:
            input = json.load(f)['msg']
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

if __name__ == '__main__':
    main()
