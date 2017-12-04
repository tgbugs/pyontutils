#!/usr/bin/env python3.6

import os
import csv
import glob
import subprocess
from datetime import date
from collections import namedtuple, defaultdict
import requests
import rdflib
from rdflib.extras import infixowl
from lxml import etree
from hierarchies import creatTree, Query
from utils import TODAY, async_getter, makePrefixes, makeGraph, createOntology, rowParse
from utils import rdf, rdfs, owl, dc, dcterms, skos, prov
from utils import TermColors as tc #TERMCOLORFUNC
from utils import PREFIXES as uPREFIXES
from ilx_utils import ILXREPLACE
from scigraph_client import Vocabulary
from IPython import embed
from process_fixed import ProcessPoolExecutor

WRITELOC = '/tmp/parc/'
GENERATED = 'http://ontology.neuinfo.org/NIF/ttl/generated/'
PARC = GENERATED + 'parcellation/'

commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode()  # FIXME this breaks scripts that import from this file
NOTICE = ' Please see https://github.com/tgbugs/pyontutils/tree/{commit}/parcellation.py for details.'.format(commit=commit)

sgv = Vocabulary(cache=True)

OntMeta = namedtuple('OntMeta',
                     ['path',
                      'filename',
                      'name',
                      'shortname',
                      'comment',
                      'version'])
OntMeta('http://ontology.neuinfo.org/NIF/ttl/',
        'swallows',
        'Python Ontology',
        'PO',
        'Tis a silly place.',
        '-1')

PScheme = namedtuple('PScheme',
                     ['curie',
                      'name',
                      'species',
                      'devstage'])
PScheme('ilx:something',
        'some parcellation scheme concept',
        'NCBITaxon:1234',
        'adult')

PSArtifact = namedtuple('PSArtifact',
                        ['curie',
                         'name',
                         'version',
                         'date',
                         'link',
                         'citation',
                         'synonyms',
                         'acronyms'])
PSArtifact('SCR:something',
           'name name',
           'v1',
           '01/01/01',
           'http://wut.wut',
           'scholarly things',
           tuple(),
           tuple())

# annotationProperties
#PARCLAB = 'ilx:parcellationLabel'
PARCLAB = 'skos:prefLabel'
ACRONYM = 'NIFRID:acronym'
SYNONYM = 'NIFRID:synonym'

# objectProperties
UNTAXON = 'ilx:ancestralInTaxon'
EXTAXON = 'ilx:hasInstanceInTaxon'  # FIXME instances?
EXSPECIES = 'ilx:hasInstanceInSpecies'
DEFTAXON = 'ilx:definedForTaxon'
DEFSPECIES = 'ilx:definedForSpecies'
DEVSTAGE = 'ilx:definedForDevelopmentalStage'
PARTOF = 'ilx:partOf'
HASPART = 'ilx:hasPart'
DELINEATEDBY = 'ilx:delineatedBy'

# classes
ADULT = 'BIRNLEX:681'
atname = 'Parcellation scheme artifact'
ATLAS_SUPER = ILXREPLACE(atname) # 'NIFRES:nlx_res_20090402'  # alternatives?
psname = 'Brain parcellation scheme concept'
PARC_SUPER = ILXREPLACE(psname)

def interlex_namespace(user):
    return 'http://uri.interlex.org/' + user + '/'

def check_hierarchy(graph, root, edge, label_edge=None):
    a, b = creatTree(*Query(root, edge, 'INCOMING', 10), json=graph.make_scigraph_json(edge, label_edge))
    print(a)

def add_ops(graph):
    graph.add_op(EXSPECIES)
    graph.add_op(DEFSPECIES)
    graph.add_op(DEVSTAGE)

def make_scheme(graph, scheme, atlas_id=None, parent=PARC_SUPER):
    graph.add_class(scheme.curie, parent, label=scheme.name)
    graph.add_restriction(scheme.curie, DEFSPECIES, scheme.species)
    graph.add_restriction(scheme.curie, DEVSTAGE, scheme.devstage)
    if atlas_id:
        graph.add_trip(scheme.curie, rdfs.isDefinedBy, atlas_id)

def make_atlas(atlas, parent=ATLAS_SUPER):
    out = [
        (atlas.curie, rdf.type, owl.Class),
        (atlas.curie, rdfs.label, atlas.name),
        (atlas.curie, rdfs.subClassOf, parent),
        (atlas.curie, 'ilx:atlasVersion', atlas.version),  # FIXME
        (atlas.curie, 'ilx:atlasDate', atlas.date),  # FIXME
        (atlas.curie, 'NIFRID:externalSourceURI', atlas.link),  # FXIME probably needs to be optional...
        (atlas.curie, 'NIFRID:definingCitation', atlas.citation),
    ] + \
    [(atlas.curie, SYNONYM, syn) for syn in atlas.synonyms] + \
    [(atlas.curie, ACRONYM, ac) for ac in atlas.acronyms]

    return out

