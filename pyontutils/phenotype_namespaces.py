#!/usr/bin/env python3

from pyontutils.neurons import *  # namesets can only be effectively defined over a specific base...
from pyontutils.neurons.lang import config  # annoying, but works

__all__ = ['Test',
           'Layers',
           'PaxRatLayers',
           'Regions',
           'PaxRatRegions',
           'Species',
           'BBP']


class Test(LocalNameManager):
    LOOK_AT_THE_CUTE_LITTLE_GUY = Phenotype('NCBITaxon:10116', 'ilxtr:hasInstanceInSpecies')


class Layers(LocalNameManager):
    # TODO there might be a way to set a default predicate here...
    L1 = Phenotype('UBERON:0005390', 'ilxtr:hasLayerLocationPhenotype')
    L2 = Phenotype('UBERON:0005391', 'ilxtr:hasLayerLocationPhenotype')
    L3 = Phenotype('UBERON:0005392', 'ilxtr:hasLayerLocationPhenotype')
    L23 = LogicalPhenotype(OR, L2, L3)
    L4 = Phenotype('UBERON:0005393', 'ilxtr:hasLayerLocationPhenotype')
    L5 = Phenotype('UBERON:0005394', 'ilxtr:hasLayerLocationPhenotype')
    L6 = Phenotype('UBERON:0005395', 'ilxtr:hasLayerLocationPhenotype')

    SO = Phenotype('UBERON:0005371', 'ilxtr:hasLayerLocationPhenotype')  # WARNING: uberon has precomposed these, which is annoying
    SPy = Phenotype('UBERON:0002313', 'ilxtr:hasLayerLocationPhenotype')  # SP
    SLA = Phenotype('UBERON:0005370', 'ilxtr:hasLayerLocationPhenotype')
    SLM = Phenotype('UBERON:0007640', 'ilxtr:hasLayerLocationPhenotype')
    SLU = Phenotype('UBERON:0007637', 'ilxtr:hasLayerLocationPhenotype')
    SR = Phenotype('UBERON:0005372', 'ilxtr:hasLayerLocationPhenotype')


class PaxRatLayers(LocalNameManager):
    # TODO there might be a way to set a default predicate here...
    L1 = Phenotype('PAXRAT:509', 'ilxtr:hasLayerLocationPhenotype')
    L2 = Phenotype('PAXRAT:512', 'ilxtr:hasLayerLocationPhenotype')
    L3 = Phenotype('PAXRAT:513', 'ilxtr:hasLayerLocationPhenotype')
    L23 = LogicalPhenotype(OR, L2, L3)
    L4 = Phenotype('PAXRAT:515', 'ilxtr:hasLayerLocationPhenotype')
    L5 = Phenotype('PAXRAT:516', 'ilxtr:hasLayerLocationPhenotype')
    L6 = Phenotype('PAXRAT:519', 'ilxtr:hasLayerLocationPhenotype')

    SO = Phenotype('PAXRAT:675', 'ilxtr:hasLayerLocationPhenotype')  # WARNING: uberon has precomposed these, which is annoying
    SPy = Phenotype('PAXRAT:815', 'ilxtr:hasLayerLocationPhenotype')  # SP
    #SLA = Phenotype('', 'ilxtr:hasLayerLocationPhenotype')  # paxrat does not seem to have this, only LM
    SLM = Phenotype('PAXRAT:443', 'ilxtr:hasLayerLocationPhenotype')
    SLU = Phenotype('PAXRAT:901', 'ilxtr:hasLayerLocationPhenotype')
    SR = Phenotype('PAXRAT:822', 'ilxtr:hasLayerLocationPhenotype')


class Regions(LocalNameManager):
    #('brain = Phenotype('UBERON:0000955', 'ilxtr:hasLocationPhenotype')  # hasLocationPhenotype a high level
    brain = Phenotype('UBERON:0000955', 'ilxtr:hasSomaLocatedIn')
    CTX = Phenotype('UBERON:0001950', 'ilxtr:hasSomaLocatedIn')
    CA2 = Phenotype('UBERON:0003882', 'ilxtr:hasSomaLocatedIn')
    CA3 = Phenotype('UBERON:0003883', 'ilxtr:hasSomaLocatedIn')
    S1 = Phenotype('UBERON:0008933', 'ilxtr:hasSomaLocatedIn')
    CA1 = Phenotype('UBERON:0003881', 'ilxtr:hasSomaLocatedIn')


