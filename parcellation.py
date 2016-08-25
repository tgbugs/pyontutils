#!/usr/bin/env python3.5

import os
import csv
import glob
from datetime import date
from collections import namedtuple, defaultdict
import requests
import rdflib
from rdflib.extras import infixowl
from lxml import etree
from hierarchies import creatTree
from utils import async_getter, makeGraph, rowParse, TermColors as tc #TERMCOLORFUNC
from scigraph_client import Vocabulary
from IPython import embed
from desc.util.process_fixed import ProcessPoolExecutor

sgv = Vocabulary(cache=True)

OntMeta = namedtuple('OntMeta', ['path', 'filename', 'name', 'shortname', 'comment', 'version'])
PScheme = namedtuple('PScheme', ['curie', 'name', 'species', 'devstage'])
PScheme('ilx:something','some parcellation scheme concept','NCBITaxon:1234','adult')
PARC_SUPER = ('ilx:ilx_brain_parcellation_scheme_concept', 'Brain parcellation scheme concept')

PSArtifact = namedtuple('PSArtifact', ['curie', 'name', 'version', 'date', 'link', 'citation', 'synonyms','acronyms'])
PSArtifact('SCR:something', 'name name', 'v1', '01/01/01','http://wut.wut', 'scholarly things', tuple(), tuple())
ATLAS_SUPER = 'ilx:parcellation_scheme_artifact' # 'NIFRES:nlx_res_20090402'  # alternatives?

ABAROOT = namedtuple('ABAROOT', ['id', 'name', 'safe_name', 'acronym', 'prefix', 'labelprefix'])

Query = namedtuple('Query', ['root','relationshipType','direction','depth'])

GENERATED = 'http://ontology.neuinfo.org/NIF/ttl/generated/'
TODAY = date.isoformat(date.today())

#annotationProperties
PARCLAB = 'ilx:parcellationLabel'

#objectProperties
UNTAXON = 'ilx:ancestralInTaxon'
EXTAXON = 'ilx:hasInstanceInTaxon'  # FIXME instances?
EXSPECIES = 'ilx:hasInstanceInSpecies'
DEFTAXON = 'ilx:definedForTaxon'
DEFSPECIES = 'ilx:definedForSpecies'
DEVSTAGE = 'ilx:definedForDevelopmentalStage'
PARTOF = 'ilx:partOf'
HASPART = 'ilx:hasPart'

ADULT = 'NIFORG:birnlex_681'

VALIDATE = False  # FIXME :/

def check_hierarchy(new_graph, root, edge, label_edge=None):
    a, b = creatTree(*Query(root, edge, 'INCOMING', 10), json=new_graph.make_scigraph_json(edge, label_edge))
    print(a)

def add_ops(graph):
    graph.add_op(EXSPECIES)
    graph.add_op(DEFSPECIES)
    graph.add_op(DEVSTAGE)

def make_scheme(graph, scheme, atlas_id=None, parent=PARC_SUPER[0]):
    graph.add_class(scheme.curie, parent, label=scheme.name)
    graph.add_hierarchy(scheme.species, DEFSPECIES, scheme.curie)
    graph.add_hierarchy(scheme.devstage, DEVSTAGE, scheme.curie)
    if atlas_id:
        graph.add_node(scheme.curie, rdflib.RDFS.isDefinedBy, atlas_id)

def make_atlas(atlas, parent=ATLAS_SUPER):
    out = [
        (atlas.curie, rdflib.RDF.type, rdflib.OWL.Class),
        (atlas.curie, rdflib.RDFS.label, atlas.name),
        (atlas.curie, rdflib.RDFS.subClassOf, parent),
        (atlas.curie, rdflib.OWL.versionInfo, atlas.version),
        (atlas.curie, 'OBOANN:createdDate', atlas.date),  # FIXME incorrect usage for this edge
        (atlas.curie, 'OBOANN:externalSourceURI', atlas.link),  # FXIME probably needs to be optional...
        (atlas.curie, 'OBOANN:definingCitation', atlas.citation),
    ] + \
    [(atlas.curie, 'OBOANN:synonym', syn) for syn in atlas.synonyms] + \
    [(atlas.curie, 'OBOANN:acronym', ac) for ac in atlas.acronyms]

    return out

