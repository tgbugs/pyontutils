#!/usr/bin/env python3
#!/usr/bin/env pypy3
__doc__ = f"""Generate NIF parcellation schemes from external resources.

Usage:
    parcellation [options]

Options:
    -f --fail                   fail loudly on common common validation checks
    -j --jobs=NJOBS             number of parallel jobs to run [default: 9]
    -l --local                  only build files with local source copies
    -s --stats                  generate report on current parcellations

"""

import csv
from pathlib import Path
from git import Repo
from rdflib import Graph, URIRef
from pyontutils.core import Class, Source, resSource, ParcOnt, LabelsBase, Collector, OntTerm
from pyontutils.core import build
from pyontutils.utils import getSourceLine, subclasses
from pyontutils.utils import TermColors as tc
from pyontutils.config import auth, working_dir
from pyontutils.namespaces import makePrefixes, nsExact
from pyontutils.namespaces import NIFRID, ilx, ilxtr, FSLATS
from pyontutils.namespaces import paxmusver, paxratver, HCPMMP
from pyontutils.namespaces import NCBITaxon, UBERON, NIFTTL, partOf
from pyontutils.namespaces import rdf, rdfs, owl, dc, dcterms, skos, prov
from pyontutils.process_fixed import ProcessPoolExecutor
from nifstd_tools.utils import log
try:
    breakpoint
except NameError:
    from IPython import embed as breakpoint

log = log.getChild('parc')

#
# New impl
# helpers

# classes


class Artifact(Class):
    """ Parcellation artifacts are the defining information sources for
        parcellation labels and/or atlases in which those labels are used.
        They may include semantic and/or geometric information. """

    iri = ilxtr.parcellationArtifact
    class_label = 'Parcellation Artifact'
    _kwargs = dict(iri=None,
                   rdfs_label=None,
                   label=None,
                   synonyms=tuple(),
                   abbrevs=tuple(),
                   definition=None,
                   shortname=None,
                   date=None,
                   copyrighted=None,
                   version=None,
                   species=None,
                   devstage=None,
                   region=None,
                   source=None,
                   citation=None,
                   docUri=None,
                   comment=None,
                   definingCitations=tuple(),
                   hadDerivation=tuple(),
                   identifiers=tuple(),
                  )
    propertyMapping = dict(
        version=ilxtr.artifactVersion,  # FIXME
        date=dc.date,
        sourceUri=ilxtr.sourceUri,  # FIXME
        copyrighted=dcterms.dateCopyrighted,
        source=dc.source,  # use for links to
        hadDerivation=prov.hadDerivation,
        identifiers=dc.identifier,  # FIXME TODO
        # ilxr.atlasDate
        # ilxr.atlasVersion
    )

    propertyMapping = {**Class.propertyMapping, **propertyMapping}  # FIXME make this implicit


class Terminology(Artifact):
    """ A source for parcellation information that applies to one
        or more spatial sources, but does not itself contain the
        spatial definitions. For example Allen MBA. """

    iri = ilxtr.parcellationTerminology
    class_label = 'Parcellation terminology'
    #class_definition = ('An artifact that only contains semantic information, '
                        #'not geometric information, about a parcellation.')

class CoordinateSystem(Artifact):
    """ An artifact that defines the geometric coordinates used by
        one or more parcellations. """

    iri = ilxtr.parcellationCoordinateSystem
    class_label = 'Parcellation coordinate system'


class Delineation(Artifact):
    """ An artifact that defines the spatial boundaries or landmarks for a parcellation.
        Delineations must be explicitly spatial and are distinct from delineation criteria
        which may provide a non-spatial definition for regions. """

    iri = ilxtr.parcellationDelineation
    class_label = 'Parcellation delineation'
    # TODO registrationCriteria => processive, usually matching delineationCriteria where practical
    # TODO delineationCriteria => definitional


class Atlas(Artifact):
    """ An artifact that contains information about the terminology,
        delineation, and coordinate system for a parcellation. These
        are usually physical atlases where it is not possibly to uniquely
        identify any of the component parts, but only all the parts taken
        together (e.g. via ISBN). """

    iri = ilxtr.parcellationAtlas
    class_label = 'Parcellation atlas'
    # hasPart Delineation, hasPart CoordinateSystem, hasPart Terminology
    # alternately hasPart DelineationCriteria and/or RegistrationCriteria
    # TODO links to identifying atlas pictures


