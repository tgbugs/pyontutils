#!/usr/bin/env python3

from pyontutils.neurons import *  # namesets can only be effectively defined over a specific base...
from pyontutils.neuron_lang import config  # annoying, but works

class Test(LocalNameManager):
    addLNT('LOOK_AT_THE_CUTE_LITTLE_GUY', 'NCBITaxon:10116', 'ilx:hasInstanceInSpecies')

class Layers(LocalNameManager):
    # TODO there might be a way to set a default predicate here...
    addLNT('L1', 'UBERON:0005390', 'ilx:hasLayerLocationPhenotype')
    addLNT('L2', 'UBERON:0005391', 'ilx:hasLayerLocationPhenotype')
    addLNT('L3', 'UBERON:0005392', 'ilx:hasLayerLocationPhenotype')
    addLN('L23', LogicalPhenotype(OR, L2, L3))
    addLNT('L4', 'UBERON:0005393', 'ilx:hasLayerLocationPhenotype')
    addLNT('L5', 'UBERON:0005394', 'ilx:hasLayerLocationPhenotype')
    addLNT('L6', 'UBERON:0005395', 'ilx:hasLayerLocationPhenotype')

    addLNT('SO', 'UBERON:0005371', 'ilx:hasLayerLocationPhenotype')  # WARNING: uberon has precomposed these, which is annoying
    addLNT('SPy', 'UBERON:0002313', 'ilx:hasLayerLocationPhenotype')  # SP
    addLNT('SLA', 'UBERON:0005370', 'ilx:hasLayerLocationPhenotype')
    addLNT('SLM', 'UBERON:0007640', 'ilx:hasLayerLocationPhenotype')
    addLNT('SLU', 'UBERON:0007637', 'ilx:hasLayerLocationPhenotype')
    addLNT('SR', 'UBERON:0005372', 'ilx:hasLayerLocationPhenotype')

class Regions(LocalNameManager):
    #('brain', 'UBERON:0000955', 'ilx:hasLocationPhenotype')  # hasLocationPhenotype a high level
    addLNT('brain', 'UBERON:0000955', 'ilx:hasSomaLocatedIn')
    addLNT('CTX', 'UBERON:0001950', 'ilx:hasSomaLocatedIn')
    addLNT('CA2', 'UBERON:0003882', 'ilx:hasSomaLocatedIn')
    addLNT('CA3', 'UBERON:0003883', 'ilx:hasSomaLocatedIn')
    addLNT('S1', 'UBERON:0008933', 'ilx:hasSomaLocatedIn')
    addLNT('CA1', 'UBERON:0003881', 'ilx:hasSomaLocatedIn')

class Species(LocalNameManager):
    addLNT('Rat', 'NCBITaxon:10116', 'ilx:hasInstanceInSpecies')
    addLNT('Mouse', 'NCBITaxon:10090', 'ilx:hasInstanceInSpecies')