def add_triples(graph, struct, struct_to_triples, parent=None):
    if not parent:
        [graph.add_trip(*triple) for triple in struct_to_triples(struct)]
    else:
        [graph.add_trip(*triple) for triple in struct_to_triples(struct, parent)]

def parcellation_schemes(ontids_atlases):
    ont = OntMeta(GENERATED,
                  'parcellation',
                  'NIF collected parcellation schemes ontology',
                  'NIF Parcellations',
                  'Brain parcellation schemes as represented by root concepts.',
                  TODAY)
    ontid = ont.path + ont.filename + '.ttl'
    PREFIXES = makePrefixes('', 'ilx', 'owl', 'skos', 'NIFRID', 'ILXREPLACE')
    graph = makeGraph(ont.filename, PREFIXES, writeloc=WRITELOC)
    graph.add_ont(ontid, *ont[2:])

    for import_id, atlas in sorted(ontids_atlases):
        graph.add_trip(ontid, owl.imports, import_id)
        add_triples(graph, atlas, make_atlas)

    graph.add_class(ATLAS_SUPER, label=atname)

    graph.add_class(PARC_SUPER, label=psname)
    graph.write()


class genericPScheme:
    ont = OntMeta
    concept = PScheme
    atlas = PSArtifact
    PREFIXES = makePrefixes('', 'ilx', 'owl', 'skos', 'BIRNLEX', 'NCBITaxon', 'ILXREPLACE')

    def __new__(cls, validate=False):
        error = 'Expected %s got %s' 
        if type(cls.ont) != OntMeta:
            raise TypeError(error % (OntMeta, type(cls.ont)))
        elif type(cls.concept) != PScheme:
            raise TypeError(error % (PScheme, type(cls.concept)))
        elif type(cls.atlas) != PSArtifact:
            raise TypeError(error % (PSArtifact, type(cls.atlas)))
            
        ontid = cls.ont.path + cls.ont.filename + '.ttl'
        PREFIXES = {k:v for k, v in cls.PREFIXES.items()}
        PREFIXES.update(genericPScheme.PREFIXES)
        #if '' in cls.PREFIXES:  # NOT ALLOWED!
            #if PREFIXES[''] is None:
                #PREFIXES[''] = ontid + '/'
        graph = makeGraph(cls.ont.filename, PREFIXES, writeloc=WRITELOC)
        graph.add_ont(ontid, *cls.ont[2:])
        make_scheme(graph, cls.concept, cls.atlas.curie)
        data = cls.datagetter()
        cls.datamunge(data)
        cls.dataproc(graph, data)
        add_ops(graph)
        graph.write()
        if validate or getattr(cls, 'VALIDATE', False):
            cls.validate(graph)
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
            graph.add_trip(*thing)
        raise NotImplementedError('You need to implement this yourlself!')

    @classmethod
    def validate(cls, graph):
        """ Put any post validation here. """
        raise NotImplementedError('You need to implement this yourlself!')


class HBA(genericPScheme):
    ont = OntMeta(PARC,
                  'hbaslim',
                  'Allen Human Brain Atlas Ontology',
                  'HBA 2013 v2',
                  'This file is automatically generated from the Allen Brain Atlas API.' + NOTICE,
                  TODAY)
    concept = PScheme(ILXREPLACE(ont.name),
                      'Allen Human Brain Atlas parcellation concept',
                      'NCBITaxon:9606',
                      ADULT)
    atlas = PSArtifact(ILXREPLACE(ont.name + 'atlas'),
                       'Allen Human Brain Atlas v2',
                       '2013 v2',
                       'October 2013',
                       'http://human.brain-map.org/',
                       'http://help.brain-map.org/download/attachments/2818165/HBA_Ontology-and-Nomenclature.pdf?version=1&modificationDate=1382051847989',
                       tuple(),
                       tuple())
    PREFIX = 'HBA'
    PREFIXES = makePrefixes('NIFRID')
    PREFIXES[PREFIX] = 'http://api.brain-map.org:80/api/v2/data/Structure/'  # FIXME hack to allow both HBA and MBA 
    ROOT = 3999
    #VALIDATE = True

    @classmethod
    def datagetter(cls):
        url = 'http://api.brain-map.org/api/v2/tree_search/Structure/{root}.json?descendants=true'.format(root=cls.ROOT)
        resp = requests.get(url).json()
        return resp['msg']

    @classmethod
    def dataproc(cls, graph, data):
        for node in data:
            curie = graph.expand(cls.PREFIX + ':' + str(node['id']))
            graph.add_class(curie, cls.concept.curie)
            parent = node['parent_structure_id']
            graph.add_trip(curie, rdfs.label, '(%s) ' % cls.ont.shortname + node['name'])
            graph.add_trip(curie, PARCLAB, node['name'])
            graph.add_trip(curie, ACRONYM, node['acronym'])
            if node['safe_name'] != node['name']:
                graph.add_trip(curie, SYNONYM, node['safe_name'])
            if parent:
                pcurie = graph.expand(cls.PREFIX + ':' + str(parent))
                graph.add_restriction(curie, PARTOF, pcurie)

    @classmethod
    def validate(cls, graph):
        check_hierarchy(graph, cls.PREFIX + ':' + str(cls.ROOT), PARTOF, PARCLAB)