def add_triples(graph, struct, struct_to_triples, parent=None):
    if not parent:
        [graph.add_node(*triple) for triple in struct_to_triples(struct)]
    else:
        [graph.add_node(*triple) for triple in struct_to_triples(struct, parent)]

def parcellation_schemes(ontids_atlases):
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/'
    filename = 'parcellation'
    ontid = ONT_PATH + filename + '.ttl'
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
    }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_ont(ontid,
                      'NIF collected parcellation schemes ontology',
                      'Brain parcellation schemes as represented by root concepts.',
                      TODAY,
                      'NIF Parcellations')

    for import_id, atlas in sorted(ontids_atlases):
        new_graph.add_node(ontid, rdflib.OWL.imports, import_id)
        add_triples(new_graph, atlas, make_atlas)

    new_graph.add_node(PARC_SUPER[0], rdflib.RDF.type, rdflib.OWL.Class)
    new_graph.add_node(PARC_SUPER[0], rdflib.RDFS.label, PARC_SUPER[1])
    new_graph.write(delay=True)


class genericPScheme:
    ont = OntMeta
    concept = PScheme
    atlas = PSArtifact
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'owl':'http://www.w3.org/2002/07/owl#',  # this should autoadd for prefixes but doesnt!?
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'NIFORG':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Organism.owl#',
        'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
    }

    def __new__(cls):
        error = 'Expected %s got %s' 
        if type(cls.ont) != OntMeta:
            raise TypeError(error % (OntMeta, type(cls.ont)))
        elif type(cls.concept) != PScheme:
            raise TypeError(error % (PScheme, type(cls.concept)))
        elif type(cls.atlas) != PSArtifact:
            raise TypeError(error % (PSArtifact, type(cls.atlas)))
            
        ontid = cls.ont.path + cls.ont.filename + '.ttl'
        cls.PREFIXES.update(genericPScheme.PREFIXES)
        graph = makeGraph(cls.ont.filename, cls.PREFIXES)
        graph.add_ont(ontid, *cls.ont[2:])
        make_scheme(graph, cls.concept, cls.atlas.curie)
        data = cls.datagetter()
        cls.datamunge(data)
        cls.dataproc(graph, data)
        add_ops(graph)
        graph.write(delay=True)
        return ontid, cls.atlas 

    @classmethod
    def datagetter(cls):
        """ example datagetter function, make any local modifications here """
        with open('myfile', 'rt') as f:
            rows = [r for r in csv.reader(f)]
        dothing = lambda _: [i for i, v in enumerate(_)]
        rows = [dothing(_) for _ in rows]
        raise NotImplementedError('You need to implement this yourlself!')
        return rows

    @classmethod
    def datamunge(cls, data):
        """ in place modifier of data """
        pass

    @classmethod
    def dataproc(cls, graph, data):
        """ example datagetter function, make any local modifications here """
        for thing in data:
            graph.add_node(*thing)
        raise NotImplementedError('You need to implement this yourlself!')


class HBA(genericPScheme):
    ont = OntMeta(GENERATED,
                  'hbaslim',
                  'Allen Human Brain Atlas Ontology',
                  'HBA 2013 v2',
                  'This file is automatically generated from the Allen Brain Atlas API',
                  TODAY)
    concept = PScheme('ilx:ilx_allen_human_brain_parc_region',
                      'Allen Human Brain Atlas parcellation concept',
                      'NCBITaxon:9606',
                      ADULT)
    atlas = PSArtifact('ilx:allen_human_atlas',
                       'Allen Human Brain Atlas v2',
                       '2013 v2',
                       'October 2013',
                       'http://human.brain-map.org/',
                       'http://help.brain-map.org/download/attachments/2818165/HBA_Ontology-and-Nomenclature.pdf?version=1&modificationDate=1382051847989',
                       tuple(),
                       tuple())
    PREFIXES = {
        'ABA':'http://api.brain-map.org/api/v2/data/Structure/',
    }
    ROOT = 3999

    @classmethod
    def datagetter(cls):
        url = 'http://api.brain-map.org/api/v2/tree_search/Structure/{root}.json?descendants=true'.format(root=cls.ROOT)
        resp = requests.get(url).json()
        return resp['msg']

    @classmethod
    def dataproc(cls, graph, data):
        for node in data:
            curie = graph.expand('ABA:' + str(node['id']))
            graph.add_class(curie, cls.concept.curie)
            parent = node['parent_structure_id']
            graph.add_node(curie, rdflib.RDFS.label, '(%s) ' % cls.ont.shortname + node['name'])
            graph.add_node(curie, PARCLAB, node['name'])
            graph.add_node(curie, 'OBOANN:acronym', node['acronym'])
            if node['safe_name'] != node['name']:
                graph.add_node(curie, 'OBOANN:synonym', node['safe_name'])
            if parent:
                pcurie = graph.expand('ABA:' + str(parent))
                graph.add_hierarchy(pcurie, PARTOF, curie)


