#!/usr/bin/env python3

import os
import glob
from datetime import date
from collections import namedtuple
import requests
import rdflib
from rdflib.extras import infixowl
from lxml import etree
from utils import add_hierarchy, makeGraph, rowParse
from IPython import embed


PScheme = namedtuple('PScheme', ['curie', 'name', 'species', 'devstage', 'citation'])

schemes = [
PScheme('ilx:empty','','','',''),
PScheme('ilx:1','CoCoMac parcellation concept','NCBITaxon:9544','various','problem'),  # problems detected :/
PScheme('ilx:2','Allen Mouse Brain Atlas parcellation concept','NCBITaxon:10090','adult P56','http://help.brain-map.org/download/attachments/2818169/AllenReferenceAtlas_v2_2011.pdf?version=1&modificationDate=1319667383440'),  # yay no doi! wat
]

PARC_SUPER = ('ilx:ilx_brain_parcellation_concept', 'Brain parcellation scheme concept')

def make_scheme(scheme, parent=PARC_SUPER[0]):  # ick...
    out = [
        (scheme.curie, rdflib.RDF.type, rdflib.OWL.Class),
        (scheme.curie, rdflib.RDFS.label, scheme.name),
        (scheme.curie, rdflib.RDFS.subClassOf, parent),
        (scheme.curie, 'ilx:has_taxon', scheme.species),
        (scheme.curie, 'ilx:has_developmental_stage', scheme.devstage),
        (scheme.curie, 'OBOANN:definingCitation', scheme.citation),
    ]
    return out

def add_scheme(graph, scheme, parent=None):
    if not parent:
        [graph.add_node(*triple) for triple in make_scheme(scheme)]
    else:
        [graph.add_node(*triple) for triple in make_scheme(scheme, parent)]

def parcellation_schemes():

    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/'

    filename = 'parcellation'
    ontid = ONT_PATH + filename + 'ttl'
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
        'skos':'http://www.w3.org/2004/02/skos/core#',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
    }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    new_graph.add_node(ontid, rdflib.RDFS.label, filename)
    new_graph.add_node(ontid, rdflib.RDFS.comment, 'Brain parcellation schemes as represented by root concepts.')
    new_graph.write()


def mouse_brain_atlas():
    # TODO source this from somewhere?
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'obo':'http://purl.obolibrary.org/obo/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'MBA':'http://api.brain-map.org/api/v2/data/Structure/',
        'owl':'http://www.w3.org/2002/07/owl#',  # this should autoadd for prefixes but doesnt!?
    }

    g = makeGraph('mbaslim', PREFIXES)  # FIXME ANNOYING :/ this shouldn't need to go out here :/

    #edge_types = {
        #namespaces['OBOANN']['acronym']:str,
        #namespaces['ABA'],
        #rdflib.RDFS['label']:str,
        #rdflib.RDFS['subClassOf']:rdflib.URIRef,
        #namespaces['OBOANN']['synonym']:str,
    #}

    aba_map = {
        'acronym':g.namespaces['OBOANN']['acronym'],  # FIXME all this is BAD WAY
        #'id':namespaces['ABA'],
        'name':rdflib.RDFS.label,
        #'parent_structure_id':rdflib.RDFS['subClassOf'],
        'safe_name':g.namespaces['OBOANN']['synonym'],
    }

    def aba_trips(node_d):
        output = []
        parent = 'MBA:' + str(node_d['id'])  # FIXME HRM what happens if we want to change ABA:  OH LOOK
        for key, edge in sorted(aba_map.items()):
            value = node_d[key]
            if not value:
                continue
            elif key == 'safe_name' and value == node_d['name']:
                continue  # don't duplicate labels as synonyms
            output.append( (parent, edge, value) )
        return output

    def aba_make():
        root = 997  # for actual parts of the brain
        url = 'http://api.brain-map.org/api/v2/tree_search/Structure/997.json?descendants=true'
        superclass = rdflib.URIRef('http://uri.interlex.org/base/ilx_allen_brain_parc_region')
        resp = requests.get(url).json()
        for node_d in resp['msg']:
            if node_d['id'] == 997:  # FIXME need a better place to document this :/
                node_d['name'] = 'allen mouse brain atlas parcellation root'
                node_d['safe_name'] = 'allen mouse brain atlas parcellation root'
                node_d['acronym'] = 'mbaroot'
            ident = g.namespaces['MBA'][str(node_d['id'])]
            cls = infixowl.Class(ident, graph=g.g)
            cls.subClassOf = [superclass]
            parent = node_d['parent_structure_id']
            if parent:
                parent = g.namespaces['MBA'][str(parent)]
                #add_hierarchy(g.g, parent, rdflib.URIRef('http://uri.interlex.org/base/proper_part_of'), cls)
                add_hierarchy(g.g, parent, rdflib.URIRef('http://purl.obolibrary.org/obo/BFO_0000050'), cls)

            for t in aba_trips(node_d):
                g.add_node(*t)

        g.add_node(superclass, rdflib.RDFS.label, 'Allen Mouse Brain Atlas brain region')
        g.add_node(superclass, rdflib.RDFS.subClassOf, PARC_SUPER[0])

        ontid = 'http://ontology.neuinfo.org/NIF/ttl/generated/mbaslim.ttl'
        g.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
        g.add_node(ontid, rdflib.RDFS.label, 'Allen Mouse Brain Atlas Ontology')
        g.add_node(ontid, rdflib.RDFS.comment, 'This file is automatically generated from the Allen Brain Atlas API')
        g.add_node(ontid, rdflib.OWL.versionInfo, date.isoformat(date.today()))
        g.write()

    aba_make()