class LabelRoot(Class):
    """ Parcellation labels are strings characthers sometimes associated
        with a unique identifier, such as an index number or an iri. """
    """ Base class for labels from a common source that should live in one file """
    # use this to define the common superclass for a set of labels
    iri = ilxtr.parcellationLabel
    class_label = 'Parcellation Label'
    _kwargs = dict(iri=None,
                   label=None,
                   comment=None,
                   shortname=None,  # used to construct the rdfs:label
                   definingArtifacts=tuple(),  # leave blank if defined for the parent class
                   definingArtifactsS=tuple(),
                  )

    def __init__(self, *args, **kwargs):
        for it_name in ('definingArtifacts', 'definingArtifactsS'):  # TODO abstract to type
            if it_name in kwargs:
                kwargs[it_name] = tuple(set(kwargs[it_name]))
        super().__init__(*args, **kwargs)


class Label(Class):
    # allen calls these Structures (which is too narrow because of ventricles etc)
    _kwargs = dict(labelRoot=None,
                   label=None,  # this will become the skos:prefLabel
                   altLabel=None,
                   synonyms=tuple(),
                   abbrevs=tuple(),
                   definingArtifacts=tuple(),  # leave blank if defined for the parent class, needed for paxinos
                   definingCitations=tuple(),
                   iri=None,  # use when a class already exists and we need to know its identifier
                  )
    def __init__(self,
                 usedInArtifacts=tuple(),  # leave blank if 1:1 map between labelRoot and use artifacts NOTE even MBA requires validate on this
                 **kwargs
                ):
        super().__init__(**kwargs)
        self.usedInArtifacts = list(usedInArtifacts)

    def usedInArtifact(self, artifact):
        self.usedInArtifacts.append(artifact)

    @property
    def rdfs_label(self):
        if hasattr(self, 'label'):
            if hasattr(self, 'labelRoot'):
                return self.label + ' (' + self.labelRoot.shortname + ')'
            return self.label + ' (WARNING YOUR LABELS HAVE NO ROOT!)'
        else:
            return 'class not initialized but here __init__ you can have this helpful string :)'

    @property
    def rdfs_subClassOf(self):
        return self.labelRoot.iri


class RegionRoot(Class):
    """ Parcellation regions are 'anatomical entities' that correspond to some
        part of a real biological system and are equivalent to an intersection
        between a parcellation label and a specific version of an atlas that
        defines or uses that label and that provides a definitive
        (0, 1, or probabilistic) way to determine whether a particular sample
        corresponds to any given region.
        """
    """
    Centroid regions (anatomical entities)

    species specific labels
    species generic labels (no underlying species specific mapping)

    Symbols             ->
    semantic labels     -> semantic anatomical region                   -> point (aka unbounded connected spatial volume defined by some 'centroid' or canonical member)
    parcellation labels -> probabalistic anatomical parcellation region -> probablistically bounded connected spatial volume
                        -> anatomical parcellation region               -> bounded connected spatial volume (as long as the 3d volume is topoligically equivalent to a sphere, unconnected planes of section are fine)
    """
    iri = ilxtr.parcellationRegion
    class_label = 'Parcellation Region'
    _kwargs = dict(iri=None,
                   label=None,
                   comment=None,
                   shortname=None,  # used to construct the rdfs:label
                   atlas=None,  # : Atlas
                   labelRoot=None)  # : LabelRoot


class Region(Class):
    iri = ilxtr.parcellationRegion
    def __init__(self,
                 regionRoot,
                 label):
        self.atlas = regionRoot.atlas
        self.label = label.label

#
# ontologies


class Artifacts(Collector):
    collects = Artifact
    HCPMMP = Terminology(iri=ilx['hcp/uris/mmp/versions/1.0'],  # ilxtr.hcpmmpv1,
                         rdfs_label='Human Connectome Project Multi-Modal human cortical parcellation',
                         shortname='HCPMMP',
                         date='2016-07-20',
                         version='1.0',
                         synonyms=('Human Connectome Project Multi-Modal Parcellation',
                                   'HCP Multi-Modal Parcellation',
                                   'Human Connectome Project Multi-Modal Parcellation version 1.0'),
                         abbrevs=('HCP_MMP', 'HCP-MMP1.0', 'HCP MMP 1.0'),
                         citation='https://doi.org/10.1038/nature18933',
                         species=NCBITaxon['9606'],
                         region=UBERON['0000955'],
                         devstage=UBERON['0000113'],
                        )