class MBA(HBA):
    ont = OntMeta(GENERATED,
                  'mbaslim',
                  'Allen Mouse Brain Atlas Ontology',
                  'MBA 2011 v2',
                  'This file is automatically generated from the Allen Brain Atlas API',
                  TODAY)
    concept = PScheme('ilx:ilx_allen_mouse_brain_parc_region',
                      'Allen Mouse Brain Atlas parcellation concept',
                      'NCBITaxon:10090',
                      ADULT)
    atlas = PSArtifact('ilx:allen_mouse_atlas',
                       'Allen Mouse Brain Atlas v2',
                       '2011 v2',
                       'November 2011',
                       'http://mouse.brain-map.org/static/atlas',
                       'http://help.brain-map.org/download/attachments/2818169/AllenReferenceAtlas_v2_2011.pdf?version=1&modificationDate=1319667383440',  # yay no doi! wat
                       tuple(),
                       tuple())
    ROOT = 997

    @classmethod
    def datamunge(cls, data):
        for node in data:
            if node['id'] == cls.ROOT:
                node['name'] = 'allen mouse brain atlas parcellation root'
                node['safe_name'] = 'allen mouse brain atlas parcellation root'
                node['acronym'] = 'mbaroot'
                break


class CoCoMac(genericPScheme):
    ont = OntMeta('http://ontology.neuinfo.org/NIF/ttl/generated/',
                  'cocomacslim',
                  'CoCoMac terminology',
                  'CoCoMac',
                  ('This file is automatically generated from the CoCoMac '
                   'database on the terms from BrainMaps_BrainSiteAcronyms.'),
                  TODAY)
    concept = PScheme('ilx:ilx_cocomac_parc_region',
                       'CoCoMac terminology parcellation concept',
                       'NCBITaxon:9544',
                       'ilx:various')
    atlas = PSArtifact('ilx:cocomac_terminology',
                        'CoCoMac terminology',
                        None, #'no version info',
                        None, #'no date',
                        'http://cocomac.g-node.org',
                        'scholarly things',
                        tuple(),
                        tuple())
    PREFIXES = {
        'cocomac':'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT%20*%20from%20BrainMaps_BrainSiteAcronyms%20where%20ID=',  # looking for better options
    }

    @classmethod
    def datagetter(cls):
        url = 'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT * from BrainMaps_BrainSiteAcronyms;&format=json'
        table = requests.get(url).json()
        fields = table['fields']
        data = [fields] + list(table['data'].values())
        return data

    @classmethod
    def dataproc(cls, graph, data):

        class cocomac(rowParse):
            def ID(self, value):
                self.identifier = 'cocomac:' + value  # safe because reset every row (ish)
                graph.add_class(self.identifier, cls.concept.curie)

            def Key(self, value):
                pass

            def Summary(self, value):
                pass

            def Acronym(self, value):
                graph.add_node(self.identifier, 'OBOANN:acronym', value)

            def FullName(self, value):
                graph.add_node(self.identifier, rdflib.RDFS.label, value)

            def LegacyID(self, value):
                graph.add_node(self.identifier, 'OBOANN:acronym', value)

            def BrainInfoID(self, value):
                pass

        cocomac(data)