class cocomac(rowParse):
    superclass = rdflib.URIRef('http://uri.interlex.org/base/ilx_cocomac_parc_region')
    def __init__(self, graph, rows, header):
        self.g = graph
        super().__init__(rows, header)#, order=[0])

    def ID(self, value):
        self.identifier = 'cocomac:' + value  # safe because reset every row (ish)
        self.g.add_node(self.identifier, rdflib.RDF.type, rdflib.OWL.Class)
        self.g.add_node(self.identifier, rdflib.RDFS.subClassOf, self.superclass)

    def Key(self, value):
        pass

    def Summary(self, value):
        pass

    def Acronym(self, value):
        self.g.add_node(self.identifier, 'OBOANN:acronym', value)

    def FullName(self, value):
        self.g.add_node(self.identifier, rdflib.RDFS.label, value)

    def LegacyID(self, value):
        if value:  # FIXME should fix in add_node
            self.g.add_node(self.identifier, 'OBOANN:acronym', value)

    def BrainInfoID(self, value):
        pass

def cocomac_make():
    #url = 'http://cocomac.g-node.org/services/search_wizard.php?T=BrainMaps_BrainSiteAcronyms&x0=&limit=3000&page=1&format=json'
    #resp = json.loads(requests.get(url).json())  # somehow everything is double escaped :x
    base_format = 'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT%20*%20from%20BrainMaps_BrainSiteAcronyms%20where%20ID='
    url = 'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT * from BrainMaps_BrainSiteAcronyms;&format=json'
    #url = 'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT%20*%20from%20BrainMaps_BrainSiteAcronyms;&format=json'
    #tab_name = resp['resultTable']
    #table = resp['tables'][tab_name]
    table = requests.get(url).json()
    fields = table['fields']
    data = table['data']
    #rows = sorted(data.values())
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'cocomac':base_format,
    }
    ccgraph = makeGraph('cocomacslim', PREFIXES)
    cocomac(ccgraph, data.values(), fields)
    ccgraph.add_node(cocomac.superclass, rdflib.RDFS.label, 'CoCoMac terminology brain region')
    ccgraph.add_node(cocomac.superclass, rdflib.RDFS.subClassOf, PARC_SUPER[0])

    ontid = 'http://ontology.neuinfo.org/NIF/ttl/generated/cocomacslim.ttl'
    ccgraph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    ccgraph.add_node(ontid, rdflib.RDFS.label, 'CoCoMac terminology')
    ccgraph.add_node(ontid, rdflib.RDFS.comment, 'This file is automatically generated from the CoCoMac database on the terms from BrainMaps_BrainSiteAcronyms.')
    ccgraph.add_node(ontid, rdflib.OWL.versionInfo, date.isoformat(date.today()))
    ccgraph.write()

def fmri_atlases():

    ATLAS_PATH = '/usr/share/fsl/data/atlases/'
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/generated/'

    # ingest the structured xml files and get the name of the atlas/parcellation scheme
    # ingest the labels
    # for each xml files/set of nii files generate a ttl file


    for xmlfile in glob.glob(ATLAS_PATH + '*.xml'):

        tree = etree.parse(xmlfile)
        name = tree.xpath('header//name')[0].text
        filename = os.path.basename(xmlfile).replace('.xml','.ttl')
        ontid = ONT_PATH + filename
        PREFIXES = {
            '':ontid+'/',
            'ilx':'http://uri.interlex.org/base/',
            'skos':'http://www.w3.org/2004/02/skos/core#',
            'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
            'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        }
        new_graph = makeGraph(os.path.splitext(filename)[0], PREFIXES)
        new_graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)

        new_graph.add_node(ontid, rdflib.RDFS.label, name)
        new_graph.add_node(ontid, rdflib.RDFS.comment, 'This file is automatically generated from the %s file in the FSL atlas collection.' % xmlfile)

        meta = PScheme('ilx:placeholder_' + name.replace(' ','_'),
                       name + ' parcellation concept',
                       'NCBITaxon:9606',
                       'adult',
                       'http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases')  # problems detected :/
        add_scheme(new_graph, meta)

        sn = tree.xpath('header//shortname')
        if sn:
            new_graph.add_node(ontid, rdflib.namespace.SKOS.altLabel, sn[0].text)

        #tree.xpath('header//shortname').text
        for node in tree.xpath('data//label'):
            id_ = ':' + node.get('index')
            label = node.text
            new_graph.add_node(id_, rdflib.RDFS.subClassOf, meta.curie)
            new_graph.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
            new_graph.add_node(id_, rdflib.RDFS.label, label)
        #print([(l.get('index'),l.text) for l in tree.xpath('data//label')])
        new_graph.write()

    #embed()

def main():
    #parcellation_schemes()
    #cocomac_make()
    #fmri_atlases()
    mouse_brain_atlas()

if __name__ == '__main__':
    main()

