#!/usr/bin/env python3.6
from collections import namedtuple
import requests
from pyontutils.core import makeGraph
from pyontutils.core import rdfs
from pyontutils.utils import TODAY, rowParse
from pyontutils.ilx_utils import ILXREPLACE
from pyontutils.namespaces import makePrefixes

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
PScheme('ilxtr:something',
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

PARCLAB = 'skos:prefLabel'
ACRONYM = 'NIFRID:acronym'

UNTAXON = 'ilxtr:ancestralInTaxon'
EXTAXON = 'ilxtr:hasInstanceInTaxon'  # FIXME instances?
EXSPECIES = 'ilxtr:hasInstanceInSpecies'
DEFTAXON = 'ilxtr:definedForTaxon'
DEFSPECIES = 'ilxtr:definedForSpecies'
DEVSTAGE = 'ilxtr:definedForDevelopmentalStage'
PARTOF = 'ilxtr:partOf'
HASPART = 'ilxtr:hasPart'
DELINEATEDBY = 'ilxtr:delineatedBy'

# classes
ADULT = 'BIRNLEX:681'
atname = 'Parcellation scheme artifact'
ATLAS_SUPER = ILXREPLACE(atname) # 'NIFRES:nlx_res_20090402'  # alternatives?
psname = 'Brain parcellation scheme concept'
PARC_SUPER = ILXREPLACE(psname)

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
        (atlas.curie, 'ilxtr:atlasVersion', atlas.version),  # FIXME
        (atlas.curie, 'ilxtr:atlasDate', atlas.date),  # FIXME
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
                  TODAY())
    ontid = ont.path + ont.filename + '.ttl'
    PREFIXES = makePrefixes('ilxtr', 'owl', 'skos', 'NIFRID', 'ILXREPLACE')
    graph = makeGraph(ont.filename, PREFIXES, writeloc='/tmp/')
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
    PREFIXES = makePrefixes('ilxtr', 'owl', 'skos', 'BIRNLEX', 'NCBITaxon', 'ILXREPLACE')

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
        graph = makeGraph(cls.ont.filename, PREFIXES, writeloc='/tmp/')
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


class CoCoMac(genericPScheme):
    ont = OntMeta('http://ontology.neuinfo.org/NIF/ttl/generated/parcellation/',
                  'cocomacslim',
                  'CoCoMac terminology',
                  'CoCoMac',
                  ('This file is automatically generated from the CoCoMac '
                   'database on the terms from BrainMaps_BrainSiteAcronyms.' + '**FIXME**'),
                  TODAY())
    concept = PScheme(ILXREPLACE(ont.name),
                       'CoCoMac terminology parcellation concept',
                       'NCBITaxon:9544',
                       'ilxtr:various')
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


def main():
    CoCoMac()

if __name__ == '__main__':
    main()