def cocomac_make():
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/generated/'
    filename = 'cocomacslim'
    ontid = ONT_PATH + filename + '.ttl'
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'cocomac':'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT%20*%20from%20BrainMaps_BrainSiteAcronyms%20where%20ID=',  # looking for better options
        'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
        'NIFORG':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Organism.owl#',
    }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    new_graph.add_node(ontid, rdflib.RDFS.label, 'CoCoMac terminology')
    new_graph.add_node(ontid, rdflib.RDFS.comment, 'This file is automatically generated from the CoCoMac database on the terms from BrainMaps_BrainSiteAcronyms.')
    new_graph.add_node(ontid, rdflib.OWL.versionInfo, TODAY)
    atlas = PSArtifact('ilx:cocomac_terminology',
                       'CoCoMac terminology',
                       None, #'no version info',
                       None, #'no date',
                       'http://cocomac.g-node.org',
                       'scholarly things',
                       tuple(),
                       tuple())
    meta = PScheme('ilx:ilx_cocomac_parc_region',
                   'CoCoMac terminology parcellation concept',
                   'NCBITaxon:9544',
                   'ilx:various')  # FIXME
    make_scheme(new_graph, meta, atlas.curie)  # FIXME problemws with atlas.curie

    class cocomac(rowParse):
        def ID(self, value):
            self.identifier = 'cocomac:' + value  # safe because reset every row (ish)
            new_graph.add_class(self.identifier, meta.curie)

        def Key(self, value):
            pass

        def Summary(self, value):
            pass

        def Acronym(self, value):
            new_graph.add_node(self.identifier, 'OBOANN:acronym', value)

        def FullName(self, value):
            new_graph.add_node(self.identifier, rdflib.RDFS.label, value)

        def LegacyID(self, value):
            new_graph.add_node(self.identifier, 'OBOANN:acronym', value)

        def BrainInfoID(self, value):
            pass

    url = 'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT * from BrainMaps_BrainSiteAcronyms;&format=json'
    table = requests.get(url).json()
    fields = table['fields']
    data = table['data']
    rows = [fields] + list(data.values())

    cocomac(rows)

    add_ops(new_graph)
    new_graph.write(delay=True)
    return ontid, atlas

def fmri_atlases():
    ATLAS_PATH = '/usr/share/fsl/data/atlases/'
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/generated/'

    # ingest the structured xml files and get the name of the atlas/parcellation scheme
    # ingest the labels
    # for each xml files/set of nii files generate a ttl file

    shortnames = {
        'JHU White-Matter Tractography Atlas':'JHU WM',
        'Oxford-Imanova Striatal Structural Atlas':'OISS',
        'Talairach Daemon Labels':'Talairach',
        'Subthalamic Nucleus Atlas':'SNA',
        'JHU ICBM-DTI-81 White-Matter Labels':'JHU ICBM WM',
        'Juelich Histological Atlas':'Juelich',
        'MNI Structural Atlas':'MNI Struct',
    }
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'skos':'http://www.w3.org/2004/02/skos/core#',
        'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'NIFORG':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Organism.owl#',
    }

    ontids = []
    atlases = []
    for xmlfile in glob.glob(ATLAS_PATH + '*.xml'):
        tree = etree.parse(xmlfile)
        name = tree.xpath('header//name')[0].text
        sn = tree.xpath('header//shortname')
        if sn:
            sn = sn[0].text
        else:
            sn = shortnames[name]

        filename = os.path.splitext(os.path.basename(xmlfile))[0]
        ontid = ONT_PATH + filename + '.ttl'

        PREFIXES[''] = ontid+'/'
        new_graph = makeGraph(filename, PREFIXES)
        new_graph.add_ont(ontid,
                          name,
                          sn,
                          ('This file is automatically generated from the'
                           ' %s file in the FSL atlas collection.') % xmlfile,
                          TODAY)

        atlas = PSArtifact('ilx:placeholder_' + name.replace(' ','_') + '_atlas', # FIXME
                           name,
                           None, #'no version info',
                           None, #'date unknown',
                           'http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases',
                           None, #'http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases',  # TODO: there are MANY defining citations for these...
                           tuple(),
                           (sn,) if sn else tuple())
        pname = name + 'concept' if name.endswith('parcellation') else name + ' parcellation concept'
        meta = PScheme('ilx:placeholder_' + name.replace(' ','_'),
                       pname,
                       'NCBITaxon:9606',
                       ADULT)
        make_scheme(new_graph, meta, atlas.curie)  # FIXME atlas.curie problem...

        for node in tree.xpath('data//label'):
            id_ = ':' + node.get('index')
            label = node.text
            display = '(%s) ' % sn + label
            new_graph.add_class(id_, meta.curie, label=display)
            new_graph.add_node(id_, PARCLAB, label)
        #print([(l.get('index'),l.text) for l in tree.xpath('data//label')])
        add_ops(new_graph)
        new_graph.write(delay=True)
        ontids.append(ontid)
        atlases.append(atlas)

    #embed()
    return [_ for _ in zip(ontids, atlases)]

