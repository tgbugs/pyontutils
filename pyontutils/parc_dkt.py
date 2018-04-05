import requests
from pyontutils.core import rdf, rdfs, owl, dc, dcterms, skos, prov
from pyontutils.core import NIFRID, ilx, ilxtr, TEMP, DKT
from pyontutils.core import NCBITaxon, UBERON
from pyontutils.core import nsExact
from pyontutils.core import makePrefixes, Source, LabelsBase, Collector, restriction, build
from pyontutils.utils import Async, deferred
# import pyontutils.parcellation as parc
from pyontutils.parcellation import parcCore, LabelRoot, Label, Terminology

class Artifacts(Collector):
    collects = Terminology
    DKT = Terminology(iri=ilx['mindboggle/uris/dkt/versions/1'],
                      rdfs_label='Desikan-Killiany-Tourville parcellation terminology',
                      synonyms=('Desikan-Killiany-Tourville (DKT) human brain cortical labeling protocol',
                                'Desikan-Killiany-Tourville brain labeling protocol',),
                      abbrevs=('DKT',),
                      date='2014-10-20',  # git log --follow mindboggle/mio/labels.py
                      docUri='https://mindboggle.readthedocs.io/en/latest/labels.html',
                      citation=('Klein A, Ghosh SS, Bao FS, Giard J, Hame Y, Stavsky E, Lee N, Rossa B, '
                                'Reuter M, Neto EC, Keshavan A. (2017) Mindboggling morphometry of human '
                                'brains. PLoS Computational Biology 13(3): e1005350. doi:10.1371/journal.pcbi.1005350'),
                      # citation='https://doi.org/10.1371/journal.pcbi.1005350',
                      species=NCBITaxon['9606'],
                      devstage=UBERON['0000113'],
                      )
class DKTSrc(Source):
    artifact = Artifacts.DKT
    # source = 'https://github.com/nipy/mindboggle/blob/master/mindboggle/mio/labels.py'
    source = 'https://github.com/nipy/mindboggle.git'
    sourceFile = 'mindboggle/mio/labels.py'  # subclass if you have more than one file
    source_original = True

    @classmethod
    def loadData(cls):
        return (ilxtr.test, ilxtr.test, ilxtr.test),


class DKTLabels(LabelsBase):
    """ Labels from the Desikan-Killiany-Tourville human brain labeling protocol. """

    filename = 'dkt-labels'
    imports = parcCore,
    name = 'Desikan-Killiany-Tourville Parcellation Labels',
    shortname = 'dkt'
    namespace = DKT
    sources = DKTSrc,
    root = LabelRoot(iri=nsExact(namespace),  # ilxtr.hcpmmproot,
                     label='DKT label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )

    def _triples(self):
        for source in self.sources:
            for record in source:
                yield record

            yield from source.isVersionOf


def main():
    from IPython import embed
    DKTSrc()
    build(DKTLabels)
    embed()

if __name__ == '__main__':
    main()
