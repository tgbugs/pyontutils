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
    g = inspect.stack()[0][0].f_locals
    addLNT('LOOK_AT_THE_CUTE_LITTLE_GUY', 'NCBITaxon:10116', 'ilx:hasInstanceInSpecies', g)

class Layers(LocalNameManager):
    g = inspect.stack()[0][0].f_locals
    # TODO there might be a way to set a default predicate here...
    addLNT('L1', 'UBERON:0005390', 'ilx:hasLayerLocationPhenotype', g)
    addLNT('L2', 'UBERON:0005391', 'ilx:hasLayerLocationPhenotype', g)
    addLNT('L3', 'UBERON:0005392', 'ilx:hasLayerLocationPhenotype', g)
    addLN('L23', LogicalPhenotype(OR, L2, L3), g)
    addLNT('L4', 'UBERON:0005393', 'ilx:hasLayerLocationPhenotype', g)
    addLNT('L5', 'UBERON:0005394', 'ilx:hasLayerLocationPhenotype', g)
    addLNT('L6', 'UBERON:0005395', 'ilx:hasLayerLocationPhenotype', g)

    addLNT('SO', 'UBERON:0005371', 'ilx:hasLayerLocationPhenotype', g)  # WARNING: uberon has precomposed these, which is annoying
    addLNT('SPy', 'UBERON:0002313', 'ilx:hasLayerLocationPhenotype', g)  # SP
    addLNT('SLA', 'UBERON:0005370', 'ilx:hasLayerLocationPhenotype', g)
    addLNT('SLM', 'UBERON:0007640', 'ilx:hasLayerLocationPhenotype', g)
    addLNT('SLU', 'UBERON:0007637', 'ilx:hasLayerLocationPhenotype', g)
    addLNT('SR', 'UBERON:0005372', 'ilx:hasLayerLocationPhenotype', g)

class Regions(LocalNameManager):
    g = inspect.stack()[0][0].f_locals
    #('brain', 'UBERON:0000955', 'ilx:hasLocationPhenotype', g)  # hasLocationPhenotype a high level
    addLNT('brain', 'UBERON:0000955', 'ilx:hasSomaLocatedIn', g)
    addLNT('CTX', 'UBERON:0001950', 'ilx:hasSomaLocatedIn', g)
    addLNT('CA2', 'UBERON:0003882', 'ilx:hasSomaLocatedIn', g)
    addLNT('CA3', 'UBERON:0003883', 'ilx:hasSomaLocatedIn', g)
    addLNT('S1', 'UBERON:0008933', 'ilx:hasSomaLocatedIn', g)
    addLNT('CA1', 'UBERON:0003881', 'ilx:hasSomaLocatedIn', g)

class Species(LocalNameManager):
    g = inspect.stack()[0][0].f_locals
    addLNT('Rat', 'NCBITaxon:10116', 'ilx:hasInstanceInSpecies', g)
    addLNT('Mouse', 'NCBITaxon:10090', 'ilx:hasInstanceInSpecies', g)