class MBA(HBA):
    ont = OntMeta(PARC,
                  'mbaslim',
                  'Allen Mouse Brain Atlas Ontology',
                  'MBA 2011 v2',
                  'This file is automatically generated from the Allen Brain Atlas API.' + NOTICE,
                  TODAY)
    concept = PScheme(ILXREPLACE(ont.name),
                      'Allen Mouse Brain Atlas parcellation concept',
                      'NCBITaxon:10090',
                      ADULT)
    atlas = PSArtifact(ILXREPLACE(ont.name + 'atlas'),
                       'Allen Mouse Brain Atlas v2',
                       '2011 v2',
                       'November 2011',
                       'http://mouse.brain-map.org/static/atlas',
                       'http://help.brain-map.org/download/attachments/2818169/AllenReferenceAtlas_v2_2011.pdf?version=1&modificationDate=1319667383440',  # yay no doi! wat
                       tuple(),
                       tuple())
    PREFIX = 'MBA'
    PREFIXES = makePrefixes('NIFRID')
    PREFIXES[PREFIX] = 'http://api.brain-map.org/api/v2/data/Structure/'  # FIXME hack to allow both HBA and MBA 
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
    ont = OntMeta(PARC,
                  'cocomacslim',
                  'CoCoMac terminology',
                  'CoCoMac',
                  ('This file is automatically generated from the CoCoMac '
                   'database on the terms from BrainMaps_BrainSiteAcronyms.' + NOTICE),
                  TODAY)
    concept = PScheme(ILXREPLACE(ont.name),
                       'CoCoMac terminology parcellation concept',
                       'NCBITaxon:9544',
                       'ilx:various')
    atlas = PSArtifact(ILXREPLACE(ont.name + 'atlas'),
                        'CoCoMac terminology',
                        None, #'no version info',
                        None, #'no date',
                        'http://cocomac.g-node.org',
                        'scholarly things',
                        tuple(),
                        tuple())

    PREFIXES = makePrefixes('NIFRID')
    PREFIXES['cocomac'] = 'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT%20*%20from%20BrainMaps_BrainSiteAcronyms%20where%20ID='  # looking for better options

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
                graph.add_trip(self.identifier, ACRONYM, value)

            def FullName(self, value):
                graph.add_trip(self.identifier, rdfs.label, '(%s) ' % cls.ont.shortname + value)
                graph.add_trip(self.identifier, PARCLAB, value)

            def LegacyID(self, value):
                graph.add_trip(self.identifier, ACRONYM, value)

            def BrainInfoID(self, value):
                pass

        cocomac(data)


class HCP(genericPScheme):
    source = 'resources/human_connectome_project_2016.csv'
    ont = OntMeta(PARC,
                  'hcp_parcellation',
                  ('Human Connectome Project Multi-Modal '
                   'human cortical parcellation'),
                  'HCP-MMP1.0',
                  'This file is automatically generated from ' + source + '.' + NOTICE,
                  TODAY)
    concept = PScheme(ILXREPLACE(ont.name),
                      'HCP parcellation concept',
                      'NCBITaxon:9606',
                      ADULT)
    atlas = PSArtifact(ILXREPLACE(ont.name + 'atlas'),
                       'Human Connectome Project Multi-Modal human cortical parcellation',
                       '1.0',
                       '20-07-2016',  # d-m-y
                       'awaiting...',
                       'doi:10.1038/nature18933',
                       ('Human Connectome Project Multi-Modal Parcellation', 'HCP Multi-Modal Parcellation','Human Connectome Project Multi-Modal Parcellation version 1.0'),
                       ('HCP_MMP', ont.shortname))
    # see also https://balsa.wustl.edu/study/show/RVVG
    PREFIXES = makePrefixes('NIFRID')
    PREFIXES['HCPMMP'] = interlex_namespace('hcpmmp/uris/labels')

    @classmethod
    def datagetter(cls):
        with open(cls.source, 'rt') as f:
            data = [r for r in csv.reader(f)]
        return data

    @classmethod
    def dataproc(cls, graph, data):

        class hcp2016(rowParse):
            def Parcellation_Index(self, value):
                self.id_ = value
                self.id_ = 'HCPMMP:' + value  # safe because reset every row (ish)
                graph.add_class(self.id_, cls.concept.curie)

            def Area_Name(self, value):
                value = value.strip()
                graph.add_trip(self.id_, ACRONYM, value)

            def Area_Description(self, value):
                value = value.strip()
                graph.add_trip(self.id_, rdfs.label, '(%s) ' % cls.ont.shortname + value)
                graph.add_trip(self.id_, PARCLAB, value)

            def Newly_Described(self, value):
                if value == 'Yes*' or value == 'Yes':
                    graph.add_trip(self.id_, 'NIFRID:definingCitation', 'Glasser and Van Essen 2016')

            def Results_Sections(self, value):
                pass

            def Other_Names(self, value):
                for name in value.split(','):
                    name = name.strip()
                    if name:
                        if len(name) <= 3:
                            graph.add_trip(self.id_, ACRONYM, name)
                        else:
                            graph.add_trip(self.id_, SYNONYM, name)
                
            def Key_Studies(self, value):
                for study in value.split(','):
                    study = study.strip()
                    if study:
                        graph.add_trip(self.id_, 'NIFRID:definingCitation', study)

        hcp2016(data)


