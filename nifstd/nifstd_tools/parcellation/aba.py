import requests
import nifstd_tools.parcellation as parc
from pyontutils.core import Source, LabelsBase, Collector, build
from pyontutils.utils import Async, deferred
from pyontutils.namespaces import makePrefixes
from pyontutils.namespaces import NCBITaxon, UBERON, NIFRID, ilx, ilxtr, TEMP
from pyontutils.namespaces import HBA, MBA, DHBA, DMBA, ilxHBA, ilxMBA, ilxDHBA, ilxDMBA, AIBS
from pyontutils.combinators import restriction
from nifstd_tools.parcellation import parcCore, LabelRoot, Label, Terminology
from pyontutils.closed_namespaces import rdf, rdfs, owl, dc, dcterms, skos, prov

# TODO! there is way more metadata that we need to provide here...
# proof that staging is a good idea -- we can can reuse allen's numbers
# and have a readable version
def getOnts():
    # generate everything from these two so that they stay up to date
    # http://help.brain-map.org/display/api/Atlas+Drawings+and+Ontologies
    func = lambda url: requests.get(url).json()['msg']
    query = 'http://api.brain-map.org/api/v2/data/query.json?criteria=model::{model}'
    models = 'Atlas', 'Ontology', 'ReferenceSpace'
    res = Async(rate=10)(deferred(func)(query.format(model=model))
                         for model in models)

    _Atlas, _Ontology, _ReferenceSpace = res

    # FIXME looks like this API  changed

    onts = {o['id']:o for o in _Ontology}
    refs = {r['id']:r for r in _ReferenceSpace}
    refs[None] = None
    onts[None] = None
    want_onts = set()
    # ontology metadata
    for at in _Atlas:
        at['name']
        at['description']
        ref = refs[at['reference_space_id']]
        try:
            ont = onts[at['structure_graph_id']]
        except KeyError as e:
            ont = dict(id=at['structure_graph_id'], organism_id=2)
            print('hey guys, could you please fix this missing ont?', e)
        if ont:
            want_onts.add(ont['id'])
        if ont and ref:
            assert ont['organism_id'] == ref['organism_id'], f"\n{ont['organism_id']}\n{ref['organism_id']}"

    have_atlases = set(o['id'] for o in onts.values() if o and o['has_atlas'])
    try:
        assert want_onts == have_atlases, f'\n{sorted(want_onts)}\n{sorted(have_atlases)}'
    except AssertionError as e:
        print('needs more attention', e)
    for oid in want_onts:
        try:
            ont = onts[oid]
        except KeyError:  # FIXME
            continue
        ont['name']
        ont['description']
        ont['id']

    # FIXME I have no idea what this was doing or why it previously worked
    #_ReferenceSpace['age_id']
    #_ReferenceSpace['name']
    #_ReferenceSpace['organism_id'] == _Ontology['organism_id']

    # the usual flattened
    # http://api.brain-map.org/api/v2/tree_search/Structure/10154.json?descendants=true
    # hierarchical
    # http://api.brain-map.org/api/v2/structure_graph_download/{1,12,7,11,4,10}.json
    # the mapping between atlasid and
    # structure query
    # http://api.brain-map.org/api/v2/data/Structure/3999   # id vs atlas_id !??!
    # atlas
    # http://atlas.brain-map.org/atlas?atlas={}

class Artifacts(Collector):
    collects = Terminology
    MBA = Terminology(iri=AIBS['mouse/versions/2'],  # ilxtr.mbav2,
                      rdfs_label='Allen Mouse Brain Atlas Terminology',  # TODO version?  XXX overwritten
                      label='Allen Mouse Brain Atlas Ontology',
                      shortname='MBA',
                      date='2011',  # TODO
                      version='2',  # XXX NOT TO BE CONFUSED WITH CCFv2
                      docUri='http://help.brain-map.org/download/attachments/2818169/AllenReferenceAtlas_v2_2011.pdf?version=1&modificationDate=1319667383440',  # yay no doi! wat
                      species=NCBITaxon['10090'],
                      devstage=UBERON['0000113'],  # FIXME mature vs adult vs when they actually did it...
                      region=UBERON['0000955'],
                      comment=('Note that the ontology version for MBA is distinct from '
                               'the common coordinate framework version. Unfortunately there '
                               'is not a link to documentation for the ontology independent '
                               'of the CCF, which makes it impossible to determine changes '
                               'to the ontology independent of changes to the CCF. However '
                               'there have been few changes over time with only one major '
                               'change between version 1 and 2.')
    )

    HBA = Terminology(iri=AIBS['human/versions/2'],  # ilxtr.hbav2,
                      # a note on the IRIs here: uris/species is implicitly the terminology
                      # if we need to deal with the atlas artifacts explicitly put them in uris/atlases/species/
                      rdfs_label='Allen Human Brain Atlas Terminology',
                      label='Allen Human Brain Atlas Ontology',
                      shortname='HBA',
                      date='2013',  # TODO
                      version='2',
                      docUri='http://help.brain-map.org/download/attachments/2818165/HBA_Ontology-and-Nomenclature.pdf?version=1&modificationDate=1382051847989',  # yay no doi! wat
                      species=NCBITaxon['9606'],
                      devstage=UBERON['0000113'],  # FIXME mature vs adult vs when they actually did it...
                      region=UBERON['0000955'],
    )

    DMBA = Terminology(iri=AIBS['mouse/devel/versions/1'],
                       rdfs_label='Allen Developing Mouse Brain Atlas Terminology',  # TODO version?  XXX overwritten
                       label='Allen Mouse Brain Atlas Ontology',
                       shortname='DMBA',
                       date='',  # TODO
                       version='1',
                       docUri='',  # TODO
                       species=NCBITaxon['10090'],
                       devstage='many',  # TODO
                       region=UBERON['0000955'],
    )

    DHBA = Terminology(iri=AIBS['human/devel/versions/1'],
                       rdfs_label='Allen Developing Human Brain Atlas Terminology',
                       label='Allen Developing Human Brain Atlas Ontology',
                       shortname='DHBA',
                       date='',  # TODO
                       version='1',
                       docUri='',  # TODO
                       species=NCBITaxon['9606'],
                       devstage='many',  # TODO
                       region=UBERON['0000955'],
    )

    MBAxCCFv2 = None  # TODO
    MBAxCCFv3 = None  # TODO