class BBP(Layers, Regions, Species):
    g = inspect.stack()[0][0].f_locals
    # cat old_neuron_example.py | grep -v ^# | grep -o "\w\+\ \=\ Pheno.\+" | sed "s/^/('/" | sed "s/\ \=\ /',/" | sed 's/Phenotype(//' | sed 's/)/)/'
    addLNT('PC', 'ilx:PyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # 
    addLNT('BPC', 'ilx:BiopolarPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # collision
    addLNT('HPC', 'ilx:HorizontalPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('IPC', 'ilx:InvertedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('NPC', 'ilx:NarrowPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # XXX These are apparently tufted.... so are they NarrowTufted or not? help!
    addLNT('SPC', 'ilx:StarPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # collision with stratum pyramidale
    addLNT('TPC_C', 'ilx:NarrowTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # are this different?  Yes, the Narrow modifieds the tufted... not entirely sure how that is different from when Narrow modifies Pyramidal...
    addLNT('TPC', 'ilx:TuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('STPC', 'ilx:SlenderTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('TTPC', 'ilx:ThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('TTPC1', 'ilx:LateBifurcatingThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('TTPC2', 'ilx:EarlyBifurcatingThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('TPC_A', 'ilx:LateBifurcatingTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g) # these are inconsistent with usages like NGC_DA NGC_SA recomend the NGCDA NGCSA versions since the acronym is better than a/b 1/2
    addLNT('TPC_B', 'ilx:EarlyBifurcatingTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('UTPC', 'ilx:UntuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('BTC', 'ilx:BituftedPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('BP', 'ilx:BipolarPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # NOTE disjoint from biopolar pyramidal... also collision
    addLNT('BS', 'ilx:BistratifiedPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('ChC', 'ilx:ChandelierPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # AA ??
    addLNT('DBC', 'ilx:DoubleBouquetPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('DAC', 'ilx:DescendingAxonPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # FIXME how to communicate that these are a bit different than actual 'axon' phenotypes? disjoint from P?
    addLNT('HAC', 'ilx:HorizontalAxonPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('LAC', 'ilx:LargeAxonPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('SAC', 'ilx:SmallAxonPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('MC', 'ilx:MartinottiPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('NGC', 'ilx:NeurogliaformPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('NGCDA', 'ilx:NeurogliaformDenseAxonPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # NGC_DA
    addLNT('NGCSA', 'ilx:NeurogliaformSparseAxonPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # NGC_SA
    addLNT('BC', 'ilx:BasketPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('SBC', 'ilx:SmallBasketPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('LBC', 'ilx:LargeBasketPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('NBC', 'ilx:NestBasketPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('SS', 'ilx:SpinyStellatePhenotype', 'ilx:hasMorphologicalPhenotype', g)  # SS is used on the website, SSC is used on the spreadsheet TODO usecase for non-injective naming...
    addLNT('AC', 'ilx:PetillaSustainedAccomodatingPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('NAC', 'ilx:PetillaSustainedNonAccomodatingPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('STUT', 'ilx:PetillaSustainedStutteringPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('IR', 'ilx:PetillaSustainedIrregularPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('b', 'ilx:PetillaInitialBurstSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('c', 'ilx:PetillaInitialClassicalSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('d', 'ilx:PetillaInitialDelayedSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('FS', 'ilx:FastSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('RSNP', 'ilx:RegularSpikingNonPyramidalPhenotype', 'ilx:hasElectrophysiologicalPhenotype', g)
    addLNT('L1D', 'UBERON:0005390', 'ilx:hasDendriteLocatedIn', g)
    addLNT('L4D', 'UBERON:0005393', 'ilx:hasDendriteLocatedIn', g)
    addLNT('L1P', 'UBERON:0005390', 'ilx:hasProjectionPhenotype', g)
    addLNT('L4P', 'UBERON:0005393', 'ilx:hasProjectionPhenotype', g)
    addLNT('SLMP', 'UBERON:0007640', 'ilx:hasProjectionPhenotype', g)
    addLNT('ThalP', 'UBERON:0001897', 'ilx:hasProjectionPhenotype', g)
    addLNT('CB', 'PR:000004967', 'ilx:hasExpressionPhenotype', g)
    addLNT('CCK', 'PR:000005110', 'ilx:hasExpressionPhenotype', g)
    addLNT('CR', 'PR:000004968', 'ilx:hasExpressionPhenotype', g)
    addLNT('NPY', 'PR:000011387', 'ilx:hasExpressionPhenotype', g)
    addLNT('PV', 'PR:000013502', 'ilx:hasExpressionPhenotype', g)
    #addLNT('PV', 'PR:000013502', 'ilx:hasExpressionPhenotype', g)  # this is ok since injection is preserved
    #addLNT('PVP', 'PR:000013502', 'ilx:hasExpressionPhenotype', g)  # this errors correctly
    addLNT('SOM', 'PR:000015665', 'ilx:hasExpressionPhenotype', g)
    addLNT('VIP', 'PR:000017299', 'ilx:hasExpressionPhenotype', g)
    addLNT('GABA', 'CHEBI:16865', 'ilx:hasExpressionPhenotype', g)
    addLNT('D1', 'PR:000001175', 'ilx:hasExpressionPhenotype', g)
    addLNT('DA', 'CHEBI:18243', 'ilx:hasExpressionPhenotype', g)
    addLNT('Th', 'ilx:ThickPhenotype', 'ilx:hasDendriteMorphologicalPhenotype', g)
    addLNT('Tu', 'ilx:TuftedPhenotype', 'ilx:hasDendriteMorphologicalPhenotype', g)
    addLN('U', NegPhenotype(Tu), g)
    addLNT('S', 'ilx:SlenderPhenotype', 'ilx:hasDendriteMorphologicalPhenotype', g)
    addLNT('EB', 'ilx:EarlyBifurcatingPhenotype', 'ilx:hasDendriteMorphologicalPhenotype', g)
    addLNT('LB', 'ilx:LateBifurcatingPhenotype', 'ilx:hasDendriteMorphologicalPhenotype', g)
    addLNT('Sp', 'ilx:SpinyPhenotype', 'ilx:hasDendriteMorphologicalPhenotype', g)
    addLN('ASp', NegPhenotype(Sp), g)
    addLNT('PPA', 'ilx:PerforantPathwayAssociated', 'ilx:hasPhenotype', g)  # TODO FIXME
    addLNT('TRI', 'ilx:TrilaminarPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('IVY', 'ilx:IvyPhenotype', 'ilx:hasMorphologicalPhenotype', g)  # check syns on this?
    addLNT('SCA', 'GO:1990021', 'ilx:hasProjectionPhenotype', g)  #'ilx:hasAssociatedTractPhenotype')  # how to model these... also schaffer collaterals are a MESS in the ontology FIXME
    addLNT('STRI', 'UBERON:0005383', 'ilx:hasSomaLocatedIn', g)  # VS UBERON:0002435 (always comes up)
    addLNT('MSN', 'ilx:MediumSpinyPhenotype', 'ilx:hasMorphologicalPhenotype', g)
    addLNT('INT', 'ilx:InterneuronPhenotype', 'ilx:hasCircuitRolePhenotype', g)  # unsatisfactory
    addLNT('CER', 'UBERON:0002037', 'ilx:hasSomaLocatedIn', g)
    addLNT('GRAN', 'ilx:GranulePhenotype', 'ilx:hasMorphologicalPhenotype', g)  # vs granular?

