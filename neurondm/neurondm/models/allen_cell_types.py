#!/usr/bin/env python3
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
from pyontutils.utils import TermColors as tc, relative_path
from pyontutils.core import simpleOnt, OntGraph
from pyontutils.namespaces import makePrefixes, ilxtr, definition
from pyontutils.namespaces import rdf, rdfs, owl, AIBSSPEC, npokb
from pyontutils.combinators import annotation, allDifferent, distinctMembers
from neurondm.core import auth
from neurondm.lang import *
from neurondm.simple import Cell
from .allen_type_specimen_mapping import ts_mapping
from docopt import docopt, parse_defaults


class NeuronACT(NeuronEBM):
    owlClass = ilxtr.NeuronACT
    shortname = 'AllenCT'


class AllenCellTypes:

    branch = auth.get('neurons-branch')

    prefixes = {**{'JAX': 'http://jaxmice.jax.org/strain/',
                   'MMRRC': 'http://www.mmrrc.org/catalog/getSDS.jsp?mmrrc_id=',
                   'AllenTL': 'http://api.brain-map.org/api/v2/data/TransgenicLine/'},
                **makePrefixes('definition', 'ilxtr', 'owl')}
    prefixes['AllenTransgenicLine'] = 'http://api.brain-map.org/api/v2/data/TransgenicLine/'
    prefixes['AIBSSPEC'] = str(AIBSSPEC)

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
        print(graphBase.ttl())

    def cell_phenotypes(self, cell_specimen):
        cell_mappings = {
            'hemisphere': 'ilxtr:hasSomaLocationLaterality',
            # 'name': 'ilxtr:hasPhenotype',
        }
        phenotypes = []
        for name, value in cell_specimen.items():
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
                    )
                )
        return phenotypes

    # TODO: wrong phenotype
    def structure_phenotypes(self, cell_specimen):
        struc = cell_specimen['structure']
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

    def donor_phenotypes(self, cell_specimen):
        donor_mappings = {
            'sex_full_name': 'ilxtr:hasBiologicalSex'
        }
        phenotypes = []
        for name, value in cell_specimen['donor'].items():
            mapping = donor_mappings.get(name)
            if mapping and value:
                if name == 'sex_full_name':
                    if value.lower() == 'female':
                        curie = 'PATO:0000383'
                    elif value.lower() == 'male':
                        curie = 'PATO:0000384'
                    else:
                        raise ValueError('unkown sex ' + str(value))
                phenotypes.append(
                    Phenotype(
                        curie,
                        mapping,
                    ),
                )
        return phenotypes

    # TODO: Figure how to add: description, name and type
    def transgenic_lines_phenotypes(self, cell_specimen):
        transgenic_mappings = {
        }
        phenotypes = []
        for tl in cell_specimen['donor']['transgenic_lines']:
            prefix = tl['transgenic_line_source_name']
            suffix = tl['stock_number'] if tl['stock_number'] else str(tl['id'])
            name = self.avoid_url_conversion(tl['name'])
            _type = tl['transgenic_line_type_name']
            if _type == 'driver':
                if 'CreERT2' in name:  # FIXME from structured instead of name?
                    pred = ilxtr.hasDriverExpressionInducedPhenotype
                else:
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
    def specimen_tags_phenotypes(self, cell_specimen):
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
        for tag in cell_specimen['specimen_tags']:
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
    def cell_soma_locations_phenotypes(self, cell_specimen):
        cell_soma_mappings = {
        }
        phenotypes = []
        for csl in cell_specimen['cell_soma_locations']:
            location = csl['id']
            phenotypes.append(
                Phenotype(
                    'ilxtr:' + str(location),
                    'ilxtr:hasSomaLocatedIn',
                )
            )
        return phenotypes

    def add_mouse_lineage(self, cell_specimen):
        phenotypes = [Phenotype('NCBITaxon:10090', 'ilxtr:hasInstanceInTaxon')]
        return phenotypes

    def build_phenotypes(self, cell_specimen):
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
            phenotypes.extend(func(cell_specimen))
        return phenotypes

    def make_config(self):
        # have to call Config here because transgenic lines doesn't exist
        self.config = Config(name=self.name,
                             imports=[f'NIFRAW:{self.branch}/ttl/generated/allen-transgenic-lines.ttl'],
                             prefixes=self.prefixes,
                             branch=self.branch,
                             sources=tuple(),  # TODO insert the link to the query...
                             source_file=relative_path(
                                 __file__,
                                 no_wd_value=__file__))

    def build_neurons(self):
        instances = []
        dids = []
        done = {}
        for cell_specimen in self.neuron_data:
            sid = cell_specimen['id']
            tid = OntId(f'npokb:{ts_mapping[sid]}') if sid in ts_mapping else None

            phens = self.build_phenotypes(cell_specimen)
            cell = Cell(*phens)  # use the simple repr to id cells and get the tid
            if cell not in done:
                if tid is not None:
                    done[cell] = tid
            else:
                tid = done[cell]

            neuron = NeuronACT(*phens, id_=tid)
            did = AIBSSPEC[str(sid)]
            neuron.add_objects(ilxtr.hasNamedIndividual, did)
            dids.append(did)
            instances.append((did, rdf.type, owl.NamedIndividual))
            instances.append((did, rdf.type, neuron.identifier))

        print(sorted(self.tag_names))
        NeuronACT.write()
        NeuronACT.write_python()
        self.build_instances(instances, dids)

    def build_instances(self, instances, dids):
        folder = Path(self.config.out_graph_path()).parent
        # WOW do I need to implement the new/better way of
        # managing writing collections of neurons to graphs
        neuron_uri = next(NeuronACT.out_graph[:rdf.type:owl.Ontology])
        name = 'allen-cell-instances.ttl'
        base, _ = neuron_uri.rsplit('/', 1)
        uri = rdflib.URIRef(base + '/' + name)
        metadata = ((uri, rdf.type, owl.Ontology),)
        instance_graph = OntGraph(path=folder / name)
        instance_graph.bind('AIBSSPEC', AIBSSPEC)
        instance_graph.bind('npokb', npokb)
        [instance_graph.add(t) for t in metadata]
        [instance_graph.add(t) for t in instances]
        [instance_graph.add(t) for t in allDifferent(None, distinctMembers(*dids))]
        instance_graph.write()

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
        for cell_specimen in self.neuron_data:
            for tl in cell_specimen['donor']['transgenic_lines']:
                _id = tl['stock_number'] if tl['stock_number'] else tl['id']
                prefix = tl['transgenic_line_source_name']
                line_type = tl['transgenic_line_type_name']
                if line_type == 'driver' and 'CreERT2' in tl['name']:
                    line_type = 'inducibleDriver'

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
                                     local_base=graphBase.local_base,
                                     path='ttl/generated/',
                                     prefixes=self.prefixes,
                                     triples=triples,
                                     comment='Allen transgenic lines for cell types',
                                     branch=self.branch,
                                     calling__file__=__file__,)

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

    input = sorted(input, key=lambda d: d['id'])  # ensure type specimens show up first
    act = AllenCellTypes(input, args['--output'])
    act.make_config()
    if __name__ == '__main__' or run:
        act.build_transgenic_lines()
        act.build_neurons()

    return act.config,


if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.4')
    main(args)
