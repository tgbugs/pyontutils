import os
import glob
from lxml import etree
import rdflib
from pyontutils.core import LabelsBase, Collector, Source, ParcOnt
from pyontutils.core import makePrefixes
from pyontutils.namespaces import nsExact
from pyontutils.namespaces import FSLATS
from pyontutils.namespaces import NCBITaxon, UBERON
from nifstd_tools.parcellation import parcCore, Artifact, Terminology, LabelRoot, Label


class FSL(LabelsBase):
    """ Ontology file containing labels from the FMRIB Software Library (FSL)
    atlases collection. All identifiers use the number of the index specified
    in the source xml file. """

    path = 'ttl/generated/parcellation/'
    filename = 'fsl'
    name = 'Terminologies from FSL atlases'
    shortname = 'fsl'
    imports = parcCore,
    prefixes = {**makePrefixes('ilxtr'), **ParcOnt.prefixes,
                'FSLATS':str(FSLATS),
    }
    sources = tuple()  # set by prepare()
    roots = tuple()  # set by prepare()

    class Artifacts(Collector):
        """ Artifacts for FSL """
        collects = Artifact


    def _triples(self):
        for source in self.sources:
            for index, label in source:
                iri = source.root.namespace[str(index)]
                yield from Label(labelRoot=source.root,
                                 label=label,
                                 iri=iri)

    @classmethod
    def prepare(cls):
        ATLAS_PATH = '/usr/share/fsl/data/atlases/'

        shortnames = {
            'JHU White-Matter Tractography Atlas':'JHU WM',
            'Oxford-Imanova Striatal Structural Atlas':'OISS',
            'Talairach Daemon Labels':'Talairach',
            'Subthalamic Nucleus Atlas':'SNA',
            'JHU ICBM-DTI-81 White-Matter Labels':'JHU ICBM WM',
            'Juelich Histological Atlas':'Juelich',
            'MNI Structural Atlas':'MNI Struct',
        }

        prefixes = {
            'Cerebellar Atlas in MNI152 space after normalization with FLIRT':'CMNIfl',
            'Cerebellar Atlas in MNI152 space after normalization with FNIRT':'CMNIfn',
            'Sallet Dorsal Frontal connectivity-based parcellation':'DFCBP',
            'Neubert Ventral Frontal connectivity-based parcellation':'VFCBP',
            'Mars Parietal connectivity-based parcellation':'PCBP',
        }

        for xmlfile in glob.glob(ATLAS_PATH + '*.xml'):
            filename = os.path.splitext(os.path.basename(xmlfile))[0]

            tree = etree.parse(xmlfile)
            parcellation_name = tree.xpath('header//name')[0].text

            # namespace
            namespace = rdflib.Namespace(FSLATS[filename + '/labels/'])

            # shortname
            shortname = tree.xpath('header//shortname')
            if shortname:
                shortname = shortname[0].text
            else:
                shortname = shortnames[parcellation_name]

            artifact_shortname = shortname
            shortname = shortname.replace(' ', '')

            # Artifact
            artifact = Terminology(iri=FSLATS[filename],
                                   label=parcellation_name,
                                   docUri='http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases',
                                   species=NCBITaxon['9606'],
                                   devstage=UBERON['0000113'],  # FIXME mature vs adult vs when they actually did it...
                                   region=UBERON['0000955'],
                                   shortname=artifact_shortname)
            setattr(cls.Artifacts, shortname, artifact)

            # LabelRoot
            root = LabelRoot(iri=nsExact(namespace),
                             label=parcellation_name + ' label root',
                             shortname=shortname,
                             definingArtifacts=(artifact.iri,))
            root.namespace = namespace
            cls.roots += root,

            # prefix
            if parcellation_name in prefixes:
                prefix = 'fsl' + prefixes[parcellation_name]
            else:
                prefix = 'fsl' + shortname

            cls.prefixes[prefix] = root.iri

            # Source
            @classmethod
            def loadData(cls, _tree=tree):
                out = []
                for node in _tree.xpath('data//label'):
                    index, label = node.get('index'), node.text
                    out.append((index, label))
                return out

            source = type('FSLsource_' + shortname.replace(' ', '_'),
                          (Source,),
                          dict(iri=rdflib.URIRef('file://' + xmlfile),
                               source=xmlfile,
                               source_original=True,
                               artifact=artifact,
                               root=root,  # used locally since we have more than one root per ontology here
                               loadData=loadData))
            cls.sources += source,

        super().prepare()
