import sys
from pyontutils.core import Source, LabelsBase, Collector, build
from pyontutils.utils import Async, deferred
from pyontutils.namespaces import makePrefixes, NCBITaxon, UBERON, nsExact
from pyontutils.namespaces import NIFRID, ilx, ilxtr, TEMP, DKT, DKTr, DKTs, MNDBGL, FSCL
from pyontutils.combinators import restriction
from pyontutils.parcellation import parcCore, LabelRoot, Label, Terminology
from pyontutils.closed_namespaces import rdf, rdfs, owl, dc, dcterms, skos, prov
from IPython import embed

class Artifacts(Collector):
    collects = Terminology
    # A note about artifacts that are digital and are under version control
    #  Artifacts that are under version control do not really need us to mint
    #  an additional versioned PID for them, we just need to make it clear that
    #  the artifact that we are referring to a an equivalent operational identifier
    #  such as a github url and then we can use the prov: relationships to track
    #  the changes at maximum granularity. I think that this is the right approach.
    class FreeSurferColorLUT(Terminology):
        iri=ilx['freesurfer/uris/FreeSurferColorLUT/']
        class_label='FreeSurfer Color LUT parcellation terminology'
        abbrevs=('FSCL',)
        date='2003-05-07'  # git log --name-status --follow distribution/FreeSurferColorLUT.txt
        docUri='https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/AnatomicalROI/FreeSurferColorLUT'
        citation='https://doi.org/10.1016/j.neuroimage.2012.01.021'
        species=NCBITaxon['9606']
        devstage=UBERON['0000113']  # FIXME not sure if this is accurate

    fsclut = FreeSurferColorLUT()

    FreeSurferColorLUT1_105 = FreeSurferColorLUT(iri=ilx['freesurfer/uris/FreeSurferColorLUT/versions/1.105'],
                                                 abbrevs=('FSCL1.105',),
                                                 # TODO FIXME the metadata on this version will be wrong
                                                 # because of how python inheritance works :/
                                                 version='1.105')

    """  # FreeSurferColorLUT is the correct source for these
         # mindboggle semantics may be different, but I think that they
         # should probably be encoded in a different way
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
    """

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


class FreeSurferSrc(Source):
    source = 'https://github.com/freesurfer/freesurfer.git'
    sourceFile = 'distribution/FreeSurferColorLUT.txt'  # subclass if you have more than one file
    source_original = True
    artifact = Artifacts.FreeSurferColorLUT1_105

    @classmethod
    def loadData(cls):
        #file_commit = next(cls.repo.iter_commits(paths=cls.source.as_posix(), max_count=1))
        #cls.artifact.date = file_commit.authored_datetime.strftime('%Y-%m-%d')
        with open(cls.source, 'rt') as f:
            header, *rows = f.readlines()
        return rows

    @classmethod
    def processData(cls):
        number_name = []
        for row in cls.raw:
            row = row.strip()
            if not row or row.startswith('#'):  # no blanks and comments
                continue

            number, name, *rgba = (c for c in row.split(' ') if c)
            number_name.append((number, name))

        return number_name,


class MNDBGLSrc(Source):
    source = 'https://github.com/nipy/mindboggle.git'
    sourceFile = 'mindboggle/mio/labels.py'  # subclass if you have more than one file
    source_original = True
    #artifact = Artifacts.MNDBGL

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


class FreeSurferLabels(LabelsBase):
    filename = 'freesurfer-labels'
    name = 'FreeSurfer color LUT Parcellation Labels'
    shortname = 'fscl'  # can't use fsl because that is already in use by another fMRI package...
    namespace = FSCL
    prefixes = {**LabelsBase.prefixes}  # FIXME it would be nice to be able to automate this...
    imports = parcCore,
    sources = FreeSurferSrc,
    root = LabelRoot(iri=nsExact(namespace),  # ilxtr.hcpmmproot,
                     label='FreeSurfer Color LUT label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),)

    def _triples(self):
        for source in self.sources:
            for index, label in source:
                iri = self.namespace[str(index)]
                yield from Label(labelRoot=self.root,
                                 label=label,
                                 iri=iri)

            yield from source.isVersionOf


#class MNDBGLLabels(LabelsBase):
class MNDBGLLabels():
    """ DEPRECATED use FreeSurfer """
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
                     #definingArtifacts=(s.artifact.iri for s in sources),
                    )

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
    prefixes = {'DKTr':str(DKTr), 'DKTs':str(DKTs), **LabelsBase.prefixes}
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
    build(DKTLabels, FreeSurferLabels)

if __name__ == '__main__':
    main()
