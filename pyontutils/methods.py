from rdflib import Literal
from pyontutils.core import qname, simpleOnt, displayGraph, flattenTriples, OntCuries, OntId, OntTerm
from pyontutils.core import oc, oc_, oop, odp, olit, oec
from pyontutils.core import restrictions, annotation, restriction, restrictionN
from pyontutils.core import NIFTTL, NIFRID, ilxtr, ilx
from pyontutils.core import definition, realizes, hasParticipant, hasPart, hasInput, hasOutput, TEMP
from pyontutils.core import partOf, hasRole
from pyontutils.core import hasAspectChangeCombinator, unionOf, intersectionOf, Restriction, EquivalentClass
from pyontutils.core import owl, rdf, rdfs, oboInOwl
from pyontutils.methods_core import asp, tech, prot, methods_core, _t

filename = 'methods'
prefixes = ('TEMP', 'ilxtr', 'NIFRID', 'definition', 'realizes', 'hasRole',
            'hasParticipant', 'hasPart', 'hasInput', 'hasOutput', 'BFO',
            'CHEBI', 'GO', 'SO', 'NCBITaxon', 'UBERON', 'SAO', 'BIRNLEX',
            'NLX',
)
OntCuries['HBP_MEM'] = 'http://www.hbp.FIXME.org/hbp_measurement_methods/'
imports = methods_core.iri, NIFTTL['bridge/chebi-bridge.ttl'], NIFTTL['bridge/tax-bridge.ttl']
#imports = methods_core.iri,
comment = 'The ontology of techniques and methods.'
_repo = True
debug = False

restHasValue = Restriction(None, owl.hasValue)
restrictionS = Restriction(owl.someValuesFrom)
oECU = EquivalentClass(owl.unionOf)

def t(subject, label, def_, *synonyms):
    yield from oc(subject, ilxtr.technique)
    yield from olit(subject, rdfs.label, label)
    if def_:
        yield from olit(subject, definition, def_)

    if synonyms:
        yield from olit(subject, NIFRID.synonyms, *synonyms)

class I:
    counter = iter(range(999999))
    @property
    def d(self):
        current = TEMP[str(next(self.counter))]
        self.current = current
        return current

    @property
    def b(self):
        """ blank node """
        current = next(self.counter)
        return TEMP[str(current)]

    @property
    def p(self):
        return self.current

i = I()

