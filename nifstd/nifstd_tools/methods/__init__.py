import rdflib
from rdflib import URIRef, Literal
from pyontutils import combinators as cmb
from pyontutils.core import OntId, OntTerm, qname
from pyontutils.core import simpleOnt, displayGraph
from pyontutils.namespaces import OntCuries, makeNamespaces
from pyontutils.namespaces import partOf, hasRole, locatedIn
from pyontutils.namespaces import NIFTTL, NIFRID, ilxti, ilxtio, ilxtr, TEMP
from pyontutils.namespaces import owl, rdf, rdfs, oboInOwl, replacedBy, BFO
from pyontutils.namespaces import definition, realizes, hasParticipant, hasPart, hasInput
from pyontutils.combinators import flattenTriples, unionOf, intersectionOf
from pyontutils.combinators import Restriction, EquivalentClass
from pyontutils.combinators import oc, oc_, olit, oec
from pyontutils.combinators import Restriction2, POCombinator
from pyontutils.combinators import annotation, restriction, restrictionN
from nifstd_tools.methods.core import methods_core, asp, proc, tech, prot, _t, restN, oECN, branch
from nifstd_tools.methods.helper import methods_helper, restHasValue

# NOTE if vim is slow it is probably becuase there are
# so many nested parens `:set foldexpr=` fixes the problem

local = rdflib.Namespace(ilxtio[''] + 'methods/')
local_blank = rdflib.Namespace(local[''] + 'blank/')

restSomeHasValue = Restriction2(None, owl.onProperty, owl.someValuesFrom, owl.hasValue)
#restSomeValuesFrom = Restriction(owl.someValuesFrom)
restMinCardValue = Restriction2(rdfs.subClassOf, owl.onProperty, owl.someValuesFrom, owl.minCardinality)
restMaxCardValue = Restriction2(rdfs.subClassOf, owl.onProperty, owl.someValuesFrom, owl.maxCardinality)
restrictionS = Restriction(owl.someValuesFrom)
oECU = EquivalentClass(owl.unionOf)


def t(subject, label, def_, *synonyms):
    yield from oc(subject, ilxtr.technique)
    yield from olit(subject, rdfs.label, label)
    if def_:
        yield from olit(subject, definition, def_)

    if synonyms:
        yield from olit(subject, NIFRID.synonym, *synonyms)


class I:
    counter = iter(range(999999))
    @property
    def d(self):
        raise BaseException('do not use')
        current = TEMP[str(next(self.counter))]
        self.current = current
        return current

    @property
    def b(self):
        raise BaseException('do not use')
        """ blank node """
        current = next(self.counter)
        return TEMP[str(current)]

    @property
    def p(self):
        return self.current


i = I()

def DEV(value, current=True):
    i.last = value
    uri = local[str(value)]
    if current:
        i.current = uri

    return uri


def blank(value):
    return local_blank[str(value)]


###
#   Methods
###

filename = 'methods'
prefixes = {'local': local,
            'blank': local_blank}
imports = (methods_core.iri,
           methods_helper.iri,
           NIFTTL['bridge/chebi-bridge.ttl'],
           NIFTTL['bridge/tax-bridge.ttl'])
#imports = methods_core.iri, methods_helper.iri
comment = 'The ontology of techniques and methods.'
_repo = True
debug = False