class parcArts(ParcOnt):
    """ Ontology file for artifacts that define labels or
        geometry for parcellation schemes. """

    # setup

    path = 'ttl/generated/'
    filename = 'parcellation-artifacts'
    name = 'Parcellation Artifacts'
    #shortname = 'parcarts'
    prefixes = {**makePrefixes('NCBITaxon', 'UBERON', 'skos'), **ParcOnt.prefixes,
                'FSLATS':str(FSLATS),
                'paxmusver':str(paxmusver),
                'paxratver':str(paxratver),
    }

    def __call__(self):
        return super().__call__()

    @property
    def _artifacts(self):
        for collector in subclasses(Collector):
            if collector.__module__ != 'nifstd_tools.parcellation':  # just run __main__
                yield from collector.arts()

    def _triples(self):
        from nifstd_tools.parcellation import Artifact
        yield from Artifact.class_triples()
        # OH LOOK PYTHON IS BEING AN AWFUL LANGUAGE AGAIN
        for art_type in subclasses(Artifact):  # this is ok because all subclasses are in this file...
            # do not comment this out it is what makes the
            # upper classes in the artifacts hierarchy
            yield from art_type.class_triples()
        for artifact in self._artifacts:
            yield from artifact


class parcCore(ParcOnt):
    """ Core OWL2 entities needed for parcellations """

    # setup

    path = 'ttl/generated/'
    filename = 'parcellation-core'
    name = 'Parcellation Core'
    #shortname = 'parcore'  # huehuehue
    prefixes = {**makePrefixes('skos', 'BFO'), **ParcOnt.prefixes}
    imports = NIFTTL['nif_backend.ttl'], parcArts

    # stuff

    parents = LabelRoot, RegionRoot

    def _triples(self):
        yield ilxtr.labelPartOf, rdf.type, owl.ObjectProperty
        yield ilxtr.labelPartOf, rdf.type, owl.TransitiveProperty
        yield ilxtr.labelPartOf, rdfs.subPropertyOf, partOf
        for parent in self.parents:
            yield from parent.class_triples()


class RegionsBase(ParcOnt):
    """ An ontology file containing parcellation regions from the
        intersection of an atlas artifact and a set of labels. """
    # TODO find a way to allow these to serialize into one file
    __pythonOnly = True  # FIXME for now perevent export
    imports = parcCore,
    atlas = None
    labelRoot = None
    def __init__(self):
        self.regionRoot = RegionRoot(atlas=self.atlas,
                                     labelRoot=self.labelRoot)


class parcBridge(ParcOnt):
    """ Main bridge for importing the various files that
        make up the parcellation ontology. """

    # setup

    path = 'ttl/bridge/'
    filename = 'parcellation-bridge'
    name = 'Parcellation Bridge'
    imports = ((g[subclass.__name__]
                if subclass.__name__ in g and subclass.__module__ == 'nifstd_tools.parcellation'  # parcellation is insurance for name reuse
                else subclass)
               for g in (globals(),)
               for subclass in subclasses(LabelsBase)  # XXX wow, well apparently __main__.Class != module.Class
               if not hasattr(subclass, f'_{subclass.__name__}__pythonOnly'))

    @property
    def __imports(self):
        for subclass in subclasses(LabelsBase):
            if not hasattr(subclass, f'_{subclass.__name__}__pythonOnly'):
                yield subclass()


#
# Sources (input files)

class LocalSource(Source):
    _data = tuple()

    def __new__(cls):
        line = getSourceLine(cls)
        cls.iri_head = URIRef(cls.iri_prefix_hd + Path(__file__).name)
        cls._this_file = Path(__file__).absolute()
        repobase = working_dir
        cls.repo = Repo(repobase)
        cls.prov()  # have to call prov here ourselves since Source only calls prov if _data is not defined
        if cls.artifact is None:  # for prov...
            class art:
                iri = cls.iri
                def addPair(self, *args, **kwargs):
                    pass

            cls.artifact = art()

        self = super().__new__(cls)
        return self

    @classmethod
    def prov(cls):
        from inspect import getsourcelines
        #source_lines = getSourceLine

        def get_commit_data(start, end):
            records = cls.repo.git.blame('--line-porcelain',
                                         f'-L {start},{end}',
                                         cls._this_file.as_posix()).split('\n')
            rl = 13
            filenames = [l.split(' ', 1)[-1].strip() for l in records[rl - 2::rl]]
            linenos = [(hexsha, int(nowL), int(thenL)) for r in records[::rl]
                       for hexsha, nowL, thenL, *n in (r.split(' '),)]
            author_times = [int(epoch) for r in records[3::rl] for _, epoch in (r.split(' '),)]
            lines = [r.strip('\t') for r in records[12::rl]]
            index, time = max(enumerate(author_times), key=lambda iv: iv[1])
            commit, then, now = linenos[index]
            filepath = filenames[index]
            # there are some hefty assumptions that go into this
            # that other lines have not been deleted from or added to the code block
            # between commits, or essentially that the code in the block is the
            # same length and has only been shifted by the distance defined by the
            # single commit that that has the maximum timestamp, so beware that
            # this can and will break which is why I use start and end instead of
            # just start like I do with the rest of the lines where I know for sure.
            # This can probably be improved with pickaxe or similar.
            shift = then - now
            then_start = start + shift
            then_end = end + shift
            return filepath, commit, then_start, then_end

        source_lines, start = getsourcelines(cls)
        end = start + len(source_lines)
        filepath, most_recent_block_commit, then_start, then_end = get_commit_data(start, end)

        cls.iri = URIRef(cls.iri_prefix_working_dir.format(file_commit=most_recent_block_commit)
                         + f'{filepath}#L{then_start}-L{then_end}')


