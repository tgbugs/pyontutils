import sys
from lxml import etree
from pyontutils.core import Source, LabelsBase, Collector, build
from pyontutils.utils import Async, deferred
from pyontutils.namespaces import NIFRID, ilx, ilxtr, WHSSD
from pyontutils.namespaces import makePrefixes, NCBITaxon, UBERON, nsExact
from pyontutils.combinators import restriction
from pyontutils.parcellation import parcCore, resSource, LabelRoot, Label, Terminology
from pyontutils.closed_namespaces import rdf, rdfs, owl, dc, dcterms, skos, prov
from IPython import embed

class Artifacts(Collector):
    collects = Terminology

    class WHSSD(Terminology):
        iri = ilx['waxholm/uris/sd/']
        class_label = 'Waxholm Space Sprague Dawley Terminology'
        citation = 'https://www.ncbi.nlm.nih.gov/pubmed/24726336'
        species=NCBITaxon['10116']
        devstage=UBERON['0000113']
        comment = ('Versions of the .label file add and remove entries and '
                   'sometimes slightly modify the label, but indexes are never '
                   'reused and retain their meaning.')

    whssd = WHSSD()  # FIXME need to clean up how this works wrt subclassing

    WHSSD1 = WHSSD(iri=ilx['waxholm/uris/sd/versions/1'],
                   rdfs_label='Waxholm Space Sprague Dawley Terminology v1',
                   shortname='WHSSD1',
                   date='2014-04-09',
                   version='1',)

    WHSSD2 = WHSSD(iri=ilx['waxholm/uris/sd/versions/2'],  # ilxtr.whssdv2,
                   rdfs_label='Waxholm Space Sprague Dawley Terminology v2',
                   shortname='WHSSD2',
                   date='2015-02-02',
                   version='2',)

class WHSSDSrc(resSource):
    sourceFile = lambda v: f'pyontutils/resources/WHS_SD_rat_atlas_v{v}.label'
    source_original = True
    artifact = lambda v: getattr(Artifacts, f'WHSSD{v}')

    @classmethod
    def loadData(cls):
        with open(cls.source, 'rt') as f:
            lines = [l.strip() for l in f.readlines() if not l.startswith('#')]
        return [(l[:3].strip(), l.split('"',1)[1].strip('"')) for l in lines]

    @classmethod
    def processData(cls):
        return cls.raw,

    @classmethod
    def validate(cls, d):
        return d


class WHSSDSrc1(WHSSDSrc):
    v = '1'
    sourceFile = WHSSDSrc.sourceFile(v)
    artifact = WHSSDSrc.artifact(v)


class WHSSDSrc2(WHSSDSrc):
    v = '2'
    sourceFile = WHSSDSrc.sourceFile(v)
    artifact = WHSSDSrc.artifact(v)


class WHSSDilfSrc(resSource):
    sourceFile = lambda v: f'pyontutils/resources/WHS_SD_rat_atlas_v{v}_labels.ilf'
    source_original = True
    artifact = lambda v: getattr(Artifacts, f'WHSSD{v}')
    predicates = lambda v: {ilxtr.labelPartOf: ilxtr[f'labelPartOf-whssd-{v}']}  # FIXME

    @classmethod
    def loadData(cls):
        tree = etree.parse(cls.source)
        return tree

    @classmethod
    def processData(cls):
        tree = cls.raw
        def recurse(label_node, parent=None):
            name = label_node.get('name')
            abbrev = label_node.get('abbreviation')
            id = label_node.get('id')
            yield id, name, abbrev, parent
            for child in label_node.getchildren():
                if child.tag == 'label':
                    yield from recurse(child, parent=id)

        records = tuple()
        for structure in tree.xpath('//structure'):
            for lab in structure.getchildren():
                if lab.tag == 'label':
                    records += tuple(recurse(lab, None))

        return records,

    @classmethod
    def validate(cls, d):
        return d


class WHSSDilfSrc1(WHSSDilfSrc):
    v = '1'
    sourceFile = WHSSDilfSrc.sourceFile(v)
    artifact = WHSSDilfSrc.artifact(v)
    predicates = WHSSDilfSrc.predicates(v)


class WHSSDilfSrc2(WHSSDilfSrc):
    v = '2'
    sourceFile = WHSSDilfSrc.sourceFile(v)
    artifact = WHSSDilfSrc.artifact(v)
    predicates = WHSSDilfSrc.predicates(v)


class WHSSDLabels(LabelsBase):
    filename = 'waxholm-rat-labels'
    name = 'Waxholm Sprague Dawley Atlas Labels'
    shortname = 'whssd'
    imports = parcCore,
    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov', 'dcterms'), 'WHSSD':str(WHSSD)}
    sources = WHSSDSrc2, WHSSDilfSrc2, WHSSDSrc1, WHSSDilfSrc1
    namespace = WHSSD
    root = LabelRoot(iri=nsExact(namespace),  # ilxtr.whssdroot,
                     label='Waxholm Space Sprague Dawley parcellation label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )

    def _triples(self):
        for source in self.sources:
            preds = False
            for index, label, *rest in source:
                abbrev, parent = rest if rest else (False, False)  # a tricky one if you miss the parens
                abbrevs = (abbrev,) if abbrev and abbrev != label else tuple()
                if int(index) >= 1000:  # FIXME this is the WRONG way to do this
                    # FIXME parentless structures in the ilf files?
                    label += ' (structure)'
                iri = WHSSD[str(index)]
                yield from Label(labelRoot=self.root,
                                 label=label,
                                 abbrevs=abbrevs,
                                 iri=iri,
                )
                if parent:
                    preds = True
                    parent = WHSSD[str(parent)]
                    yield from restriction.serialize(iri, source.predicates[ilxtr.labelPartOf], parent)

            yield from source.isVersionOf
            if preds:
                for parent, child in source.predicates.items():  # FIXME annotationProperty vs objectProperty
                    yield child, rdfs.subPropertyOf, parent

def main():
    build(WHSSDLabels)

if __name__ == '__main__':
    main()