triples = (
    # biccn

    (ilxtr.hasSomething, owl.inverseOf, ilxtr.isSomething),

    _t(i.d, 'atlas registration technique',
       # ilxtr.hasPrimaryParticipant, restriction(partOf, some animalia)
       # TODO this falls into an extrinsic classification technique...
       # or a context classification/naming technique...
       (ilxtr.isConstrainedBy, ilxtr.parcellationArtifact),
       #(ilxtr.assigns, asp.location),  # FIXME ilxtr.assigns needs to imply naming...
       (ilxtr.asserts, asp.location),  # FIXME ilxtr.asserts needs to imply naming...
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

    _t(i.d, 'randomization technique',  # FIXME this is not defined correctly
       (ilxtr.hasPrimaryAspect, asp.informationEntropy),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
    ),

    _t(i.d, 'chemical technique',  # FIXME but not molecular? or are molecular subset?
       (hasParticipant,  # FIXME hasParticipant is incorrect? too broad?
        OntTerm('CHEBI:24431', label='chemical entity')
       ),),

    _t(i.d, 'molecular technique',  # FIXME help I have no idea how to model this same with chemical technique
       # TODO FIXME I think it is clear that there are certain techniques which are
       # named in a way that is assertional, not definitional
       # it seems appropriate for those arbitrarily named techniques to use subClassOf?
       (hasParticipant,
        OntTerm('CHEBI:25367', label='molecule')
       ),),

    _t(i.d, 'cellular technique',
       (hasParticipant,
        OntTerm('SAO:1813327414', label='Cell')
       ),),

    _t(i.d, 'cell type induction technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('SAO:1813327414', label='Cell')),
       (hasParticipant, ilxtr.inducationFactor),
    ),

    _t(i.d, 'molecular cloning technique',

       (ilxtr.hasPrimaryParticipant,
        OntTerm('CHEBI:33696', label='nucleic acid')
        #OntTerm('CHEBI:16991', label='deoxyribonucleic acid')
        # FIXME other options are OntTerm('SAO:454034570') or OntTerm('SO:0000352')
        ),
       # the objective is to isolate a _specific_ sequence of DNA/RNA
       # amplification is the next step
       (ilxtr.hasPrimaryAspect, asp['count']),  # the general objective being to increase the DNA
       synonyms=('cloning technique', 'molecular cloning')
    ),

    _t(i.d, 'microarray technique',
       (hasInput,
        # TODO leverage EFO here
        # OntTerm(search='microarray', limit=20, prefix='NIFSTD')  # nice trick
        OntTerm('BIRNLEX:11031', label='Microarray platform')
        ),
    ),

    _t(tech.sequencing, 'sequencing technique',
       # hasParticipant molecule or chemical?
       (hasParticipant, ilxtr.thingWithSequence),  # peptide nucleotie sacharide
       (ilxtr.hasPrimaryAspect, asp.sequence),  # nucleic and peptidergic, and chemical etc.
        ),

    _t(tech._naSeq, 'nucleic acid sequencing technique',
       (ilxtr.hasPrimaryParticipant,
        # hasParticipant molecule or chemical?
        #OntTerm(term='nucleic acid')
         OntTerm('CHEBI:33696', label='nucleic acid')
        ),
       (ilxtr.hasPrimaryAspect,
        #OntTerm(term='sequence')
        #OntTerm('SO:0000001', label='region', synonyms=['sequence'])  # label='region'
        asp.sequence,  # pretty sure that SO:0000001 is not really an aspect...
       ),
        ),

    _t(i.d, 'deep sequencing technique',
       tech._naSeq,
       (ilxtr.isConstrainedBy, prot.deepSequencing),  # FIXME circular
       synonyms=('deep sequencing',)
    ),

    _t(i.d, 'sanger sequencing technique',
       tech._naSeq,
       (ilxtr.isConstrainedBy, prot.sangerSequencing),
       # we want these to differentiate based on the nature of the technqiue
       synonyms=('sanger sequencing',)
    ),

    _t(i.d, 'shotgun sequencing technique',
       tech._naSeq,
       (ilxtr.isConstrainedBy, prot.shotgunSequencing),
       synonyms=('shotgun sequencing',)
    ),

    _t(i.d, 'single cell sequencing technique',
       # FIXME vs pp -> *NA from a single cell
       (hasParticipant, OntTerm('CHEBI:33696', label='nucleic acid')),  # not much protein in a single cell
       (hasParticipant, OntTerm('SAO:1813327414', label='Cell')),
       # (ilxtr.hasPrimaryParticipantCardinality, 1)  # FIXME need this...
       synonyms=('single cell sequencing',)
    ),

    _t(i.d, 'single nucleus sequencing technique',
       (hasParticipant, OntTerm('CHEBI:33696', label='nucleic acid')),  # not much protein in the nucleus...
       (hasParticipant, OntTerm('GO:0005634', label='nucleus')),
       # (ilxtr.hasPrimaryParticipantCardinality, 1)  # FIXME need this...
       synonyms=('single nucleus sequencing',)
    ),

    # sequencing TODO

    _t(i.d, 'RNAseq',
       (ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:33697', label='RNA')),
       synonyms=('RNA-seq',)),

    # Split-seq single cell single nuclei
    # SPLiT-seq

    _t(i.d, 'mRNA-seq',
       (ilxtr.hasPrimaryParticipant,
        #OntTerm(term='mRNA')
        ilxtr.mRNA
        # FIXME wow... needed a rerun on this fellow OntTerm('SAO:116515730', label='MRNA', synonyms=[])
       ),
    ),

    _t(i.d, 'snRNAseq',
       (ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:33697', label='RNA')),
       (hasParticipant, OntTerm('GO:0005634', label='nucleus')),
       synonyms=('snRNA-Seq',
                 'single nucleus RNAseq',)),

    _t(i.d, 'scRNAseq',
       (ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:33697', label='RNA')),
       (hasParticipant, OntTerm('SAO:1813327414', label='Cell')),
       synonyms=('scRNA-Seq',
                 'scRNA-seq',
                 'single cell RNAseq',)),
        # 'deep-dive scRNA-Seq'  # deep-dive vs wide-shallow I think is what this is


    _t(i.d, 'Patch-seq',
       (ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:33697', label='RNA')),
       (hasParticipant, ilxtr.microPipette),  # FIXME TODO
       synonyms=('Patch-Seq',
                 'patch seq',)),

    _t(i.d, 'mC-seq',
       (ilxtr.hasSomething, i.d),
       def_='non CG methylation',
    ),

    _t(i.d, 'snmC-seq',
       (hasParticipant, OntTerm('GO:0005634', label='nucleus')),
       synonyms=('snmC-Seq',)),

    # mCH

    _t(tech.ATACseq, 'ATAC-seq',
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'snATAC-seq',
       tech.ATACseq,  # FIXME primary participant...
       (hasParticipant, OntTerm('GO:0005634', label='nucleus')),
       synonyms=('single-nucleus ATAC-seq',
                 'single nucleus ATAC-seq',)),

    _t(i.d, 'scATAC-seq',
       tech.ATACseq,  # FIXME
       (hasParticipant, OntTerm('SAO:1813327414', label='Cell')),
       def_='enriched for open chromatin',
       synonyms=('single-cell ATAC-seq',
                 'single cell ATAC-seq',)),

    _t(i.d, 'Bulk-ATAC-seq',
       tech.ATACseq,  # FIXME
       (ilxtr.hasSomething, i.d),
    ),

    #'scranseq'  # IS THIS FOR REAL!?
    #'ssranseq'  # oh boy, this is just me being bad at spelling scrnaseq?

    _t(i.d, 'Drop-seq',
       (ilxtr.hasSomething, i.d),
       synonyms=('DroNc-seq',)  #???? is this the same
    ),

    _t(i.d, '10x Genomics sequencing',
       (ilxtr.hasSomething, i.d),
       def_='commercialized drop seq',
       # snRNA-seq 10x Genomics Chromium v2
       # 10x Genomics Chromium V2 scRNA-seq
       # 10X (sigh)
       synonyms=('10x Genomics', '10x sequencing', '10x',)),

    _t(i.d, 'MAP seq',
       (ilxtr.hasSomething, i.d),
       synonyms=("MAPseq",),
    ),

    _t(i.d, 'Smart-seq',
       (ilxtr.hasSomething, i.d),
       # Clontech
       synonyms=('Smart-seq2',
                 'SMART-seq',
                 'SMART-Seq v4',
                 'SMART-seq v4',)),

    # 'deep smart seq',

    _t(i.d, ' technique',
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, ' technique',
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'anaesthesia technique',
       # anaesthesia is an excellent example of a case where
       # just the use of an anaesthetic is not sufficient
       # and should not be part of the definition
       #(ilxtr.hasPrimaryParticipant,
        #oc_(restriction(partOf, OntTerm('UBERON:0001016', label='nervous system')))),
       (ilxtr.hasPrimaryAspect, ilxtr.nervousResponsiveness),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       #(hasInput, OntTerm('CHEBI:38867', label='anaesthetic')),
       (hasParticipant, OntTerm('NCBITaxon:33208', label='Metazoa')),
    ),
    # local anaesthesia technique
    # global anaesthesia technique

    _t(OntTerm('NLXINV:20090610'), 'in situ hybridization technique',  # TODO
       (ilxtr.hasSomething, i.d),
       synonyms=('in situ hybridization', 'ISH'),),

    _t(tech.FISH, 'fluorescence in situ hybridization technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('fluorescence in situ hybridization', 'FISH'),
    ),

    _t(tech.smFISH, 'single-molecule fluorescence in situ hybridization technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('single-molecule fluorescence in situ hybridization',
                 'single molecule fluorescence in situ hybridization',
                 'single-molecule FISH',
                 'single molecule FISH',
                 'smFISH'),
    ),

    _t(tech.MERFISH, 'multiplexed error-robust fluorescence in situ hybridization technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('multiplexed error-robust fluorescence in situ hybridization',
                 'multiplexed error robust fluorescence in situ hybridization',
                 'multiplexed error-robust FISH',
                 'multiplexed error robust FISH',
                 'MERFISH'),
    ),

    _t(i.d, 'genetic technique',
       (hasParticipant,
        # the participant is really some DNA that corresponds to a gene
        OntTerm('SO:0000704', label='gene')  # prefer SO for this case?
        #OntTerm(term='gene', prefix='obo')  # representing a gene
        ),
       # FIXME OR has participant some nucleic acid...
    ),

    _t(tech.enrichment, 'enrichment technique',
       #(ilxtr.hasSomething, i.d),
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

    _t(i.d, 'nucleic acid amplification technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:33696', label='nucleic acid')),
       (ilxtr.hasPrimaryAspect, asp['count']),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
      ),
    _t(i.d, 'expression manipulation technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'conditional expression manipulation technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'knock in technique',
       (ilxtr.hasSomething, i.b),
    ),
    (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000121')),

    _t(i.d, 'knock down technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('underexpression technique',),
    ),

    # endogenous genetic manipulation   HRM 'HBP_MEM:0000119'
    # conditional knockout 'HBP_MEM:0000122'
    # morpholino 'HBP_MEM:0000124'
    # RNA interference 'HBP_MEM:0000123'
    # dominant-negative inhibition   sigh 'HBP_MEM:0000125'

    _t(i.d, 'knock out technique',
       (ilxtr.hasSomething, i.b),
    ),
    (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000120')),

    _t(i.d, 'mutagenesis technique',
       (ilxtr.hasSomething, i.d)
    ),

    _t(i.d, 'overexpression technique',
       (ilxtr.hasSomething, i.d)
    ),

    _t(i.d, 'delivery technique',
       (ilxtr.hasPrimaryAspect, asp.location),
       (ilxtr.hasSomething, i.d),
       def_='A technique for moving something from point a to point b.',),

    _t(i.d, 'physical delivery technique',
       (ilxtr.hasPrimaryAspect, asp.location),
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'diffusion based delivery technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'bath application technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'topical application technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'mechanical delivery technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'rocket delivery technique',
       (ilxtr.hasSomething, i.d)),

    _t(OntTerm('BIRNLEX:2135'), 'injection technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('injection',)),

    _t(i.d, 'ballistic injection technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'pressure injection technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'brain injection technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('UBERON:0000955')),
       synonyms=('brain injection', 'injection into the brain')),

    _t(OntTerm('BIRNLEX:2136'), 'intracellular injection technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('SAO:1289190043', label='Cellular Space')),  # TODO add intracellular as synonym
       synonyms=('intracellular injection',)),

    _t(i.d, 'electrical delivery technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'electroporation technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'in utero electroporation technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'single cell electroporation technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'chemical delivery technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'DNA delivery technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'transfection technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'delivery exploiting some pre-existing mechanism technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'DNA delivery via primary genetic code technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'DNA delivery via germ line technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'DNA delivery via plasmid technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'DNA delivery via viral particle technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'tracing technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('axon tracing technique',
                 'axonal tracing technique',
                 'axon tracing',
                 'axonal tracing',)),
    _t(i.d, 'anterograde tracing technique',
       (ilxtr.hasSomething, i.d),
       synonyms=( 'anterograde tracing',)
    ),
    _t(i.d, 'retrograde tracing technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('retrograde tracing',)
    ),
    _t(i.d, 'diffusion tracing technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('diffusion tracing',)
    ),
    _t(i.d, 'transsynaptic tracing technique',
       (ilxtr.hasSomething, i.d),
       synonyms=( 'transsynaptic tracing',)
    ),
    _t(i.d, 'multisynapse transsynaptic tracing technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('multisynaptic transsynaptic tracing technique',
                 'multisynaptic transsynaptic tracing')),

    # 'TRIO'
    # 'tracing the relationship between input and output'

    _t(i.d, 'statistical technique',
       (ilxtr.hasSomething, i.d)
       #(hasPart, tech.statistics)
      ),

    _t(i.d, 'computational technique',  # these seem inherantly circulat... they use computation...
       (ilxtr.hasSomething, i.d)
      ),

    _t(i.d, 'simulation technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'storage technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'preservation technique',
       (ilxtr.hasSomething, i.d)

      ),

    _t(i.d, 'tissue preservation technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'colocalization technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'image reconstruction technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'tomographic technique',
       (ilxtr.hasSomething, i.d),
       (ilxtr.isConstrainedBy, ilxtr.radonTransform),
       synonyms=('tomography',)),
    _t(i.d, 'positron emission tomography',
       (ilxtr.hasSomething, i.b),
       synonyms=('PET', 'PET scan')),
    (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000009')),

    # "Single-Proton emission computerized tomography"
    # "HBP_MEM:0000010"  # TODO

    _t(i.d, 'stereology technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('stereology',)),

    _t(i.d, 'design based stereology technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('design based stereology',)),

    _t(i.d, 'spike sorting technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('spike sorting',)),

    _t(i.d, 'detection technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'identification technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'characterization technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'classification technique',
       (ilxtr.hasSomething, i.d)),
    _t(i.d, 'curation technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'angiographic technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('angiography',)),

    _t(i.d, 'ex vivo technique',
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

    _t(i.d, 'in situ technique',  # TODO FIXME
       # detecting something in the location that it was originally in
       # not in the dissociated remains thereof...
       # hasPrimaryParticipantLocatedIn
       (ilxtr.hasSomething, i.d),
       synonyms=('in situ',),),

    _t(i.d, 'in vivo technique',
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

    _t(i.d, 'in utero technique',
       # has something in 
       (hasParticipant, ilxtr.somethingThatIsAliveAndIsInAUterus),
       synonyms=('in vitro',),),

    _t(i.d, 'in vitro technique',
       (hasParticipant, ilxtr.somethingThatIsAliveAndIsInAGlassContainer),
       synonyms=('in vitro',),),

    _t(i.d, 'high throughput technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('high throughput',),),

    _t(i.d, 'fourier analysis technique',
       (realizes, ilxtr.analysisRole),  # FIXME needs to be subClassOf role...
       (ilxtr.isConstrainedBy, ilxtr.fourierTransform),
       synonyms=('fourier analysis',),),

    _t(i.d, 'preparation technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('sample preparation technique',
                 'specimine preparation technique',
                 'sample preparation',
                 'specimine preparation',),),

    _t(i.d, 'dissection technique',
       (hasOutput, ilxtr.partOfSomePrimaryInput),  #FIXME
       synonyms=('dissection',),),

    _t(i.d, 'atlas guided microdissection technique',
       (ilxtr.isConstrainedBy, ilxtr.parcellationAtlas),
       (hasOutput, ilxtr.partOfSomePrimaryInput),  #FIXME
       synonyms=('atlas guided microdissection',),),

    _t(i.d, 'crystallization technique',
       (ilxtr.hasPrimaryAspect, asp.latticePeriodicity),  # physical order
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
       # cyrstallized vs amorphous
       # xray diffraction can tell you what proportion of the whole samle is crystallized (S. Manna)
       def_=('A technique for enducing a regular crystal patterning '
             'on a set of non-patterend components'),
       synonyms=('crystallization',)),

    _t(i.d, 'crystal quality evalulation technique',
       (ilxtr.hasPrimaryAspect, asp.physicalOrderedness),
       # (ilxtr.hasPrimaryAspect, asp.percentCrystallinity),
       # there are many other metrics that can be used that are subclasses
      ),

    _t(i.d, 'tissue clearing technique',
       (ilxtr.hasPrimaryAspect, asp.transparency),  # FIXME
      ),

    _t(i.d, 'CLARITY technique',
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
       #(ilxtr.hasSomething, i.d),
       #(ilxtr.hasPrimaryAspect, asp.spontaneousChangeInStructure),
       #(ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       #(ilxtr.hasPrimaryAspect, asp.likelinessToDecompose),
       #(ilxtr.hasPrimaryAspect, asp.mechanicalRigidity),
       #(ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
       ilxtr.technique,
       unionOf(hasAspectChangeCombinator(asp.mechanicalRigidity, ilxtr.positive),
               hasAspectChangeCombinator(asp.spontaneousChangeInStructure, ilxtr.negative)),
       synonyms=('fixation',)),

    #oc_(tech.fixation,
       #),


    _t(i.d, 'tissue fixation technique',
       tech.fixation,
       (ilxtr.hasPrimaryParticipant, ilxtr.tissue),
       synonyms=('tissue fixation',)),

    _t(i.d, 'sensitization technique',
       # If we were to try to model this fully in the ontology
       # then we would have a giant hiearchy of sensitivities to X
       # when in fact sensitivity is a defined measure/aspect not
       # a fundamental aspect. It is fair to say that there could be
       # an aspect for every different way there is to measure sensitivity
       # to sunlight since the term is so broad
       (ilxtr.hasPrimaryAspect, asp.sensitivity),
    ),

    _t(i.d, 'permeabilization technique',
       # TODO how to model 'the permeability of a membrane to X'
       #  check go
       (ilxtr.hasPrimaryAspect, asp.permeability),
    ),

    _t(i.d, 'chemical synthesis technique',
       # involves some chemical reaction ...
       # is ioniziation a chemical reaction? e.g. NaCl -> Na+ Cl-??
       (hasOutput,  OntTerm('CHEBI:24431', label='chemical entity')),
       tech.creating,),
    _t(i.d, 'physical synthesis technique',
       tech.creating,),
    _t(i.d, 'mixing technique',
       #tech.creating,  # not entirely clear that this is the case...
       #ilxtr.mixedness is circular
       (ilxtr.hasSomething, i.d),
       synonyms=('mixing',),),
    _t(i.d, 'agitating technique',
       #tech.mixing,
       # allocation on failure?
       # classification depends exactly on the goal
       (ilxtr.hasSomething, i.d),
       synonyms=('agitating',),),
    _t(i.d, 'stirring technique',
       #tech.mixing,  # not clear, the intended outcome may be that the thing is 'mixed'...
       (ilxtr.hasSomething, i.d),
       synonyms=('stirring',),),
    _t(i.d, 'dissolving technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('dissolve',),),

    _t(i.d, 'husbandry technique',
       # FIXME maintenance vs growth
       # also how about associated techniques?? like feeding
       # include in the oec or 'part of some husbandry technique'??
       # alternately we can change it to hasParticipant ilxtr.livingOrganism
       # to allow them to include techniques where locally the
       # primary participant is something like food, instead of the organism HRM
       tech.maintaining,
       (hasParticipant,  # vs primary participant
        OntTerm('NCBITaxon:1', label='ncbitaxon')
       ),
       synonyms=('culture technique', 'husbandry', 'culture'),),

    oc_(OntTerm('NCBITaxon:1', label='ncbitaxon'), restriction(ilxtr.hasAspect, asp.livingness)),

    _t(i.d, 'feeding technique',
       # metabolism required so no viruses
       # TODO how to get this to classify as a maintenance technique
       #  without having to include the entailment explicitly
       #  i.e. how do we deal side effects of processes

       (hasParticipant, OntTerm('NCBITaxon:131567', label='cellular organisms')),
       (hasInput, ilxtr.food),
       synonyms=('feeding',)),

       (i.p, rdfs.subClassOf, tech.maintaining),
       # this is a legitimate case where there is no easy
       # way to communicate a side effect of feeding
       # I will thing a bit more on this but I think it is the easiest way
       # maybe a general class axiom or something like that could do it
       # FIXME the issue is that the primary aspects will then start to fight...
       #  there might be a way to create a class that will work using
       #  ilxtr.hasSideEffectTechnique or ilxtr.hasSideEffect?

    _t(i.d, 'high-fat diet feeding technique',
       (hasParticipant, OntTerm('NCBITaxon:131567', label='cellular organisms')),
       (ilxtr.hasPrimaryAspect, asp.weight),
       (hasInput, ilxtr.highFatDiet),
    ),

    _t(i.d, 'mouse circadian based high-fat diet feeding technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('NCBITaxon:10090', label='Mus musculus')),
       # ie that if one were to measure rather than specify
       # the mouse should be in in the same phase during the activity
       (ilxtr.hasConstrainingAspect, asp.circadianPhase),  # TODO? 'NBO:0000169'
       (ilxtr.hasPrimaryAspect, asp.weight),
       (hasInput, ilxtr.highFatDiet),
       ),

    _t(i.d, 'mouse age based high-fat diet feeding technique',
       # TODO there are a whole bunch of other high fat diet feeding techniques
       # 'MmusDv:0000050'
       # as opposed to the primary aspect being the current point in the cyrcadian cycle
       (ilxtr.hasPrimaryParticipant, OntTerm('NCBITaxon:10090', label='Mus musculus')),
       (ilxtr.hasConstrainingAspect, OntTerm('PATO:0000011', label='age')),  # FIXME not quite right
       (ilxtr.hasPrimaryAspect, asp.weight),  # FIXME not quite right
       (hasInput, ilxtr.highFatDiet),
       # (hasInput, ilx['researchdiets/uris/productnumber/D12492']),  # too specific
       ),

    _t(i.d, 'bacterial culture technique',
       tech.maintaining,
       #(hasParticipant, OntTerm('NCBITaxon:2', label='Bacteria <prokaryote>')),
       (hasParticipant, OntId('NCBITaxon:2')),  # FIXME > 1 label
       synonyms=('bacterial culture',),),

    _t(i.d, 'cell culture technique',
       tech.maintaining,
       (hasParticipant, OntTerm('SAO:1813327414', label='Cell')),
       synonyms=('cell culture',),),

    _t(i.d, 'yeast culture technique',
       tech.maintaining,
       (hasParticipant, OntTerm('NCBITaxon:4932', label='Saccharomyces cerevisiae')),
       synonyms=('yeast culture',),),

    _t(i.d, 'tissue culture technique',
       tech.maintaining,
       (hasParticipant, ilxtr.tissue),
       synonyms=('tissue culture',),),

    _t(i.d, 'slice culture technique',
       tech.maintaining,
       (hasParticipant, ilxtr.brainSlice),  # FIXME
       synonyms=('slice culture',),),

    _t(i.d, 'open book preparation technique',
       (ilxtr.hasInput,
        OntTerm('UBERON:0001049', label='neural tube')
        #OntTerm(term='neural tube', prefix='UBERON')  # FIXME dissected out neural tube...
       ),
       synonyms=('open book culture', 'open book preparation'),),

    _t(i.d, 'fly culture technique',
       tech.maintaining,
       (hasParticipant,
        OntTerm('NCBITaxon:7215', label='Drosophila <fruit fly, genus>')
        #OntTerm(term='drosophila')
       ),
       synonyms=('fly culture',),),

    _t(i.d, 'rodent husbandry technique',
       tech.maintaining,
       (ilxtr.hasPrimaryParticipant,
        OntTerm('NCBITaxon:9989', label='Rodentia')  # FIXME population vs individual?
       ),
       synonyms=('rodent husbandry', 'rodent culture technique'),),

    _t(i.d, 'enclosure design technique',  # FIXME design technique? produces some information artifact?
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'housing technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('housing',),
    ),
    _t(i.d, 'mating technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('mating',),
    ),
    _t(i.d, 'watering technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('watering',),
    ),

    _t(tech.contrastEnhancement, 'contrast enhancement technique',
       (ilxtr.hasPrimaryAspect, asp.contrast),  # some contrast
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
       synonyms=('contrast enhancement',),),
    _t(i.d, 'tagging technique',
       (ilxtr.hasSomething, i.d)),

    _t(OntTerm('BIRNLEX:2107'), 'staining technique',  # TODO integration
       (ilxtr.hasSomething, i.d)),

    _t(i.d, 'immunochemical technique',
       (ilxtr.hasSomething, i.d)),

    _t(i.d,'immunocytochemical technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('immunocytochemistry technique',
                 'immunocytochemistry')),

    _t(OntTerm('NLXINV:20090609'), 'immunohistochemical technique',  # TODO
       (ilxtr.hasSomething, i.d),
       synonyms=('immunohistochemistry technique',
                 'immunohistochemistry')),
    (OntTerm('NLXINV:20090609'), ilxtr.hasTempId, OntId("HBP_MEM:0000115")),
    
    # TODO "HBP_MEM:0000116"
    # "Immunoelectron microscopy"

    _t(i.d, 'direct immunohistochemical technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('direct immunohistochemistry technique',
                 'direct immunohistochemistry')),
    _t(i.d, 'indirect immunohistochemical technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('indirect immunohistochemistry technique',
                 'indirect immunohistochemistry')),

    _t(tech.stateBasedContrastEnhancement, 'state based contrast enhancement technique',
       #tech.contrastEnhancement,  # FIXME compare this to how we modelled fMRI below? is BOLD and _enhancement_?
       (ilxtr.hasSomething, i.d),

    ),

    _t(i.d, 'separation technique',
       (ilxtr.hasPrimarAspec, asp.location),  # TODO
       #(ilxtr.hasSomething, i.d),
    ),
    _t(i.d, 'sorting technique',
       (ilxtr.hasSomething, i.d),),
    _t(i.d, 'sampling technique',
       (ilxtr.hasSomething, i.d),),
    _t(i.d, 'extraction technique',
       (hasParticipant, ilxtr.extract),  # FIXME circular
       ),
    _t(i.d, 'precipitation technique',
       (hasParticipant, ilxtr.precipitate),  # FIXME circular
      ),
    _t(i.d, 'pull-down technique',
       (hasPart, tech.precipitation),
       # allocation enrichement
       (ilxtr.hasSomething, i.d),),
    _t(i.d, 'isolation technique',
       # enrichment
       (ilxtr.hasSomething, i.d),),
    _t(i.d, 'purification technique',
       (ilxtr.hasSomething, i.d),),

    _t(i.d, 'selection technique',
       (ilxtr.hasSomething, i.d),),
    _t(i.d, 'blind selection technique',
       (ilxtr.hasSomething, i.d),),
    _t(i.d, 'random selection technique',
       (ilxtr.hasSomething, i.d),),
    _t(i.d, 'targeted selection technique',
       (ilxtr.hasSomething, i.d),),

    _t(i.d, 'fractionation technique',
       (ilxtr.hasSomething, i.d),),
    _t(i.d, 'chromatography technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('chromatography',),),
    _t(i.d, 'distillation technique',
       (ilxtr.knownDifferentiatingPhenomena, asp.boilingPoint),
       (ilxtr.knownDifferentiatingPhenomena, asp.condensationPoint),
       synonyms=('distillation',),),
    _t(i.d, 'electrophoresis technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('electrophoresis',),),
    _t(i.d, 'centrifugation technique',
       (ilxtr.knownDifferentiatingPhenomena, asp.size),  # TODO hasImplicitMeasurement
       (ilxtr.knownDifferentiatingPhenomena, asp.shape),
       (ilxtr.knownDifferentiatingPhenomena, asp.density),
       synonyms=('centrifugation',),),
    _t(i.d, 'ultracentrifugation technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('ultracentrifugation',),),

    _t(i.d, 'biological activity measurement technique',
       (ilxtr.hasPrimaryAspect, asp.biologicalActivity),  # TODO
       (ilxtr.hasInformationOutput, ilxtr.informationArtifact),
       synonyms=('activity measurement technique', 'bioassay')),

    _t(i.d, 'observational technique',
       tech.measuring,
       (ilxtr.hasSomething, i.d),
       synonyms=('observation', 'observation technique'),),

    _t(i.d, 'procurement technique',
       (ilxtr.hasPrimaryParticipant,
        OntTerm('BFO:0000040', label='material entity')
        #OntTerm(term='material entity', prefix='BFO')
       ),
       (hasOutput,
        OntTerm('BFO:0000040', label='material entity')
        #OntTerm(term='material entity', prefix='BFO')
       ),
       def_='A technique for getting or retrieving something.',
       synonyms=('acquisition technique', 'procurement', 'acquistion', 'get')
    ),

    _t(i.d, 'technique defined by constraint',
       (ilxtr.hasConstrainingAspect, ilxtr.aspect),
      ),

    _t(tech.measuring, 'measuring technique',
       # TODO is detection distinct from measurement if there is no explicit symbolization?
       (ilxtr.hasInformationOutput, ilxtr.informationEntity),  # observe that this not information artifact
       (hasParticipant,
        # FIXME vs material entity (alignment to what I mean by 'being')
        OntTerm('BFO:0000001', label='entity')
       ),
       synonyms=('measure', 'measurment technique'),
    ),

    _t(tech.probing, 'probing technique',
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

    _t(tech.allocating, 'allocating technique',
       (ilxtr.hasPrimaryAspect, asp.location),
       def_=('Allocating techniques move things around without changing how their participants '
             'are named. More accurately they move them around without changing any part of their '
             'functional defintions which are invariant as a function of their location.'),
      ),
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

    _t(tech.creating, 'creating technique',   # FIXME mightent we want to subclass off of these directly?
       (ilxtr.hasPrimaryAspect, asp['is']),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
       synonyms=('synthesis technique',),
    ),

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
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),),

    _t(tech.maintaining, 'maintaining technique',
       # if these were not qualified by the primary participant
       # then this would be both a creating and a destroying technique
       (ilxtr.hasPrimaryAspect, asp['is']),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.zero),  # FIXME value?
       synonyms=('maintenance technique',),
    ),

    _t(i.d, 'analysis technique',
       (realizes, ilxtr.analysisRole),
       synonyms=('analysis',),),

    _t(i.d, 'data processing technique',
       (ilxtr.hasInformationInput, ilxtr.informationArtifact),
       (ilxtr.hasInformationOutput, ilxtr.informationArtifact),
       synonyms=('data processing', 'data transformation technique'),),

    _t(i.d, 'image processing technique',
       (ilxtr.hasInformationInput, ilxtr.image),
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('image processing',),),

    _t(tech.sigproc, 'signal processing technique',
       (ilxtr.hasInformationInput, ilxtr.timeSeries),  # FIXME are information inputs the priamry participant?
       (ilxtr.hasInformationOutput, ilxtr.timeSeries),
       synonyms=('signal processing',),),

    _t(i.d, 'signal filtering technique',
       # FIXME aspects of information entities...
       # lots of stuff going on here...
       tech.sigproc,
       (ilxtr.hasInformationPrimaryAspect, asp.spectrum),
       (ilxtr.hasInformationPrimaryAspect_dAdT, ilxtr.negative),
       (ilxtr.hasInformationPrimaryParticipant, ilxtr.timeSeries),  # FIXME
       synonyms=('signal filtering',),
    ),

    _t(i.d, 'electrophysiology technique',
       # TODO is this one of the cases where partonomy implies techniqueness?
       # technique and (hasPart some i.p)
       (ilxtr.hasPrimaryAspect, asp.electrical),  # FIXME...
       (ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystem),
       synonyms=('electrophysiology', 'electrophysiological technique'),
    ),
    (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000014')),

    _t(tech.contrastDetection, 'contrast detection technique',
       # a subclass could be differential contrast to electron scattering or something...
       #(ilxtr.hasPrimaryAspect_dAdPartOfPrimaryParticipant, ilxtr.nonZero),  # TODO FIXME this is MUCH better
       (ilxtr.hasPrimaryAspect, asp.contrast),  # contrast to something? FIXME this seems a bit off...
       (ilxtr.hasPrimaryAspect_dAdS, ilxtr.nonZero),
       synonyms=('contrast detection',),
    ),

    _t(i.d, 'microscopy technique',
       (hasParticipant, ilxtr.microscope),  # electrophysiology microscopy techinque?
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('microscopy',),
    ),

    _t(i.d, 'light microscopy technique',
       (hasParticipant, OntTerm('BIRNLEX:2112', label='Optical microscope')),  # FIXME light microscope !

       #(ilxtr.detects, OntTerm(search='visible light', prefix='obo')),
       #(ilxtr.detects, OntTerm(search='photon', prefix='NIFSTD')),
       (ilxtr.detects, ilxtr.visibleLight),  # TODO photos?
       #(hasParticipant, OntTerm(term='visible light')),  # FIXME !!! detects vs participant ???
       synonyms=('light microscopy',)),
    (ilxtr.lightMicroscope, owl.equivalentClass, OntTerm('BIRNLEX:2112', label='Optical microscope')),

    _t(i.d, 'confocal microscopy technique',
       (hasParticipant, OntTerm('BIRNLEX:2029', label='Confocal microscope')),
       (ilxtr.isConstrainedBy, OntTerm('BIRNLEX:2258', label='Confocal imaging protocol')),
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('confocal microscopy',)),
    (OntTerm('BIRNLEX:2029', label='Confocal microscope'), rdfs.subClassOf, ilxtr.microscope),

    _t(tech.imaging, 'imaging technique',
       (ilxtr.hasInformationOutput, ilxtr.image),
       def_='Imaging is the process of forming an image.',
       synonyms=('imaging',),
    ),

    _t(i.d, 'functional brain imaging',
       (hasParticipant, OntTerm('UBERON:0000955', label='brain')),
       (ilxtr.hasPrimaryAspect, asp.anySpatioTemporalMeasure),  # FIXME and thus we see that 'functional' is a buzzword!
       (ilxtr.hasPrimaryAspect_dAdS, ilxtr.nonZero),
       (ilxtr.hasInformationOutput, ilxtr.image),

       synonyms=('imaging that relies on contrast provided by differential aspects of some biological process',)
       ),
    (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000007')),

    _t(i.d, 'photographic technique',
       (ilxtr.hasInformationOutput, ilxtr.photograph),
       synonyms=('photography',),
    ),

    _t(i.d, 'positron emission imaging',
       (ilxtr.detects, ilxtr.positron),
       (hasOutput, ilxtr.image),
       (ilxtr.detects, ilxtr.positron)),

    _t(tech.opticalImaging, 'optical imaging',
       # FIXME TODO what is the difference between optical imaging and light microscopy?
       (ilxtr.detects, ilxtr.visibleLight),  # owl:Class photon and hasWavelenght range ...
       (hasOutput, ilxtr.image),
       synonyms=('light imaging', 'visible light imaging'),
    ),
    (tech.opticalImaging, ilxtr.hasTempId, OntId("HBP_MEM:0000013")),

    _t(i.d, 'intrinsic optical imaging',
       #tech.opticalImaging,
       #tech.contrastDetection,
       # this is a good counter example to x-ray imaging concernts
       # because it shows clearly how
       # "the reflectance to infared light by the brain"
       # that is not a thing that is a derived thing I think...
       # it is an aspect of the black box, it is not a _part_ of the back box
       (ilxtr.hasProbe, ilxtr.visibleLight),  # FIXME
       (ilxtr.detects, ilxtr.visibleLight),  # FIXME
       #(ilxtr.hasPrimaryAspect, ilxtr.intrinsicSignal),  # this is a 'known phenomena'
       (ilxtr.knownDetectedPhenomena, ilxtr.intrinsicSignal),
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('intrinsic signal optical imaging',),
    ),

    _t(i.d, 'x-ray imaging',
       #tech.imaging,
       (ilxtr.hasInformationOutput, ilxtr.image),
       # VS contrast in the primary aspect being the signal created by the xrays...
       # can probably expand detects in cases where there are non-aspects...
       # still not entirely sure these shouldn't all be aspects too...

       # TODO need a way to deal with the fact that what we really care about here
       # is the connection to the fact that there is some pheonmena that has
       # differential contrast to the pheonmena
       (ilxtr.detects, ilxtr.xrays),
    ),  # owl:Class photon and hasWavelenght range ...

    _t(tech.MRI_ImageProcessing, 'magnetic resonance image processing',
       # the stuff that goes on inside the scanner
       # or afterward to produce the 'classic' output data
       # this way we can create as many subclasses of contrast as we need
       (ilxtr.hasPrimaryAspect, asp.contrast),  # contrast to something? FIXME this seems a bit off...
       (ilxtr.hasPrimaryAspect_dAdS, ilxtr.nonZero),
       (ilxtr.hasSomething, i.d),
      ),

    _t(tech.MRI, 'magnetic resonance imaging',
       #tech.imaging,
       (hasParticipant, ilxtr.MRIScanner),
       (ilxtr.hasPrimaryAspect, ilxtr.nuclearMagneticResonance),  # FIXME hasPrimaryAspect appears twice
       # FIXME the output image for MRI should be subClassOf image, and not done this way
       # NRM is an aspect not one of the mediators
       (hasPart, tech.MRI_ImageProcessing),
       (hasPart, tech.MRI),
       (ilxtr.hasInformationOutput, ilxtr.spatialFrequencyImageStack),  # TODO FIXME
       # as long as the primaryAspect is subClassOf ilxtr.nuclearMagneticResonance then we are ok
       # and we won't get duplication of primary aspects
       synonyms=('MRI', 'nuclear magnetic resonance imaging'),
    ),

    _t(tech.fMRI, 'functional magnetic resonance imaging',
       (ilxtr.isConstrainedBy, prot.fMRI),
       (hasPart, tech.MRI),
       (hasPart, tech.fMRI_ImageProcessing),
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

       ilxtr.technique,
       unionOf(
           intersectionOf(
               restrictionN(ilxtr.hasPart, tech.MRI),
               # TODO 'knownProbedPhenomena' or something similar
               # TODO 
               #restrictionN(ilxtr.hasPrimaryParticipant, OntTerm('CHEBI:15377', label='water')),
               restrictionN(ilxtr.hasPart, tech.dwMRI_ImageProcessing)),
           restrictionN(ilxtr.isConstrainedBy, prot.dwMRI),
       ),
       synonyms=('dwMRI', 'diffusion weighted nuclear magnetic resonance imaging'),
       ),

    _t(tech.dwMRI_ImageProcessing, 'diffusion weighted MRI image processing',
       (ilxtr.hasSomething, i.d),
      ),

    _t(tech.DTI, 'diffusion tensor imaging',
       ilxtr.technique,
       unionOf(
           intersectionOf(restrictionN(hasPart, tech.dwMRI),
                          restrictionN(hasPart, tech.DTI_ImageProcessing)),
           restrictionN(ilxtr.isConstrainedBy, prot.DTI),
           # FIXME not clear that this should be in the intersection...
           # it seems like it may make more sense to do these as unions?
           # TODO kpp kdp
           intersectionOf(
               restrictionN(ilxtr.hasParticipant, ilxtr.MRIScanner),
               restrictionN(ilxtr.knownProbedPhenomena, OntTerm('CHEBI:15377', label='water')),
               restrictionN(ilxtr.knownDetectedPhenomena, OntTerm('CHEBI:15377', label='water')))),
       synonyms=('DTI',),
      ),

    _t(tech.DTI_ImageProcessing, 'diffusion tensor image processing',
       (ilxtr.hasSomething, i.d),
      ),

    _t(i.d, 'electroencephalography',
       (ilxtr.hasSomething, i.b),
       synonyms=('EEG',)),
    (i.p, ilxtr.hasTempId, OntId("HBP_MEM:0000011")),

    _t(i.d, 'magnetoencephalography',
       (ilxtr.hasSomething, i.b),
       synonyms=('MEG',)),
    (i.p, ilxtr.hasTempId, OntId("HBP_MEM:0000012")),
       
    # modification techniques
    _t(i.d, 'modification technique',
       (ilxtr.hasPrimaryAspect, asp.isClassifiedAs),
       # is classified as
       synonyms=('state creation technique', 'state induction technique')
    ),

    _t(i.d, 'activation technique',
       (ilxtr.hasProbe, ilxtr.materialEntity),  # FIXME some pheonmena... very often light...
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
       # hasPrimaryAspect some aspect of the primary participant which FOR THAT PARTICIPANT
       # has been defined as functional
       #(hasPart, ilxtr.),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
    ),

    _t(i.d, 'deactivation technique',
       (ilxtr.hasProbe, ilxtr.materialEntity),  # FIXME some pheonmena... very often light...
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),  # FIXME this is more state?
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
    ),

    _t(tech.killing, 'killing technique',
       (ilxtr.hasPrimaryAspect, asp.aliveness),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
      ),

    _t(i.d, 'euthanasia technique',
       (ilxtr.hasPrimaryAspect, asp.aliveness),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
    ),

    _t(i.d, 'pharmacological technique',
       (ilxtr.hasSomething, i.d),
       (hasParticipant, oc_.full_combinator(restriction(hasRole, OntId('CHEBI:23888')))),
       synonyms=('pharmacology',)
    ),

    _t(i.d, 'photoactivation technique',
       (ilxtr.hasProbe, ilxtr.photons),
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
    ),

    _t(i.d, 'photoinactivation technique',
       (ilxtr.hasProbe, ilxtr.photons),
       (ilxtr.hasPrimaryAspect, asp.boundFunctionalAspect),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
    ),

    _t(i.d, 'photobleaching technique',
       (ilxtr.hasProbe, ilxtr.photons),
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'photoconversion technique',
       (ilxtr.hasProbe, ilxtr.photons),
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'molecular uncaging technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('uncaging', 'uncaging technique')
    ),

    _t(i.d, 'physical modification technique',
       # FIXME for all physical things is it that the aspect is physical?
       # or that there is actually a physical change induced?
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'ablation technique',
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'blinding technique',
       (ilxtr.hasPrimaryAspect, asp.vision),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
    ),

    _t(i.d, 'crushing technique',
       # tissue destruction technique
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'deafferenting technique',
       # tissue destruction technique
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'depolarization technique',
       (ilxtr.hasPrimaryAspect, asp.voltage),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),  # or is it neative (heh)
       # yes this is confusing, but cells have negative membrane potentials
    ),

    _t(i.d, 'hyperpolarization technique',
       (ilxtr.hasPrimaryAspect, asp.voltage),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
    ),

    _t(i.d, 'illumination technique',
       # as distinct from a technique for illuminating a page in a medieval text
       #tech.agnostic,  # TODO agnostic techniques try to do nothing scientific usually
       # they are purely goal driven
       #(ilxtr.phenomena, ilxtr.photons),
       (ilxtr.hasPrimaryAspect, asp.lumenance),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
    ),

    _t(i.d, 'lesioning technique',
       #(hasPart, tech.surgical),  # is this tru
       # has intention to destory some subset of the nervous system
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'sensory deprivation technique',
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'transection technique',
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'stimulation technique',
       #(ilxtr.hasPrimaryAspect, ilxtr.physiologicalActivity),  # TODO
       (ilxtr.hasProbe, ilxtr.materialEntity),
       (ilxtr.hasPrimaryAspect, asp.biologicalActivity),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.positive),
    ),

    _t(i.d, 'physical stimulation technique',  # FIXME another use of physical
       (ilxtr.hasSomething, i.d),
       (ilxtr.hasProbe, ilxtr.mechanicalForce),  # but is this physical?
       def_='A technique using mechanical force to enduce a state change on a system.',
       synonyms=('mechanical stimulation technique',)
    ),

    _t(i.d, 'electrical stimulation technique',
       #(ilxtr.hasProbe, asp.electrical),  # FIXME the probe should be the physical mediator
       #(ilxtr.hasProbe, ilxtr.electricalPhenomena),  # electircal field?
       (ilxtr.hasProbe, ilxtr.electricalField),  # electircal field?
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasSomething, i.d),
    ),

    _t(tech.stim_Magnetic, 'magnetic stimulation technique',
       # TODO need a way to accomodate the stimulation of biological activity
       # with the stimulating phenomena
       # has intention to stimulate???
       (ilxtr.hasProbe, ilxtr.magneticField),  # FIXME TODO duality between stimulus and response...
       (ilxtr.hasPrimaryAspect, asp.magnetic),
    ),

    _t(i.d, 'transcranial magnetic stimulation technique',
       (ilxtr.hasProbe, ilxtr.magneticField),
       (ilxtr.hasPrimaryAspect, asp.magnetic),
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'cortico-cortical evoked potential technique',
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'microstimulation technique',
       (ilxtr.hasSomething, i.d),
    ),

    _t(tech.surgery, 'surgical technique',
       (ilxtr.hasSomething, i.d),
       # any technique that involves the destruction of some anatomical structure
       # which requires healing (if possible)
       (hasPart, tech.cutting),  # FIXME obviously too broad
       synonyms=('surgery',),),

    _t(i.d, 'biopsy technique',
       tech.surgery,  # FIXME
       tech.maintaining,  # things that have output tissue that don't unis something
       (hasOutput, ilxtr.tissue),  # TODO
    ),

    _t(i.d, 'craniotomy technique',
       tech.surgery,  # FIXME
       (ilxtr.hasSomething, i.d),
       def_='Makes a hold in the cranium (head).',
    ),

    _t(i.d, 'durotomy technique',
       tech.surgery,  # FIXME
       (ilxtr.hasSomething, i.d),
       def_='Makes a hold in the dura.',
    ),

    _t(i.d, 'transplantation technique',
       tech.surgery,  # FIXME
       (ilxtr.hasSomething, i.d),
       synonyms=('transplant',)
    ),

    _t(i.d, 'implantation technique',
       tech.surgery,  # FIXME
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'stereotaxic technique',
       tech.surgery,  # FIXME
       (hasParticipant, ilxtr.stereotax),
       (ilxtr.isConstrainedBy, ilxtr.stereotaxiCoordinateSystem),
    ),

    _t(i.d, 'behavioral technique',  # FIXME this is almost always actually some environmental manipulation
       # asp.behavioral -> 'Something measurable aspect of an organisms behavior. i.e. the things that it does.'
       (ilxtr.hasPrimaryAspect, asp.behavioral),
    ),

    _t(i.d, 'behavioral conditioning technique',
       (ilxtr.hasSomething, i.d),
       def_='A technique for producing a specific behavioral response to a set of stimuli.',  # FIXME
       synonyms=('behavioral conditioning', 'conditioning', 'conditioning technique')
    ),

    _t(i.d, 'environmental manipulation technique',
       # FIXME extremely broad, includes basically everything we do in science that is not
       # done directly to the primary subject
       (ilxtr.hasPrimarySubject, ilxtr.notTheSubject),
    ),

    _t(i.d, 'environmental enrichment technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('behavioral enrichment technique',)
       # and here we see the duality between environment and behavior
    ),

    _t(i.d, 'dietary technique',
       ilxtr.technique,
       # unionOf hasPart dietary technique OR hasPrimaryParticipant food
       unionOf(intersectionOf(
           restrictionN(ilxtr.hasPrimaryParticipant, ilxtr.food_and_water),  # metabolic input
           restrictionN(ilxtr.hasPrimaryAspect, asp.allocation)),
           restrictionN(hasPart, i.p))
    ),

    _t(i.d, 'dietary restriction technique',
       (ilxtr.hasSomething, i.d),
       (hasParticipant, ilxtr.food_and_water),  # metabolic input
       # reduction in some metabolic input
    ),

    _t(i.d, 'food deprivation technique',
       (ilxtr.hasPrimaryParticipant, ilxtr.food),
       (ilxtr.hasPrimaryAspect, asp.allocation),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       # the above is correct, use hasPart
       # where the food amount is decresed, how to bind food to negative
       # do we have to use has part?!
       #hasPart, food
       #(hasParticipant, ilxtr.food),
       #(ilxtr.hasConstrainingAspect, asp.amount),
       #oc_(ilxtr.food,
           #asp.amount, ilxtr.negative),
       #hasAspectChangeCombinator(asp.amount, ilxtr.negative),
       synonyms=('starvation technique',
                 'food restriction technique',
                )
    ),

    _t(i.b, 'technique that makes use of food deprivation',
       (hasPart, i.p),),

    _t(i.d, 'water deprivation technique',
       (ilxtr.hasPrimaryParticipant,
        OntTerm('CHEBI:15377', label='water')
       ),
       (ilxtr.hasPrimaryAspect, asp.allocation),
       (ilxtr.hasPrimaryAspect_dAdT, ilxtr.negative),
       synonyms=('water restriction technique',
                 'water restriction',
       )
    ),

    _t(tech.sectioning, 'sectioning technique',
       tech.destroying,  # ok to assert here
       # easier than having say inputs are not outputs every time
       # NOTE: the thing to be sectioned is thus the primary participant
       # conservation of mass/energy implies that it is also a creating technique
       # if viewed from the persective of the sections
       # we should be able to infer that the outputs
       # from a sectioning technique were 'created'
       #(hasOutput, ilxtr.sectionsOfPrimaryInput),  # FIXME circular
       (hasOutput,
        oc_.full_combinator(intersectionOf(
            restrictionN(partOf,
                         restrictionN(ilxtr.primaryParticipantIn,
                                      tech.sectioning)),
            restrictionN(ilxtr.hasAssessedAspect,
                         asp.flatness)))),
                        #intersectionOf(
                        # hasAssessedAspect better than hasAspect?
                        # implies there is another technique...
                        # you can measure the flatness of the himallayals
                        # or of an electron if you wanted
                        # so hasAspect is maybe not the best?
       synonyms=('sectioning',)),  # FIXME

    _t(i.d, 'tissue sectioning technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('UBERON:0000479', label='tissue')),
       synonyms=('tissue sectioning',)),

    _t(i.d, 'brain sectioning technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('UBERON:0000955', label='brain')),
       synonyms=('brain sectioning',)),

    _t(i.d, 'block face sectioning technique',
       # SBEM vs block face for gross anatomical registration
       tech.sectioning,
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, 'microtomy technique',
       (ilxtr.hasParticipant, ilxtr.microtome),
       (hasOutput, ilxtr.thinSections),  # this prevents issues with microtome based warfare techniques
       synonyms=('microtomy',)
    ),

    _t(i.d, 'ultramicrotomy technique',
       (ilxtr.hasParticipant, ilxtr.ultramicrotome),
       (hasOutput, ilxtr.veryThinSections),  # FIXME has intended output?
       synonyms=('ultramicrotomy',)
    ),

    _t(i.d, 'array tomographic technique',
       (hasPart, tech.microscopy),
       #(hasParticipant, ilxtr.microscope),  # FIXME more precisely?
       (ilxtr.isConstrainedBy, ilxtr.radonTransform),
       synonyms=('array tomography', 'array tomography technique')
    ),

    _t(tech.electronMicroscopy, 'electron microscopy technique',
       (hasParticipant, OntTerm('BIRNLEX:2041', label='Electron microscope', synonyms=[])),
       (ilxtr.detects, OntTerm('CHEBI:10545', label='electron')),  # FIXME chebi ok in this context?
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('electron microscopy',)),
    (tech.electronMicroscopy, oboInOwl.hasDbXref, OntTerm('NLX:82779')),  # ICK from assay branch which conflates measurement :/

    _t(i.d, 'correlative light-electron microscopy technique',
       (hasParticipant, OntTerm('BIRNLEX:2041', label='Electron microscope')),
       # this works extremely well because the information outputs propagate nicely
       (hasPart, tech.lightMicroscopy),
       (hasPart, tech.electronMicroscopy),
       (ilxtr.hasInformationOutput, ilxtr.image),
       synonyms=('correlative light-electron microscopy',)
    ),

    _t(i.d, 'serial blockface electron microscopy technique',
       (hasPart, tech.electronMicroscopy),
       (hasPart, tech.ultramicrotomy),
       #(hasParticipant, OntTerm('BIRNLEX:2041', label='Electron microscope')),
       #(hasParticipant, ilxtr.ultramicrotome),
       synonyms=('serial blockface electron microscopy',)
    ),

    _t(i.d, 'super resolution microscopy technique',
       #(hasParticipant, OntTerm('BIRNLEX:2106', label='Microscope', synonyms=[])),  # TODO more
       (hasPart, tech.microscopy),  # FIXME special restriction on the properties of the scope?
       (ilxtr.isConstrainedBy, ilxtr.superResolutionAlgorithem),
       synonyms=('super resolution microscopy',)
    ),

    _t(i.d, 'northern blotting technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('northern blot',)
    ),
    _t(i.d, 'southern blotting technique',
       (ilxtr.hasSomething, i.d),
       synonyms=('southern blot',)
    ),
    _t(i.d, 'western blotting technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('PR:000000001', label='protein')),  # at least one
       (hasParticipant, OntTerm('BIRNLEX:2110', label='Antibody')),
       synonyms=('wester blot',)),
    (i.p, ilxtr.hasTempId, OntId("HBP_MEM:0000112")),

    _t(i.d, 'intracellular electrophysiology technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('SAO:1289190043', label='Cellular Space')),  # TODO add intracellular as synonym
    ),

    _t(tech.extracellularEphys, 'extracellular electrophysiology technique',
       (ilxtr.hasPrimaryParticipant, OntTerm('GO:0005615', label='extracellular space')),
    ),
    (tech.extracellularEphys, ilxtr.hasTempId, OntId('HBP_MEM:0000015')),

    _t(tech.singleElectrodeEphys, 'single electrode extracellular electrophysiology technique',
       # FIXME extracellular space that is part of some other participant... how to convey this...
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasPrimaryParticipant, OntTerm('GO:0005615', label='extracellular space')),
       (ilxtr.hasParticipant, ilxtr.singleElectrode),  # cardinality 1?
       synonyms=('single extracellular electrode technique',)),
       (tech.singleElectrodeEphys, ilxtr.hasTempId, OntId('HBP_MEM:0000019')),

    # FIXME should probably be to a higher level go?
    (OntTerm('GO:0005615', label='extracellular space'), rdfs.subClassOf, ilxtr.physiologicalSystem),

    _t(tech.sharpElectrodeEphys, 'sharp intracellular electrode technique',
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasPrimaryParticipant, ilxtr.physiologicalSystem),
       (ilxtr.hasParticipant, ilxtr.sharpElectrode),
       synonyms=('sharp electrode technique',)),
       (tech.sharpElectrodeEphys, ilxtr.hasTempId, OntId('HBP_MEM:0000023')),

    _t(tech.patchClamp, 'patch clamp technique',
       (ilxtr.hasPrimaryAspect, asp.electrical),
       (ilxtr.hasPrimaryParticipant, ilxtr.cellMembrane),
       (ilxtr.hasSomething, i.d),
    ),
       (tech.patchClamp, ilxtr.hasTempId, OntId('HBP_MEM:0000017')),

    _t(i.d, 'cell attached patch technique',
       (ilxtr.hasSomething, i.b),
    ),
       (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000029')),

    _t(i.d, 'inside out patch technique',
       (ilxtr.hasSomething, i.b),
    ),
       (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000028')),

    _t(i.d, 'loose patch technique',
       (ilxtr.hasSomething, i.b),
    ),
       (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000024')),

    _t(i.d, 'outside out patch technique',
       (ilxtr.hasSomething, i.b),
    ),
       (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000026')),

    _t(i.d, 'perforated patch technique',
       (ilxtr.hasSomething, i.b),
    ),
       (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000025')),

    _t(i.d, 'whole cell patch clamp technique',
       (ilxtr.hasSomething, i.b),
    ),
       (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000027')),

    _t(i.d, 'current clamp technique',
       (ilxtr.hasSomething, i.b),
    ),
       (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000204')),

    _t(i.d, 'voltage clamp technique',
       (ilxtr.hasSomething, i.b),
    ),
       (i.p, ilxtr.hasTempId, OntId('HBP_MEM:0000203')),

    _t(i.d, ' technique',
       (ilxtr.hasSomething, i.d),
    ),

    _t(i.d, ' technique',
       (ilxtr.hasSomething, i.d),
    ),
)
triples += (  # aspects

            oc(asp.behavioral, ilxtr.aspect),

            oc(asp.physiological, ilxtr.aspect),  # FIXME vs ilxtr.physiologicalSystem?

            oc(asp.sequence, ilxtr.aspect),
            #(OntTerm('SO:0000001', label='region', synonyms=['sequence']), rdfs.subClassOf, asp.sequence), this very much does not work...

            oc(asp.sensory, ilxtr.aspect),
            oc(asp.vision, asp.sensory),

            oc(asp.anySpatioTemporalMeasure, ilxtr.aspect),  # FIXME
            oc(asp.electromagnetic, ilxtr.aspect),
            oc(asp.electrical, asp.electromagnetic),
            oc(asp.voltage, asp.electrical),
            oc(asp.current, asp.electrical),
            oc(asp.charge, asp.electrical),
            oc(asp.magnetic, asp.electromagnetic),

            oc(asp.informationEntropy, ilxtr.aspect),
            oc(asp.mechanicalRigidity, ilxtr.aspect),
            oc(asp.spectrum, ilxtr.aspect),
            oc(asp.spontaneousChangeInStructure, ilxtr.aspect),

            oc(asp.physicalOrderedness, ilxtr.aspect),
            oc(asp.latticePeriodicity, asp.physicalOrderedness),  # physical order

            #oc(asp.functional, ilxtr.aspect),  # asp.functional is not the right way to model this
            #olit(ilxtr.functionalAspectRole, definition,
                 #('A functional aspect is any aspect that can be used to define ')),
            oc(asp.biologicalActivity, ilxtr.aspect),  # TODO very broad from enyme activity to calories burned
            #oc(asp.circadianPhase, asp.biologicalActivity),
            oc(asp.circadianPhase, ilxtr.aspect),  # FIXME hrm... time as a proxy for biological state?

            oc(asp.sensitvity, ilxtr.aspect),
            # FIXME issue with sensitivity and the 'towards' relation

            oc(asp.functionalDefinition, asp['is']),  # TODO not quite right?
            oc(asp.permeability, asp.functionalDefinition),  # changes some functional property so is thus an isness?
)

triples += ( # protocols
            oc(prot.CLARITY, ilxtr.protocol),
            oc(prot.deepSequencing, ilxtr.protocol),
            oc(prot.sangerSequencing, ilxtr.protocol),
            oc(prot.shotgunSequencing, ilxtr.protocol),
           )

triples += ( # information entity
            oc(ilxtr.superResolutionAlgorithem, ilxtr.informationEntity),
            oc(ilxtr.stereotaxiCoordinateSystem, ilxtr.informationEntity),
            oc(ilxtr.radonTransform, ilxtr.informationEntity),
)

triples += (  # other
            oc(ilxtr.thingWithSequence),
            oc(OntTerm('CHEBI:33696', label='nucleic acid'), ilxtr.thingWithSequence),  # FIXME should not have to put oc here, but byto[ito] becomes unhappy

            # FIXME owl:sameAs is NOT for generic iris >_<
            oc(ilxtr.physiologicalSystem, ilxtr.materialEntity),
            oc(ilxtr.brainSlice, ilxtr.materialEntity),

            oc(ilxtr.informationArtifact),  # FIXME entity vs artifact, i think clearly artifact by my def
            oc(ilxtr.image, ilxtr.informationArtifact),
            olit(ilxtr.image,
                 definition,
                 ('A symbolic representation of some spatial or spatial-temporal '
                  'aspect of a participant. Often takes the form of a 2d or 3d matrix '
                  'that has some mapping to sensor space and may also be collected at '
                  'multiple timepoints. Regardless of the ultimate format has some '
                  'part that can be reduced to a two dimensional matrix.'  # TODO
                 )),
            oc(ilxtr.spatialFrequencyImageStack, ilxtr.image),

            oc(ilxtr.food_and_water, ilxtr.materialEntity),
            oc(ilxtr.food, ilxtr.food_and_water),  # TODO edible organic matter with variable nutritional value depending on the organism
            oc(ilxtr.highFatDiet, ilxtr.food),
            oc(ilxtr.DIODiet, ilxtr.highFatDiet),
            oc(ilx['researchdiets/uris/productnumber/D12492'], ilxtr.DIODiet),

            # TODO have parcellation-artifacts import methods-core?
            oc(ilxtr.parcellationArtifact, ilxtr.informationArtifact),
            oc(ilxtr.parcellationCoordinateSystem, ilxtr.parcellationArtifact),
            oc(ilxtr.parcellationCoordinateSystem, ilxtr.parcellationArtifact),
            oc(ilxtr.commonCoordinateFramework, ilxtr.parcellationCoordinateSystem),
            olit(ilxtr.commonCoordinateFramework, rdfs.label, 'common coordinate framework'),
            olit(ilxtr.commonCoordinateFramework, NIFRID.synonym, 'CCF', 'atlas coordinate framework'),
            oc(ilxtr.microPipette, ilxtr.materialEntity),
            oc(ilxtr.microscope, ilxtr.materialEntity),
            oc(ilxtr.lightMicroscope, ilxtr.microscope),
            oc(OntTerm('BIRNLEX:2041', label='Electron microscope', synonyms=[]), ilxtr.microscope),
            oc(ilxtr.microtome, ilxtr.materialEntity),
            oc(ilxtr.ultramicrotome, ilxtr.microtome),
            oc(ilxtr.stereotax, ilxtr.materialEntity),

            oc(ilxtr.photons, ilxtr.materialEntity),
            oc(ilxtr.visibleLight, ilxtr.photons),
            oc(ilxtr.xrays, ilxtr.photons),

            # FIXME
            oc(OntTerm('CHEBI:33697', label='RNA'), OntTerm('CHEBI:33696', label='nucleic acid')),
            oc(ilxtr.mRNA, OntTerm('CHEBI:33697', label='RNA')),

            oc(ilxtr.positive, ilxtr.changeType),
            oc(ilxtr.negative, ilxtr.changeType),
            (ilxtr.negative, owl.disjointWith, ilxtr.positive),
            oc(ilxtr.nonZero, ilxtr.changeType),
            oc(ilxtr.zero, ilxtr.changeType),
            (ilxtr.zero, owl.disjointWith, ilxtr.nonZero),

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
(tech.fMRI, ilxtr.hasTempId, OntId("HBP_MEM:0000008")),
"""


methods = simpleOnt(filename=filename,
                    prefixes=prefixes,
                    imports=imports,
                    triples=triples,
                    comment=comment,
                    _repo=_repo)

[methods.graph.add((o2, rdfs.subClassOf, TEMP.urg))
 for s1, p1, o1 in methods.graph if
 p1 == owl.onProperty and
 o1 == ilxtr.hasSomething
 for p2, o2 in methods.graph[s1:] if
 p2 == owl.someValuesFrom]

methods._graph.add_namespace('asp', str(asp))
methods._graph.add_namespace('ilxtr', str(ilxtr))  # FIXME why is this now showing up...
methods._graph.add_namespace('tech', str(tech))
methods._graph.add_namespace('HBP_MEM', OntCuries['HBP_MEM'])
methods._graph.write()

def halp():
    import rdflib
    from IPython import embed
    trips = sorted(flattenTriples(triples))
    graph = rdflib.Graph()
    *(graph.add(t) for t in trips),
    *(print(tuple(qname(e) if not isinstance(e, rdflib.BNode) else e[:5] for e in t)) for t in trips),
    embed()
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

def main():
    displayGraph(methods.graph, debug=debug)
    mc = methods.graph.__class__()
    #mc.add(t) for t in methods_core.graph if t[0] not in
    expand(methods_core._graph, methods_core.graph)#, methods_core.graph)  # FIXME including core breaks everying?
    expand(methods._graph, methods.graph)#, methods_core.graph)  # FIXME including core breaks everying?

if __name__ == '__main__':
    pass
    #main()