#for k, v in ABA.__dict__.items():
    #if v is not None and isinstance(v, parc.Artifact):
        #setattr(parc.Artifacts, k, v)  # still needed for the time being
        #parc.Artifacts._artifacts += v,
        #print(k, v)


class ABASrc(Source):  # NOTE cannot inherit directly from MBASrc because __new__ sets data for all subclasses
    artifact = None
    root = None
    sourcePattern = 'http://api.brain-map.org/api/v2/tree_search/Structure/{}.json?descendants=true'

    @classmethod
    def runonce(cls):
        cls.source = cls.sourcePattern.format(cls.root)
        cls.artifact.source = cls.source

    @classmethod
    def loadData(cls):
        resp = requests.get(cls.source)
        return resp.json()

    @classmethod
    def processData(cls):
        return cls.raw['msg'],

    @classmethod
    def validate(cls, d):
        return d


class MBASrc(ABASrc):
    artifact = Artifacts.MBA
    root = 997


class HBASrc(ABASrc):
    artifact = Artifacts.HBA
    root = 3999


class DMBASrc(ABASrc):
    artifact = Artifacts.DMBA
    root = 15564


class DHBASrc(ABASrc):
    artifact = Artifacts.DHBA
    root = 10154


class HBALabels(LabelsBase):
    filename = 'hbaslim'
    name = 'Allen Human Brain Atlas Ontology'
    shortname = 'hba'
    imports = parcCore,
    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov'), 'HBA':str(HBA), 'ilxHBA':str(ilxHBA)}
    sources = HBASrc,
    namespace = HBA
    root = LabelRoot(iri=AIBS['human/labels/'],  # ilxtr.hbaroot,
                     label='Allen Human Brain Atlas parcellation label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )

    def _triples(self):
        for source in self.sources:
            for record in source:
                iri = self.namespace[str(record['id'])]
                sn = record['safe_name']
                if sn and sn != record['name']: syns = sn,
                else: syns = tuple()
                yield from Label(labelRoot=self.root,
                                 label=record['name'],
                                 synonyms=syns,
                                 abbrevs=(record['acronym'],),
                                 iri=iri,
                )
                superpart = record['parent_structure_id']
                if superpart:
                    superpart_iri = self.namespace[str(superpart)]
                    yield from restriction.serialize(iri, ilxtr.labelPartOf, superpart_iri)


class MBALabels(HBALabels):
    path = 'ttl/generated/parcellation/'
    filename = 'mbaslim'
    name = 'Allen Mouse Brain Atlas Ontology'
    shortname='mba'
    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov'), 'MBA':str(MBA), 'ilxMBA':str(ilxMBA)}
    sources = MBASrc,
    namespace = MBA
    root = LabelRoot(iri=AIBS['mouse/labels/'],  # ilxtr.mbaroot,
                     label='Allen Mouse Brain Atlas parcellation label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )


class DHBALabels(HBALabels):
    path = 'ttl/generated/parcellation/'
    filename = 'dhbaslim'
    name = 'Allen Developing Human Brain Atlas Ontology'
    shortname='dhba'
    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov'), 'DHBA':str(DHBA), 'ilxDHBA':str(ilxDHBA)}
    sources = DHBASrc,
    namespace = DHBA
    root = LabelRoot(iri=AIBS['human/devel/labels/'],
                     label='Allen Developing Human Brain Atlas parcellation label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )


class DMBALabels(HBALabels):
    path = 'ttl/generated/parcellation/'
    filename = 'dmbaslim'
    name = 'Allen Developing Mouse Brain Atlas Ontology'
    shortname='dmba'
    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov'), 'DMBA':str(DMBA), 'ilxDMBA':str(ilxDMBA)}
    sources = DMBASrc,
    namespace = DMBA
    root = LabelRoot(iri=AIBS['mouse/devel/labels/'],
                     label='Allen Developing Mouse Brain Atlas parcellation label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )


def allenLabels():  # really just abaonts?
    return tuple()

def abaArts():
    for k, v in ABA.__dict__.items():
        if v is not None and isinstance(v, parc.Artifact):
            yield v

def main():
    getOnts()
    return
    out = build(
        DHBALabels,
        DMBALabels,
        HBALabels,
        MBALabels,
    )

if __name__ == '__main__':
    main()