class BBP(Layers, Regions, Species):
    # cat old_neuron_example.py | grep -v ^# | grep -o "\w\+\ \=\ Pheno.\+" | sed "s/^/('/" | sed "s/\ \=\ /',/" | sed 's/Phenotype(//' | sed 's/)/)/'
    addLNT('PC', 'ilx:PyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # 
    addLNT('BPC', 'ilx:BiopolarPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # collision
    addLNT('HPC', 'ilx:HorizontalPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('IPC', 'ilx:InvertedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('NPC', 'ilx:NarrowPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # XXX These are apparently tufted.... so are they NarrowTufted or not? help!
    addLNT('SPC', 'ilx:StarPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # collision with stratum pyramidale
    addLNT('TPC_C', 'ilx:NarrowTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')  # are this different?  Yes, the Narrow modifieds the tufted... not entirely sure how that is different from when Narrow modifies Pyramidal...
    addLNT('TPC', 'ilx:TuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('STPC', 'ilx:SlenderTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('TTPC', 'ilx:ThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('TTPC1', 'ilx:LateBifurcatingThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('TTPC2', 'ilx:EarlyBifurcatingThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('TPC_A', 'ilx:LateBifurcatingTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype') # these are inconsistent with usages like NGC_DA NGC_SA recomend the NGCDA NGCSA versions since the acronym is better than a/b 1/2
    addLNT('TPC_B', 'ilx:EarlyBifurcatingTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('UTPC', 'ilx:UntuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('BTC', 'ilx:BituftedPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('BP', 'ilx:BipolarPhenotype', 'ilx:hasMorphologicalPhenotype')  # NOTE disjoint from biopolar pyramidal... also collision
    addLNT('BS', 'ilx:BistratifiedPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('ChC', 'ilx:ChandelierPhenotype', 'ilx:hasMorphologicalPhenotype')  # AA ??
    addLNT('DBC', 'ilx:DoubleBouquetPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('DAC', 'ilx:DescendingAxonPhenotype', 'ilx:hasMorphologicalPhenotype')  # FIXME how to communicate that these are a bit different than actual 'axon' phenotypes? disjoint from P?
    addLNT('HAC', 'ilx:HorizontalAxonPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('LAC', 'ilx:LargeAxonPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('SAC', 'ilx:SmallAxonPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('MC', 'ilx:MartinottiPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('NGC', 'ilx:NeurogliaformPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('NGCDA', 'ilx:NeurogliaformDenseAxonPhenotype', 'ilx:hasMorphologicalPhenotype')  # NGC_DA
    addLNT('NGCSA', 'ilx:NeurogliaformSparseAxonPhenotype', 'ilx:hasMorphologicalPhenotype')  # NGC_SA
    addLNT('BC', 'ilx:BasketPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('SBC', 'ilx:SmallBasketPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('LBC', 'ilx:LargeBasketPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('NBC', 'ilx:NestBasketPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('SS', 'ilx:SpinyStellatePhenotype', 'ilx:hasMorphologicalPhenotype')  # SS is used on the website, SSC is used on the spreadsheet TODO usecase for non-injective naming...
    addLNT('AC', 'ilx:PetillaSustainedAccomodatingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('NAC', 'ilx:PetillaSustainedNonAccomodatingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('STUT', 'ilx:PetillaSustainedStutteringPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('IR', 'ilx:PetillaSustainedIrregularPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('b', 'ilx:PetillaInitialBurstSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('c', 'ilx:PetillaInitialClassicalSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('d', 'ilx:PetillaInitialDelayedSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('FS', 'ilx:FastSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('RSNP', 'ilx:RegularSpikingNonPyramidalPhenotype', 'ilx:hasElectrophysiologicalPhenotype')
    addLNT('L1D', 'UBERON:0005390', 'ilx:hasDendriteLocatedIn')
    addLNT('L4D', 'UBERON:0005393', 'ilx:hasDendriteLocatedIn')
    addLNT('L1P', 'UBERON:0005390', 'ilx:hasProjectionPhenotype')
    addLNT('L4P', 'UBERON:0005393', 'ilx:hasProjectionPhenotype')
    addLNT('SLMP', 'UBERON:0007640', 'ilx:hasProjectionPhenotype')
    addLNT('ThalP', 'UBERON:0001897', 'ilx:hasProjectionPhenotype')
    addLNT('CB', 'PR:000004967', 'ilx:hasExpressionPhenotype')
    addLNT('CCK', 'PR:000005110', 'ilx:hasExpressionPhenotype')
    addLNT('CR', 'PR:000004968', 'ilx:hasExpressionPhenotype')
    addLNT('NPY', 'PR:000011387', 'ilx:hasExpressionPhenotype')
    addLNT('PV', 'PR:000013502', 'ilx:hasExpressionPhenotype')
    #('PV', 'PR:000013502', 'ilx:hasExpressionPhenotype')  # yes this does cause the error
    #('PVP', 'PR:000013502', 'ilx:hasExpressionPhenotype')  # as does this
    addLNT('SOM', 'PR:000015665', 'ilx:hasExpressionPhenotype')
    addLNT('VIP', 'PR:000017299', 'ilx:hasExpressionPhenotype')
    addLNT('GABA', 'CHEBI:16865', 'ilx:hasExpressionPhenotype')
    addLNT('D1', 'PR:000001175', 'ilx:hasExpressionPhenotype')
    addLNT('DA', 'CHEBI:18243', 'ilx:hasExpressionPhenotype')
    addLNT('Th', 'ilx:ThickPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    addLNT('Tu', 'ilx:TuftedPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    addLN('U', NegPhenotype(Tu))
    addLNT('S', 'ilx:SlenderPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    addLNT('EB', 'ilx:EarlyBifurcatingPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    addLNT('LB', 'ilx:LateBifurcatingPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    addLNT('Sp', 'ilx:SpinyPhenotype', 'ilx:hasDendriteMorphologicalPhenotype')
    addLN('ASp', NegPhenotype(Sp))
    addLNT('PPA', 'ilx:PerforantPathwayAssociated', 'ilx:hasPhenotype')  # TODO FIXME
    addLNT('TRI', 'ilx:TrilaminarPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('IVY', 'ilx:IvyPhenotype', 'ilx:hasMorphologicalPhenotype')  # check syns on this?
    addLNT('SCA', 'GO:1990021', 'ilx:hasProjectionPhenotype')  #'ilx:hasAssociatedTractPhenotype')  # how to model these... also schaffer collaterals are a MESS in the ontology FIXME
    addLNT('STRI', 'UBERON:0005383', 'ilx:hasSomaLocatedIn')  # VS UBERON:0002435 (always comes up)
    addLNT('MSN', 'ilx:MediumSpinyPhenotype', 'ilx:hasMorphologicalPhenotype')
    addLNT('INT', 'ilx:InterneuronPhenotype', 'ilx:hasCircuitRolePhenotype')  # unsatisfactory
    addLNT('CER', 'UBERON:0002037', 'ilx:hasSomaLocatedIn')
    addLNT('GRAN', 'ilx:GranulePhenotype', 'ilx:hasMorphologicalPhenotype')  # vs granular?

