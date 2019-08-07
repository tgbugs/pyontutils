#!/usr/bin/env python3.7
""" Converts owl or ttl or raw rdflib graph into a pandas DataFrame. Saved in .pickle format.

Usage:
    allen_cell_types [options]

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
from pyontutils.utils import TermColors as tc, relative_path
from pyontutils.core import simpleOnt
from pyontutils.config import devconfig
from pyontutils.namespaces import makePrefixes, ilxtr, definition
from pyontutils.combinators import annotation
from neurondm.lang import *
from pyontutils.closed_namespaces import rdf, rdfs, owl
from docopt import docopt, parse_defaults
from IPython import embed


class NeuronACT(NeuronEBM):
    owlClass = ilxtr.NeuronACT
    shortname = 'AllenCT'


class AllenCellTypes:

    branch = devconfig.neurons_branch

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

    prefixes = {**{'JAX': 'http://jaxmice.jax.org/strain/',
                   'MMRRC': 'http://www.mmrrc.org/catalog/getSDS.jsp?mmrrc_id=',
                   'AllenTL': 'http://api.brain-map.org/api/v2/data/TransgenicLine/'},
                **makePrefixes('definition', 'ilxtr', 'owl')}

    def __init__(self, input, name):
        self.name = name
        self.ns = {k:rdflib.Namespace(v) for k, v in self.prefixes.items()}
        self.neuron_data = input
        self.tag_names = set()
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
            'sex_full_name': 'ilxtr:hasBiologicalSex'
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
            if _type == 'driver':
                pred = 'ilxtr:hasDriverExpressionPhenotype'
            elif _type == 'reporter':
                pred = 'ilxtr:hasReporterExpressionPhenotype'
            else:
                pred = 'ilxtr:hasExpressionPhenotype'

            line_names = []
            if prefix and suffix and prefix in ['AIBS', 'MMRRC', 'JAX']:
                if prefix == 'AIBS':
                    prefix = 'AllenTL'
                iri = self.ns[prefix][suffix]
                phenotypes.append(Phenotype(iri, pred))
        return phenotypes

    # TODO: search if description exists
    # TODO: Create mapping for all possible types
    # TODO: Fork negatives to NegPhenotype
    def specimen_tags_phenotypes(self, cell_line):
        pred = 'ilxtr:hasDendriteMorphologicalPhenotype'
        specimen_tag_mappings = {
            'spiny': Phenotype('ilxtr:SpinyPhenotype', pred),
            'aspiny': NegPhenotype('ilxtr:SpinyPhenotype', pred),
            'sparsely spiny': LogicalPhenotype(AND,
                                               Phenotype('ilxtr:SpinyPhenotype', pred),
                                               Phenotype('PATO:0001609', 'ilxtr:hasPhenotypeModifier')),
            'apicalIntact': Phenotype('ilxtr:ApicalDendritePhenotype', 'ilxtr:hasMorphologicalPhenotype'),
            'apicalTruncated': LogicalPhenotype(AND,
                                                Phenotype('ilxtr:ApicalDendritePhenotype', 'ilxtr:hasMorphologicalPhenotype'),
                                                Phenotype('PATO:0000936', 'ilxtr:hasPhenotypeModifier')),
            'apicalNa': NegPhenotype('ilxtr:ApicalDendritePhenotype', 'ilxtr:hasMorphologicalPhenotype'),  # NA means there was no apical dendrite
        }
        phenotypes = []
        for tag in cell_line['specimen_tags']:
            if 'dendrite type' in tag['name']:
                one_two = tag['name'].split(' - ')[1]
                #if ' ' in one_two:
                    #one, two = one_two.split(' ')
                    #name = one + two.capitalize()
                #else:
                name = one_two
            else:
                one, two = tag['name'].split(' - ')
                #if two == 'NA':  # apical - NA
                    #continue
                name = one + two.capitalize()

            self.tag_names.add(tag['name'])
            # if phenotype == '+':
            if name not in specimen_tag_mappings:
                raise ValueError(name)

            phenotypes.append(specimen_tag_mappings[name]
                              if name in specimen_tag_mappings else
                              Phenotype('ilxtr:' + name, pred))
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

    def make_config(self):
        # have to call Config here because transgenic lines doesn't exist
        self.config = Config(name=self.name,
                             imports=[f'NIFRAW:{self.branch}/ttl/generated/allen-transgenic-lines.ttl'],
                             prefixes=self.prefixes,
                             branch=self.branch,
                             sources=tuple(),  # TODO insert the link to the query...
                             source_file=relative_path(__file__))

    def build_neurons(self):
        for cell_line in self.neuron_data:
            NeuronACT(*self.build_phenotypes(cell_line))

        print(sorted(self.tag_names))
        NeuronACT.write()
        NeuronACT.write_python()

    def build_transgenic_lines(self):
        """
        init class     |  "transgenic_line_source_name":"stock_number" a Class
        add superClass |  rdfs:subClassOf ilxtr:transgenicLine
        add *order*    |  ilxtr:useObjectProperty ilxtr:<order>
        add name       |  rdfs:label "name"
        add def        |  definition: "description"
        add transtype  |  rdfs:hasTransgenicType "transgenic_line_type_name"
        """

        triples = []
        for cell_line in self.neuron_data:
            for tl in cell_line['donor']['transgenic_lines']:
                _id = tl['stock_number'] if tl['stock_number'] else tl['id']
                prefix = tl['transgenic_line_source_name']
                line_type = tl['transgenic_line_type_name']
                if prefix not in ['JAX', 'MMRRC', 'AIBS']:
                    print(tc.red('WARNING:'), 'unknown prefix', prefix, json.dumps(tl, indent=4))
                    continue
                elif prefix == 'AIBS':
                    prefix = 'AllenTL'

                _class = self.ns[prefix][str(_id)]
                triples.append((_class, rdf.type, owl.Class))
                triples.append((_class, rdfs.label, rdflib.Literal(tl['name'])))
                triples.append((_class, definition, rdflib.Literal(tl['description'])))
                triples.append((_class, rdfs.subClassOf, ilxtr.transgenicLine))
                triples.append((_class, ilxtr.hasTransgenicType, ilxtr[line_type + 'Line']))

        # TODO aspects.ttl?
        transgenic_lines = simpleOnt(filename='allen-transgenic-lines',
                                     path='ttl/generated/',
                                     prefixes=self.prefixes,
                                     triples=triples,
                                     comment='Allen transgenic lines for cell types',
                                     branch=self.branch)

        transgenic_lines._graph.write()


def main(args={o.name:o.value for o in parse_defaults(__doc__)}, run=True):
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

    act = AllenCellTypes(input, args['--output'])
    act.make_config()
    if __name__ == '__main__' or run:
        act.build_transgenic_lines()
        act.build_neurons()

    return act.config


if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.4')
    main(args)