class PAXRAT6(genericPScheme):
    source = 'resources/paxinos09names.txt'
    ont = OntMeta(PARC,
                  'paxinos_r_s_6',
                  'Paxinos Rat Parcellation 6th',
                  'PAXRAT6',
                  'This file is automatically generated from ' + source + '.' + NOTICE,
                  TODAY)
    concept = PScheme(ILXREPLACE(ont.name),
                      'Paxinos Rat Stereological 6th Ed parcellation concept',
                      'NCBITaxon:10116',
                      ADULT)
    atlas = PSArtifact(ILXREPLACE(ont.name + 'atlas'),
                       'The Rat Brain in Stereotaxic Coordinates 6th Edition',
                       '6th',
                       '02-11-2006',  # d-m-y
                       None,  # the fact this is missing is very big problem :/
                       ('Paxinos, George, Charles RR Watson, and Piers C. Emson.'
                        ' "AChE-stained horizontal sections of the rat brain'
                        ' in stereotaxic coordinates." Journal of neuroscience'
                        ' methods 3, no. 2 (1980): 129-149.'),  # FIXME
                       ('Paxinos Rat 6th',),
                       tuple())
    PREFIXES = makePrefixes('NIFRID')
    PREFIXES['PAXRAT'] = interlex_namespace('paxinos/uris/rat/labels')

    @classmethod
    def datagetter(cls):
        with open(cls.source, 'rt') as f:
            lines = [l.rsplit('#')[0].strip() for l in f.readlines() if not l.startswith('#')]

        return [l.rsplit(' ',1) for l in lines]

    @classmethod
    def dataproc(cls, graph, data):
        for i, (label, abrv) in enumerate(data):
            id_ = 'PAXRAT:' + str(i + 1)
            display = '(%s) ' % cls.ont.shortname + label
            graph.add_class(id_, cls.concept.curie, label=display)
            graph.add_trip(id_, PARCLAB, label)
            graph.add_trip(id_, ACRONYM, abrv)  # FIXME these are listed as abbreviations in the text


class WHSSD(genericPScheme):
    source = 'resources/WHS_SD_rat_atlas_v2.label'
    ont = OntMeta(PARC,
                  'whs_sd_2',
                  'Waxholm Space Sprague Dawley Ontology',
                  'WHS SD v2',
                  'This file is automatically generated from ' + source + '.' + NOTICE,
                  TODAY)
    concept = PScheme(ILXREPLACE(ont.name),
                      'Waxholm Space Sprague Dawley parcellation concept',
                      'NCBITaxon:10116',  # TODO
                      ADULT)  # TODO
    atlas = PSArtifact(ILXREPLACE(ont.name + 'atlas'),
                       'Sprague Dawley Atlas v2',
                       'v2',
                       '02-02-2015',  # d-m-y
                       'https://scalablebrainatlas.incf.org/rat/PLCJB14',  # FIXME... this seems... off...
                       'halp!',  # FIXME
                       ('WHS SD',ont.shortname),
                       tuple())
    PREFIXES = {
        #'':ont.path + ont.filename + '.ttl/',  # FIXME
        'WHSSD':interlex_namespace('waxholm/uris/sd/labels')
    }

    @classmethod
    def datagetter(cls):
        with open(cls.source, 'rt') as f:
            lines = [l.strip() for l in f.readlines() if not l.startswith('#')]
        rows = [(l[:3].strip(), l.split('"',1)[1].strip('"')) for l in lines]
        return rows

    @classmethod
    def dataproc(cls, graph, data):
        for index, label in data:
            id_ = 'WHSSD:' + str(index)
            display = '(%s) ' % cls.ont.shortname + label
            graph.add_class(id_, cls.concept.curie, label=display)
            graph.add_trip(id_, PARCLAB, label)