def hcp2016_make():
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/generated/'
    filename = 'hcp_parcellation'
    ontid = ONT_PATH + filename + '.ttl'
    SHORTNAME = 'HCP-MMP1.0'
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        '':ontid + '/',  # looking for better options
        'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
        'NIFORG':'http://ontology.neuinfo.org/NIF/BiomaterialEntities/NIF-Organism.owl#',
    }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_ont(ontid,
                      ('Human Connectome Project Multi-Modal'
                       ' human cortical parcellation'),
                      SHORTNAME,
                      'This file is automatically generated from....',
                      TODAY)

    atlas = PSArtifact('ilx:hcp_2016_atlas',
                       'Human Connectome Project Multi-Modal human cortical parcellation',
                       '1.0',
                       '07-20-2016',
                       'awaiting...',
                       'doi:10.1038/nature18933',
                       ('Human Connectome Project Multi-Modal Parcellation', 'HCP Multi-Modal Parcellation','Human Connectome Project Multi-Modal Parcellation version 1.0'),
                       ('HCP_MMP', SHORTNAME))
    meta = PScheme('ilx:ilx_hcp2016_parc_region',
                   'HCP parcellation concept',
                   'NCBITaxon:9606',
                   ADULT)
    make_scheme(new_graph, meta, atlas.curie)

    class hcp2016(rowParse):
        def Parcellation_Index(self, value):
            self.id_ = value
            self.id_ = ':' + value  # safe because reset every row (ish)
            new_graph.add_node(self.id_, rdflib.RDF.type, rdflib.OWL.Class)
            new_graph.add_node(self.id_, rdflib.RDFS.subClassOf, meta.curie)

        def Area_Name(self, value):
            value = value.strip()
            new_graph.add_node(self.id_, 'OBOANN:acronym', value)

        def Area_Description(self, value):
            value = value.strip()
            new_graph.add_node(self.id_, rdflib.RDFS.label, '(%s) ' % SHORTNAME + value)
            new_graph.add_node(self.id_, PARCLAB, value)

        def Newly_Described(self, value):
            if value == 'Yes*' or value == 'Yes':
                new_graph.add_node(self.id_, 'OBOANN:definingCitation', 'Glasser and Van Essen 2016')

        def Results_Sections(self, value):
            pass

        def Other_Names(self, value):
            for name in value.split(','):
                name = name.strip()
                if name:
                    new_graph.add_node(self.id_, 'OBOANN:synonym', name)
            
        def Key_Studies(self, value):
            for study in value.split(','):
                study = study.strip()
                if study:
                    new_graph.add_node(self.id_, 'OBOANN:definingCitation', study)

    with open('resources/human_connectome_project_2016.csv', 'rt') as f:
        rows = [r for r in csv.reader(f)]
    hcp2016(rows)

    new_graph.write(delay=True)
    return ontid, atlas

