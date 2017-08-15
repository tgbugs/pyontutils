#!/usr/bin/env python3

import inspect
from pyontutils.neurons import *  # namesets can only be effectively defined over a specific base...
from pyontutils.neuron_lang import config  # annoying, but works

__all__ = ['Test',
           'Layers',
           'Regions',
           'Species',
           'BBP']

class Test(LocalNameManager):
    LOOK_AT_THE_CUTE_LITTLE_GUY = Phenotype('NCBITaxon:10116', 'ilx:hasInstanceInSpecies')

class Layers(LocalNameManager):
    # TODO there might be a way to set a default predicate here...
    L1 = Phenotype('UBERON:0005390', 'ilx:hasLayerLocationPhenotype')
    L2 = Phenotype('UBERON:0005391', 'ilx:hasLayerLocationPhenotype')
    L3 = Phenotype('UBERON:0005392', 'ilx:hasLayerLocationPhenotype')
    L23 = LogicalPhenotype(OR, L2, L3)
    L4 = Phenotype('UBERON:0005393', 'ilx:hasLayerLocationPhenotype')
    L5 = Phenotype('UBERON:0005394', 'ilx:hasLayerLocationPhenotype')
    L6 = Phenotype('UBERON:0005395', 'ilx:hasLayerLocationPhenotype')

    SO = Phenotype('UBERON:0005371', 'ilx:hasLayerLocationPhenotype')  # WARNING: uberon has precomposed these, which is annoying
    SPy = Phenotype('UBERON:0002313', 'ilx:hasLayerLocationPhenotype')  # SP
    SLA = Phenotype('UBERON:0005370', 'ilx:hasLayerLocationPhenotype')
    SLM = Phenotype('UBERON:0007640', 'ilx:hasLayerLocationPhenotype')
    SLU = Phenotype('UBERON:0007637', 'ilx:hasLayerLocationPhenotype')
    SR = Phenotype('UBERON:0005372', 'ilx:hasLayerLocationPhenotype')

class Regions(LocalNameManager):
    #('brain = Phenotype('UBERON:0000955', 'ilx:hasLocationPhenotype')  # hasLocationPhenotype a high level
    brain = Phenotype('UBERON:0000955', 'ilx:hasSomaLocatedIn')
    CTX = Phenotype('UBERON:0001950', 'ilx:hasSomaLocatedIn')
    CA2 = Phenotype('UBERON:0003882', 'ilx:hasSomaLocatedIn')
    CA3 = Phenotype('UBERON:0003883', 'ilx:hasSomaLocatedIn')
    S1 = Phenotype('UBERON:0008933', 'ilx:hasSomaLocatedIn')
    CA1 = Phenotype('UBERON:0003881', 'ilx:hasSomaLocatedIn')

class Species(LocalNameManager):
    Rat = Phenotype('NCBITaxon:10116', 'ilx:hasInstanceInSpecies')
    Mouse = Phenotype('NCBITaxon:10090', 'ilx:hasInstanceInSpecies')