class FMRI(genericPScheme):
    PREFIXES = makePrefixes('', 'skos', 'ILXREPLACE')

    @classmethod
    def datagetter(cls):
        data = cls.DATA
        return data

    @classmethod
    def dataproc(cls, graph, data):
        for node in data:
            id_ = 'ATLAS:' + node.get('index')
            label = node.text
            display = '(%s) ' % cls.ont.shortname + label
            graph.add_class(id_, cls.concept.curie, label=display)
            graph.add_trip(id_, PARCLAB, label)


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

    interlex_base = interlex_namespace('fsl/uris/atlases')

    comment = 'This file is automatically generated from the %s file in the FSL atlas collection.' + NOTICE
    ontids = []
    atlases = []
    for xmlfile in glob.glob(ATLAS_PATH + '*.xml'):
        tree = etree.parse(xmlfile)
        name = tree.xpath('header//name')[0].text
        cname = name + ' concept' if name.endswith('parcellation') else name + ' parcellation concept'
        shortname = tree.xpath('header//shortname')
        if shortname:
            shortname = shortname[0].text
        else:
            shortname = shortnames[name]

        filename = os.path.splitext(os.path.basename(xmlfile))[0]

        PREFIXES = {k:v for k, v in FMRI.PREFIXES.items()}
        PREFIXES.update({'ATLAS': interlex_base + filename + '/labels/'})

        classdict = dict(
        ont = OntMeta(PARC,
                      filename,
                      name, 
                      shortname,
                      comment % xmlfile,
                      TODAY),
        concept = PScheme(ILXREPLACE(name),
                          cname,
                          'NCBITaxon:9606',
                          ADULT),
        atlas = PSArtifact(ILXREPLACE(name + 'atlas'),
                           name,
                           None, #'no version info',
                           None, #'date unknown',
                           'http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases',
                           None, #'http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases',  # TODO: there are MANY defining citations for these...
                           tuple(),
                           (shortname,) if shortname else tuple()),
        DATA = tree.xpath('data//label'),
        PREFIXES = PREFIXES)

        tempclass = type('tempclass', (FMRI,), classdict)
        ontid, atlas_ = tempclass()

        #print([(l.get('index'),l.text) for l in tree.xpath('data//label')])
        ontids.append(ontid)
        atlases.append(atlas_)

    return [_ for _ in zip(ontids, atlases)]

def swanson():
    """ not really a parcellation scheme """
    source = 'resources/swanson_aligned.txt'
    ONT_PATH = GENERATED
    filename = 'swanson_hierarchies'
    ontid = ONT_PATH + filename + '.ttl'
    PREFIXES = makePrefixes('', 'ilx', 'owl', 'skos', 'NIFRID', 'ILXREPLACE')
    PREFIXES.update({
        #'':ontid + '/',  # looking for better options
        'SWAN':interlex_namespace('swanson/uris/neuroanatomical-terminology/terms/'),
        'SWAA':interlex_namespace('swanson/uris/neuroanatomical-terminology/appendix/'),
    })
    new_graph = makeGraph(filename, PREFIXES, writeloc=WRITELOC)
    new_graph.add_ont(ontid,
                      'Swanson brain partomies',
                      'Swanson 2014 Partonomies',
                      'This file is automatically generated from ' + source + '.' + NOTICE,
                      TODAY)

    # FIXME citations should really go on the ... anatomy? scheme artifact
    definingCitation = 'Swanson, Larry W. Neuroanatomical Terminology: a lexicon of classical origins and historical foundations. Oxford University Press, USA, 2014.'
    definingCitationID = 'ISBN:9780195340624'
    new_graph.add_trip(ontid, 'NIFRID:definingCitation', definingCitation)
    new_graph.add_trip(ontid, 'NIFRID:definingCitationID', definingCitationID)
            
    with open(source, 'rt') as f:
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
    nbase = PREFIXES['SWAN'] + '%s' 
    json_ = {'nodes':[],'edges':[]}
    parent = ILXREPLACE('swansonBrainRegionConcept')
    for node, anns in sp.nodes.items():
        nid = nbase % node
        new_graph.add_class(nid, parent, label=anns['label'])
        new_graph.add_trip(nid, 'NIFRID:definingCitation', anns['citation'])
        json_['nodes'].append({'lbl':anns['label'],'id':'SWA:' + str(node)})
        #if anns['uberon']:
            #new_graph.add_trip(nid, owl.equivalentClass, anns['uberon'])  # issues arrise here...

    for appendix, data in sp.appendicies.items():
        aid = PREFIXES['SWAA'] + str(appendix)
        new_graph.add_class(aid, label=data['name'].capitalize())
        new_graph.add_trip(aid, 'ilx:hasTaxonRank', data['taxon'])  # FIXME appendix is the data artifact...
        children = data['children']
        ahp = HASPART + str(appendix)
        apo = PARTOF + str(appendix)
        new_graph.add_op(ahp, transitive=True)
        new_graph.add_op(apo, inverse=ahp, transitive=True)
        for parent, childs in children.items():  # FIXME does this give complete coverage?
            pid = nbase % parent
            for child in childs:
                cid = nbase % child
                new_graph.add_restriction(pid, ahp, cid)  # note hierarhcy inverts direction
                new_graph.add_restriction(cid, apo, pid)
                json_['edges'].append({'sub':'SWA:' + str(child),'pred':apo,'obj':'SWA:' + str(parent)})

    new_graph.write()
    if False:
        Query = namedtuple('Query', ['root','relationshipType','direction','depth'])
        mapping = (1, 1, 1, 1, 30, 83, 69, 70, 74, 1)  # should generate?
        for i, n in enumerate(mapping):
            a, b = creatTree(*Query('SWA:' + str(n), 'ilx:partOf' + str(i + 1), 'INCOMING', 10), json=json_)
            print(a)
    return ontid, None

    #embed()