def swanson():
    """ not really a parcellation scheme """
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/generated/'
    filename = 'swanson_hierarchies'
    ontid = ONT_PATH + filename + '.ttl'
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        '':ontid + '/',  # looking for better options
        'UBERON':'http://purl.obolibrary.org/obo/UBERON_'
    }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_ont(ontid,
                      'Swanson brain partomies',
                      'Swanson 2014 Partonomies',
                      'This file is automatically generated from....',
                      TODAY)
            
    with open('resources/swanson_aligned.txt', 'rt') as f:
        lines = [l.strip() for l in f.readlines()]

    # join header on page 794
    lines[635] += ' ' + lines.pop(636)
    #fix for capitalization since this header is reused
    fixed = ' or '.join([' ('.join([n.capitalize() for n in _.split(' (')]) for _ in lines[635].lower().split(' or ')]).replace('human','HUMAN')
    lines[635] = fixed
    
    data = []
    for l in lines:
        if not l.startswith('#'):
            level = l.count('.'*5)
            l = l.strip('.')
            if ' (' in l:
                if ') or' in l:
                    n1, l = l.split(') or')
                    area_name, citationP =  n1.strip().split(' (')
                    citation = citationP.rstrip(')')
                    d = (level, area_name, citation, 'NEXT SYN')
                    data.append(d)
                    #print(tc.red(tc.bold(repr(d))))

                area_name, citationP =  l.strip().split(' (')
                citation = citationP.rstrip(')')
            else:
                area_name = l
                citation = None
            
            d = (level, area_name, citation, None)
            #print(d)
            data.append(d)
    results = async_getter(sgv.findByTerm, [(d[1],) for d in data])
    #results = [None] * len(data)
    curies = [[r['curie'] for r in _ if 'UBERON' in r['curie']] if _ else [] for _ in results]
    output = [_[0] if _ else None for _ in curies]

    header = ['Depth', 'Name', 'Citation', 'NextSyn', 'Uberon']
    zoop = [header] + [r for r in zip(*zip(*data), output)] + \
            [(0, 'Appendix END None', None, None, None)]  # needed to add last appendix

    class SP(rowParse):
        def __init__(self):
            self.nodes = defaultdict(dict)
            self._appendix = 0
            self.appendicies = {}
            self._last_at_level = {}
            self.names = defaultdict(set)
            self.children = defaultdict(set)
            self.parents = defaultdict(set)
            self.next_syn = False
            super().__init__(zoop)

        def Depth(self, value):
            if self.next_syn:
                self.synonym = self.next_syn
            else:
                self.synonym = False
            self.depth = value

        def Name(self, value):
            self.name = value

        def Citation(self, value):
            self.citation = value

        def NextSyn(self, value):
            if value:
                self.next_syn = self._rowind
            else:
                self.next_syn = False

        def Uberon(self, value):
            self.uberon = value

        def _row_post(self):
            # check if we are in the next appendix
            # may want to xref ids between appendicies as well...
            if self.depth == 0:
                if self.name.startswith('Appendix'):
                    if self._appendix:
                        self.appendicies[self._appendix]['children'] = dict(self.children)
                        self.appendicies[self._appendix]['parents'] = dict(self.parents)
                        self._last_at_level = {}
                        self.children = defaultdict(set)
                        self.parents = defaultdict(set)
                    _, num, apname = self.name.split(' ', 2)
                    if num == 'END':
                        return
                    self._appendix = int(num)
                    self.appendicies[self._appendix] = {
                        'name':apname.capitalize(),
                        'type':self.citation.capitalize() if self.citation else None}
                    return
                else:
                    if ' [' in self.name:
                        name, taxonB = self.name.split(' [')
                        self.name = name
                        self.appendicies[self._appendix]['taxon'] = taxonB.rstrip(']').capitalize()
                    else:  # top level is animalia
                        self.appendicies[self._appendix]['taxon'] = 'ANIMALIA'.capitalize()

                    self.name = self.name.capitalize()
                    self.citation = self.citation.capitalize()
            # nodes
            if self.synonym:
                self.nodes[self.synonym]['synonym'] = self.name
                self.nodes[self.synonym]['syn-cite'] = self.citation
                self.nodes[self.synonym]['syn-uberon'] = self.uberon
                return
            else:
                if self.citation:  # Transverse Longitudinal etc all @ lvl4
                    self.names[self.name + ' ' + self.citation].add(self._rowind)
                else:
                    self.name += str(self._appendix) + self.nodes[self._last_at_level[self.depth - 1]]['label']
                    #print(level, self.name)
                    # can't return here because they are their own level
                # replace with actually doing something...
                self.nodes[self._rowind]['label'] = self.name
                self.nodes[self._rowind]['citation'] = self.citation
                self.nodes[self._rowind]['uberon'] = self.uberon
            # edges
            self._last_at_level[self.depth] = self._rowind
            # TODO will need something to deal with the Lateral/
            if self.depth > 0:
                try:
                    parent = self._last_at_level[self.depth - 1]
                except:
                    embed()
                self.children[parent].add(self._rowind)
                self.parents[self._rowind].add(parent)

        def _end(self):
            replace = {}
            for asdf in [sorted(n) for k,n in self.names.items() if len(n) > 1]:
                replace_with, to_replace = asdf[0], asdf[1:]
                for r in to_replace:
                    replace[r] = replace_with

            for r, rw in replace.items():
                #print(self.nodes[rw])
                o = self.nodes.pop(r)
                #print(o)

            for vals in self.appendicies.values():
                children = vals['children']
                parents = vals['parents']
                # need reversed so children are corrected before swap
                for r, rw in reversed(sorted(replace.items())):
                    if r in parents:
                        child = r
                        new_child = rw
                        parent = parents.pop(child)
                        parents[new_child] = parent
                        parent = list(parent)[0]
                        children[parent].remove(child)
                        children[parent].add(new_child)
                    if r in children:
                        parent = r
                        new_parent = rw
                        childs = children.pop(parent)
                        children[new_parent] = childs
                        for child in childs:
                            parents[child] = {new_parent}

            self.nodes = dict(self.nodes)

    sp = SP()
    tp = [_ for _ in sorted(['{: <50}'.format(n['label']) + n['uberon'] if n['uberon'] else n['label'] for n in sp.nodes.values()])]
    #print('\n'.join(tp))
    #print(sp.appendicies[1].keys())
    #print(sp.nodes[1].keys())
    nbase = 'http://swanson.org/node/%s' 
    json_ = {'nodes':[],'edges':[]}
    for node, anns in sp.nodes.items():
        nid = nbase % node
        new_graph.add_class(nid, 'ilx:swansonBrainRegionConcept', label=anns['label'])
        new_graph.add_node(nid, 'OBOANN:definingCitation', anns['citation'])
        json_['nodes'].append({'lbl':anns['label'],'id':'SWA:' + str(node)})
        #if anns['uberon']:
            #new_graph.add_node(nid, rdflib.OWL.equivalentClass, anns['uberon'])  # issues arrise here...

    for appendix, data in sp.appendicies.items():
        aid = 'http://swanson.org/appendix/%s' % appendix
        new_graph.add_class(aid, label=data['name'].capitalize())
        new_graph.add_node(aid, 'ilx:hasTaxonRank', data['taxon'])  # FIXME appendix is the data artifact...
        children = data['children']
        ahp = HASPART + str(appendix)
        apo = PARTOF + str(appendix)
        new_graph.add_op(ahp, transitive=True)
        new_graph.add_op(apo, inverse=ahp, transitive=True)
        for parent, childs in children.items():  # FIXME does this give complete coverage?
            pid = nbase % parent
            for child in childs:
                cid = nbase % child
                new_graph.add_hierarchy(cid, ahp, pid)  # note hierarhcy inverts direction
                new_graph.add_hierarchy(pid, apo, cid)
                json_['edges'].append({'sub':'SWA:' + str(child),'pred':apo,'obj':'SWA:' + str(parent)})

    new_graph.write(delay=True)
    if VALIDATE:
        Query = namedtuple('Query', ['root','relationshipType','direction','depth'])
        mapping = (1, 1, 1, 1, 30, 83, 69, 70, 74, 1)  # should generate?
        for i, n in enumerate(mapping):
            a, b = creatTree(*Query('SWA:' + str(n), 'ilx:partOf' + str(i + 1), 'INCOMING', 10), json=json_)
            print(a)
    return ontid, None

    #embed()