triples = (
    # biccn

    (ilxtr.hasSomething, owl.inverseOf, ilxtr.isSomething),
    _t(tech.unfinished, 'Unfinished techniques',
       (ilxtr.hasSomething, ilxtr.Something),
       synonyms=('incompletely modeled techniques',)
      ),

    _t(DEV(0), 'atlas registration technique',
       # ilxtr.hasPrimaryParticipant, restriction(partOf, some animalia)
       # TODO this falls into an extrinsic classification technique...
       # or a context classification/naming technique...
       (ilxtr.isConstrainedBy, ilxtr.parcellationArtifact),
       #(ilxtr.assigns, asp.location),  # FIXME ilxtr.assigns needs to imply naming...
       #(ilxtr.asserts, asp.location),  # FIXME ilxtr.asserts needs to imply naming...
       (ilxtr.hasPrimaryAspect, asp.locationInAtlas),
       # (ilxtr.hasPrimaryAspect, asp.location),
       synonyms=('registration technique',
                 'atlas registration',
                 'registration')),

    # 'spatial transcriptomics'

    # 'anatomy registration'
    # feducial points
    # '3d atlas registration'
    # '2d atlas registration'
    # 'image registration'
    # fresh frozen ventricles are smaller
    # 4% pfa non perfused

    # 'ROI based atlas registration technique'

    # biccn
    oc(ilxtr.analysisRole, OntTerm('BFO:0000023', label='role')
    ),

    _t(DEV(1), 'randomization technique',  # FIXME this is not defined correctly
       (ilxtr.hasPrimaryAspect, asp.informationEntropy),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
    ),

    # FIXME see if we really want these?
    _t(DEV(2), 'techniques classified by inputs',
       (hasInput, ilxtr.materialEntity)),

    _t(DEV(3), 'techniques classified by aspects',
       (ilxtr.processHasAspect, ilxtr.aspect)),

    _t(DEV(4), 'techniques classified by primary aspects',
       (ilxtr.hasPrimaryAspect, ilxtr.aspect)),

    _t(DEV(5), 'techniques classified by constraining aspects',
       (ilxtr.hasConstrainingAspect, ilxtr.aspect),
       synonyms=('has constraining aspect',
                 'technique defined by constraint')),

    _t(DEV(6), 'composite techniques',
       (hasPart, ilxtr.technique),
       comment=('Note that while the notion of atomic techniques is '
                'the complement of composite techniques, in an open world '
                'it is very hard to show that at technique cannot be broken '
                'down any further. Therefore we have to use something other than '
                "owl in order to account for techniques that 'at the current time' "
                "or 'in the current model' or 'at the current level of abstraction' "
                'do not have any explicit parts.')),

    _t(DEV(7), 'chemical technique',  # FIXME but not molecular? or are molecular subset?
       (hasParticipant,  # FIXME hasParticipant is incorrect? too broad?
        OntTerm('CHEBI:24431', label='chemical entity')
       ),),

    _t(DEV(8), 'molecular technique',  # FIXME help I have no idea how to model this same with chemical technique
       # TODO FIXME I think it is clear that there are certain techniques which are
       # named in a way that is assertional, not definitional
       # it seems appropriate for those arbitrarily named techniques to use subClassOf?
       (hasInput,
        OntTerm('CHEBI:25367', label='molecule')
       ),),

    _t(DEV(9), 'cellular technique',
       intersectionOf(ilxtr.technique,
                      restN(hasInput, OntTerm('SAO:1813327414', label='Cell'))),
       intersectionOf(ilxtr.technique,
                      restN(hasInput,
                            restN(partOf,
                                  OntTerm('SAO:1813327414', label='Cell')))),
       # indeed the equivalence of these two statements is factually correct
       # if I have a technique that inputs something, it also inputs all of the parts of it
       # including the ones that we have named
       equivalentClass=oECN),

    _t(DEV(10), 'cell type induction technique',
       (ilxtr.hasPrimaryInput, OntTerm('SAO:1813327414', label='Cell')),
       (hasInput, ilxtr.inductionFactor),
    ),

    _t(DEV(11), 'molecular cloning technique',

       (ilxtr.hasPrimaryInput,
        OntTerm('CHEBI:33696', label='nucleic acid')
        #OntTerm('CHEBI:16991', label='deoxyribonucleic acid')
        # FIXME other options are OntTerm('SAO:454034570') or OntTerm('SO:0000352')
        ),
       # the objective is to isolate a _specific_ sequence of DNA/RNA
       # amplification is the next step
       (ilxtr.hasPrimaryAspect, asp['count']),  # the general objective being to increase the DNA
       synonyms=('cloning technique', 'molecular cloning')
    ),

    _t(DEV(12), 'microarray technique',
       (hasInput,
        # TODO leverage EFO here
        # OntTerm(search='microarray', limit=20, prefix='NIFSTD')  # nice trick
        OntTerm('BIRNLEX:11031', label='Microarray platform')
        ),
    ),

    # sequencing TODO

    _t(tech.sequencing, 'sequencing technique',
       intersectionOf(ilxtr.technique,
                      # FIXME for this to classify property as a molecular technique
                      # we need a variant of kdp that is an input not just participant...
                      restrictionN(ilxtr.hasPrimaryInput, ilxtr.thingWithSequence),
                      restrictionN(ilxtr.hasPrimaryAspect, asp.sequence,),
                      restrictionN(ilxtr.hasInformationOutput, ilxtr.informationArtifact)),
       intersectionOf(ilxtr.technique,
                      restrictionN(hasPart, tech.sequencing)),
       equivalentClass=oECN),


    _t(tech._naSeq, 'nucleic acid sequencing technique',
       intersectionOf(ilxtr.technique,
                      restrictionN(ilxtr.hasPrimaryInput,
                        # hasParticipant molecule or chemical?
                        #OntTerm(term='nucleic acid')
                                   ilxtr._NApolymer),
                      restrictionN(ilxtr.hasPrimaryAspect,
                                   #OntTerm(term='sequence')
                                   #OntTerm('SO:0000001', label='region', synonyms=['sequence'])  # label='region'
                                   asp.sequence,  # pretty sure that SO:0000001 is not really an aspect...
       ),
                      restrictionN(ilxtr.hasInformationOutput,
                                   ilxtr.informationArtifact),  # note use of artifact
       ),
       intersectionOf(ilxtr.technique,
                      restrictionN(hasPart, tech._naSeq)),
       equivalentClass=oECN),

    _t(DEV(13), 'deep sequencing technique',
       (hasPart, tech._naSeq),
       (ilxtr.isConstrainedBy, prot.deepSequencing),  # FIXME circular
       synonyms=('deep sequencing',)
    ),

    _t(DEV(14), 'sanger sequencing technique',
       (hasPart, tech._naSeq),
       (ilxtr.isConstrainedBy, prot.sangerSequencing),
       # we want these to differentiate based on the nature of the technqiue
       synonyms=('sanger sequencing',)
    ),

    _t(DEV(15), 'shotgun sequencing technique',
       (hasPart, tech._naSeq),
       (ilxtr.isConstrainedBy, prot.shotgunSequencing),
       synonyms=('shotgun sequencing',)
    ),

    _t(tech.scSeq, 'single cell sequencing technique',
       # FIXME vs pp -> *NA from a single cell
       #ilxtr.technique,
       # TODO (hasPart, tech._NALibraryPreparation)
       (hasPart, tech.sequencing),
       #(hasInput, OntTerm('CHEBI:33696', label='nucleic acid')),  # not much protein in a single cell
       # hasInput o hasPart some owl:Thing TODO
       #(hasInput, OntTerm('SAO:1813327414', label='Cell')),  # inputs also need to input all their parts
       # this will continue to work if we use hasPart NucleicAcidExtractionIsolationTechnique
       # (ilxtr.hasPrimaryParticipantCardinality, 1)  # FIXME need this...
       #restMaxCardValue(),
        restMaxCardValue(ilxtr.hasPrimaryInput, OntTerm('SAO:1813327414', label='Cell'), Literal(1)),
       #(ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
       synonyms=('single cell sequencing',)
    ),

    _t(tech.snSeq, 'single nucleus sequencing technique',
       (hasPart, tech.sequencing),
       #(hasInput, OntTerm('CHEBI:33696', label='nucleic acid')),  # not much protein in the nucleus...
       #(ilxtr.hasPrimaryInput, OntTerm('GO:0005634', label='nucleus')),
        restMaxCardValue(ilxtr.hasPrimaryInput, OntTerm('GO:0005634', label='nucleus'), Literal(1)),
       # or rather does NOT have input some CytoPlasm
       # (ilxtr.hasPrimaryParticipantCardinality, 1)  # FIXME need this...
       synonyms=('single nucleus sequencing',)
    ),
    (tech.snSeq, owl.disjointWith, tech.scSeq),

    _t(tech.libraryPrep, 'nucleic acid library preparation technique',
       (ilxtr.hasPrimaryOutput, ilxtr.nucleicAcidLibrary),
       synonyms=('library prep', 'library preparation')),

    _t(tech.rnaSeq, 'RNA-seq',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryInput,
                            ilxtr.RNApolymer),  # RNA but labels are inconsistent
                      restN(ilxtr.hasPrimaryAspect,
                            asp.sequence),
                      restN(hasPart, tech.libraryPrep),
                      restN(ilxtr.hasInformationOutput,
                            ilxtr.informationArtifact)),
       intersectionOf(ilxtr.technique,
                      restN(hasPart, tech.rnaSeq)),
       synonyms=('RNAseq',),
       equivalentClass=oECN),

    # Split-seq single cell single nuclei
    # SPLiT-seq

    _t(DEV(16), 'mRNA-seq',
       (hasPart, tech.rnaSeq),
       (ilxtr.hasPrimaryInput, OntTerm('SO:0000234')
       #(ilxtr.hasPrimaryInput, ilxtr.mRNA
        #OntTerm(term='mRNA')
        # FIXME wow... needed a rerun on this fellow OntTerm('SAO:116515730', label='MRNA', synonyms=[])
       ),
       #(ilxtr.hasPrimaryAspect, asp.sequence),
       #(ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
    ),

    _t(DEV(17), 'snRNA-seq',
       #(ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:33697', label='RNA')),
       (hasPart, tech.rnaSeq),
       #(hasParticipant, OntTerm('GO:0005634', label='nucleus')),
        restMaxCardValue(ilxtr.hasPrimaryInput, OntTerm('GO:0005634', label='nucleus'), Literal(1)),
       synonyms=('snRNA-Seq',
                 'snRNAseq',
                 'sNuc-Seq',  # why sequencing community WHY
                 'single nucleus RNA-seq',)),

    _t(DEV(18), 'scRNA-seq',
       #(ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:33697', label='RNA')),
       (hasPart, tech.rnaSeq),
       #(ilxtr.hasPrimaryInput, OntTerm('SAO:1813327414', label='Cell')),
        restMaxCardValue(ilxtr.hasPrimaryInput, OntTerm('SAO:1813327414', label='Cell'), Literal(1)),
       synonyms=('scRNA-Seq',
                 'scRNAseq',
                 'single cell RNAseq',)),
        # 'deep-dive scRNA-Seq'  # deep-dive vs wide-shallow I think is what this is


    _t(DEV(19), 'Patch-seq',
       (hasPart, tech.rnaSeq),  # FIXME I don't think this modelling is correct/complete
       (ilxtr.hasPrimaryInput, ilxtr.RNApolymer),
       (hasParticipant, ilxtr.microPipette),  # FIXME TODO
       synonyms=('Patch-Seq',
                 'patch seq',)),

    _t(tech.mcSeq, 'mC-seq',
       #(ilxtr.hasPrimaryInput, ilxtr.openChromatin),  # nucleus has part?
       #(ilxtr.hasPrimaryInput, ilxtr.methylatedDNA),
       (hasPart, tech.libraryPrep),
       (ilxtr.hasPrimaryAspect, asp.methylationSequence),
       #(ilxtr.hasPrimaryInput, ilxtr.DNA),
       (ilxtr.hasPrimaryInput, ilxtr.DNApolymer),
       (ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
       def_='non CG methylation',
    ),

    _t(DEV(20), 'snmC-seq',
       (hasPart, tech.mcSeq),
       #(ilxtr.hasPrimaryInput, OntTerm('GO:0005634', label='nucleus')),
        restMaxCardValue(ilxtr.hasPrimaryInput, OntTerm('GO:0005634', label='nucleus'), Literal(1)),
       synonyms=('snmC-Seq',)),

    # mCH

    _t(tech.ATACseq, 'ATAC-seq',
       (ilxtr.hasSomething, blank(1)),
       (hasPart, tech.libraryPrep),
       (hasPart, tech.sequencing),  # TODO
       #(ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
    ),

    _t(DEV(21), 'snATAC-seq',
       (hasPart, tech.ATACseq),
       #(ilxtr.hasPrimaryInput, OntTerm('GO:0005634', label='nucleus')),
        restMaxCardValue(ilxtr.hasPrimaryInput, OntTerm('GO:0005634', label='nucleus'), Literal(1)),
       synonyms=('single-nucleus ATAC-seq',
                 'single nucleus ATAC-seq',)),

    _t(DEV(22), 'scATAC-seq',
       (hasPart, tech.ATACseq),
       #(ilxtr.hasPrimaryInput, OntTerm('SAO:1813327414', label='Cell')),
        restMaxCardValue(ilxtr.hasPrimaryInput, OntTerm('SAO:1813327414', label='Cell'), Literal(1)),
       def_='enriched for open chromatin',
       synonyms=('single-cell ATAC-seq',
                 'single cell ATAC-seq',)),

    _t(DEV(23), 'bulk ATAC-seq',
       (hasPart, tech.ATACseq),
       (ilxtr.hasSomething, blank(2)),
       synonyms=('Bulk-ATAC-seq',)),

    #'scranseq'  # IS THIS FOR REAL!?
    #'ssranseq'  # oh boy, this is just me being bad at spelling scrnaseq?

    _t(tech.dropSep, 'droplet based separation technique',
       (ilxtr.hasSomething, blank(3)),
       synonyms=('droplet sequencing', 'Droplet-Sequencing',
                 'droplet based sequencing technique')
    ),
    # FIXME I think we want to do this this way so that the sequencing techniques
    # aren't also classified as separation techniques
    cmb.Class(tech.dropSep, restriction(hasParticipant, ilxtr.dropletFormingMicrofluidicsDevice)),

    _t(DEV(24), 'Drop-seq',
       (hasPart, tech.dropSep),  # TODO
       (hasPart, tech.rnaSeq),  # TODO
       (ilxtr.isConstrainedBy, prot.dropSeq),  # TODO
       # TODO has a specific barcoding technique associated with it
       # TODO hasParticipant some droplet formming microfulidics device
       #(ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
    ),

    _t(DEV(25), 'DroNc-seq',
       (ilxtr.hasSomething, blank(4)),
       (hasPart, tech.dropSep),  # TODO
       (hasPart, tech.rnaSeq),  # TODO
       # https://www.ncbi.nlm.nih.gov/pubmed/28846088
      ),

    _t(tech.chromium3p, "chromium 3' sequencing",
       (ilxtr.hasSomething, blank(5)),
       (hasParticipant, ilxtr.chromium3pkit),
       (hasPart, tech.dropSep),  # TODO
       (hasPart, tech.rnaSeq),  # TODO
       #(ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
       def_='a droplet based sequencing library preparation technique',
       # snRNA-seq 10x Genomics Chromium v2
       # 10x Genomics Chromium V2 scRNA-seq
       # 10X (sigh)
       synonyms=('10x Genomics sequencing', '10x sequencing', '10x', 'Chromium sequencing'
                 "10x 3' chemistry", "chromium 3' assay",
                 "10x Chromium 3' chemsitry",
                 "10x chromium 3' sequencing",
                 "Chromium Single Cell 3' Library",
       )),

    _t(tech.chromium3pv1, "chromium 3' sequencing v1",
       tech.chromium3p,
       (hasParticipant, ilxtr.chromium3pv1kit),
       (hasPart, tech.rnaSeq),  # TODO
       synonyms=("10x Chromium Single Cell 3' Solution v1",
                 "10x chromium 3' v1 sequencing",
       ),  # FIXME
       comment=("different versions of the chromium 3' chemistry use different barcoding "
                'strategies and require different processing pipelines.')),

    _t(tech.chromium3pv2, "chromium 3' sequencing v2",
       tech.chromium3p,
       (hasParticipant, ilxtr.chromium3pv2kit),
       (hasPart, tech.rnaSeq),  # TODO
       synonyms=("10x Chromium Single Cell 3' Solution v2",
                 "10x chromium 3' v2 sequencing",
       ),  # FIXME
       comment=("different versions of the chromium 3' chemistry use different barcoding "
                'strategies and require different processing pipelines.')),
    (tech.chromium3pv1, owl.disjointWith, tech.chromium3pv2),

    _t(DEV(26), 'MAP-seq',
       (ilxtr.hasSomething, blank(6)),
       (hasPart, tech.sequencing),
       (hasPart, tech.libraryPrep),
       #(ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
       synonyms=('MAPseq',
                 'MAP seq',
                 'Multiplexed Analysis of Projections by Sequencing',)),

    _t(tech.smartSeq, 'SMART-seq',
       (hasPart, tech.rnaSeq),
       (hasInput, ilxtr.SMARTSeqKit),
       (ilxtr.isConstrainedBy, prot.SMARTSeq),
       # Clontech / Takara prep kits feeding Illumina?
       comment=('This space is completely loony. '
                'See https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5449089/ for a review. '
                'This is also a great example of the conflation of protocol with technique.'),
       synonyms=('Switching Mechanism at 5\' End of RNA Template sequencing',
                 'Smart-seq',
                 'SMART-Seq®',
       )),

    _t(DEV(27), 'SMART-seq2',
       # but illumina also has a page on it ...
       # what is going on
       (hasPart, tech.rnaSeq),
       (ilxtr.isImplementationOf, tech.smartSeq),
       (ilxtr.hasSomething, blank(7)),
       def_='Improved version of the Smart-seq technique',
       synonyms=('Smart-Seq2',
                 'SMART-seq2')),

    _t(DEV(28), 'SMART-seq v4',
       (hasPart, tech.rnaSeq),
       (ilxtr.isImplementationOf, tech.smartSeq),
       def_='Commercial compeitor for Smart-seq2 developed later in time',
       synonyms=('SMART-Seq v4',
                 'SMARTer v4')),

    # 'deep smart seq',

    _t(tech.anestheticAdministration, 'anesthetic adminstration technique',
       # TODO delivered to partOf primaryparticipant
       # parent partof primary participant deliver or something
      (ilxtr.hasPrimaryParticipant, restN(hasRole, OntTerm('CHEBI:38867', label='anaesthetic'))),),

    _t(tech.sedation, 'sedation technique',
       # FIXME sedative administration? reading a boring book? physical cooling? bonking on the head?
       (ilxtr.hasPrimaryAspect, asp.behavioralActivity),  # FIXME asp.activeMovement? doesn't block pain?
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       (hasParticipant, OntTerm('NCBITaxon:33208', label='Metazoa')),
       comment='QUESTION: what is the difference between sedation and anaesthesia?',
       synonyms=('sedation',)),

    _t(tech.anaesthesia, 'anaesthesia technique',
       # anaesthesia is an excellent example of a case where
       # just the use of an anaesthetic is not sufficient
       # and should not be part of the definition
       #(ilxtr.hasPrimaryParticipant,
        #cmb.Class(restriction(partOf, OntTerm('UBERON:0001016', label='nervous system')))),
       #(hasParticipant, ilxtr.anesthetic),  # FIXME has role?
       (ilxtr.hasPrimaryAspect, asp.nervousResponsiveness),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       (hasPart, tech.anestheticAdministration),
       (hasParticipant, OntTerm('NCBITaxon:33208', label='Metazoa')),
       synonyms=('anaesthesia',),
    ),
    # local anaesthesia technique
    # global anaesthesia technique
    _t(DEV(29), 'survival anaesthesia technique',
       (ilxtr.hasPrimaryAspect, asp.nervousResponsiveness),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       (hasPart, tech.anestheticAdministration),
       (hasParticipant, OntTerm('NCBITaxon:33208', label='Metazoa')),
       (ilxtr.hasSomething, blank(8)),
       synonyms=('anaesthesia with recovery',),
    ),

    _t(DEV(30), 'terminal anaesthesia technique',
       (ilxtr.hasPrimaryAspect, asp.nervousResponsiveness),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       (hasPart, tech.anestheticAdministration),
       (hasParticipant, OntTerm('NCBITaxon:33208', label='Metazoa')),
       (ilxtr.hasSomething, blank(9)),
       synonyms=('anaesthesia without recovery',
                 'anaesthesia with no recovery',),
    ),

    _t(tech.ISH, 'in situ hybridization technique',  # TODO
       intersectionOf(ilxtr.technique,  # FIXME
                      restN(ilxtr.hasPartPriParticipant, ilxtr.RNApolymer),  # FIXME non-specic open DNA binding?
                      # or is it hasPrimaryAspect_dAdS?
                      restN(ilxtr.hasPrimaryAspect, asp.complementSequencePresent),
                      restN(hasInput, ilxtr.hybridizationProbe)),
       restN(hasPart, tech.ISH),
       synonyms=('in situ hybridization', 'ISH'),
       equivalentClass=oECN),
    #(tech.ISH, owl.equivalentClass, OntTerm('NLXINV:20090610')),  # TODO

    _t(tech.FISH, 'fluorescence in situ hybridization technique',
       (hasPart, tech.ISH),
       (hasInput, ilxtr.fluorescentMolecule),
       synonyms=('fluorescence in situ hybridization', 'FISH'),
    ),

    _t(tech.smFISH, 'single-molecule fluorescence in situ hybridization technique',
       (hasPart, tech.ISH),
       (hasInput, ilxtr.fluorescentMolecule),
       (ilxtr.hasSomething, blank(10)),
       synonyms=('single-molecule fluorescence in situ hybridization',
                 'single molecule fluorescence in situ hybridization',
                 'single-molecule FISH',
                 'single molecule FISH',
                 'smFISH'),
    ),

    _t(tech.MERFISH, 'multiplexed error-robust fluorescence in situ hybridization technique',
       (hasPart, tech.ISH),
       (hasInput, ilxtr.fluorescentMolecule),
       (ilxtr.hasSomething, blank(11)),
       synonyms=('multiplexed error-robust fluorescence in situ hybridization',
                 'multiplexed error robust fluorescence in situ hybridization',
                 'multiplexed error-robust FISH',
                 'multiplexed error robust FISH',
                 'MERFISH'),
    ),

    _t(DEV(31), 'genetic technique',
       (hasParticipant,
        # the participant is really some DNA that corresponds to a gene
        OntTerm('SO:0000704', label='gene')  # prefer SO for this case?
        #OntTerm(term='gene', prefix='obo')  # representing a gene
        ),
       # FIXME OR has participant some nucleic acid...
    ),

    _t(tech.enrichment, 'enrichment technique',
       #(ilxtr.hasSomething, TEMP(42.5)),
       (ilxtr.hasPrimaryAspect, asp.proportion),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
       def_='increase proporation',  # the count stays the same
       # this is a purification technique
       # amplification is a creating technique
    ),

    _t(tech.amplification, 'amplification technique',
       (ilxtr.hasPrimaryAspect, asp['count']),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
       def_='increase number',
    ),

    _t(DEV(32), 'nucleic acid amplification technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:33696', label='nucleic acid')),
       (ilxtr.hasPrimaryAspect, asp['count']),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
      ),
    _t(DEV(33), 'expression manipulation technique',
       (ilxtr.hasSomething, blank(12))),
    _t(DEV(34), 'conditional expression manipulation technique',
       (ilxtr.hasSomething, blank(13))),

    _t(DEV(35), 'knock in technique',
       (ilxtr.hasSomething, blank(14)),
    ),
    (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000121')),

    _t(DEV(36), 'knock down technique',
       (ilxtr.hasSomething, blank(15)),
       synonyms=('underexpression technique',),
    ),

    # endogenous genetic manipulation   HRM 'HBP_MEM:0000119'
    # conditional knockout 'HBP_MEM:0000122'
    # morpholino 'HBP_MEM:0000124'
    # RNA interference 'HBP_MEM:0000123'
    # dominant-negative inhibition   sigh 'HBP_MEM:0000125'

    _t(DEV(37), 'knock out technique',
       (ilxtr.hasSomething, blank(16)),
    ),
    (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000120')),

    _t(DEV(38), 'mutagenesis technique',
       (ilxtr.hasSomething, blank(17))
    ),

    _t(DEV(39), 'overexpression technique',
       (ilxtr.hasSomething, blank(18))
    ),

    _t(tech.delivery, 'delivery technique',
       intersectionOf(ilxtr.technique,
           restN(ilxtr.hasPrimaryParticipant,
                 ilxtr.materialEntity),  # email delivery? fun... not really delivery...
           restN(ilxtr.hasPrimaryAspectActualized,
                 asp.location),
           #restN(ilxtr.hasPrimaryAspect_dAdT,
           #ilxtr.nonZero)
                     #),
       #intersectionOf(ilxtr.technique,
                      # FIXME how to use this to start in syringe end in brain?
                      # maybe using hasTechniqueContext instead?
                      restN(ilxtr.hasConstrainingAspect, asp.startLocation),
                      restN(ilxtr.hasConstrainingAspect, asp.endLocation)),
       # alternate looking only at different times doesn not work because
       # the location at both those times could stay the same :/
       # have to also include the value
       #intersectionOf(
           #restN(ilxtr.hasConstrainingAspect,
                 #intersectionOf(asp.location,  # can't use hasActualizedValue because can't tell times apart?
                                #restN(ilxtr.hasAspectContext,
                                      #asp.startTime))),
           #restN(ilxtr.hasConstrainingAspect,
                 #intersectionOf(asp.location,
                                #restN(ilxtr.hasAspectContext,
                                      #asp.endTime)))),
       #(ilxtr.hasSomething, TEMP(57.5)),
       def_='A technique for moving something from point a to point b.',
       equivalentClass=oECN),

    _t(DEV(40), 'package delivery technique',
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (ilxtr.hasPrimaryParticipant, ilxtr.package),
       # the DHL guy case
       synonyms=('parcel delivery technique',)
    ),

    _t(DEV(41), 'physical delivery technique',
       # i.e. distinct from energy released by chemical means?
       # gravity not ATP hydrolysis?
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       # FIXME
       (ilxtr.hasMotiveForce, ilxtr.physicalForce)),

    _t(DEV(42), 'diffusion based delivery technique',
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       # FIXME
       (ilxtr.hasMotiveForce, ilxtr.brownianMotion)),

    _t(DEV(43), 'bath application technique',
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       # FIXME
       (hasParticipant, ilxtr.bathSolution)),

    _t(DEV(44), 'topical application technique',
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       #(ilxtr.hasTarget, ilxtr.externalSurfaceOfOrganism)
       (ilxtr.hasTarget, ilxtr.surface),  # TODO surface as a 'generic' black box component
       comment='topical application of peanutbutter to bread is allowed',
       # potential subclasses, spread, smear, wipe, daub, dust
    ),

    _t(DEV(45), 'mechanical delivery technique',
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       # FIXME
       (ilxtr.hasMotiveForce, ilxtr.mechanicalForce)),

    _t(DEV(46), 'rocket delivery technique',
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (hasInput, ilxtr.rocket),
       comment=('This is here for (among other things) the morbid clinical scenario '
                'where someone might need to know that a nerve agent was delivered by '
                'rocket and not just released to drift on the wind, because it means '
                'that there might be additional complications.')),

    _t(OntTerm('BIRNLEX:2135'), 'injection technique',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasSomething, ilxtr.intoSomething),  # FIXME
                      restN(ilxtr.hasPrimaryAspectActualized, asp.location)),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryParticipant, ilxtr.somethingThatCanBeInjected)),  # FIXME
       synonyms=('injection',),
       # TODO def_=('must cross some barries or overcome some opposing force or obstacle')
       equivalentClass=oECN),

    _t(DEV(47), 'ballistic injection technique',
       # makes use of phenomena?
       (ilxtr.hasSomething, ilxtr.intoSomething),  # FIXME
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (ilxtr.hasSomething, blank(19))),

    _t(DEV(48), 'biolistic injection technique',
       # makes use of phenomena?
       (ilxtr.hasSomething, ilxtr.intoSomething),  # FIXME
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (ilxtr.hasSomething, blank(20))),

    _t(DEV(49), 'pressure injection technique',
       # makes use of phenomena?
       (ilxtr.hasSomething, ilxtr.intoSomething),  # FIXME
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (ilxtr.hasSomething, blank(21))),

    _t(DEV(50), 'brain injection technique',
       (hasPart, tech.injection),  # FIXME we need a way to have primary aspect + target? what is a target?
       # in other similar cases we have used hasPart, but then we have to have the
       # non-transitive hasPart because
       (ilxtr.hasPrimaryParticipant, OntTerm('UBERON:0000955')),
       synonyms=('brain injection', 'injection into the brain')),

    _t(OntTerm('BIRNLEX:2136'), 'intracellular injection technique',
       ilxtr.technique,
       (hasPart, tech.injection),
       unionOf(restN(hasPart, tech.cellPatching),  # vs oneOf? which fails to load?
               restN(hasPart, tech.sharpElectrodeTechnique)),
       (ilxtr.hasPrimaryParticipant, OntTerm('GO:0005622', label='intracellular anatomical structure')),
       #(ilxtr.hasPrimaryParticipant, OntTerm()),
       #(ilxtr.hasPrimaryParticipant, OntTerm('SAO:1289190043', label='Cellular Space')),  # TODO add intracellular as synonym
       synonyms=('intracellular injection',)),

    _t(DEV(51), 'viral injection technique',
       (hasPart, tech.injection),
       (hasParticipant, ilxtr.viralParticle),
       def_='a technique for injecting viral particles',
    ),

    _t(DEV(52), 'AAVretro injection technique',
       (hasPart, tech.injection),
       (hasParticipant, ilxtr.AAVretro),
       synonyms=('AAVretro injection',)
    ),

    _t(DEV(53), 'electrical delivery technique',
       # FIXME electroporation doesn't actually work this way
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (ilxtr.hasConstrainingAspect, asp.electrical),
       (ilxtr.hasSomething, blank(22)),
       comment='rail gun seems about as close was we can get'
    ),

    _t(tech.poration, 'poration technique',
       restN(ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
       restN(ilxtr.hasPrimaryAspectActualized, asp.permeability),
       def_='a technique for making holes in things',
       synonyms=('membrane poration technique', 'permeabilization technique')
       # FIXME vs general poration?
    ),

    _t(tech.thermalporation, 'thermalporation technique',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
                      restN(ilxtr.hasPrimaryAspectActualized, asp.permeability),
                      restN(hasPart, restN(ilxtr.hasPrimaryAspectActualized, asp.temperature))),
       synonyms=('heatshock', 'heatshock poration technique'),
    ),

    _t(tech.electroporation, 'electroporation technique',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
                      restN(ilxtr.hasPrimaryAspectActualized, asp.permeability),
                      restN(hasParticipant, ilxtr.electricalField)),  # FIXME ?
       intersectionOf(ilxtr.technique,
                      restN(hasPart, tech.electroporation)),
       # TODO can we add a check that the partOf hasParticipant cell?
       synonyms=('electropermeabilization technique',),  # FIXME sp?
       equivalentClass=oECN),

    _t(DEV(54), 'in utero electroporation technique',
       (hasPart, tech.electroporation),
       (ilxtr.hasPrimaryParticipant, restN(locatedIn, ilxtr.uterus))),
    _t(DEV(55), 'single cell electroporation technique',
       (hasPart, tech.electroporation),
       (hasPart, tech.cellPatching),
       # FIXME the target of permeability is not the cell but rather the cell membrane :/
       restMaxCardValue(ilxtr.hasPrimaryInput, OntTerm('SAO:1813327414', label='Cell'), Literal(1))),
    #_t(TEMP(77.5), 'chemical delivery technique',  # not obvious how to define this or if it is used
       #(ilxtr.hasSomething, TEMP(77.6))),
    _t(DEV(56), 'single neuron electroporation technique',
       (hasPart, tech.electroporation),
       (hasPart, tech.cellPatching),
       # FIXME the target of permeability is not the cell but rather the cell membrane :/
       restMaxCardValue(ilxtr.hasPrimaryInput,
                        OntTerm('SAO:1417703748', label='Neuron'), Literal(1))),
    #_t(TEMP(78.5), 'chemical delivery technique',  # not obvious how to define this or if it is used
       #(ilxtr.hasSomething, TEMP(78.6))),

    _t(DEV(57), 'DNA delivery technique',
       (ilxtr.hasPrimaryInput, OntTerm('SO:0001235', term='replicon')),
       # isConstrainedBy information content of the dna?
       (ilxtr.hasPrimaryAspectActualized, asp.location),
      ),
    _t(DEV(58), 'transfection technique',
       (ilxtr.hasPrimaryInput, OntTerm('SO:0001235', term='replicon')),
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (ilxtr.hasSomething, blank(23)),  # TODO hasIntention -> GO gene expression of _that_ gene?
       #(ilxtr.hasIntention, 'GO:0010467')  # FIXME or DNA amplification
       # incorporation into the hosts cellular biology?
       # into a cell?
    ),
    _t(DEV(59), 'DNA delivery technique exploiting some active biological process',
       (ilxtr.hasPrimaryInput, OntTerm('SO:0001235', term='replicon')),
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (ilxtr.hasSomething, blank(24)),
       synonyms=('DNA delivery exploiting some pre-existing mechanism technique',),
    ),
    _t(DEV(60), 'DNA delivery via primary genetic code technique',
       (ilxtr.hasPrimaryInput, OntTerm('SO:0001235', term='replicon')),
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (hasParticipant, ilxtr.primaryHeritableGeneticMaterial)),
    #_t(TEMP(84.5), 'DNA delivery via germ line technique',  # too cryptic, and is probably actually a process
       #(ilxtr.hasPrimaryInput, OntTerm('SO:0001235', term='replicon')),
       #(ilxtr.hasPrimaryAspectActualized, asp.location),
       #(ilxtr.hasSomething, TEMP(84.6))),
    _t(DEV(61), 'DNA delivery via plasmid technique',
       (ilxtr.hasPrimaryInput, OntTerm('SO:0001235', term='replicon')),
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       (hasParticipant, ilxtr.plasmidDNA)),
    _t(DEV(62), 'DNA delivery via viral particle technique',
       (ilxtr.hasPrimaryInput, OntTerm('SO:0001235', term='replicon')),
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       # notion of failure due to inadequate titer...
       (hasParticipant, ilxtr.viralParticle)),

    _t(DEV(63), 'tracing technique',
       (hasParticipant, ilxtr.axon),
       (ilxtr.hasPrimaryAspect, asp.connectivity),
       synonyms=('axon tracing technique',
                 'axonal tracing technique',
                 'axon tracing',
                 'axonal tracing',)),

    _t(proc.anterogradeMovement, 'anterograde movement',
       BFO['0000015'],
       (hasParticipant, ilxtr.materialEntity),
       #(ilxtr.processActualizesAspect, asp.distanceFromSoma),  # asp and has hasContext
       # FIXME aspects for processes
       (ilxtr.hasActualPrimaryAspect, asp.distanceFromSoma),  # asp and has hasContext
       (ilxtr.hasActualPrimaryAspect_dAdT, ilxtr.positive),  # TODO not intended ... actual
       def_='movement via active or passive means away from the soma of a cell'
      ),

    _t(proc.retrogradeMovement, 'retrograde movement',
       BFO['0000015'],
       (hasParticipant, ilxtr.materialEntity),
       #(ilxtr.processActualizesAspect, asp.distanceFromSoma),  # asp and has hasContext
       # FIXME aspects for processes
       (ilxtr.hasActualPrimaryAspect, asp.distanceFromSoma),  # asp and has hasContext
       (ilxtr.hasActualPrimaryAspect_dAdT, ilxtr.negative),
       def_='movement via active or passive means toward the soma of a cell'
      ),

    _t(DEV(64), 'anterograde tracing technique',
       (hasPart, tech.delivery),
       (hasParticipant, ilxtr.axon),
       (hasPart, proc.anterogradeMovement),
       (ilxtr.hasPrimaryAspect, asp.connectivity),
       #(ilxtr.hasConstrainingAspect, asp.direction),  # need a value... also hasParticipantPartConstrainingAspect?
       #(ilxtr.hasConstrainingAspect_value, ilxtr.awayFromSoma),  # FIXME actual binding requiress subprocess
       # has subprocess (anterograte transport/movement)
       # hasPrimaryParticipant ilxtr.materialEntity
       # hasPrimaryAspect distanceFromSoma
       # hasPrimaryAspect_dAdT ilxtr.negative
       synonyms=( 'anterograde tracing',)
    ),
    _t(DEV(65), 'retrograde tracing technique',
       (hasPart, tech.delivery),
       (hasParticipant, ilxtr.axon),
       (hasPart, proc.retrogradeMovement),
       (ilxtr.hasPrimaryAspect, asp.connectivity),
       #(ilxtr.hasConstrainingAspect, asp.direction),  # need a value... also hasParticipantPartConstrainingAspect?
       #(ilxtr.hasConstrainingAspect_value, ilxtr.towardSoma),  # FIXME actual binding requiress subprocess
       # has subprocess
       # hasPrimaryParticipant ilxtr.materialEntity
       # hasPrimaryAspect distanceFromSoma
       # hasPrimaryAspect_dAdT ilxtr.positive
       synonyms=('retrograde tracing',)
    ),
    _t(DEV(66), 'bidirectional tracing technique',
       (hasPart, tech.delivery),
       (hasParticipant, ilxtr.axon),
       (hasPart, proc.anterogradeMovement),
       (hasPart, proc.retrogradeMovement),
       (ilxtr.hasPrimaryAspect, asp.connectivity),
       synonyms=('bidirectional tracing',)
    ),
    _t(DEV(67), 'diffusion tracing technique',
       (hasParticipant, ilxtr.axon),
       (hasPart, tech.delivery),
       (ilxtr.hasPrimaryAspect, asp.connectivity),
       (ilxtr.hasSomething, blank(25)),
       synonyms=('diffusion tracing',)
    ),
    _t(DEV(68), 'transsynaptic tracing technique',
       (hasPart, tech.delivery),  # agentous delivery mechanism...
       (hasParticipant, ilxtr.axon),
       (ilxtr.hasPrimaryAspect, asp.connectivity),
       (ilxtr.hasParticipant, ilxtr.synapse),
       # more than one cell body
       synonyms=( 'transsynaptic tracing',)
    ),
    _t(DEV(69), 'monosynapse transsynaptic tracing technique',
       (hasParticipant, ilxtr.axon),
       (hasPart, tech.delivery),
       (ilxtr.hasPrimaryAspect, asp.connectivity),
       # more than cell body and more than one nerve
       (ilxtr.hasParticipant, ilxtr.synapse),  # synapses between at least 2 pairs of cells
       (ilxtr.hasSomething, blank(26)),
       synonyms=('monosynaptic transsynaptic tracing technique',
                 'monosynaptic transsynaptic tracing')),
    _t(DEV(70), 'multisynapse transsynaptic tracing technique',
       (hasParticipant, ilxtr.axon),
       (hasPart, tech.delivery),
       (ilxtr.hasPrimaryAspect, asp.connectivity),
       # more than cell body and more than one nerve
       (ilxtr.hasParticipant, ilxtr.synapse),  # synapses between at least 2 pairs of cells
       (ilxtr.hasSomething, blank(27)),
       synonyms=('multisynaptic transsynaptic tracing technique',
                 'multisynaptic transsynaptic tracing')),

    # 'TRIO'
    # 'tracing the relationship between input and output'

    _t(DEV(71), 'computational technique',  # these seem inherantly circulat... they use computation...
       ilxtr.technique,
       restMinCardValue(ilxtr.isConstrainedBy, ilxtr.algorithm, Literal(1)),  # axioms??
       (ilxtr.hasDirectInformationInput, ilxtr.informationEntity),
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       # different from?
      ),

    #_t(TEMP(98.5), 'mathematical technique',
       #(ilxtr.hasSomething, TEMP(98.6)),
       #(ilxtr.isConstrainedBy, ilxtr.algorithm),
      #),

    _t(tech.statistics, 'statistical technique',
       (ilxtr.hasDirectInformationInput, ilxtr.informationEntity),
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       (ilxtr.isConstrainedBy, ilxtr.statisticalAlgorithm),
      ),

    _t(DEV(72), 'simulation technique',
       (ilxtr.isConstrainedBy, ilxtr.algorithm),
       (ilxtr.hasDirectInformationInput, ilxtr.informationEntity),
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       (ilxtr.hasSomething, blank(28))),

    _t(DEV(73), 'storage technique',
       (ilxtr.hasPrimaryAspectActualized, asp.location),
       # to put away for future use?
       # not for immediate use
       # sir no longer appearing in this protocol
       # leaves the scope of the technique's black box
       # put something in a consistent and known location
       # so that it can be retrieved again later when needed
       #(ilxtr.hasFutureTechique, tech.unstorage)
       # changing the primary aspect to a _known_ location
       #ilxtr.hasPrimaryAspect_dAdT
       (ilxtr.hasIntention, ilxtr.saveForTheFuture),
       ),

    _t(DEV(74), 'preservation technique',
       (ilxtr.hasPrimaryAspect, asp.spontaneousChangeInStructure),
       # FIXME change in change in some aspect
       # expected change in black box if this is not done?
       # asp.unbecoming
       # FIXME InContents? in anything inside the black box?
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
      ),

    _t(DEV(75), 'tissue preservation technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.tissue),
       (ilxtr.hasPrimaryAspect, asp.spontaneousChangeInStructure),
      ),

    _t(tech.localization, 'localization technique',
       (ilxtr.hasSomething, blank(29))),

    _t(DEV(76), 'colocalization technique',
       # FIXME measurement vs putting them together?
       ilxtr.technique,
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       restMinCardValue(hasPart, tech.localization, Literal(2)),
       (ilxtr.hasPrimaryAspect, asp.location),
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       # the localtion of the primary participants of eac
      ),

    _t(DEV(77), 'image reconstruction technique',
       (ilxtr.hasDirectInformationInput, ilxtr.image),
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.isConstrainedBy, ilxtr.inverseProblemAlgorithm)),

    _t(tech.tomography, 'tomographic technique',
       (ilxtr.hasDirectInformationInput, ilxtr.image),  # more than one...
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.isConstrainedBy, ilxtr.radonTransform),
       synonyms=('tomography',)),

    _t(DEV(78), 'positron emission tomography',
       (hasPart, tech.positronEmissionImaging),
       (hasPart, tech.tomography),
       synonyms=('PET', 'PET scan')),
    (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000009')),

    # "Single-Proton emission computerized tomography"
    # "HBP_MEM:0000010"  # TODO

    _t(DEV(79), 'stereology technique',
       (hasPart, tech.statistics),
       (ilxtr.hasSomething, blank(30)),
       synonyms=('stereology',)),

    _t(DEV(80), 'design based stereology technique',
       (ilxtr.hasSomething, blank(31)),
       synonyms=('design based stereology',)),

    _t(DEV(81), 'spike sorting technique',
       (ilxtr.hasDirectInformationInput, ilxtr.timeSeries),  # TODO more specific
       (ilxtr.hasInformationOutput, ilxtr.timeSeries),  # TODO MUCH more specific
       #(ilxtr.detects, ilxtr['informationPattern/spikes'])  # TODO?
       #(ilxtr.hasSomething, TEMP(112.5)),
       (ilxtr.isConstrainedBy, ilxtr.spikeSortingAlgorithm),
       synonyms=('spike sorting',)),

    _t(DEV(82), 'detection technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       (ilxtr.detects, ilxtr.materialEntity)),
    # detecting something means you are measuring some aspect
    # even if it is as simple as the presence or absense of the
    # detected phenomena
    cmb.Class(i.p, restriction(ilxtr.hasPrimaryAspect, ilxtr.aspect)),

    _t(DEV(83), 'identification technique',
       (ilxtr.isConstrainedBy, ilxtr.identificationCriteria),  # FIXME circular and not what actually differentiates
       ),
    _t(DEV(84), 'characterization technique',
       (ilxtr.hasSomething, blank(32))),
    _t(DEV(85), 'classification technique',
       (ilxtr.isConstrainedBy, ilxtr.classificationCriteria),  # FIXME circular and not what actually differentiates
       ),
    _t(DEV(86), 'curation technique',
       # ilxtr.isConstrainedBy, curation workflow specification... not helful and not correct
       (hasParticipant, OntTerm('NCBITaxon:9606')),
       (ilxtr.hasDirectInformationInput, ilxtr.informationArtifact),
       (ilxtr.hasInformationOutput, ilxtr.informationArtifact),
       (ilxtr.hasSomething, blank(33))),

    _t(DEV(87), 'angiographic technique',
       (hasPart, ilxtr.xrayImaging),
       (ilxtr.knownDetectedPhenomena, restN(partOf, OntTerm('UBERON:0007798'))),
       synonyms=('angiography',)),

    _t(DEV(88), 'ex vivo technique',
       # (hasParticipant, ilxtr.somethingThatUsedToBeAlive),
       # more like 'was' a cellular organism
       # ah time...
       ilxtr.technique,
       (ilxtr.hasPrimaryParticipant, OntTerm('NCBITaxon:131567', label='cellular organisms')),
       # has part some technique destroying primary participant
       # we really really need dead organisms to still have that type
       # which restricts our operational definitions a bit, but that is probably a good thing
       # 'dead but can still sequence its dna to confirm that -presently- its dna is that of a mouse'
       # the technique needs to have killed the exact member otherwise you can kill one mouse and study
       # a living one
       # (ilxtr.hasPriorTechnique, tech.killing),  # FIXME HRMMMMMM with same primary participant...
       (ilxtr.hasConstrainingAspect, asp.livingness),  # FIXME aliveness?
       restHasValue(ilxtr.hasConstrainingAspect_value, Literal(False)), # Literal(False)),  # FIXME dataProperty???
       #(ilxtr.hasConstrainingAspect, asp.livingness),  # FIXME aliveness?
       # (ilxtr.hasConstrainingAspect, ilxtr['is']),
       synonyms=('ex vivo',),),

    _t(tech.inSitu, 'in situ technique',  # TODO FIXME
       # detecting something in the location that it was originally in
       # not in the dissociated remains thereof...
       # hasPrimaryParticipantLocatedIn
       # and the primary participant is located in / still part of its original part of
       # part of the thing that it was part of before the start of _any_ technique
       #(ilxtr.hasConstrainingAspect, asp.location),

       # the pimary participant is still part of the part of the primary participant of the
       # preceeding technique where the input was living
       #(ilxtr.hasConstrainingAspect, asp.location),
       #(ilxtr.hasConstrainingAspect_value, ilxtr.unchanged),  # FIXME
       (ilxtr.hasPartPriParticipant, ilxtr.materialEntity),
       (ilxtr.hasSomething, blank(34)),

       # process has part that has primary aspect actualized location
       # process has part that has constraining aspect some aspect matches
       # primary participant has part that has aspect matches # TODO not quite
       # intersectionOf(
           #ilxtr.technique,
           #restN(ilxtr.hasPrimaryParticipant,
                 #restN(hasPart, restN(ilxtr.primaryParticipantIn,
                                      #ilxtr.separationProcessPart)))),

       #(ilxtr.hasSomething, TEMP(122.5)),
       # primary participant partOf theSameContainingEntity
       synonyms=('in situ',),),
    (tech.inSitu, owl.disjointWith, tech.inVitro),

    _t(DEV(89), 'in vivo technique',
       # (hasParticipant, ilxtr.somethingThatIsAlive),
       ilxtr.technique,
       (ilxtr.hasPrimaryParticipant, OntTerm('NCBITaxon:131567', label='cellular organisms')),
       (ilxtr.hasConstrainingAspect, asp.livingness),  # FIXME rocks can have aspect aliveness,
       # aspects don't tell you about the universality of a result in the way that a quality might
       # because right now we only care about the details of the process and what we are measuring
       # that is what the value is included explicitly, because some day we might find out that our
       # supposedly universal axiom is not, and then we are cooked
       restHasValue(ilxtr.hasConstrainingAspect_value, Literal(True)), #  FIXME data property  Literal(True)),
       synonyms=('in vivo',),),

    _t(tech.animal, 'in vivo animal technique',
       # FIXME vs animal experiment ...
       # TODO we probably need a compose operator in addition to hasPart:
       # which is to say that this technique is the union of these other techniques ...
       (ilxtr.hasPrimaryParticipant, OntTerm('NCBITaxon:33208', label='Metazoa')),
       (ilxtr.hasConstrainingAspect, asp.livingness),
       restHasValue(ilxtr.hasConstrainingAspect_value, Literal(True)),
    ),

    _t(DEV(90), 'in utero technique',
       # has something in
       #(hasParticipant, ilxtr.somethingThatIsAliveAndIsInAUterus),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasConstrainingAspect, asp.location),
                      restN(ilxtr.hasConstrainingAspect_value, ilxtr.uterus)),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryParticipant, restN(locatedIn, ilxtr.uterus))),
       synonyms=('in utero',),
       equivalentClass=oECN),

    _t(tech.inVitro, 'in vitro technique',
       (ilxtr.hasSomething, blank(35)),
       (ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystemDisjointWithLivingOrganism),
       #(ilxtr.hasPrimaryParticipant, thing that was derived from living organsim? no? pure synthesis...),
       (hasParticipant, ilxtr.somethingThatIsAliveAndIsInAGlassContainer),
       # this is more complicated than it seems,
       # the idea that you can have a physiological system
       # that is not either derived from some organism ...
       synonyms=('in vitro',),),

    _t(DEV(91), 'high throughput technique',
       (ilxtr.hasSomething, blank(36)),
       # TODO has minimum cardinality 'large' on the primary participant
       synonyms=('high throughput',),),

    _t(DEV(92), 'fourier analysis technique',
       (realizes, ilxtr.analysisRole),  # FIXME needs to be subClassOf role...
       (ilxtr.isConstrainedBy, ilxtr.fourierTransform),
       synonyms=('fourier analysis',),),

    _t(DEV(93), 'sample preparation technique',
       (ilxtr.hasSomething, blank(37)),
       # TODO
       # (ilxtr.hasIntention, ???)
       # to get the thing in the right state so that it can be measured
       (ilxtr.hasPrimaryAspect, intersectionOf(asp.nonLocal,
                                               restN(ilxtr.hasContext,
                                                     # FIXME again we see that hasContext
                                                     # is much broader
                                                     ilxtr.constraintImposedByNextStep))),
       synonyms=('preparation technique',
                 'specimine preparation technique',
                 'sample preparation',
                 'specimine preparation',),),

    _t(tech.dissection, 'dissection technique',
       (ilxtr.hasPrimaryOutput, ilxtr.partOfSomePrimaryInput),  #FIXME
       comment='''
       # FIXME need to implement the dual for this
       # hasDualTechnique -> hasPrimaryInput -> hasPart <-> removal invariant aka wasPartOf
       # vs extraction technique ...
       # note that dissection may not actually be a destroying technique in all cases
       # for example microdissection or biopsy techniques
       ''',
       synonyms=('dissection',),),

    _t(DEV(94), 'atlas guided microdissection technique',
       (ilxtr.isConstrainedBy, ilxtr.parcellationAtlas),
       (ilxtr.hasPrimaryOutput, ilxtr.partOfSomePrimaryInput),  #FIXME
       synonyms=('atlas guided microdissection',),),

    _t(DEV(95), 'crystallization technique',
       (ilxtr.hasPrimaryAspect, asp.latticePeriodicity),  # physical order
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
       # cyrstallized vs amorphous
       # xray diffraction can tell you what proportion of the whole samle is crystallized (S. Manna)
       def_=('A technique for enducing a regular crystal patterning '
             'on a set of non-patterend components'),
       synonyms=('crystallization',)),

    _t(DEV(96), 'crystal quality evalulation technique',
       (ilxtr.hasPrimaryInput, ilxtr.materialEntity),
       (ilxtr.hasPrimaryAspect, asp.physicalOrderedness),
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       # (ilxtr.hasPrimaryAspect, asp.percentCrystallinity),
       # there are many other metrics that can be used that are subclasses
      ),

    _t(DEV(97), 'tissue clearing technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.tissue),
       (ilxtr.hasPrimaryAspect, asp.transparency),  # FIXME
      ),

    _t(DEV(98), 'CLARITY technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.tissue),
       (ilxtr.isConstrainedBy, prot.CLARITY),
       (ilxtr.hasPrimaryAspect, asp.transparency),  # FIXME
       def_='A tissue clearing technique',
       synonyms=('CLARITY',)),

    _t(tech.fixation, 'fixation technique',
       # prevent decay, decomposition
       # modify the mechanical properties to prevent disintegration
       # usually crosslinks proteins?
       # cyrofixation also for improving the mechanical properties
       # literally "fix" something so that it doesn't move or changed, it is "fixed" in time
       #(ilxtr.hasSomething, TEMP(135.5)),
       #(ilxtr.hasPrimaryAspect, asp.spontaneousChangeInStructure),
       #(ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       #(ilxtr.hasPrimaryAspect, asp.likelinessToDecompose),
       #(ilxtr.hasPrimaryAspect, asp.mechanicalRigidity),
       #(ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
       # TODO I think spontaneous change in structure has to be a requirement
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryAspectActualized,
                            asp.spontaneousChangeInStructure),
                      restN(ilxtr.hasPrimaryAspect_dAdT,
                            ilxtr.negativeNonZero),
                      unionOf(restN(ilxtr.hasPrimaryAspectActualized,
                                    asp.stiffness),  # mechanical rigidity
                              restN(ilxtr.hasPrimaryAspectActualized,
                                    asp.elasticity),
                              restN(ilxtr.hasPrimaryAspectActualized,
                                    asp.spontaneousChangeInStructure))),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasConstrainingAspect, asp.fixedness),
                      restN(ilxtr.hasConstrainingAspect_dAdT, ilxtr.positiveNonZero),
                     ),
       #unionOf(hasAspectChangeCombinator(asp.mechanicalRigidity, ilxtr.positive),
               # this approach was simply too verbose and didn't help with classification at all
               #hasAspectChangeCombinator(asp.spontaneousChangeInStructure, ilxtr.negative)),
       synonyms=('fixation',),
       equivalentClass=oECN),

    #cmb.Class(tech.fixation,
       #),

    _t(DEV(99), 'tissue fixation technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.tissue),
       (ilxtr.hasConstrainingAspect, asp.fixedness),
       (ilxtr.hasConstrainingAspect_dAdT, ilxtr.positiveNonZero),
       synonyms=('tissue fixation',)),

    _t(DEV(100), 'sensitization technique',
       # If we were to try to model this fully in the ontology
       # then we would have a giant hiearchy of sensitivities to X
       # when in fact sensitivity is a defined measure/aspect not
       # a fundamental aspect. It is fair to say that there could be
       # an aspect for every different way there is to measure sensitivity
       # to sunlight since the term is so broad
       (ilxtr.hasPrimaryAspectActualized, asp.sensitivity),
    ),

    _t(DEV(101), 'permeabilization technique',
       # TODO how to model 'the permeability of a membrane to X'
       #  check go
       (ilxtr.hasPrimaryAspectActualized, asp.permeability),
    ),

    _t(DEV(102), 'chemical synthesis technique',
       # involves some chemical reaction ...
       # is ioniziation a chemical reaction? e.g. NaCl -> Na+ Cl-??
       (ilxtr.hasPrimaryOutput,  OntTerm('CHEBI:24431', label='chemical entity')),
      ),
    #_t(TEMP(139.5), 'physical synthesis technique',  # this term isn't used very widely
       # e.g. making a microchip, doesn't just use chemistry, though it uses some chemistry
       # the output is not chemical...
       #(ilxtr.hasPrimaryOutput, ilxtr.materialEntity),
      #),

    _t(DEV(103), 'construction technique',
       # build something, or assemble something that cannot be removed
       # deconstruction vs destruction, deconstruction usually suggests
       # can't be reconstructed? but then we reconstructive surgery
       (ilxtr.hasPrimaryOutput, ilxtr.building),  # TODO
       (ilxtr.hasSomething, blank(38)),
      ),

    _t(DEV(104), 'assembly technique',
       # put something together
       # suggests that disassembly is possible
       (ilxtr.hasPrimaryOutput, ilxtr.materialEntity),  # TODO
       (ilxtr.hasSomething, blank(39)),
      ),

    _t(DEV(105), 'mixing technique',
       #tech.creating,  # not entirely clear that this is the case...
       #ilxtr.mixedness is circular
       (ilxtr.hasSomething, blank(40)),
       synonyms=('mixing',),),

    _t(DEV(106), 'agitating technique',
       #tech.mixing,
       # allocation on failure?
       # classification depends exactly on the goal
       (ilxtr.hasSomething, blank(41)),
       synonyms=('agitating',),),

    _t(DEV(107), 'stirring technique',
       #tech.mixing,  # not clear, the intended outcome may be that the thing is 'mixed'...
       (ilxtr.hasSomething, blank(42)),
       synonyms=('stirring',),),

    _t(DEV(108), 'dissolving technique',
       (ilxtr.hasSomething, blank(43)),
       synonyms=('dissolve',),),

    _t(DEV(109), 'husbandry technique',
       # FIXME maintenance vs growth
       # also how about associated techniques?? like feeding
       # include in the oec or 'part of some husbandry technique'??
       # alternately we can change it to hasParticipant ilxtr.livingOrganism
       # to allow them to include techniques where locally the
       # primary participant is something like food, instead of the organism HRM
       (ilxtr.hasPrimaryInputOutput,  # vs primary participant
        OntTerm('NCBITaxon:1', label='root')
       ),
       synonyms=('culture technique', 'husbandry', 'culture'),
      ),

    _t(DEV(110), 'feeding technique',
       # metabolism required so no viruses
       # TODO how to get this to classify as a maintenance technique
       #  without having to include the entailment explicitly
       #  i.e. how do we deal side effects of processes

       (ilxtr.hasPrimaryInputOutput, OntTerm('NCBITaxon:131567', label='cellular organisms')),
       (hasInput, ilxtr.food),  # this works because hasPart food allocation technique will lift to this
       synonyms=('feeding',)),

       # this is a legitimate case where there is no easy
       # way to communicate a side effect of feeding
       # I will thing a bit more on this but I think it is the easiest way
       # maybe a general class axiom or something like that could do it
       # FIXME the issue is that the primary aspects will then start to fight...
       #  there might be a way to create a class that will work using
       #  ilxtr.hasSideEffectTechnique or ilxtr.hasSideEffect?

    _t(DEV(111), 'high-fat diet feeding technique',
       (ilxtr.hasPrimaryInputOutput, OntTerm('NCBITaxon:131567', label='cellular organisms')),
       (ilxtr.hasPrimaryAspectActualized, asp.weight),
       (hasInput, ilxtr.highFatDiet),
    ),

    _t(DEV(112), 'mouse circadian based high-fat diet feeding technique',
       (ilxtr.hasPrimaryInputOutput, OntTerm('NCBITaxon:10090', label='Mus musculus')),
       # ie that if one were to measure rather than specify
       # the mouse should be in in the same phase during the activity
       (ilxtr.hasConstrainingAspect, asp.circadianPhase),  # TODO? 'NBO:0000169'
       (ilxtr.hasPrimaryAspectActualized, asp.weight),
       (hasInput, ilxtr.highFatDiet),
       ),

    _t(DEV(113), 'mouse age based high-fat diet feeding technique',
       # TODO there are a whole bunch of other high fat diet feeding techniques
       # 'MmusDv:0000050'
       # as opposed to the primary aspect being the current point in the cyrcadian cycle
       (ilxtr.hasPrimaryInputOutput, OntTerm('NCBITaxon:10090', label='Mus musculus')),
       (ilxtr.hasConstrainingAspect, OntTerm('PATO:0000011', label='age')),  # FIXME not quite right
       (ilxtr.hasPrimaryAspectActualized, asp.weight),  # FIXME not quite right
       (hasInput, ilxtr.highFatDiet),
       # (hasInput, ilx['researchdiets/uris/productnumber/D12492']),  # too specific
       ),

    _t(DEV(114), 'bacterial culture technique',
       #(hasParticipant, OntTerm('NCBITaxon:2', label='Bacteria <prokaryote>')),
       (ilxtr.hasPrimaryInputOutput, OntTerm('NCBITaxon:2')),  # FIXME > 1 label
       synonyms=('bacterial culture',),),

    _t(tech.cellCulture, 'cell culture technique',
       (ilxtr.hasPrimaryInputOutput, OntTerm('SAO:1813327414', label='Cell')),
       # maybe useing subClassOf instead of equivalentClass?
       synonyms=('cell culture',),),
    # I think this is the right way to add 'non-definitional' restrictions to a technique
    cmb.Class(tech.cellCulture,
        restriction(ilxtr.hasConstrainingAspect, asp.temperature),
        restriction(hasInput, ilxtr.cultureMedia)),

    _t(DEV(115), 'yeast culture technique',
       (ilxtr.hasPrimaryInputOutput, OntTerm('NCBITaxon:4932', label='Saccharomyces cerevisiae')),
       synonyms=('yeast culture',),),

    _t(DEV(116), 'tissue culture technique',
       (ilxtr.hasPrimaryInputOutput, ilxtr.tissue),
       synonyms=('tissue culture',),),

    _t(DEV(117), 'slice culture technique',
       (ilxtr.hasPrimaryInputOutput, intersectionOf(ilxtr.brainSlice,
                                                    ilxtr.physiologicalSystem)),
       synonyms=('slice culture',),),

    _t(DEV(118), 'open book preparation technique',
       tech.maintaining,
       (hasInput,
        OntTerm('UBERON:0001049', label='neural tube')
        #OntTerm(term='neural tube', prefix='UBERON')  # FIXME dissected out neural tube...
       ),
       (ilxtr.hasSomething, blank(44)),
       synonyms=('open book culture', 'open book preparation'),),

    _t(DEV(119), 'fly culture technique',
       (ilxtr.hasPrimaryInputOutput,
        OntTerm('NCBITaxon:7215', label='Drosophila <flies,genus>')
        #OntTerm(term='drosophila')
       ),
       synonyms=('fly culture',),),

    _t(DEV(120), 'rodent husbandry technique',
       (ilxtr.hasPrimaryInputOutput,
        OntTerm('NCBITaxon:9989', label='Rodentia')  # FIXME population vs individual?
       ),
       synonyms=('rodent husbandry', 'rodent culture technique'),),

    _t(DEV(121), 'enclosure design technique',  # FIXME design technique? produces some information artifact?
       (ilxtr.hasSomething, blank(45))),

    _t(DEV(122), 'housing technique',
       (ilxtr.hasSomething, blank(46)),
       synonyms=('housing',),
    ),
    _t(DEV(123), 'mating technique',
       ilxtr.technique,
       restMinCardValue(hasParticipant, ilxtr.sexuallyReproducingOrgansim, Literal(2)),
       synonyms=('mating',),
    ),
    _t(DEV(124), 'watering technique',
       (ilxtr.hasPrimaryInputOutput, OntTerm('NCBITaxon:131567', label='cellular organisms')),
       (hasInput, ilxtr.water),  # no output
       synonyms=('watering',),
    ),

    _t(tech.contrastEnhancement, 'contrast enhancement technique',
       #restMinCardValue(ilxtr.hasParticipantPartConstrainingAspect, ilxtr.aspect, Literal(1)),
       #restMinCardValue(ilxtr.hasConstrainingAspect, ilxtr.aspect, Literal(1)),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasParticipantPartPrimaryAspect, ilxtr.aspect),
                      restN(ilxtr.hasPartNotPart,
                            intersectionOf(restN(ilxtr.hasPrimaryAspectActualized, asp.location),
                                           # FIXME need to be able to say that pp part primary aspect and
                                           # part pp constraining aspect are the same
                                           restMinCardValue(ilxtr.hasConstrainingAspect,
                                                            ilxtr.aspect,
                                                            Literal(1))))),
       #intersectionOf(ilxtr.technique,
                      #restN(ilxtr.hasPrimaryAspect, asp.contrast),
                      #restN(ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive)),
       #intersectionOf(ilxtr.technique,
                      # FIXME vs contrast detection
                      #restN(ilxtr.hasProbe, ilxtr.materialEntity)),
       synonyms=('contrast enhancement',
                 'material contrast enhancement technique',),
       equivalentClass=oECN),

    _t(DEV(125), 'tagging technique',
       (ilxtr.hasSomething, blank(47))),

    _t(tech.histology, 'histological technique',
       # is this the assertional/definitional part where we include everything?
       (ilxtr.hasPrimaryParticipant, ilxtr.tissue),
       #(ilxtr.hasSomething, TEMP(172.5)),
       synonyms=('histology',)),

    _t(OntTerm('BIRNLEX:2107'), 'staining technique',  # TODO integration
       (ilxtr.hasSomething, blank(48))),

    _t(DEV(126), 'immunochemical technique',
       (ilxtr.hasSomething, blank(49))),

    _t(DEV(127),'immunocytochemical technique',
       (ilxtr.hasSomething, blank(50)),
       (hasInput, ilxtr.cell),
       synonyms=('immunocytochemistry technique',
                 'immunocytochemistry')),

    _t(OntTerm('NLXINV:20090609'), 'immunohistochemical technique',  # TODO
       (ilxtr.hasSomething, blank(51)),
       (hasInput, ilxtr.tissue),
       synonyms=('immunohistochemistry technique',
                 'immunohistochemistry')),
    (OntTerm('NLXINV:20090609'), ilxtr.hasTempId, OntTerm("HBP_MEM:0000115")),

    # TODO "HBP_MEM:0000116"
    # "Immunoelectron microscopy"

    _t(DEV(128), 'direct immunohistochemical technique',
       (ilxtr.hasSomething, blank(52)),
       synonyms=('direct immunohistochemistry technique',
                 'direct immunohistochemistry')),
    _t(DEV(129), 'indirect immunohistochemical technique',
       (ilxtr.hasSomething, blank(53)),
       synonyms=('indirect immunohistochemistry technique',
                 'indirect immunohistochemistry')),

    _t(tech.stateBasedContrastEnhancement, 'state based contrast enhancement technique',
       #tech.contrastEnhancement,  # FIXME compare this to how we modelled fMRI below? is BOLD and _enhancement_?
       (ilxtr.hasSomething, blank(54)),

    ),

    _t(ilxtr.separationProcessPart, 'separation process',
       # FIXME this definition would also work for homogenization/mixing
       # each part has a different location based on the aspect vs
       # each part has the 'same' location based on the aspect (e.g. density of fat vs protein in milk)
       intersectionOf(BFO['0000015'],  # infers correctly but include for clarity
           restN(partOf, tech.separation),
           restN(ilxtr.hasPrimaryAspectActualized, asp.location),
           #restN(ilxtr.hasPrimaryAspect_dAdT, ilxtr.nonZero),  # TODO
           restN(ilxtr.hasConstrainingAspect, ilxtr.aspect),
       ),
       def_='this is probably too detailed a model, better to have a measure of separateness',
       equivalentClass=oECN),

    _t(tech.separating, 'separating technique',
       intersectionOf(
           ilxtr.technique,
           restN(ilxtr.hasPrimaryAspectActualized, asp.homogenaity),  # TODO vs Constraining
           restN(ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero)),
       intersectionOf(
           ilxtr.technique,
           restN(ilxtr.hasPrimaryParticipant,
                 restN(hasPart, restN(ilxtr.primaryParticipantIn,
                                      ilxtr.separationProcessPart)))),
       equivalentClass=oECN),

    _t(tech.separation, 'separation technique (old)',
       # TODO owl.inverseOf homogenization
       # the aspect of each part is to separate it by class
       # the location of each of its parts
       # the rule for transforming an aspect of the _parts_ into
       # the location aspect is the key differentiator
       #(ilxtr.knownDifferentiatingPhenomena, ),
       #restN(hasPart, )
       #(ilxtr.hasPrimaryAspectActualized, asp.location),  # TODO we need a clearer subclass for this
       intersectionOf(
           ilxtr.technique,
           restN(ilxtr.hasPrimaryParticipant,
                 restN(hasPart, restN(ilxtr.primaryParticipantIn,
                                      ilxtr.separationProcessPart)))),
                           #intersectionOf(
                               #restN(partOf, i.p),
                               #restN(ilxtr.hasPrimaryAspectActualized, asp.location),
                               #restN(ilxtr.hasConstrainingAspect, ilxtr.aspect))))))),

       #intersectionOf(ilxtr.tchnique,
                      #restN(ilxtr.hasPartPriAspect, restN(hasPart, ()))
                     #),
       #intersectionOf(ilxtr.technique,
                      #restN(ilxtr.hasPartPart,
                            #intersectionOf(restN(ilxtr.hasPrimaryAspectActualized, asp.location),
                                           #ilxtr.primaryParticipantPartOfPrimaryParticipantOfParent,
                                           # intentionally not requiring this to be a technique
                                           #restMinCardValue(ilxtr.hasConstrainingAspect,
                                                            #ilxtr.aspect,
                                                            #Literal(1))))),
       #intersectionOf(ilxtr.technique,
                      #restN(ilxtr.hasParticipantPartPrimaryAspectActualized, asp.location),
                      #restMinCardValue(ilxtr.hasParticipantPartConstrainingAspect,
                                       #ilxtr.aspect,
                                       #Literal(1))),
       #restMinCardValue(ilxtr.hasParentPrimaryAspect, ilxtr.aspect, Literal(1)),
       # primary input has parts that can all actualize on the same set of aspects
       # hasConstrainingAspect maybe??
       #(ilxtr.hasConstrainingAspect, ilxtr.aspect),
       # VS FIXME TODO does the cardinality restriction work for auto subclassing?
       # FIXME hasConstrainingAspect is implicitly on the primary participant, these are on its parts...
       #restMinCardValue(ilxtr.hasConstrainingAspect, ilxtr.aspect, Literal(1)),
       #(ilxtr.hasSomething, TEMP(183.5)),
       equivalentClass=oECN),

    _t(DEV(130), 'filtering technique',
       (hasPart, intersectionOf(
           ilxtr.allocatingProcessPart,
           restN(ilxtr.hasConstrainingAspect, asp.size)))),

    _t(DEV(131), 'sorting technique',
       ilxtr.technique,
       # FIXME has part vs has member?
       (ilxtr.hasPrimaryParticipant,
        restN(hasPart,
              restN(ilxtr.primaryParticipantIn,
                    intersectionOf(ilxtr.separationProcessPart,
                                   restN(ilxtr.hasPrimaryAspect,
                                         asp.categoryAssigned),  # FIXME nonLocal
                                   restN(ilxtr.hasConstrainingAspect,
                                         # another true predicate
                                        asp.isCategoryMember))))),

       # FIXME named => there is a larger black box where the name _can_ be measured
       # hasPrimaryParticipant partOf (hasAspect ilxtr.aspect)
       # or is it partOf (hasPrimaryAspect ilxtr.aspect)?
       # note that for this approach axioms appear automatically as
       # the unresolved names
       #(ilxtr.hasParticipantPartPrimaryAspectActualized, asp.category),
       #(ilxtr.hasParticipantPartConstrainingAspect, ilxtr.aspect)
      ),

    _t(DEV(132), 'extraction technique',
       (hasParticipant, ilxtr.extract),  # FIXME circular
       ),
    _t(tech.precipitation, 'precipitation technique',
       (hasParticipant, ilxtr.precipitate),  # FIXME circular
      ),
    _t(DEV(133), 'pull-down technique',
       (hasPart, tech.precipitation),
       # allocation enrichement
       (ilxtr.hasSomething, blank(55)),),
    _t(DEV(134), 'isolation technique',
       # enrichment
       (ilxtr.hasSomething, blank(56)),),
    _t(DEV(135), 'purification technique',
       # enrichment
       (ilxtr.hasSomething, blank(57)),),

    _t(DEV(136), 'fractionation technique',
       (ilxtr.hasSomething, blank(58)),),
    _t(DEV(137), 'chromatography technique',
       (ilxtr.hasParticipantPartPrimaryAspectActualized, asp.location),
       (ilxtr.hasParticipantPartConstrainingAspect, asp.partitionCoefficient),
       synonyms=('chromatography',),),
    _t(DEV(138), 'distillation technique',
       (ilxtr.hasParticipantPartConstrainingAspect, asp.boilingPoint),
       (ilxtr.hasParticipantPartConstrainingAspect, asp.condensationPoint),
       #(ilxtr.knownDifferentiatingPhenomena, asp.boilingPoint),
       #(ilxtr.knownDifferentiatingPhenomena, asp.condensationPoint),
       synonyms=('distillation',),),
    _t(tech.electrophoresis, 'electrophoresis technique',
       #(ilxtr.hasSomething, TEMP(196.5)),
       (ilxtr.hasParticipantPartPrimaryAspectActualized, asp.location),
       (ilxtr.hasParticipantPartConstrainingAspect, asp.size),
       (ilxtr.hasParticipantPartConstrainingAspect, asp.charge),
       (ilxtr.hasParticipantPartConstrainingAspect, asp.bindingAffinity),  # FIXME ... this is qualified...
       synonyms=('electrophoresis',),),
    _t(DEV(139), 'centrifugation technique',
       intersectionOf(ilxtr.technique,
                      restN(hasInput, ilxtr.centrifuge)),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasParticipantPartPrimaryAspectActualized, asp.location),
                      restN(ilxtr.hasParticipantPartConstrainingAspect, asp.size),  # TODO hasImplicitMeasurement
                      restN(ilxtr.hasParticipantPartConstrainingAspect, asp.shape),
                      restN(ilxtr.hasParticipantPartConstrainingAspect, asp.density)),
       #(ilxtr.knownDifferentiatingPhenomena, asp.size),  # TODO hasImplicitMeasurement
       #(ilxtr.knownDifferentiatingPhenomena, asp.shape),
       #(ilxtr.knownDifferentiatingPhenomena, asp.density),
       synonyms=('centrifugation',),
       equivalentClass=oECN),
    _t(DEV(140), 'ultracentrifugation technique',
       (hasInput, ilxtr.ultracentrifuge),
       synonyms=('ultracentrifugation',),),

    _t(DEV(141), 'sampling technique',
       # selection technqiue, not a separation technique
       # it has to do with picking
       (ilxtr.hasSomething, blank(59)),),
    _t(DEV(142), 'selection technique',
       (ilxtr.hasSomething, blank(60)),),
    _t(DEV(143), 'blind selection technique',
       (ilxtr.hasSomething, blank(61)),),
    _t(DEV(144), 'random selection technique',
       (ilxtr.hasSomething, blank(62)),),
    _t(DEV(145), 'targeted selection technique',
       (ilxtr.hasSomething, blank(63)),),

    _t(DEV(146), 'biological activity measurement technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystem),
       (ilxtr.hasPrimaryAspect, asp.biologicalActivity),  # TODO
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       synonyms=('activity measurement technique', 'bioassay')),

    _t(DEV(147), 'observational technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       # non numerical? interpretational?
       (ilxtr.hasSomething, blank(64)),
       synonyms=('observation', 'observation technique'),),

    _t(DEV(148), 'procurement technique',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryAspectActualized, asp.location),
                      restN(ilxtr.hasConstrainingAspect, asp.endLocation),
                      restN(ilxtr.hasPrimaryParticipant,  # FIXME vs hasPrimaryOutput...
                            # could have part some delivery technique
                            # distingushed from delivery technique in that it only
                            # cares about the _endpoint_ not start and end
                            OntTerm('BFO:0000040', label='material entity')
                            #OntTerm(term='material entity', prefix='BFO')
                      )),
       #(ilxtr.hasPrimaryOutput,  # primary outputs imply creation
        #OntTerm('BFO:0000040', label='material entity')
        #OntTerm(term='material entity', prefix='BFO')
       #),
       def_='A technique for getting or retrieving something.',
       synonyms=('acquisition technique', 'procurement', 'acquistion', 'get'),
       equivalentClass=oECN),

    # naming
    oc(tech.naming, ilxtr.technique),
    olit(tech.naming, rdfs.label, 'naming'),
    olit(tech.naming, definition ,
         ('Naming is an assertional process that is orthogonal to measuring.'
          'Names may be assigned as a product of measurements, but the assignment '
          'of a name can only be based on aspects of the thing, the name can never be '
          'an aspect of the thing. Names may also be assigned based on aspects of the '
          'process that produced the thing, or the prvious state of the thing. '
          'For example a protein dissociated from its original cell/tissue no longer '
          'contains sufficient information to reconsturct where it came from based on '
          'any measurements that can be made on it beyond the species that it came from '
          'and maybe where the individual lived if there are enough atoms to do an isotope test.'
          'A cell on the other hand may very well have enough information in its RNA and DNA to '
          'allow for a bottom up assignment of a name based on its gene expression pattern.')),

    _t(tech.ising, 'ising technique',
       (ilxtr.hasPrimaryAspect, asp['is']),
       def_=('Ising techniques are techniques that affect whether a thing \'is\' or not. '
             'Whether they primary participant \'is\' in this context must shall be determined '
             'by whether measurements made on the putative primary particiant '
             'provide data that meet the necessary and sufficient criteria for the putative primary '
             'participant to be assigned the categorical name as defined by the '
             'primary particiant\'s owl:Class. For example if the primary particiant of a technique '
             'is 100ml of liquid water, then a boiling technique which produces gaseous water from '
             'liquid water negatively affects the isness of the 100ml of liquid water because we can '
             'no longer assign the name liquid water to the steam that is produced by boiling.')),

    olit(tech.ising, rdfs.comment,
         ('Because \'isness\' or \'being\' is modelled as an aspect it is implied that '
          '\'being\' in this context depends entirely on some measurement process and some '
          'additional process for classifying or categorizing the object based on that measurement, '
          'so that it can be assigned a name. The objective here is to demistify the process of '
          'assigning a name to a thing so that it will be possible to provide exact provenance '
          'for how the assignment of the name was determined.')),

    # allocating

    _t(ilxtr.allocatingProcessPart, 'allocating process',
       intersectionOf(BFO['0000015'],  # infers correctly but include for clarity
           restN(partOf, tech.allocating),  # FIXME would be nice to have a generator on this...
           restN(ilxtr.hasPrimaryAspectActualized, asp.location)),
       equivalentClass=oECN),

    _t(tech.allocating, 'allocating technique',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryAspectActualized,
                            # FIXME intrinsic extrinsic issue :/
                            asp.location)),
       # FIXME allocation of a part of the primary participant
       intersectionOf(
           restN(ilxtr.hasPrimaryParticipant,
                 restN(hasPart, restN(ilxtr.primaryParticipantIn,
                                      ilxtr.allocatingProcessPart)))),
       # FIXME no information output
       def_=('Allocating techniques move things around without changing how their participants '
             'are named. More accurately they move them around without changing any part of their '
             'functional defintions which are invariant as a function of their location.'),
      equivalentClass=oECN),

    _t(tech.aliquoting, 'aliquoting technique',
       # TODO should be subClassOf allocating
       (ilxtr.hasSomething, blank(65)),
      ),

    # disjointness
    (tech.allocating, owl.disjointWith, tech.measuring),  # i am an idiot
    (tech.allocating, owl.disjointWith, tech.probing),
    (tech.allocating, owl.disjointWith, tech.ising),
    (tech.measuring, owl.disjointWith, tech.probing),
    (tech.measuring, owl.disjointWith, tech.ising),
    (tech.probing, owl.disjointWith, tech.ising),

    #cmb.Class(None, disjointUnionOf(tech.allocating, tech.measuring, tech.ising, tech.probing)),
    # why doesn't this work?
    # measured does not imply actualized
    # FIXME what about tech.actualizing? i think it is ising or allocating
    # FIXME this causes issues
    # we may need to split hasPrimaryAspect into hasPrimaryAspectMeasure hasPrimaryAspectActualized
    # better to just add hasPrimaryAspectActualized for allocation and friends since pretty much all
    # aspects end up being measured one way or another, they have to be
    #cmb.Class(tech.allocating,
        #cmb.Pair(owl.disjointWith,  # overkill using oec but it works
               #oc_.full_combinator(oec(
                   #ilxtr.technique,
                   #restrictionN(ilxtr.hasInformationOutput,
                                #ilxtr.informationEntity))))),

    # measuring
    _t(tech.measuring, 'measuring technique',
       # TODO is detection distinct from measurement if there is no explicit symbolization?
       (ilxtr.hasPrimaryAspect, ilxtr.aspect),  # if you are measuring something you had bettered know what you are measuring
       #(ilxtr.detects, ilxtr.materialEntity),  # FIXME
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),  # observe that this not information artifact
       # FIXME has primary input?
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity #OntTerm('BFO:0000001', label='entity')
        # FIXME vs hasPrimaryParticipant
        # go with material entity since seeing data processing under measurement seems off
       ),
       synonyms=('measure', 'measurment technique'),
    ),

    # actualizing
    _t(tech.actualizing, 'actualizing technique',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryAspectActualized, ilxtr.aspect)),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasParticipantPartPrimaryAspectActualized, ilxtr.aspect)),
       # taking action to make the value
       #unionOf(tech.ising, tech.allocating),
       def_='a technique that realizes a value of some aspect',
       synonyms=('actualize',),
       equivalentClass=oECN),

    # probing
    _t(tech.probing, 'probing technique',  # manipulating, poking, purturbing, changing state
       (ilxtr.hasProbe, owl.Thing),
       #(ilxtr.hasProbe, OntTerm('BFO:0000040', label='material entity')),
       # FIXME technically could be an informational entity?
       # if I probe someone by speaking latin but they do not respond
       # vs if they do it is not the physical content of the sounds
       # it is how they interact with the state of the other person's brain
       def_=('Probing techniques attempt (intende) to change the state of a thing without changing '
            'how it is named. Hitting something with just enough light to excite but not to '
            'bleach would be one example, as would poking something with a non-pointy stick.'
           ),
     ),

    _t(tech.creating, 'creating technique',   # FIXME mightent we want to subclass off of these directly?
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryOutput, ilxtr.materialEntity)),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryAspect, asp['is']),
                      restN(ilxtr.hasPrimaryAspect_dAdT, ilxtr.positiveNonZero)),
       synonyms=('synthesis technique',),
       equivalentClass=oECN),
    (tech.creating, owl.disjointWith, tech.destroying),
    # NOTE ! creating and destroying are only with respect to the primary participant
    # it is entirely possible to have a composite technique that has two parts
    # one of which is destroying and the other of which is creating
    # and to link those two parts in such as way as to assert the symmetry

    # attempt to create a class that explicitly does not have relationships to the same other class
    #oc(ilxtr._helper0),
    #olit(ilxtr._helper0, 'that have classes that are primary participants and outputs of the same technique'),
    #disjointwith(oec(None, ilxtr.technique,
                  #*restrictions((ilxtr.hasPrimaryParticipant,
                                  #OntTerm('continuant', prefix='BFO'))))),
    #obnode(object_predicate_combinator(rdf.type, owl.Class),
           #oec_combinator(ilxtr.technique,
                     #(ilxtr.hasPrimaryParticipant,)
                     #(hasOutput,))),

    _t(tech.destroying, 'destroying technique',
       # owl.unionOf with not ilxtr.disjointWithOutput of? not this will not work
       (ilxtr.hasPrimaryAspect, asp['is']),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),),

    _t(tech.maintaining, 'maintaining technique',
       # if these were not qualified by the primary participant
       # then this would be both a creating and a destroying technique
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryAspect, asp['is']),
                      restN(ilxtr.hasPrimaryAspect_dAdT, ilxtr.zero)),  # FIXME value?
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryInputOutput, ilxtr.materialEntity)),
       synonyms=('maintenance technique',),
       equivalentClass=oECN),

    _t(tech.analysis, 'analysis technique',
       (realizes, ilxtr.analysisRole),
       synonyms=('analysis',),),

    _t(DEV(149), 'data processing technique',
       (ilxtr.hasDirectInformationInput, ilxtr.informationEntity),
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),
       synonyms=('data processing', 'data transformation technique'),),

    _t(DEV(150), 'image processing technique',
       (ilxtr.hasDirectInformationInput, ilxtr.image),
       (ilxtr.hasInformationOutput, ilxtr.image),
       # some subpart may have the explicit output it just requires the direct input
       synonyms=('image processing',),),

    _t(tech.sigproc, 'signal processing technique',
       (ilxtr.hasDirectInformationInput, ilxtr.timeSeries),
       (ilxtr.hasInformationOutput, ilxtr.timeSeries),
       synonyms=('signal processing',),),

    _t(DEV(151), 'signal filtering technique',
       # FIXME aspects of information entities...
       # lots of stuff going on here...
       tech.sigproc,
       (ilxtr.hasInformationPrimaryAspect, asp.spectrum),
       (ilxtr.hasInformationPrimaryAspect_dAdT, ilxtr.negativeNonZero),
       (ilxtr.hasInformationPrimaryParticipant, ilxtr.timeSeries),  # FIXME
       synonyms=('signal filtering',),
    ),

    _t(tech.ephys, 'electrophysiology technique',
       # TODO is this one of the cases where partonomy implies techniqueness?
       # note ephys is not itself a measurement technique? stimulation can occur without measurement
       # technique and (hasPart some i.p)
       intersectionOf(ilxtr.technique,
                      restN(hasInput, ilxtr.ephysRig)),
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryAspect, asp.electromagnetic),  # FIXME...
                      restN(ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystem)),
       synonyms=('electrophysiology', 'electrophysiological technique'),
       equivalentClass=oECN),
    (tech.ephys, ilxtr.hasTempId, OntTerm('HBP_MEM:0000014')),

    _t(tech.IRDIC, 'IR DIC video microscopy',
       (hasInput, ilxtr.IRCamera),
       (ilxtr.detects, ilxtr.infaredLight),  # FIXME should be bound to the camera and propagate
       (hasInput, ilxtr.DICmicroscope),
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),  # how to deal with the parts of a primary input?
       # TODO
      ),

    _t(DEV(152), 'in vitro IR DIC slice electrophysiology',
       #(hasPart, tech.IRDIC),
       (hasInput, ilxtr.IRCamera),
       (hasInput, ilxtr.DICmicroscope),
       (ilxtr.hasPrimaryInput, ilxtr.acuteBrainSlice),  # how to deal with the parts of a primary input?
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (hasPart, ilxtr.cellPatching),
       (hasPart, ilxtr.eClamp),
       (ilxtr.hasInformationOutput, ilxtr.timeSeries),
      ),

    _t(tech.ephysRecording, 'electrophysiology recording technique',
       ilxtr.technique,
       (ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystem),
       #oneOf((hasInput, ilxtr.physiologicalSystem),
             #(hasInput, OntTerm('NCBITaxon:1'))),
       (ilxtr.hasPrimaryAspect, asp.electrical),  # FIXME...
       #(ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystem),
       #(hasPart, tech.ephys),
       (ilxtr.hasInformationOutput, ilxtr.timeSeries),
       synonyms=('electrophysiology recording',),
      ),

    _t(tech.contrastDetection, 'contrast detection technique',
       # a subclass could be differential contrast to electron scattering or something...
       #(ilxtr.hasPrimaryAspect_dAdPartOfPrimaryParticipant, ilxtr.nonZero),  # TODO FIXME this is MUCH better
       (ilxtr.hasPrimaryAspect, asp.contrast),  # contrast to something? FIXME this seems a bit off...
       (ilxtr.hasPrimaryAspect_dAdS, ilxtr.nonZero),
       synonyms=('contrast detection',),
    ),

    _t(tech.microscopy, 'microscopy technique',
       (hasInput, ilxtr.microscope),  # electrophysiology microscopy techinque?
       # can't use hasParticipant because we need it to be distinct from 'microscope production technique'
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       synonyms=('microscopy',),
    ),

    _t(DEV(153), 'microscope production technique',
       (ilxtr.hasPrimaryOutput, ilxtr.microscope),
      ),

    _t(DEV(154), 'recording electrode production technique',
       (ilxtr.hasPrimaryOutput, ilxtr.recordingElectrode),
      ),

    _t(DEV(155), 'micropipette production technique',
       (ilxtr.hasPrimaryOutput, ilxtr.microPipette)),

    _t(DEV(156), 'microscope repair technique',
       (ilxtr.hasPrimaryInputOutput, ilxtr.microscope)),

    _t(tech.lightMicroscopy, 'light microscopy technique',
       (hasInput, OntTerm('BIRNLEX:2112', label='Optical microscope')),  # FIXME light microscope !
       (ilxtr.detects, ilxtr.visibleLight),  # TODO photos?
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       #(ilxtr.detects, OntTerm(search='visible light', prefix='obo')),
       #(ilxtr.detects, OntTerm(search='photon', prefix='NIFSTD')),
       #(hasParticipant, OntTerm(term='visible light')),  # FIXME !!! detects vs participant ???
       synonyms=('light microscopy',)),

    _t(DEV(157), 'confocal microscopy technique',
       (hasInput, OntTerm('BIRNLEX:2029', label='Confocal microscope')),
       (ilxtr.detects, ilxtr.visibleLight),
       (ilxtr.isConstrainedBy, OntTerm('BIRNLEX:2258', label='Confocal imaging protocol')),
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       synonyms=('confocal microscopy',)),

    _t(DEV(158), 'phase contrast microscopy technique',  # TODO
       (hasInput, ilxtr.phaseContrastMicroscope),  # FIXME circular
       (ilxtr.detects, ilxtr.visibleLight),  # FIXME true??
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       synonyms=('phase contrast microscopy',)),

    _t(tech.imaging, 'imaging technique',
       (ilxtr.hasPrimaryAspect, ilxtr.aspect),
       # FIXME... contrast isnt quite right
       # it is more total energy flux in a spectrum to which the detection medium is opaque
       # over some area with some resolution, though the difference is that imaging is
       # spatial in nature where as pure particle detection is less spatial and more event based
       #(ilxtr.hasPrimaryAspect, asp.contrast),
       #(ilxtr.hasPrimaryAspect, asp.detectedThingPresent),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),  # the thing to be imaged
       (ilxtr.hasInformationOutput, ilxtr.image),
       def_='Imaging is the process of forming an image.',
       synonyms=('imaging',),
       #equivalentClass=oECN
    ),

    _t(DEV(159), 'functional brain imaging',
       intersectionOf(ilxtr.technique,
                      # TODO figure out how to tie in the bFA, maybe make it 'functional' contrast
                      # suitably nebulous to allow for many operational definitions
                      #restN(ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),  # this is interpretational
                      restN(ilxtr.hasPrimaryAspect, asp.contrast),  # this is what is actually measured
                      restN(ilxtr.hasInformationOutput, ilxtr.image),
                      restN(ilxtr.hasPrimaryParticipant,
                            OntTerm('UBERON:0000955', label='brain'))),
       # FIXME this is very verbose...
       intersectionOf(ilxtr.technique,
                      #restN(ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
                      restN(ilxtr.hasPrimaryAspect, asp.contrast),  # this is what is actually measured
                      restN(ilxtr.hasInformationOutput, ilxtr.image),
                      restN(ilxtr.hasPrimaryParticipant,
                            restN(partOf,
                                  OntTerm('UBERON:0000955', label='brain')))),

       #restN(ilxtr.hasPrimaryParticipant,
             #unionOf(OntTerm('UBERON:0000955', label='brain'),
                     #restN(partOf,
                           #OntTerm('UBERON:0000955', label='brain')))),
       #(ilxtr.hasPrimaryAspect, asp.anySpatioTemporalMeasure),  # FIXME and thus we see that 'functional' is a buzzword!
       #(ilxtr.hasPrimaryAspect_dAdS, ilxtr.nonZero),
       synonyms=('imaging that relies on contrast provided by differential aspects of some biological process',),
       equivalentClass=oECN),
    (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000007')),

    _t(DEV(160), 'photographic technique',
       (ilxtr.detects, ilxtr.photons),  # FIXME acctually it detects energy in _any_ form including electrons
       #(ilxtr.hasPrimaryAspect, asp.contrast),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),  # the scene
       (ilxtr.hasInformationOutput, ilxtr.photograph),
       synonyms=('photography',),
    ),

    _t(tech.positronEmissionImaging, 'positron emission imaging',
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       (ilxtr.detects, ilxtr.positron),
       #(ilxtr.hasPrimaryAspect, asp.contrast),  # contrast to positrons... TODO model as gca?
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.detects, ilxtr.positron)),

    cmb.Class(None,  # FIXME this doesn't work because it can't fill in the specifics...
        intersectionOf(restN(ilxtr.detects, ilxtr.materialEntity),
                       restN(ilxtr.hasPrimaryAspect, asp.contrast)),
        oECN(restN(ilxtr.hasPrimaryAspect,
                   intersectionOf(asp.contrast,
                                  restN(ilxtr.hasMaterialContext, ilxtr.interactingPhenomena),
                                  restN(ilxtr.hasAspectContext, asp.dynamicRange))))),

    _t(tech.opticalImaging, 'optical imaging',
       # FIXME TODO what is the difference between optical imaging and light microscopy?
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       (ilxtr.detects, ilxtr.visibleLight),  # owl:Class photon and hasWavelenght range ...
       #(ilxtr.hasPrimaryAspect, ilxtr.contrast),
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('light imaging', 'visible light imaging'),
    ),
    (tech.opticalImaging, ilxtr.hasTempId, OntTerm("HBP_MEM:0000013")),

    _t(DEV(161), 'intrinsic optical imaging',
       #tech.opticalImaging,
       #tech.contrastDetection,
       # this is a good counter example to x-ray imaging concernts
       # because it shows clearly how
       # "the reflectance to infared light by the brain"
       # that is not a thing that is a derived thing I think...
       # it is an aspect of the black box, it is not a _part_ of the back box
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       #(ilxtr.hasProbe, ilxtr.visibleLight),  # FIXME
       (ilxtr.detects, ilxtr.visibleLight),  # FIXME
       #(ilxtr.hasPrimaryAspect, asp.contrast),
       #(ilxtr.hasPrimaryAspect, ilxtr.intrinsicSignal),  # this is a 'known phenomena'
       #(ilxtr.knownProbedPhenomena, ilxtr.intrinsicSignal),
       (ilxtr.hasSomething, ilxtr.intrinsicSignal),
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('intrinsic signal optical imaging',),
    ),

    _t(ilxtr.xrayImaging, 'x-ray imaging',
       #tech.imaging,
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       (ilxtr.hasInformationOutput, ilxtr.image),
       #(ilxtr.hasPrimaryAspect, asp.contrast),
       (ilxtr.detects, ilxtr.xrays),
       # VS contrast in the primary aspect being the signal created by the xrays...
       # can probably expand detects in cases where there are non-aspects...
       # still not entirely sure these shouldn't all be aspects too...

       # TODO need a way to deal with the fact that what we really care about here
       # is the connection to the fact that there is some pheonmena that has
       # differential contrast to the pheonmena
    ),  # owl:Class photon and hasWavelenght range ...

    _t(tech.MRI_ImageProcessing, 'magnetic resonance image processing',
       # the stuff that goes on inside the scanner
       # or afterward to produce the 'classic' output data
       # this way we can create as many subclasses of contrast as we need
       (ilxtr.hasDirectInformationInput, ilxtr.image),  # TODO raw mri image
       (ilxtr.hasPrimaryAspect, asp.contrast),  # contrast to something? FIXME this seems a bit off...
       (ilxtr.hasPrimaryAspect_dAdS, ilxtr.nonZero),
       (ilxtr.hasInformationOutput, ilxtr.spatialFrequencyImageStack),  # TODO FIXME
       (ilxtr.hasSomething, blank(66)),
      ),

    _t(tech.MRI, 'magnetic resonance imaging',
       #tech.imaging,
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
                      restN(hasInput, ilxtr.MRIScanner),
                      # NRM is an aspect not one of the mediators FIXME
                      restN(ilxtr.hasPrimaryAspect, asp.nuclearMagneticResonance),
                      # FIXME nmr vs nrm contrast... detection vs measurement
                      #restN(ilxtr.hasPrimaryAspect, asp.NMRcontrast),
                      restN(hasPart, tech.MRI_ImageProcessing)),
       intersectionOf(ilxtr.technique,
                      restN(hasPart, tech.MRI)),
       # as long as the primaryAspect is subClassOf asp.nuclearMagneticResonance then we are ok
       # and we won't get duplication of primary aspects
       synonyms=('MRI', 'nuclear magnetic resonance imaging'),
       equivalentClass=oECN),

    _t(tech.fMRI, 'functional magnetic resonance imaging',
       (ilxtr.isConstrainedBy, prot.fMRI),
       (hasPart, tech.MRI),
       (hasPart, tech.fMRI_ImageProcessing),
      ),

    _t(tech.fMRI_ImageProcessing, 'fMRI image processing',
       # FIXME hasPart MRI image processing?
       (ilxtr.hasDirectInformationInput, ilxtr.image),
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasSomething, blank(67)),
      ),

    olit(tech.fMRI, rdfs.comment,
         ('In contrast to previous definitions of fMRI technqiues, here we try to '
          'remain agnostic as possible about the actual phenomena that is being detected '
          'since it is still a matter of scientific exploration. The key is that the process '
          'follows a protocol that sets the proper parameters on the scanner (and uses the '
          'proper scanner).')),

    _t(tech.dwMRI, 'diffusion weighted magnetic resonance imaging',
       # FIXME the primary participant isn't really water so much as it is
       #  the water that is part of the primary participant...

       intersectionOf(ilxtr.technique,
                      restrictionN(hasPart, tech.MRI),
                      # TODO 'knownProbedPhenomena' or something similar
                      # TODO
                      #restrictionN(ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:15377', label='water')),
                      restrictionN(hasPart, tech.dwMRI_ImageProcessing)),
       intersectionOf(ilxtr.technique,
                      restrictionN(ilxtr.isConstrainedBy, prot.dwMRI)),
       synonyms=('dwMRI', 'diffusion weighted nuclear magnetic resonance imaging'),
       equivalentClass=oECN),

    _t(tech.dwMRI_ImageProcessing, 'diffusion weighted MRI image processing',
       (ilxtr.hasDirectInformationInput, ilxtr.image),
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasSomething, blank(68)),
      ),

    _t(proc.diffusion, 'diffusion process',
       BFO['0000015'],
       (hasParticipant, ilxtr.materialEntity),  # collective material entity?
       (ilxtr.hasActualPrimaryAspect, asp.allocation),  # dispersion dispersal
       def_=('a process where particles spread out due to random motion')),

    _t(tech.DTI, 'diffusion tensor imaging',  # FIXME very much
       intersectionOf(ilxtr.technique,
                      restrictionN(hasPart, tech.dwMRI),
                      restrictionN(hasPart, tech.DTI_ImageProcessing)),
       intersectionOf(ilxtr.technique,
                      restrictionN(ilxtr.isConstrainedBy, prot.DTI)),
           # FIXME not clear that this should be in the intersection...
           # it seems like it may make more sense to do these as unions?
           # TODO kpp kdp
       intersectionOf(ilxtr.technique,
                      restrictionN(hasInput, ilxtr.MRIScanner),
                      # NOTE using processes is prior knowledge
                      restrictionN(hasPart, proc.diffusion)),
       synonyms=('DTI',),
       equivalentClass=oECN),

    _t(tech.DTI_ImageProcessing, 'diffusion tensor image processing',
       (ilxtr.hasDirectInformationInput, ilxtr.image),
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasSomething, blank(69)),
      ),

    _t(DEV(162), 'electroencephalography',
       (ilxtr.hasSomething, blank(70)),
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystem),  # FIXME uberon part of should work for this?
       (ilxtr.hasInformationOutput, ilxtr.timeSeries),
       synonyms=('EEG',)),
    (i.p, ilxtr.hasTempId, OntTerm("HBP_MEM:0000011")),

    _t(DEV(163), 'magnetoencephalography',
       (ilxtr.hasSomething, blank(71)),
       (ilxtr.hasPrimaryParticipant, OntTerm('NCBITaxon:40674', 'Mammalia')),
       (ilxtr.hasPrimaryAspect, asp.magnetic),
       (ilxtr.hasInformationOutput, ilxtr.timeSeries),
       synonyms=('MEG',)),
    (i.p, ilxtr.hasTempId, OntTerm("HBP_MEM:0000012")),

    # modification techniques
    _t(DEV(164), 'modification technique',
       # FIXME TODO
       (ilxtr.hasPrimaryAspect, asp.isClassifiedAs),
       # is classified as
       synonyms=('state creation technique', 'state induction technique')
    ),

    _t(tech.activityModulation, 'activity modulation technique',
       (ilxtr.hasProbe, ilxtr.materialEntity),  # FIXME some pheonmena... very often light...
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
       synonyms=('modulation technique', 'modulation', 'activity modulation')),

    _t(DEV(165), 'activation technique',
       (ilxtr.hasProbe, ilxtr.materialEntity),  # FIXME some pheonmena... very often light...
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
       # hasPrimaryAspect some aspect of the primary participant which FOR THAT PARTICIPANT
       # has been defined as functional owl.hasSelf?
       # hasSelf asp.functional !??! no, not really what we want
       #(hasPart, ilxtr.),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positiveNonZero),
    ),

    _t(DEV(166), 'deactivation technique',
       (ilxtr.hasProbe, ilxtr.materialEntity),  # FIXME some pheonmena... very often light...
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),  # FIXME this is more state?
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
    ),

    _t(tech.killing, 'killing technique',
       (ilxtr.hasPrimaryAspect, asp.aliveness),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
      ),

    _t(tech.euthanasia, 'euthanasia technique',
       (ilxtr.hasPrimaryAspect, asp.aliveness),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
       synonyms=('euthanasia',),
    ),

    _t(tech.perfusion, 'perfusion technique',
       (ilxtr.hasSomething, blank(72)),
      ),

    _t(DEV(167), 'intracardial perfusion technique',
       (ilxtr.hasSomething, blank(73)),
       synonyms=('intracardial perfusion',),
      ),

    _t(DEV(168), 'pharmacological technique',
       intersectionOf(ilxtr.technique,
                      #restN(ilxtr.hasProbe, ilxtr.molecule),  # FIXME on a living system?
                      restN(hasInput, restN(hasRole, OntTerm('CHEBI:23888')))),
       intersectionOf(ilxtr.technique,
                      #restN(ilxtr.hasProbe, ilxtr.molecule),  # FIXME on a living system?
                      restN(hasInput, restN(hasRole, OntTerm('CHEBI:38632')))),
       synonyms=('pharmacology',),
       equivalentClass=oECN),

    _t(DEV(169), 'ttx bath application technique',
       (hasParticipant, ilxtr.bathSolution),
       (ilxtr.hasPrimaryAspectActualized, asp.location),  # in bath?
       (ilxtr.hasPrimaryInput, OntTerm('CHEBI:9506')),
      ),

    _t(DEV(170), 'photoactivation technique',
       (ilxtr.hasProbe, ilxtr.photons),
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positiveNonZero),
    ),

    _t(DEV(171), 'photoinactivation technique',
       (ilxtr.hasProbe, ilxtr.photons),
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
    ),

    _t(DEV(172), 'photobleaching technique',
       (ilxtr.hasProbe, ilxtr.photons),
       (ilxtr.hasSomething, blank(74)),
    ),

    _t(DEV(173), 'photoconversion technique',
       (ilxtr.hasProbe, ilxtr.photons),
       (ilxtr.hasSomething, blank(75)),
    ),

    _t(DEV(174), 'molecular uncaging technique',
       # FIXME caged molecule?
       (ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:25367', label='molecule')),
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positiveNonZero),
       synonyms=('uncaging', 'uncaging technique')
    ),

    _t(DEV(175), 'physical modification technique',
       # FIXME for all physical things is it that the aspect is physical?
       # or that there is actually a physical change induced?
       (ilxtr.hasSomething, blank(76)),
    ),

    _t(DEV(176), 'ablation technique',
       (ilxtr.hasSomething, blank(77)),
    ),

    _t(DEV(177), 'blinding technique',
       (ilxtr.hasPrimaryAspect, asp.vision),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
    ),

    _t(DEV(178), 'crushing technique',
       # tissue destruction technique
       (ilxtr.hasSomething, blank(78)),
    ),

    _t(DEV(179), 'deafferenting technique',
       # tissue destruction technique
       (ilxtr.hasSomething, blank(79)),
    ),

    _t(DEV(180), 'depolarization technique',
       (ilxtr.hasPrimaryAspect, asp.voltage),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positiveNonZero),  # or is it neative (heh)
       # yes this is confusing, but cells have negative membrane potentials
    ),

    _t(DEV(181), 'hyperpolarization technique',
       (ilxtr.hasPrimaryAspect, asp.voltage),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
    ),

    _t(DEV(182), 'illumination technique',
       # as distinct from a technique for illuminating a page in a medieval text
       #tech.agnostic,  # TODO agnostic techniques try to do nothing scientific usually
       # they are purely goal driven
       #(ilxtr.phenomena, ilxtr.photons),
       (ilxtr.hasPrimaryAspectActualized, asp.lumenance),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positiveNonZero),
    ),

    _t(DEV(183), 'lesioning technique',
       (hasPart, tech.surgical),  # is this true
       # has intention to destory some subset of the nervous system
       (ilxtr.hasSomething, blank(80)),
    ),

    _t(DEV(184), 'sensory deprivation technique',
       (ilxtr.hasPrimaryAspect, asp.sensory),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
       (ilxtr.hasSomething, blank(81)),
    ),

    _t(DEV(185), 'transection technique',
       (hasPart, tech.surgical),
       (ilxtr.hasSomething, blank(82)),
    ),

    _t(DEV(186), 'stimulation technique',
       #(ilxtr.hasPrimaryAspect, ilxtr.physiologicalActivity),  # TODO
       (ilxtr.hasProbe, ilxtr.materialEntity),
       (ilxtr.hasPrimaryAspect, asp.biologicalActivity),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positiveNonZero),
    ),

    #cmb.Class(None,  # FIXME this is incorrect the equivalence is asymmetric
        # and the way we are using biological activity does not imply phsyiology
        #intersectionOf(ilxtr.technique,
                       #restN(ilxtr.techniqueHasAspect, asp.biologicalActivity)),
        #oECN(intersectionOf(ilxtr.technique,
                            #restN(ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystem)))),

    _t(DEV(187), 'physical stimulation technique',  # FIXME another use of physical
       (ilxtr.hasSomething, blank(83)),
       (ilxtr.hasProbe, ilxtr.mechanicalForce),  # but is this physical?
       def_='A technique using mechanical force to enduce a state change on a system.',
       synonyms=('mechanical stimulation technique',)
    ),

    _t(DEV(188), 'electrical stimulation technique',
       #(ilxtr.hasProbe, asp.electrical),  # FIXME the probe should be the physical mediator
       #(ilxtr.hasProbe, ilxtr.electricalPhenomena),  # electircal field?
       (ilxtr.hasProbe, ilxtr.electricalField),  # electircal field?
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasSomething, blank(84)),
    ),

    _t(tech.stim_Magnetic, 'magnetic stimulation technique',
       # TODO need a way to accomodate the stimulation of biological activity
       # with the stimulating phenomena
       # has intention to stimulate???
       (ilxtr.hasProbe, ilxtr.magneticField),  # FIXME TODO duality between stimulus and response...
       (ilxtr.hasPrimaryAspect, asp.magnetic),
    ),

    _t(DEV(189), 'transcranial magnetic stimulation technique',
       (ilxtr.hasProbe, ilxtr.magneticField),
       (ilxtr.hasPrimaryAspect, asp.magnetic),
       (ilxtr.hasSomething, blank(85)),
    ),

    _t(DEV(190), 'cortico-cortical evoked potential technique',
       (ilxtr.hasSomething, blank(86)),
    ),

    _t(DEV(191), 'microstimulation technique',
       (ilxtr.hasSomething, blank(87)),
    ),

    _t(tech.cutting, 'cutting technique',
       (ilxtr.hasPrimaryInput, ilxtr.cuttingTool),  # FIXME tool use...
       # TODO
      ),

    _t(tech.surgical, 'surgical technique',
       (ilxtr.hasSomething, blank(88)),
       # any technique that involves the destruction of some anatomical structure
       # which requires healing (if possible)
       (hasPart, tech.cutting),  # FIXME obviously too broad
       synonyms=('surgery',),),

    cmb.Class(DEV(192), cmb.Pair(rdfs.label, Literal('reconstructive surgery')),  # FIXME TODO
        oec(restN(hasPart, tech.surgical),
            restN(ilxtr.hasIntention, ilxtr.toReconstruct))),

    _t(DEV(193), 'biopsy technique',
       (hasPart, tech.surgical),  # FIXME
       #tech.maintaining,  # things that have output tissue that don't unis something
       # this is not creating so it is not a primary output
       # if maintaining and creating are disjoin on primary inputs then have to be careful
       # about usage of hasOutput vs hasPrimaryOutput
       (ilxtr.hasPrimaryOutput, ilxtr.tissue),  # TODO
    ),

    _t(DEV(194), 'craniotomy technique',
       (hasPart, tech.surgical),  # FIXME
       (ilxtr.hasSomething, blank(89)),
       def_='Makes a hold in the cranium (head).',
    ),

    _t(DEV(195), 'durotomy technique',
       (hasPart, tech.surgical),  # FIXME
       (ilxtr.hasSomething, blank(90)),
       def_='Makes a hold in the dura.',
    ),

    _t(DEV(196), 'transplantation technique',
       (hasPart, tech.surgical),  # FIXME
       (ilxtr.hasSomething, blank(91)),
       synonyms=('transplant',)
    ),

    _t(DEV(197), 'implantation technique',
       (hasPart, tech.surgical),  # FIXME
       (ilxtr.hasSomething, blank(92)),
    ),

    _t(DEV(198), 'stereotaxic technique',
       (hasPart, tech.surgical),  # FIXME
       (hasInput, ilxtr.stereotax),
       (ilxtr.isConstrainedBy, ilxtr.stereotaxiCoordinateSystem),
    ),

    _t(DEV(199), 'behavioral technique',  # FIXME this is almost always actually some environmental manipulation
       # asp.behavioral -> 'Something measurable aspect of an organisms behavior. i.e. the things that it does.'
       (ilxtr.hasPrimaryAspect, asp.behavioral),
    ),

    _t(DEV(200), 'behavioral conditioning technique',
       (ilxtr.hasSomething, blank(93)),
       def_='A technique for producing a specific behavioral response to a set of stimuli.',  # FIXME
       synonyms=('behavioral conditioning', 'conditioning', 'conditioning technique')
    ),

    _t(DEV(201), 'environmental manipulation technique',
       # FIXME extremely broad, includes basically everything we do in science that is not
       # done directly to the primary subject
       (ilxtr.hasPrimaryParticipant, ilxtr.notTheSubject),
    ),

    _t(DEV(202), 'environmental enrichment technique',
       (ilxtr.hasSomething, blank(94)),
       synonyms=('behavioral enrichment technique',)
       # and here we see the duality between environment and behavior
    ),

    _t(DEV(203), 'dietary technique',
       # FIXME this doesn't capture feeding and watering as we might expect
       #ilxtr.technique,
       # unionOf hasPart dietary technique OR hasPrimaryParticipant food
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryInput, ilxtr.food_and_water),
                      restN(ilxtr.hasPrimaryAspectActualized, asp.allocation)),
       intersectionOf(ilxtr.technique,
                      restN(hasPart, i.p)),
       #unionOf(intersectionOf(
           #restrictionN(ilxtr.hasPrimaryParticipant, ilxtr.food_and_water),  # metabolic input
           #restrictionN(ilxtr.hasPrimaryAspect, asp.allocation)),
           #restrictionN(hasPart, i.p))
       equivalentClass=oECN),

    _t(DEV(204), 'dietary enrichment technique',
       (hasInput, ilxtr.food_and_water),
       # NOTE the aspect could be amount or diversity
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positiveNonZero),
    ),

    _t(DEV(205), 'dietary restriction technique',
       #(ilxtr.hasSomething, TEMP(299.5)),
       (hasInput, ilxtr.food_and_water),  # metabolic input
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),  # FIXME may need to use has part?
       # reduction in some metabolic input
    ),

    _t(DEV(206), 'food deprivation technique',
       (ilxtr.hasPrimaryInput, ilxtr.food),
       (ilxtr.hasPrimaryAspectActualized, asp.allocation),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
       # the above is correct, use hasPart
       # where the food amount is decresed, how to bind food to negative
       # do we have to use has part?!
       #hasPart, food
       #(hasParticipant, ilxtr.food),
       #(ilxtr.hasConstrainingAspect, asp.amount),
       #cmb.Class(ilxtr.food,
           #asp.amount, ilxtr.negative),
       #hasAspectChangeCombinator(asp.amount, ilxtr.negative),
       synonyms=('starvation technique',
                 'food restriction technique',
                )
    ),

    _t(DEV(207, current=False), 'technique that makes use of food deprivation',
       (hasPart, i.p),),

    _t(DEV(208), 'water deprivation technique',
       (ilxtr.hasPrimaryInput, ilxtr.water),
       (ilxtr.hasPrimaryAspectActualized, asp.allocation),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negativeNonZero),
       synonyms=('water restriction technique',
                 'water restriction',
       )
    ),

    _t(tech.sectioning, 'sectioning technique',
       #tech.destroying,  # ok to assert here
       # easier than having say inputs are not outputs every time
       # NOTE: the thing to be sectioned is thus the primary participant
       # conservation of mass/energy implies that it is also a creating technique
       # if viewed from the persective of the sections
       # we should be able to infer that the outputs
       # from a sectioning technique were 'created'
       (ilxtr.hasPrimaryOutput, ilxtr.section),
       #(hasOutput, ilxtr.sectionsOfPrimaryInput),  # FIXME circular
       #(hasOutput,
        #oc_.full_combinator(intersectionOf(
            #ilxtr.partOfSomePrimaryInput,
            #restN(partOf,
                  #restrictionN(ilxtr.primaryParticipantIn,
                               #tech.sectioning)),
            #restrictionN(ilxtr.hasAssessedAspect,
            #restN(ilxtr.hasConstrainingAspect, asp.flatness)))),
                        #intersectionOf(
                        # hasAssessedAspect better than hasAspect?
                        # implies there is another technique...
                        # you can measure the flatness of the himallayals
                        # or of an electron if you wanted
                        # so hasAspect is maybe not the best?
       synonyms=('sectioning',)),  # FIXME
    cmb.Class(tech.sectioning, restriction(ilxtr.hasDualInputTechnique, tech.destroying)),

    _t(DEV(209), 'tissue sectioning technique',
       (ilxtr.hasPrimaryOutput, ilxtr.section),
       # FIXME primary participant to be destroyed? seems like there is a comflict here...
       # the cardinality rules are not catching it?
       # FIXME conflict between primary participant and output?
       #(ilxtr.hasDualInputTechnique, tech.destroying), # tech.brainInputTechnique?
       (ilxtr.hasPrimaryParticipant, OntTerm('UBERON:0000479', label='tissue')),
       synonyms=('tissue sectioning',)),

    _t(DEV(210), 'brain sectioning technique',
       (ilxtr.hasPrimaryOutput, ilxtr.section),
        (ilxtr.hasDualTechnique,
         restN(ilxtr.hasPrimaryInput,
               OntTerm('UBERON:0000955', label='brain'))),
       #(ilxtr.hasDualInputTechnique, tech.destroying),  # TODO
       #(ilxtr.hasPrimaryParticipant, OntTerm('UBERON:0000955', label='brain')),
       synonyms=('brain sectioning',)),
    #cmb.Class(i.p,),

    _t(DEV(211), 'block face sectioning technique',
       # SBEM vs block face for gross anatomical registration
       tech.sectioning,
       (ilxtr.hasSomething, blank(95)),
    ),

    _t(DEV(212), 'microtomy technique',
       (hasInput, ilxtr.microtome),
       #(ilxtr.hasDualInputTechnique, tech.destroying),  # TODO
       (ilxtr.hasPrimaryOutput, ilxtr.thinSection),  # this prevents issues with microtome based warfare techniques
       synonyms=('microtomy',)
    ),

    _t(DEV(213), 'ultramicrotomy technique',
       (hasInput, ilxtr.ultramicrotome),
       (ilxtr.hasPrimaryOutput, ilxtr.veryThinSection),  # FIXME > 1?
       synonyms=('ultramicrotomy',)
    ),

    _t(DEV(214), 'array tomographic technique',
       (hasPart, tech.lightMicroscopy),
       #(hasParticipant, ilxtr.microscope),  # FIXME more precisely?
       (hasPart, tech.tomography),
       #(ilxtr.hasInformationInput, ilxtr.image),
       #(ilxtr.hasInformationOutput, ilxtr.image),
       #(ilxtr.isConstrainedBy, ilxtr.radonTransform),
       synonyms=('array tomography', 'array tomography technique')
    ),

    _t(tech.electronMicroscopy, 'electron microscopy technique',
       (hasInput, OntTerm('BIRNLEX:2041', label='Electron microscope', synonyms=[])),
       (ilxtr.detects, OntTerm('CHEBI:10545', label='electron')),  # FIXME chebi ok in this context?
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       # hasProbe ilxtr.electron and some focusing elements and detects ilxtr.electron
       synonyms=('electron microscopy',)),
    (tech.electronMicroscopy, oboInOwl.hasDbXref, OntTerm('NLX:82779')),  # ICK from assay branch which conflates measurement :/

    _t(tech.scanningElectronMicroscopy, 'scanning electron microscopy technique',
       (hasInput, OntTerm('BIRNLEX:2044', label='Scanning electron microscope', synonyms=[])),
       (ilxtr.detects, OntTerm('CHEBI:10545', label='electron')),  # FIXME chebi ok in this context?
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       # hasProbe ilxtr.electron and some focusing elements and detects ilxtr.electron
       synonyms=('scanning electron microscopy', 'SEM')),

    _t(DEV(215), 'electron tomography technique',
       (hasPart, tech.electronMicroscopy),
       (hasPart, tech.tomography),
       synonyms=('electron tomography',),
      ),

    _t(DEV(216), 'correlative light-electron microscopy technique',
       #(hasInput, OntTerm('BIRNLEX:2041', label='Electron microscope')),
       # this works extremely well because the information outputs propagate nicely
       (hasPart, tech.lightMicroscopy),
       (hasPart, tech.electronMicroscopy),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('correlative light-electron microscopy',)
    ),

    _t(DEV(217), 'serial blockface electron microscopy technique',
       (hasPart, tech.electronMicroscopy),
       (hasPart, tech.ultramicrotomy),
       (hasInput, ilxtr.serialBlockfaceUltraMicrotome),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       #(hasParticipant, OntTerm('BIRNLEX:2041', label='Electron microscope')),
       #(hasParticipant, ilxtr.ultramicrotome),
       synonyms=('serial blockface electron microscopy',)
    ),

    _t(DEV(218), 'super resolution microscopy technique',
       #(hasParticipant, OntTerm('BIRNLEX:2106', label='Microscope', synonyms=[])),  # TODO more
       (hasPart, tech.lightMicroscopy),  # FIXME special restriction on the properties of the scope?
       (ilxtr.isConstrainedBy, ilxtr.superResolutionAlgorithm),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       synonyms=('super resolution microscopy',)
    ),

    _t(DEV(219), 'northern blotting technique',
       (hasPart, tech.electrophoresis),
       # fixme knownDetectedPhenomena?
       (ilxtr.hasPrimaryParticipant, OntId('CHEBI:33697')),
       (ilxtr.hasProbe, ilxtr.hybridizationProbe),  # has part some probe addition?
       (ilxtr.hasPrimaryAspect, asp.sequence),
       synonyms=('northern blot',)
    ),
    _t(DEV(220), 'Southern blotting technique',
       (hasPart, tech.electrophoresis),
       #(ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:16991', term='DNA')),
       (ilxtr.hasPrimaryParticipant, ilxtr.DNApolymer),
       (ilxtr.hasProbe, ilxtr.hybridizationProbe),
       (ilxtr.hasPrimaryAspect, asp.sequence),
       synonyms=('Southern blot',)
    ),
    _t(DEV(221), 'western blotting technique',
       # FIXME dissociated
       (hasPart, tech.electrophoresis),
       (ilxtr.hasPrimaryParticipant, OntTerm('PR:000000001', label='protein')),  # at least one
       (ilxtr.hasProbe, OntTerm('BIRNLEX:2110', label='Antibody')),
       # FIXME is this really a probes in the way that say, an xray is a probe? I think yes
       # they create the contrast that will later be detected
       (ilxtr.hasPrimaryAspect, asp.epitopePresent),  # in sufficient quantity?
       # epitope is in theory more physical, but since we don't understand the mechanism
       # we don't really know what the antibody is 'measuring' about the epitope
       # to deal with this we make it a binary aspect and use the intentional nature of
       # has primary aspect to deal with false negatives
       # false negative is a failure with respect to a binary aspect intention caused by
       # a report of false when the omega measure implementation of the aspect on the
       # black box evaluates to true
       synonyms=('wester blot',
                 'protein immunoblot',)),
    (i.p, ilxtr.hasTempId, OntTerm("HBP_MEM:0000112")),

    _t(DEV(222), 'intracellular electrophysiology technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('GO:0005622', label='intracellular anatomical structure')),
       # FIXME in a physiological (not dead) system
       (ilxtr.hasPrimaryAspect, asp.electrical),
       #(ilxtr.hasPrimaryParticipant, OntTerm('SAO:1289190043', label='Cellular Space')),  # TODO add intracellular as synonym
    ),

    _t(tech.extracellularEphys, 'extracellular electrophysiology technique',
       # or is it hasPrimaryParticipant hasPart some extracellularSpace? (no)
       (ilxtr.hasPrimaryParticipant, OntTerm('GO:0005615', label='extracellular space')),
       (ilxtr.hasPrimaryAspect, asp.electrical),
    ),
    (tech.extracellularEphys, ilxtr.hasTempId, OntTerm('HBP_MEM:0000015')),

    _t(tech.singleElectrodeEphys, 'single electrode extracellular electrophysiology technique',
       # FIXME extracellular space that is part of some other participant... how to convey this...
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasPrimaryParticipant, OntTerm('GO:0005615', label='extracellular space')),
       (hasInput, ilxtr.singleElectrode),  # cardinality 1?
       synonyms=('extracellular single electrode technique',)),
       (tech.singleElectrodeEphys, ilxtr.hasTempId, OntTerm('HBP_MEM:0000019')),

    _t(tech.multiElectrodeEphys, 'multi electrode extracellular electrophysiology technique',
       # FIXME extracellular space that is part of some other participant... how to convey this...
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasPrimaryParticipant, OntTerm('GO:0005615', label='extracellular space')),
       (hasInput, ilxtr.multiElectrode),  # cardinality n?
       synonyms=('extracellular multi electrode technique',)),
       (tech.singleElectrodeEphys, ilxtr.hasTempId, OntTerm('HBP_MEM:0000019')),

    _t(DEV(223), 'multi electrode extracellular electrophysiology recording technique',
       (hasPart, tech.multiElectrodeEphys),
       (hasPart, tech.ephysRecording),
       synonyms=('multi unit recording',
                 'multi unit recording technique',
                 'multi-unit recording',),
      ),
    _t(DEV(224), 'single electrode extracellular electrophysiology recording technique',
       (hasPart, tech.singleElectrodeEphys),
       (hasPart, tech.ephysRecording),
       synonyms=('single unit recording',
                 'single unit recording technique',
                 'single-unit recording',),
      ),

    _t(DEV(225), 'extracellular electrophysiology recording technique',
       (hasPart, tech.extracellularEphys),
       (hasPart, tech.ephysRecording),
       synonyms=('extracellular recording',),
      ),

    _t(tech.sharpElectrodeEphys, 'sharp intracellular electrode technique',
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasPrimaryParticipant, OntTerm('GO:0005622', label='intracellular anatomical structure')),
       (hasInput, ilxtr.sharpElectrode),
       synonyms=('sharp electrode technique',)),
       (tech.sharpElectrodeEphys, ilxtr.hasTempId, OntTerm('HBP_MEM:0000023')),

    _t(tech.sharpElectrodeTechnique, 'sharp electrode technique',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryParticipant, ilxtr.cell),
                      restN(hasInput, ilxtr.sharpMicroPipette)),
       equivalentClass=oECN),

    _t(tech.cellPatching, 'cell patching technique',
       intersectionOf(ilxtr.technique,
                      restN(ilxtr.hasPrimaryParticipant,
                            unionOf(ilxtr.cellMembrane,
                                    restN(partOf, ilxtr.cellMembrane))),
                      restN(hasInput, ilxtr.patchPipette)),
       equivalentClass=oECN),
    cmb.Class(tech.cellPatching, restriction(hasInput, ilxtr.inVitroEphysRig)),

    _t(tech.patchClamp, 'patch clamp technique',
       intersectionOf(ilxtr.technique,
                      restN(hasPart, tech.cellPatching),
                      restN(ilxtr.hasPrimaryAspect, asp.electrical),
                      restN(hasInput, ilxtr.patchElectrode)),
       intersectionOf(ilxtr.technique,
                      restN(hasPart, tech.patchClamp)),
       equivalentClass=oECN),
       (tech.patchClamp, ilxtr.hasTempId, OntTerm('HBP_MEM:0000017')),

    _t(DEV(226), 'cell attached patch technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
       (hasInput, ilxtr.patchPipette),
       (hasParticipant, OntTerm('GO:0005622', label='intracellular anatomical structure')),
       # cell attached configuration?
       (ilxtr.hasSomething, blank(96)),
    ),
       (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000029')),

    _t(DEV(227), 'inside out patch technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
       (hasInput, ilxtr.patchPipette),
       (ilxtr.hasSomething, blank(97)),
    ),
       (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000028')),

    _t(DEV(228), 'loose patch technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
       (hasInput, ilxtr.patchPipette),
       (ilxtr.hasSomething, blank(98)),
    ),
       (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000024')),

    _t(DEV(229), 'outside out patch technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
       (hasInput, ilxtr.patchPipette),
       (ilxtr.hasSomething, blank(99)),
    ),
       (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000026')),

    _t(DEV(230), 'perforated patch technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
       (hasInput, ilxtr.patchPipette),
       (ilxtr.hasSomething, blank(100)),
    ),
       (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000025')),

    _t(tech.wholeCellPatch, 'whole cell patch technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
       (hasParticipant, OntTerm('GO:0005622', label='intracellular anatomical structure')),
       (hasInput, ilxtr.patchPipette),
       (ilxtr.hasSomething, blank(101)),
    ),
       (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000027')),

    _t(tech.eClamp, 'electrical clamping technique',
       (hasInput, ilxtr.recordingElectrode),
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasConstrainingAspect, asp.electrical),
       # FIXME should be different aspects??
      ),
    _t(DEV(231), 'current clamp technique',
       (hasInput, ilxtr.recordingElectrode),
       (ilxtr.hasPrimaryAspect, asp.voltage),
       (ilxtr.hasConstrainingAspect, asp.current),
       # TODO hasPrimaryAspectActualized, asp.current
       # TODO isConstrainedBy V=IR
    ),
       (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000204')),

    _t(tech.vClamp, 'voltage clamp technique',
       # voltage really only works in patch configuration
       # need to be able to inject enough current
       (hasInput, ilxtr.recordingElectrode),
       (ilxtr.hasPrimaryAspect, asp.current),
       (ilxtr.hasConstrainingAspect, asp.voltage),
       # TODO hasPrimaryAspectActualized, asp.current
    ),
       (i.p, ilxtr.hasTempId, OntTerm('HBP_MEM:0000203')),

    _t(DEV(232), 'dynamic clamp technique',
       (hasPart, tech.vClamp),
       (hasInput, ilxtr.dynamicClampAmplifier),
      ),

    _t(DEV(233), 'whole cell patch clamp technique',
       (hasPart, tech.eClamp),
       (hasPart, tech.wholeCellPatch),
       synonyms=('whole cell patch clamp',),
      ),

    _t(DEV(234), 'cell filling technique',
       (hasPart, tech.cellPatching),
       #(hasPart, tech.contrastEnhancement),  #not the right way to do this?
       #(hasParticipant, OntTerm('GO:0005622', label='intracellular anatomical structure')),
       (hasInput, ilxtr.contrastAgent),  # FIXME ...
      ),

    _t(DEV(235), 'neuron morphology reconstruction technique',
       (ilxtr.hasSomething, blank(102))),
    _t(DEV(236), 'autoradiographic technique',
       (ilxtr.hasSomething, blank(103))),
    _t(DEV(237), 'intravascaular filling technique',
       (ilxtr.hasSomething, blank(104))),
    _t(DEV(238), 'brightfield microscopy technique',
       (ilxtr.hasSomething, blank(105))),
    _t(DEV(239), 'machine learning technique',
       (ilxtr.hasSomething, blank(106))),
    _t(DEV(240), 'deep learning technique',
       (ilxtr.hasSomething, blank(107))),
    _t(DEV(241), 'delineation technique',
       (ilxtr.hasSomething, blank(108))),
    _t(DEV(242), 'epifluorescent microscopy technique',
       (ilxtr.hasSomething, blank(109))),
    _t(DEV(243), 'epifluorescent microscopy',
       (ilxtr.hasSomething, blank(110))),
    _t(DEV(244), 'fiber photometry technique',
       (ilxtr.hasSomething, blank(111))),
    _t(DEV(245), 'focused ion beam scanning electron microscoscopy technique',
       (ilxtr.hasSomething, blank(112))),
    _t(DEV(246), 'microendoscopic technique',
       (ilxtr.hasSomething, blank(113))),
    _t(tech.twoPhoton, 'two-photon microscopy technique',
       (hasInput, ilxtr.twoPhotonMicroscope),  # TODO
       (ilxtr.hasSomething, blank(114)),  # TODO visible light vs microscopy
       synonyms=('two-photon microscopy',)),
    _t(tech.lightsheetMicroscopy, 'light sheet microscopy technique',
       (hasInput, ilxtr.lightSheetMicroscope),  # TODO
       (ilxtr.detects, ilxtr.visibleLight),
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       synonyms=('light sheet microscopy',)),
    _t(tech.lightSheetMicroscopyFluorescent, 'light sheet fluorescence microscopy technique',
       (hasInput, ilxtr.lightSheetMicroscope),  # TODO
       (ilxtr.detects, ilxtr.visibleLight),
       (hasInput, ilxtr.fluorescentMolecule),  # hasParticipant hasPart FIXME
       (ilxtr.hasInformationOutput, ilxtr.image),
       (ilxtr.hasPrimaryParticipant, ilxtr.materialEntity),
       synonyms=('light sheet fluorescence microscopy', 'LSFM')),
    oc(DEV(247)),
    (DEV(248), owl.deprecated, Literal(True)),
    (DEV(249), replacedBy, DEV(250)),  # STPT and TPT used to be 361 and 362, now merged
    _t(DEV(251), 'two-photon tomographic technique',
       (hasPart, tech.twoPhoton),
       (hasPart, tech.tomography),
       (ilxtr.hasSomething, blank(115)), # TODO serial??  this model conflates with 2p tomography ...
       synonyms=('serial two-photon tomography', 'STPT',)
       # FIXME acronym
      ),
    _t(tech.lightSheetTomographyOblique, 'oblique light sheet tomographic technique',
       (hasPart, tech.lightsheetMicroscopy),
       (hasPart, tech.tomography),
       (ilxtr.hasSomething, blank(116)), # TODO oblique?
       synonyms=('oblique light sheet tomography', 'OLST',)
       # FIXME acronym
      ),
    _t(DEV(252), 'wide-field microscopy technique',
       (ilxtr.hasSomething, blank(117))),
    _t(DEV(253), 'brain-wide technique',
       (ilxtr.hasSomething, blank(118))),
    _t(DEV(254), 'gene characterization technique',
       (ilxtr.hasSomething, blank(119))),
)

def ect():  # FIXME not used supposed to make dAdT zero equi to value hasValue 0
    b = rdflib.BNode()

    r = tuple(restG(None, POC(owl.onProperty, ilxtr.hasPrimaryAspect_dAdT),
                    POC(owl.someValuesFrom,
                        rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
                    POC(owl.onClass, ilxtr.changeType)),
              restG(None, POC(owl.onProperty, ilxtr.hasPrimaryAspect_dAdT),
                    POC(owl.maxQualifiedCardinality,
                        rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
                    POC(owl.onClass, ilxtr.changeType)))

    ax = (b, rdf.type, owl.Axiom)
    ecr = (b, owl.equivalentClass, r[0][0])

    return r1 + r2 + ax + ecr

#triples += ect()
"""
_t(tech.fMRI, 'functional magnetic resonance imaging',
   # AAAAAAA how to deal with
   # "change in nuclear magnetic resonance of iron molecules as a function of time and their bound oxygen"
   # "BOLD" blood oxygenation level dependent contrast is something different...
   #ilxtr.NMR_of_iron_in_the_blood  # ICK
   #(hasPrimaryParticipant, ilxtr.???)
   #(hasPart, tech.MRI),  # FIXME how to deal with this...
   #(hasPart, tech.bloodOxygenLevel),
   #(ilxtr.hasPrimaryAspect, ilxtr.nuclearMagneticResonance),
   tech.MRI,  # FIXME vs respeccing everything?
   #(ilxtr.hasPrimaryParticipantSubeset, ilxtr.haemoglobin)
   #(ilxtr.hasPrimaryParticipantPart, ilxtr.haemoglobin)
   (ilxtr.hasPrimaryParticipant, ilxtr.haemoglobin),
   (ilxtr.hasPrimaryParticipantSubsetRule, ilxtr.hasBoundOxygen),  # FIXME not quite right still?
   synonyms=('fMRI', 'functional nuclear magnetic resonance imaging'),),
olit(tech.fMRI, rdfs.comment,
     ('Note that this deals explicitly only with the image acquistion portion of fMRI. '
      'Other parts of the full process and techniques in an fMRI study should be modelled separately. '
      'They can be tied to fMRI using hasPart: or hasPriorTechnique something similar.')),  # TODO
(tech.fMRI, ilxtr.hasTempId, OntTerm("HBP_MEM:0000008")),
"""
"""
_t(tech.sequencing, 'sequencing technique',
   # hasParticipant molecule or chemical?
   (ilxtr.hasPrimaryParticipant, ilxtr.thingWithSequence),  # peptide nucleotie sacharide
   # can't use hasParticipant because then it would caputre peptide synthesis or oligo synthesis
   (ilxtr.hasPrimaryAspect, asp.sequence),  # nucleic and peptidergic, and chemical etc.
   (ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
    ),
"""
"""
_t(tech.rnaSeq, 'RNAseq',
   (ilxtr.knownDetectedPhenomena, OntTerm('CHEBI:33697', label='RNA')),
   (ilxtr.hasPrimaryAspect, asp.sequence),
   (ilxtr.hasInformationOutput, ilxtr.informationArtifact),  # note use of artifact
   synonyms=('RNA-seq',)
  ),

"""


methods = simpleOnt(filename=filename,
                    prefixes=prefixes,
                    imports=imports,
                    triples=triples,
                    comment=comment,
                    branch=branch,
                    _repo=_repo,
                    calling__file__=__file__,)

[methods.graph.add((o2, rdfs.subClassOf, ilxtr.Something))
 for s1, p1, o1 in methods.graph if
 p1 == owl.onProperty and
 o1 == ilxtr.hasSomething
 for p2, o2 in methods.graph[s1:] if
 p2 == owl.someValuesFrom]

methods.graph.add((methods.graph.boundIdentifier,
                   ilxtr.indexNamespace,
                   rdflib.URIRef(str(local))))


def methods_main():
    methods._graph.add_namespace('asp', str(asp))
    methods._graph.add_namespace('ilxtr', str(ilxtr))  # FIXME why is this now showing up...
    methods._graph.add_namespace('prot', str(prot))
    methods._graph.add_namespace('tech', str(tech))
    methods._graph.add_namespace('HBP_MEM', OntCuries['HBP_MEM'])
    methods._graph.write()


from collections import defaultdict
data = defaultdict(set)
for t in methods.graph:
    for e in t:
        if isinstance(e, URIRef) and 'tgbugs' in e:
            prefix, suffix = methods._graph.qname(e).split(':')
            data[prefix].add(suffix)

intersection = defaultdict(set)
for ki, vi in data.items():
    for kj, vj in data.items():
        if ki == kj:
            continue

        intersection[ki,kj].update(vi & vj)

def testbt(simpleont):
    bad_types = set((s, bo) for s in simpleont.graph[:rdf.type:owl.Class]
                    for bo in simpleont.graph[s:rdf.type] if
                    bo != owl.Class)
    [print(t) for t in bad_types]
    if bad_types:
        raise TypeError()

testbt(methods_helper)
testbt(methods_core)
testbt(methods)

#assert not any(intersection.values()), f'duplicate namespace issue {intersection!r}'

def halp():
    import rdflib
    trips = sorted(flattenTriples(triples))
    graph = rdflib.Graph()
    *(graph.add(t) for t in trips),
    *(print(tuple(qname(e) if not isinstance(e, rdflib.BNode) else e[:5] for e in t)) for t in trips),
    breakpoint()
    return trips
#trips = halp()

def expand(_makeGraph, *graphs, debug=False):
    import rdflib
    import RDFClosure as rdfc
    graph = rdflib.Graph()
    for graph_ in graphs:
        [graph.bind(k, v) for k, v in graph_.namespaces()]
        [graph.add(t) for t in graph_]
    g = _makeGraph.__class__('', graph=graph)
    g.filename = _makeGraph.filename
    # other options are
    # OWLRL_Semantis RDFS_OWLRL_Semantics but both cuase trouble
    # all of these are SUPER slow to run on cpython, very much suggest pypy3
    #rdfc.DeductiveClosure(rdfc.OWLRL_Extension_Trimming).expand(graph)  # monumentally slow even on pypy3
    #rdfc.DeductiveClosure(rdfc.OWLRL_Extension).expand(graph)
    eg = rdflib.Graph()
    [eg.add(t) for t in graph_]
    closure = rdfc.OWLRL_Semantics
    rdfc.DeductiveClosure(closure).expand(eg)
    [not graph.add((s, rdfs.subClassOf, o))
     and [graph.add(t) for t in annotation.serialize((s, rdfs.subClassOf, o),
                                                     ilxtr.isDefinedBy, closure.__name__)]
     for s, o in eg.subject_objects(rdfs.subClassOf)
     if s != o and  # prevent cluttering the graph
     #o not in [to for o_ in eg.objects(s, rdfs.subClassOf)  # not working correctly
               #for to in eg.objects(o_) if o_ != o] and
     not isinstance(s, rdflib.BNode) and
     not isinstance(o, rdflib.BNode) and
     'interlex' in s and 'interlex' in o]
    #g.write()
    displayGraph(graph, debug=debug)

def forComparison():

    obo, *_ = makeNamespaces('obo')
    filename = 'methods-external-test-bridge'
    imports = (obo['ero.owl'],
               #URIRef('https://www.eagle-i.net/ero/latest/ero.owl'),
               obo['obi.owl'],
               obo['ro.owl'],
               URIRef('http://www.ebi.ac.uk/efo/efo.owl'),
               URIRef('http://purl.org/incf/ontology/ExperimentalNeurophysiology/oen_term.owl'),
              )  # CNO still uses bfo1.1
    comment = 'Bridge for querying against established methods related ontologies.'
    _repo = True
    debug = False

    triples = tuple()

    methods_helper = simpleOnt(filename=filename,
                               #prefixes=prefixes,
                               imports=imports,
                               triples=triples,
                               comment=comment,
                               branch=branch,
                               _repo=_repo,
                               calling__file__=__file__)


def extra():
    forComparison()
    displayGraph(methods.graph, debug=debug)
    mc = methods.graph.__class__()
    #mc.add(t) for t in methods_core.graph if t[0] not in
    expand(methods_core._graph, methods_core.graph)#, methods_core.graph)  # FIXME including core breaks everying?
    expand(methods._graph, methods.graph)#, methods_core.graph)  # FIXME including core breaks everying?


def main():
    from nifstd_tools.methods import core
    from nifstd_tools.methods import helper
    core.main()
    helper.main()
    methods_main()


if __name__ == '__main__':
    main()