def main():
    if not os.path.exists(WRITELOC):
        os.mkdir(WRITELOC)

    with ProcessPoolExecutor(4) as ppe:
        funs = [fmri_atlases,
                CoCoMac, #cocomac_make,
                MBA, #mouse_brain_atlas,
                HBA, #human_brain_atlas,
                HCP, #hcp2016_make,
                PAXRAT6,
                WHSSD,
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

#
# paxinos

def paxinos():
    from desc.prof import profile_me
    from pysercomb.parsers.pax import sections
    with open('resources/pax-4th-ed-indexes.txt', 'rt') as f:
        four = f.read()
    with open('resources/pax-6th-ed-indexes.txt', 'rt') as f:
        six = f.read()
    @profile_me
    def test():
        return sections(four), sections(six)
    #test4, test6 = test()

    with open(os.path.expanduser('~/ni/nifstd/paxinos/tree.txt'), 'rt') as f:
        tree = f.read()

    def parse_tree():
        lines = [l for l in tree.split('\n') if l]
        out = {}
        recs = []
        parent_stack = [None]
        old_depth = 0
        for l in lines:
            depth, abbrev, _, name = l.split(' ', 3)
            depth = len(depth)
            if old_depth < depth:  # don't change
                parent = parent_stack[-1]
                parent_stack.append(abbrev)
                old_depth = depth
            elif old_depth == depth:
                if len(parent_stack) - 1 > depth:
                    parent_stack.pop()
                parent = parent_stack[-1]
                parent_stack.append(abbrev)
            elif old_depth > depth:  # bump back
                for _ in range(old_depth - depth + 1):
                    parent_stack.pop()
                parent = parent_stack[-1]
                parent_stack.append(abbrev)
                old_depth = depth

            struct = None if name == '-------' else name
            o = (depth, abbrev, struct, parent)
            recs.append(o)
            out[abbrev] = ([struct], (), parent)
        return recs, out
    trecs, tr = parse_tree()
    assert len(tr) == len(trecs), 'Abbreviations in tr are not unique!'

    @profile_me
    def fast(t):
        a, b = t.split('List of Structures')
        if not a:
            los, loa = b.split('List of Abbreviations')
        else:
            los = b
            _, loa = a.split('List of Abbreviations')

        sr = []
        for l in los.split('\n'):
            if l and not l[0] == ';':
                if ';' in l:
                    l, *comment = l.split(';')
                    l = l.strip()
                    print(l, comment)
                struct, abbrev = l.rsplit(' ', 1)
                sr.append((abbrev, struct))
        ar = []
        for l in loa.split('\n'):
            if l and not l[0] == ';':
                if ';' in l:
                    l, *comment = l.split(';')
                    l = l.strip()
                    print(l, comment)
                abbrev, rest = l.split(' ', 1)
                parts = rest.split(' ')
                #print(parts)
                for i, pr in enumerate(parts[::-1]):
                    #print(i, pr)
                    z = pr[0].isdigit()
                    if not z or i > 0 and z and pr[-1] != ',':
                        break
                struct = ' '.join(parts[:-i])
                figs = tuple(tuple(int(_) for _ in p.split('-'))
                             if '-' in p
                             else (tuple(f'{nl[:-1]}{l}'
                                        for nl, *ls in p.split(',')
                                        for l in (nl[-1], *ls))
                                   if ',' in p or p[-1].isalpha()
                                   else int(p))
                             for p in (_.rstrip(',') for _ in parts[-i:]))
                figs = tuple(f for f in figs if f)  # zero marks abbrevs in index that are not in figures
                #print(struct)
                ar.append((abbrev, struct, figs))
        return sr, ar

    def missing(a, b):
        am = a - b
        bm = b - a
        return am, bm

    def check(t):
        sr, ar = fast(t)
        sabs = set(_[0] for _ in sr)
        aabs = set(_[0] for _ in ar)
        ssts = set(_[1] for _ in sr)
        asts = set(_[1] for _ in ar)
        ar2 = set(_[:2] for _ in ar)
        aam, sam = missing(aabs, sabs)
        asm, ssm = missing(asts, ssts)
        ar2m, sr2m = missing(ar2, set(sr))
        print('OK to skip')
        print(sorted(aam))
        print('Need to be created')
        print(sorted(sam))
        print()
        print(sorted(asm))
        print()
        print(sorted(ssm))
        print()
        #print(sorted(ar2m))
        #print()
        #print(sorted(sr2m))
        #print()
        out = {}
        for a, s, f in ar:
            if a not in out:
                out[a] = ([s], f)
            else:
                if s not in out[a][0]:
                    print(f'Found new label from ar for {a}:\n{s}\n{out[a][0]}')
                    out[a][0].append(s)
        for a, s in sr:
            if a not in out:
                out[a] = ([s], tuple())
            else:
                if s not in out[a][0]:
                    print(f'Found new label from sr for {a}:\n{s}\n{out[a][0]}')
                    out[a][0].append(s)
                    #raise TypeError(f'Mismatched labels on {a}: {s} {out[a][0]}')
        return sr, ar, out

    sr4, ar4, fr = check(four)
    # abbreviations 1-10 in 4th are not unique
    one_to_ten_contexts = ('cortical layer',
                           'spinal cord layer',
                           'cerebellar folium',
                           'cranial nerve nucleus')
    sr6, ar6, sx = check(six)
    sx2 = {a:([s], ()) for s, a in PAXRAT6.datagetter()}
    sfr = set(fr)
    ssx = set(sx)
    ssx2 = set(sx2)
    str_ = set(tr)
    in_four_not_in_six = sfr - ssx
    in_six_not_in_four = ssx - sfr
    in_tree_not_in_six = str_ - ssx
    in_six_not_in_tree = ssx - str_
    in_six2_not_in_six = ssx2 - ssx
    in_six_not_in_six2 = ssx - ssx2

    print(len(in_four_not_in_six), len(in_six_not_in_four),
          len(in_tree_not_in_six), len(in_six_not_in_tree),
          len(in_six2_not_in_six), len(in_six_not_in_six2),
         )
    for a, ((s), _, p) in tr.items():
        if a in sx:
            if s[0] not in sx[a][0]:
                print(f'Found new label from tr for {a}:\n{s}\n{sx[a][0]}')
    for a, ((s), _) in sx2.items():
        if a in sx:
            if s[0] not in sx[a][0]:
                print(f'Found new label from sx2 for {a}:\n{s}\n{sx[a][0]}')

    tree_no_name = {_:tr[_] for _ in sorted(in_tree_not_in_six) if not tr[_][0][0]}
    tree_with_name = {_:tr[_] for _ in sorted(in_tree_not_in_six) if tr[_][0][0]}
    not_in_tree_with_figures = {_:sx[_] for _ in sorted(in_six_not_in_tree) if sx[_][-1]}
    a = f'{"abv":<25} | {"structure name":<60} | parent abv\n' + '\n'.join(f'{k:<25} | {v[0][0]:<60} | {v[-1]}' for k, v in tree_with_name.items())
    b = f'{"abv":<25} | {"structure name":<15} | parent abv\n' + '\n'.join(f'{k:<25} | {"":<15} | {v[-1]}' for k, v in tree_no_name.items())
    c = f'abv    | {"structure name":<60} | figures (figure ranges are tuples)\n' + '\n'.join(f'{k:<6} | {v[0][0]:<60} | {v[-1]}' for k, v in not_in_tree_with_figures.items())
    with open(os.path.expanduser('~/ni/nifstd/paxinos/tree-with-name.txt'), 'wt') as f: f.write(a)
    with open(os.path.expanduser('~/ni/nifstd/paxinos/tree-no-name.txt'), 'wt') as f: f.write(b)
    with open(os.path.expanduser('~/ni/nifstd/paxinos/not-in-tree-with-figures.txt'), 'wt') as f: f.write(c)
    match_name_not_abrev = set(v[0][0] for v in tree_with_name.values()) & set(v[0][0] for v in sx.values())
    embed()


class PAX_Labels(genericPScheme):
    sources = {'resources/paxinos09names.txt':6,
               'resources/pax-6th-ed-indexes.txt':6,
               os.path.expanduser('~/ni/nifstd/paxinos/tree.txt'):6,
               'resources/pax-4th-ed-indexes.txt':4}
    graph = createOntology(filename='paxinos-rat-labels',
                           name='Paxinos Rat Parcellation Labels',
                           #prefixes=
                           comment='',
                           shortname='paxrat6',
                           path='ttl/generated/parcellation/')

#
# New impl

# namespaces
NIFRID = rdflib.Namespace(uPREFIXES['NIFRID'])
ilxrt = rdflib.Namespace(uPREFIXES['ilxrt'])

# classes
class Class:
    rdfType = owl.Class
    propertyMapping = dict(
        rdfs_lable=rdfs.label,
        label=skos.prefLabel,
        synonyms=NIFRID.synonym,
        abbrevs=NIFRID.abbrev,
        version=None,
        shortname=None,  # use NIFRID:acronym originally probably need something better
        species=None,
        devstage=None,
        source=dc.source,  # replaces NIFRID.externalSourceURI?
        # things that go on classes namely artifacts
        # documentation of where the exact information came from
        # documentation from the source about how the provenance was generated
        #NIFRID.definingCitation
    )
    _kwargs = None
    def __init__(*args, **kwargs):
        self.args = args
        if self._kwargs:
            for kw, arg in self._kwargs.items():
                if kw in kwargs:
                    arg = kwargs[kw]
                setattr(self, kw, arg)
        else:
            for kw, arg in kwargs:
                setattr(self, kw, arg)

    @property
    def triples(self):
        yield self.iri, rdf.Type, owl.Class
        for key, value in self.__dict__.items():
            if key in self.propertyMapping:
                predicate = self.propertyMapping[key]
                if value is not None:
                    if type(value) != str and hasattr(value, '__iter__'):  # FIXME do generators have __iter__?
                        for v in value:
                            yield self.iri, predicate, v
                    else:
                        yield self.iri, predicate, value


class Artifact(Class):
    iri = ilxrt.parcellationArtifact
    _kwargs = dict(iri=None,
                   label=None,
                   synonyms=tuple(),
                   abbrevs=tuple(),
                   shortname=None,
                   date=None,
                   version=None,
                   species=None,
                   devstage=None,
                   source=None,
                  )
    propertyMapping = dict(
        version=dcterms,
        date=dc.date,
        source=dc.sorce,  # use for links to
        # ilxr.atlasDate
        # ilxr.atlasVersion
    )
    def ___init___(self, **kwargs):

        self.iri = iri
        self.label = label
        self.synonyms = synonyms
        self.abbrevs = abbrevs
        self.version = version
        self.shortname = shortname
        self.species = species
        self.devstage = devstage


class Terminology(Artifact):
    """ A source for parcellation information that applies to one
        or more spatial sources, but does not itself contain the
        spatial definitions. For example Allen MBA. """
    iri = ilxrt.parcellationTerminology


class Atlas(Artifact):
    """ Atlases are may define a terminology themselves, or """
    iri = ilxrt.parcellationAtlas


class LabelRoot(Class):
    """ Parcellation labels are strings characthers sometimes associated
        with a unique identifier, such as an index number or an iri. """
    """ Base class for labels from a common source that should live in one file """
    # use this to define the common superclass for a set of labels
    iri = ilxrt.parcellationLabel
    _kwargs = dict(iri=None,
                   label=None,
                   shortname=None,  # used to construct the rdfs:label
                   definingArtifacts=tuple(),  # leave blank if defined for the parent class
                  )


class Label(Class):
    # allen calls these Structures (which is too narrow because of ventricles etc)
    _kwargs = dict(labelRoot=None,
                   label=None,  # this will become the skos:prefLabel
                   altLabel=None,
                   synonyms=tuple(),
                   abbrevs=tuple(),
                   definingArtifacts=tuple(),  # leave blank if defined for the parent class, needed for paxinos
                  )
    def __init__(self,
                 usedInArtifacts=tuple(),  # leave blank if 1:1 map between labelRoot and use artifacts NOTE even MBA requires validate on this
                 **kwargs
                ):
        super().__init__(**kwargs)
        self.usedInArtifacts = list(usedInArtifact)

    def usedInArtifact(self, artifact):
        self.usedInArtifacts.append(artifact)

    @property
    def rdfs_label(self):
        return self.label + '(' + self.labelRoot.shortname + ')'


class RegionRoot(Class):
    """ Parcellation regions are 'anatomical entities' that are equivalent some
    part of a real biological system and are equivalent to an intersection
    between a parcellation label and a specific version of an atlas that
    defines that label and a difinitive (0, 1, or probabilistics) way to
    determine whether a particular sample corresponds to that region. """
    iri = ilxrt.parcellationRegion
    _kwargs = dict(iri=None,
                   atlas=None,  # : Atlas
                   labelRoot=None)  # : LabelRoot


class Region(Class):
    iri = ilxrt.parcellationRegion
    def __init__(self,
                 regionRoot,
                 label):
        self.atlas = regionRoot.atlas
        self.label = label.label

#
# ontologies

class Ont:
    rdfType = owl.Ontology
    iri = None
    comment = None  # about how the file was generated, nothing about what it contains
    version = TODAY
    propertyMapping = dict(
        sources=prov.wasDerivedFrom,  # the direct source file(s)
    )
    def __init__(*args, **kwargs):
        self.graph = rdflib.Graph()


class parcBase(Ont):
    """ Import everything and bridging """
    labelRoot = LabelRoot
    regionRoot = RegionRoot
    atlasRoot = AtlasRoot


class Artifacts(Ont):
    """ An ontology file containing all the parcellation scheme artifacts. """
    path = 'ttl/generated/'
    filename = 'parcellation-artifacts'
    name = 'Parcellation Artifacts'
    prefixes = {}
    comment = ('Parcellation artifacts are the defining information sources for '
               'parcellation labels and/or atlases in which those labels are used.')
    def __init__(self, artifacts):
        self.artifacts = artifacts


class LabelsBase(Ont):  # this replaces genericPScheme
    """ An ontology file containing parcellation labels from a common source. """
    iri = None
    source_artifacts = tuple()
    root = None  # : LabelRoot 
    filename = None
    name = None
    prefixes = {}
    comment = None


class RegionsBase(Ont):
    """ An ontology file containing parcellation regions from the
        intersection of an atlas artifact and a set of labels. """
    # TODO find a way to allow these to serialize into one file
    iri = None
    atlas = None
    labelRoot = None
    def __init__(self):
        self.regionRoot = RegionRoot(atlas=self.atlas,
                                     labelRoot=self.labelRoot)


def main():
    pass

if __name__ == '__main__':
    main()