class BBP(Layers, Regions, Species):
    # cat old_neuron_example.py | grep -v ^# | grep -o "\w\+\ \=\ Pheno.\+" | sed "s/^/('/" | sed "s/\ \=\ /',/" | sed 's/Phenotype(//' | sed 's/)/)/'
    PC = Phenotype('ilx:PyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # 
    BPC = Phenotype('ilx:BiopolarPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # collision
    HPC = Phenotype('ilx:HorizontalPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    IPC = Phenotype('ilx:InvertedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    NPC = Phenotype('ilx:NarrowPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # XXX These are apparently tufted.... so are they NarrowTufted or not? help!
    SPC = Phenotype('ilx:StarPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # collision with stratum pyramidale
    TPC_C = Phenotype('ilx:NarrowTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # are this different?  Yes, the Narrow modifieds the tufted... not entirely sure how that is different from when Narrow modifies Pyramidal...
    TPC = Phenotype('ilx:TuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    STPC = Phenotype('ilx:SlenderTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    TTPC = Phenotype('ilx:ThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    TTPC1 = Phenotype('ilx:LateBifurcatingThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    TTPC2 = Phenotype('ilx:EarlyBifurcatingThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    TPC_A = Phenotype('ilx:LateBifurcatingTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype') # these are inconsistent with usages like NGC_DA NGC_SA recomend the NGCDA NGCSA versions since the acronym is better than a/b 1/2
    TPC_B = Phenotype('ilx:EarlyBifurcatingTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    UTPC = Phenotype('ilx:UntuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    BTC = Phenotype('ilx:BituftedPhenotype', 'ilx:hasMorphologicalPhenotype')
    BP = Phenotype('ilx:BipolarPhenotype', 'ilx:hasMorphologicalPhenotype')  # NOTE disjoint from biopolar pyramidal... also collision
    BS = Phenotype('ilx:BistratifiedPhenotype', 'ilx:hasMorphologicalPhenotype')
    ChC = Phenotype('ilx:ChandelierPhenotype', 'ilx:hasMorphologicalPhenotype')  # AA ??
    DBC = Phenotype('ilx:DoubleBouquetPhenotype', 'ilx:hasMorphologicalPhenotype')
    DAC = Phenotype('ilx:DescendingAxonPhenotype', 'ilx:hasMorphologicalPhenotype')  # FIXME how to communicate that these are a bit different than actual 'axon' phenotypes? disjoint from P?
    HAC = Phenotype('ilx:HorizontalAxonPhenotype', 'ilx:hasMorphologicalPhenotype')
    LAC = Phenotype('ilx:LargeAxonPhenotype', 'ilx:hasMorphologicalPhenotype')
    SAC = Phenotype('ilx:SmallAxonPhenotype', 'ilx:hasMorphologicalPhenotype')
    MC = Phenotype('ilx:MartinottiPhenotype', 'ilx:hasMorphologicalPhenotype')
    NGC = Phenotype('ilx:NeurogliaformPhenotype', 'ilx:hasMorphologicalPhenotype')
    NGCDA = Phenotype('ilx:NeurogliaformDenseAxonPhenotype', 'ilx:hasMorphologicalPhenotype')  # NGC_DA
    NGCSA = Phenotype('ilx:NeurogliaformSparseAxonPhenotype', 'ilx:hasMorphologicalPhenotype')  # NGC_SA
    BC = Phenotype('ilx:BasketPhenotype', 'ilx:hasMorphologicalPhenotype')
    SBC = Phenotype('ilx:SmallBasketPhenotype', 'ilx:hasMorphologicalPhenotype')
    LBC = Phenotype('ilx:LargeBasketPhenotype', 'ilx:hasMorphologicalPhenotype')
    NBC = Phenotype('ilx:NestBasketPhenotype', 'ilx:hasMorphologicalPhenotype')
    SS = Phenotype('ilx:SpinyStellatePhenotype', 'ilx:hasMorphologicalPhenotype')  # SS is used on the website, SSC is used on the spreadsheet TODO usecase for non-injective naming...
    AC = Phenotype('ilx:PetillaSustainedAccomodatingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    NAC = Phenotype('ilx:PetillaSustainedNonAccomodatingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    STUT = Phenotype('ilx:PetillaSustainedStutteringPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    IR = Phenotype('ilx:PetillaSustainedIrregularPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    b = Phenotype('ilx:PetillaInitialBurstSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    c = Phenotype('ilx:PetillaInitialClassicalSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    d = Phenotype('ilx:PetillaInitialDelayedSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    FS = Phenotype('ilx:FastSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    RSNP = Phenotype('ilx:RegularSpikingNonPyramidalPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    L1D = Phenotype('UBERON:0005390', 'ilx:hasDendriteLocatedIn')
    L4D = Phenotype('UBERON:0005393', 'ilx:hasDendriteLocatedIn')
    L1P = Phenotype('UBERON:0005390', 'ilx:hasProjectionPhenotype')
    L4P = Phenotype('UBERON:0005393', 'ilx:hasProjectionPhenotype')
    SLMP = Phenotype('UBERON:0007640', 'ilx:hasProjectionPhenotype')
    ThalP = Phenotype('UBERON:0001897', 'ilx:hasProjectionPhenotype')
    CB = Phenotype('PR:000004967', 'ilx:hasExpressionPhenotype')
    CCK = Phenotype('PR:000005110', 'ilx:hasExpressionPhenotype')
    CR = Phenotype('PR:000004968', 'ilx:hasExpressionPhenotype')
    NPY = Phenotype('PR:000011387', 'ilx:hasExpressionPhenotype')
    PV = Phenotype('PR:000013502', 'ilx:hasExpressionPhenotype')
    #PV = Phenotype('PR:000013502_1', 'ilx:hasExpressionPhenotype')  # this errors as expected
    #PVP = Phenotype('PR:000013502', 'ilx:hasExpressionPhenotype')  # this errors as expected
    SOM = Phenotype('PR:000015665', 'ilx:hasExpressionPhenotype')
    VIP = Phenotype('PR:000017299', 'ilx:hasExpressionPhenotype')
    GABA = Phenotype('CHEBI:16865', 'ilx:hasExpressionPhenotype')
    D1 = Phenotype('PR:000001175', 'ilx:hasExpressionPhenotype')
    DA = Phenotype('CHEBI:18243', 'ilx:hasExpressionPhenotype')
    Th = Phenotype('ilx:ThickPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    Tu = Phenotype('ilx:TuftedPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    U = NegPhenotype(Tu)
    S = Phenotype('ilx:SlenderPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    EB = Phenotype('ilx:EarlyBifurcatingPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    LB = Phenotype('ilx:LateBifurcatingPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    Sp = Phenotype('ilx:SpinyPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    ASp = NegPhenotype(Sp)
    PPA = Phenotype('ilx:PerforantPathwayAssociated', 'ilx:hasPhenotype')  # TODO FIXME
    TRI = Phenotype('ilx:TrilaminarPhenotype', 'ilx:hasMorphologicalPhenotype')
    IVY = Phenotype('ilx:IvyPhenotype', 'ilx:hasMorphologicalPhenotype')  # check syns on this?
    SCA = Phenotype('GO:1990021', 'ilx:hasProjectionPhenotype')  #'ilx:hasAssociatedTractPhenotype')  # how to model these... also schaffer collaterals are a MESS in the ontology FIXME
    STRI = Phenotype('UBERON:0005383', 'ilx:hasSomaLocatedIn')  # VS UBERON:0002435 (always comes up)
    MSN = Phenotype('ilx:MediumSpinyPhenotype', 'ilx:hasMorphologicalPhenotype')
    INT = Phenotype('ilx:InterneuronPhenotype', 'ilx:hasCircuitRolePhenotype')  # unsatisfactory
    CER = Phenotype('UBERON:0002037', 'ilx:hasSomaLocatedIn')
    GRAN = Phenotype('ilx:GranulePhenotype', 'ilx:hasMorphologicalPhenotype')  # vs granular?