def main():
    #return
    ppe = ProcessPoolExecutor(4)
    with makeGraph('', {}) as _:
        funs = [fmri_atlases,
               CoCoMac, #cocomac_make,
               MBA, #mouse_brain_atlas,
               HBA, #human_brain_atlas,
               hcp2016_make,
               swanson]
        futures = [ppe.submit(f) for f in funs]
        print('futures compiled')
        fs = [f.result() for f in futures]
        fs = fs[0] + fs[1:]
        parcellation_schemes(fs[:-1])

    # make a protege catalog file to simplify life
    uriline = '  <uri id="User Entered Import Resolution" name="{ontid}" uri="{filename}"/>'
    xmllines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
    '<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">',] + \
    [uriline.format(ontid=f, filename=f.rsplit('/',1)[-1]) for f,_ in fs] + \
    ['  <group id="Folder Repository, directory=, recursive=true, Auto-Update=true, version=2" prefer="public" xml:base=""/>',
    '</catalog>',]
    xml = '\n'.join(xmllines)
    with open('/tmp/catalog-v001.xml','wt') as f:
        f.write(xml)

    # be sure to run
    # find -name '*.ttl.ttl' -exec sh -c 'a=$(echo "$0" | sed -r "s/.ttl$//") && mv "$0" "$a"' {}  \;
    # to move the converted files

if __name__ == '__main__':
    main()