##
#  Instances
##

# Source instances  TODO put everything under one class as we do for Artifacts?


class HCPMMPSrc(resSource):
    sourceFile = auth.get_path('resources') / 'human_connectome_project_2016.csv'
    source_original = True
    artifact = Artifacts.HCPMMP

    @classmethod
    def loadData(cls):
        with open(cls.source, 'rt') as f:
            return [r for r in csv.reader(f)][1:]  # skip header

    @classmethod
    def processData(cls):
        return cls.raw,

    @classmethod
    def validate(cls, d):
        return d


#
# Ontology Instances

#
# labels


class HCPMMPLabels(LabelsBase):
    filename = 'hcpmmp'
    name = 'Human Connectome Project Multi-Modal human cortical parcellation'
    shortname = 'hcpmmp'
    imports = parcCore,
    prefixes = {**makePrefixes('NIFRID', 'ilxtr', 'prov'), 'HCPMMP':str(HCPMMP)}
    sources = HCPMMPSrc,
    namespace = HCPMMP
    root = LabelRoot(iri=nsExact(namespace),  # ilxtr.hcpmmproot,
                     label='HCPMMP label root',
                     shortname=shortname,
                     definingArtifacts=(s.artifact.iri for s in sources),
    )

    def _triples(self):
        for source in self.sources:
            for record in source:
                (Parcellation_Index, Area_Name, Area_Description,
                 Newly_Described, Results_Section, Other_Names,
                 Key_Studies) = [r.strip() for r in record]
                iri = HCPMMP[str(Parcellation_Index)]
                onames = [n.strip() for n in Other_Names.split(',') if n.strip()]
                syns = (n for n in onames if len(n) > 3)
                abvs = tuple(n for n in onames if len(n) <= 3)
                cites = tuple(s.strip() for s in Key_Studies.split(','))
                if Newly_Described in ('Yes*', 'Yes'):
                    cites = cites + ('Glasser and Van Essen 2016',)

                yield from Label(labelRoot=self.root,
                                 label=Area_Description,
                                 altLabel=Area_Name,
                                 synonyms=syns,
                                 abbrevs=abvs,
                                 #bibliographicCitation=  # XXX vs definingCitation
                                 definingCitations=cites,
                                 iri=iri)


#
# regions

def getOnts():
    return tuple(l for l in subclasses(ParcOnt)
                 if l.__name__ != 'parcBridge'
                 and not hasattr(l, f'_{l.__name__}__pythonOnly')
                 and (l.__module__ != 'nifstd_tools.parcellation'
                      if __name__ == '__main__' or __name__ == '__init__'
                      else l.__module__ != '__main__' and l.__module__ != '__init__'))


def main():
    olr = auth.get_path('ontology-local-repo')
    resources = auth.get_path('resources')
    if not olr.exists():
        raise FileNotFoundError(f'{olr} does not exist cannot continue')
    if not resources.exists():
        raise FileNotFoundError(f'{resources} does not exist cannot continue')

    from docopt import docopt
    args = docopt(__doc__, version='parcellation 0.0.1')
    # import all ye submodules we have it sorted! LabelBase will find everything for us. :D
    if not args['--local']:
        from nifstd_tools.parcellation.aba import Artifacts as abaArts
    from nifstd_tools.parcellation.fsl import FSL  # Artifacts is attached to the class
    from nifstd_tools.parcellation.whs import Artifacts as whsArts
    from nifstd_tools.parcellation.berman import Artifacts as bermArts
    from nifstd_tools.parcellation.paxinos import Artifacts as paxArts
    from nifstd_tools.parcellation.swanson import Artifacts as swArts
    from nifstd_tools.parcellation.freesurfer import Artifacts as fsArts
    onts = getOnts()
    _ = *(print(ont) for ont in onts),
    out = build(*onts,
                parcBridge,
                fail=args['--fail'],
                n_jobs=int(args['--jobs']))
    if args['--stats']:
        breakpoint()


if __name__ == '__main__':
    main()
