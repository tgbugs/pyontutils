import sys
import requests
from pyontutils.core import rdf, rdfs, owl, dc, dcterms, skos, prov
from pyontutils.core import NIFRID, ilx, ilxtr, TEMP, DKT, DKTr, DKTs, MNDBGL
from pyontutils.core import NCBITaxon, UBERON
from pyontutils.core import nsExact
from pyontutils.core import makePrefixes, Source, LabelsBase, Collector, restriction, build
from pyontutils.utils import Async, deferred
# import pyontutils.parcellation as parc
from pyontutils.parcellation import parcCore, LabelRoot, Label, Terminology
from IPython import embed

class Artifacts(Collector):
    collects = Terminology
    MNDBGL = Terminology(iri=ilx['mindboggle/uris/mndbgl/versions/1'],
                     rdfs_label='Mindboggle parcellation terminology',
                     abbrevs=('MNDBGL',),
                     date='2014-10-20',  # git log --follow mindboggle/mio/labels.py
                     docUri='https://mindboggle.readthedocs.io/en/latest/labels.html',
                     # citation='https://doi.org/10.1371/journal.pcbi.1005350',
                     citation=('Klein A, Ghosh SS, Bao FS, Giard J, Hame Y, Stavsky E, Lee N, Rossa B, '
                               'Reuter M, Neto EC, Keshavan A. (2017) Mindboggling morphometry of human '
                               'brains. PLoS Computational Biology 13(3): e1005350. doi:10.1371/journal.pcbi.1005350'),
                     species=NCBITaxon['9606'],
                     devstage=UBERON['0000113'],)

    DKT = Terminology(iri=DKT['versions/1'],  # FIXME there is a note about removing corpus colossum?
                      rdfs_label='Desikan-Killiany-Tourville parcellation terminology',
                      synonyms=('Desikan-Killiany-Tourville (DKT) human brain cortical labeling protocol',
                                'Desikan-Killiany-Tourville brain labeling protocol',),
                      abbrevs=('DKT',),
                      date='2014-10-20',  # git log --follow mindboggle/mio/labels.py
                      docUri='https://mindboggle.readthedocs.io/en/latest/labels.html',
                      # citation='https://doi.org/10.3389/fnins.2012.00171'
                      citation=('101 labeled brain images and a consistent human cortical '
                                'labeling protocol. Arno Klein, Jason Tourville. Frontiers '
                                'in Brain Imaging Methods. 6:171. DOI: 10.3389/fnins.2012.00171'),
                      species=NCBITaxon['9606'],
                      devstage=UBERON['0000113'],)


class MNDBGLSrc(Source):
    source = 'https://github.com/nipy/mindboggle.git'
    sourceFile = 'mindboggle/mio/labels.py'  # subclass if you have more than one file
    source_original = True
    artifact = Artifacts.MNDBGL

    @classmethod
    def loadData(cls):
        sys.path.append(cls.repo_path.as_posix())
        from mindboggle.mio.labels import DKTprotocol as dkt
        cls.dkt = dkt
        return dkt

    @classmethod
    def processData(cls):
        dkt = cls.dkt
        # mb_all = tuple(zip(iter(lambda:'all', 0), dkt.numbers, dkt.names))
        mb_labels = tuple(zip(dkt.label_numbers, dkt.label_names))
        return mb_labels,


class DKTSrc(MNDBGLSrc):
    artifact = Artifacts.DKT

    @classmethod
    def processData(cls):
        dkt = cls.dkt
        dkt31 = tuple(zip(iter(lambda:DKTr, 0), dkt.DKT31_numbers, dkt.DKT31_names))
        sul = tuple(zip(iter(lambda:DKTs, 0), dkt.sulcus_numbers, dkt.sulcus_names))
        return dkt31 + sul,


class MNDBGLLabels(LabelsBase):
    """ Parcellation labels from Mindboggle. """
    filename = 'mndbgl-labels'
    name = 'Mindboggle Parcellation Labels'
    shortname = 'mndbgl'
    namespace = MNDBGL
    imports = parcCore,
    sources = MNDBGLSrc,
    root = LabelRoot(iri=nsExact(namespace),  # ilxtr.hcpmmproot,
                     label='Mindboggle label root',
                     shortname=shortname,
                     comment=('The local integer identifiers in the MNDBGL namespace '
                              'correspond to numbers from FreeSurferColorLUT.txt.'),
                     definingArtifacts=(s.artifact.iri for s in sources),)

    def _triples(self):
        for source in self.sources:
            for index, label in source:
                iri = self.namespace[str(index)]
                yield from Label(labelRoot=self.root,
                                 label=label,
                                 iri=iri)

            yield from source.isVersionOf


class DKTLabels(LabelsBase):
    """ Labels from the Desikan-Killiany-Tourville human brain labeling protocol. """

    filename = 'dkt-labels'
    name = 'Desikan-Killiany-Tourville Parcellation Labels'
    shortname = 'dkt'
    namespace = DKT
    prefixes = {'DKTr':str(DKTr), 'DTKs':str(DKTs), **LabelsBase.prefixes}
    imports = parcCore,
    sources = DKTSrc,
    root = LabelRoot(iri=nsExact(namespace),  # ilxtr.hcpmmproot,
                     label='DKT label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )

    def _triples(self):
        for source in self.sources:
            for namespace, index, label in source:
                iri = namespace[str(index)]
                yield from Label(labelRoot=self.root,
                                 label=label,
                                 iri=iri)

            yield from source.isVersionOf


def main():
    build(DKTLabels, MNDBGLLabels)

if __name__ == '__main__':
    main()