class PaxRatRegions(LocalNameManager):
    brain = Phenotype('UBERON:0000955', 'ilxtr:hasSomaLocatedIn')  # paxinos does not go this high
    CTX = Phenotype('UBERON:0001950', 'ilxtr:hasSomaLocatedIn')  # paxinos does not go this high
    CA1 = Phenotype('PAXRAT:322', 'ilxtr:hasSomaLocatedIn')
    CA2 = Phenotype('PAXRAT:323', 'ilxtr:hasSomaLocatedIn')
    CA3 = Phenotype('PAXRAT:324', 'ilxtr:hasSomaLocatedIn')
    S1 = Phenotype('PAXRAT:794', 'ilxtr:hasSomaLocatedIn')


class Species(LocalNameManager):
    Rat = Phenotype('NCBITaxon:10116', 'ilxtr:hasInstanceInSpecies')
    Mouse = Phenotype('NCBITaxon:10090', 'ilxtr:hasInstanceInSpecies')


class BBP(PaxRatLayers, PaxRatRegions, Species):
    # cat old_neuron_example.py | grep -v ^# | grep -o "\w\+\ \=\ Pheno.\+" | sed "s/^/('/" | sed "s/\ \=\ /',/" | sed 's/Phenotype(//' | sed 's/)/)/'
    PC = Phenotype('ilxtr:PyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')  #
    BPC = Phenotype('ilxtr:BiopolarPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # collision
    HPC = Phenotype('ilxtr:HorizontalPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    IPC = Phenotype('ilxtr:InvertedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    NPC = Phenotype('ilxtr:NarrowPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # XXX These are apparently tufted.... so are they NarrowTufted or not? help!
    SPC = Phenotype('ilxtr:StarPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # collision with stratum pyramidale
    TPC_C = Phenotype('ilxtr:NarrowTuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # are this different?  Yes, the Narrow modifieds the tufted... not entirely sure how that is different from when Narrow modifies Pyramidal...
    TPC = Phenotype('ilxtr:TuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    STPC = Phenotype('ilxtr:SlenderTuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    TTPC = Phenotype('ilxtr:ThickTuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    TTPC1 = Phenotype('ilxtr:LateBifurcatingThickTuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    TTPC2 = Phenotype('ilxtr:EarlyBifurcatingThickTuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    TPC_A = Phenotype('ilxtr:LateBifurcatingTuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype') # these are inconsistent with usages like NGC_DA NGC_SA recomend the NGCDA NGCSA versions since the acronym is better than a/b 1/2
    TPC_B = Phenotype('ilxtr:EarlyBifurcatingTuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    UTPC = Phenotype('ilxtr:UntuftedPyramidalPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    BTC = Phenotype('ilxtr:BituftedPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    BP = Phenotype('ilxtr:BipolarPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # NOTE disjoint from biopolar pyramidal... also collision
    BS = Phenotype('ilxtr:BistratifiedPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    ChC = Phenotype('ilxtr:ChandelierPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # AA ??
    DBC = Phenotype('ilxtr:DoubleBouquetPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    DAC = Phenotype('ilxtr:DescendingAxonPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # FIXME how to communicate that these are a bit different than actual 'axon' phenotypes? disjoint from P?
    HAC = Phenotype('ilxtr:HorizontalAxonPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    LAC = Phenotype('ilxtr:LargeAxonPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    SAC = Phenotype('ilxtr:SmallAxonPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    MC = Phenotype('ilxtr:MartinottiPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    NGC = Phenotype('ilxtr:NeurogliaformPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    NGCDA = Phenotype('ilxtr:NeurogliaformDenseAxonPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # NGC_DA
    NGCSA = Phenotype('ilxtr:NeurogliaformSparseAxonPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # NGC_SA
    BC = Phenotype('ilxtr:BasketPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    SBC = Phenotype('ilxtr:SmallBasketPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    LBC = Phenotype('ilxtr:LargeBasketPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    NBC = Phenotype('ilxtr:NestBasketPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    SS = Phenotype('ilxtr:SpinyStellatePhenotype', 'ilxtr:hasMorphologicalPhenotype')  # SS is used on the website, SSC is used on the spreadsheet TODO usecase for non-injective naming...
    AC = Phenotype('ilxtr:PetillaSustainedAccomodatingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    NAC = Phenotype('ilxtr:PetillaSustainedNonAccomodatingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    STUT = Phenotype('ilxtr:PetillaSustainedStutteringPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    IR = Phenotype('ilxtr:PetillaSustainedIrregularPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    b = Phenotype('ilxtr:PetillaInitialBurstSpikingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    c = Phenotype('ilxtr:PetillaInitialClassicalSpikingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    d = Phenotype('ilxtr:PetillaInitialDelayedSpikingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    FS = Phenotype('ilxtr:FastSpikingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    RSNP = Phenotype('ilxtr:RegularSpikingNonPyramidalPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype')
    L1D = Phenotype('UBERON:0005390', 'ilxtr:hasDendriteLocatedIn')
    L4D = Phenotype('UBERON:0005393', 'ilxtr:hasDendriteLocatedIn')
    L1P = Phenotype('UBERON:0005390', 'ilxtr:hasProjectionPhenotype')
    L4P = Phenotype('UBERON:0005393', 'ilxtr:hasProjectionPhenotype')
    SLMP = Phenotype('UBERON:0007640', 'ilxtr:hasProjectionPhenotype')
    ThalP = Phenotype('UBERON:0001897', 'ilxtr:hasProjectionPhenotype')
    CB = Phenotype('PR:000004967', 'ilxtr:hasExpressionPhenotype')
    CCK = Phenotype('PR:000005110', 'ilxtr:hasExpressionPhenotype')
    CR = Phenotype('PR:000004968', 'ilxtr:hasExpressionPhenotype')
    NPY = Phenotype('PR:000011387', 'ilxtr:hasExpressionPhenotype')
    PV = Phenotype('PR:000013502', 'ilxtr:hasExpressionPhenotype')
    #PV = Phenotype('PR:000013502_1', 'ilxtr:hasExpressionPhenotype')  # this errors as expected
    #PVP = Phenotype('PR:000013502', 'ilxtr:hasExpressionPhenotype')  # this errors as expected
    SOM = Phenotype('PR:000015665', 'ilxtr:hasExpressionPhenotype')
    VIP = Phenotype('PR:000017299', 'ilxtr:hasExpressionPhenotype')
    GABA = Phenotype('CHEBI:16865', 'ilxtr:hasExpressionPhenotype')
    D1 = Phenotype('PR:000001175', 'ilxtr:hasExpressionPhenotype')
    DA = Phenotype('CHEBI:18243', 'ilxtr:hasExpressionPhenotype')
    Th = Phenotype('ilxtr:ThickPhenotype', 'ilxtr:hasDendriteMorphologicalPhenotype')
    Tu = Phenotype('ilxtr:TuftedPhenotype', 'ilxtr:hasDendriteMorphologicalPhenotype')
    U = NegPhenotype(Tu)
    S = Phenotype('ilxtr:SlenderPhenotype', 'ilxtr:hasDendriteMorphologicalPhenotype')
    EB = Phenotype('ilxtr:EarlyBifurcatingPhenotype', 'ilxtr:hasDendriteMorphologicalPhenotype')
    LB = Phenotype('ilxtr:LateBifurcatingPhenotype', 'ilxtr:hasDendriteMorphologicalPhenotype')
    Sp = Phenotype('ilxtr:SpinyPhenotype', 'ilxtr:hasDendriteMorphologicalPhenotype')
    ASp = NegPhenotype(Sp)
    PPA = Phenotype('ilxtr:PerforantPathwayAssociated', 'ilxtr:hasPhenotype')  # TODO FIXME
    TRI = Phenotype('ilxtr:TrilaminarPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    IVY = Phenotype('ilxtr:IvyPhenotype', 'ilxtr:hasMorphologicalPhenotype')  # check syns on this?
    SCA = Phenotype('GO:1990021', 'ilxtr:hasProjectionPhenotype')  #'ilxtr:hasAssociatedTractPhenotype')  # how to model these... also schaffer collaterals are a MESS in the ontology FIXME
    #STRI = Phenotype('UBERON:0005383', 'ilxtr:hasSomaLocatedIn')  # VS UBERON:0002435 (always comes up)
    STRI = Phenotype('PAXRAT:168', 'ilxtr:hasSomaLocatedIn')  # VS UBERON:0002435 (always comes up)
    MSN = Phenotype('ilxtr:MediumSpinyPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    INT = Phenotype('ilxtr:InterneuronPhenotype', 'ilxtr:hasCircuitRolePhenotype')  # unsatisfactory
    #CER = Phenotype('UBERON:0002037', 'ilxtr:hasSomaLocatedIn')
    CER = Phenotype('PAXRAT:191', 'ilxtr:hasSomaLocatedIn')
    GRAN = Phenotype('ilxtr:GranulePhenotype', 'ilxtr:hasMorphologicalPhenotype')  # vs granular?

