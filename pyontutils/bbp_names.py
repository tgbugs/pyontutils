#!/usr/bin/env python3

import inspect
#from pyontutils.neuron_lang import *  # namesets can only be effectively defined over a specific base...
# FIXME however it does not help with cases where we want to use someone elses definitions (local) withour own
#  translated naming scheme :/

#def pythonSucks(pred, setLocalName, setLocalNameTrip, NegPhenotype, LogicalPhenotype):

#__g = inspect.stack()[1][0].f_locals  #  get globals of calling scope
__g = globals()

# cat neuron_example.py | grep -v ^# | grep -o "\w\+\ \=\ Pheno.\+" | sed "s/^/('/" | sed "s/\ \=\ /',/" | sed 's/Phenotype(//' | sed 's/)/),/'
__bbp_names = (
    ('Rat','NCBITaxon:10116', pred.hasInstanceInSpecies),
    ('Mouse','NCBITaxon:10090', pred.hasInstanceInSpecies),
    ('S1','UBERON:0008933', pred.hasSomaLocatedIn),
    ('CA1','UBERON:0003881', pred.hasSomaLocatedIn),
    ('PC','ilx:PyramidalPhenotype', pred.hasMorphologicalPhenotype),  # 
    ('BPC','ilx:BiopolarPyramidalPhenotype', pred.hasMorphologicalPhenotype),  # collision
    ('HPC','ilx:HorizontalPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('IPC','ilx:InvertedPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('NPC','ilx:NarrowPyramidalPhenotype', pred.hasMorphologicalPhenotype),  # XXX These are apparently tufted.... so are they NarrowTufted or not? help!
    ('SPC','ilx:StarPyramidalPhenotype', pred.hasMorphologicalPhenotype),  # collision with stratum pyramidale
    ('TPC_C','ilx:NarrowTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype),  # are this different?  Yes, the Narrow modifieds the tufted... not entirely sure how that is different from when Narrow modifies Pyramidal...
    ('TPC','ilx:TuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('STPC','ilx:SlenderTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('TTPC','ilx:ThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('TTPC1','ilx:LateBifurcatingThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('TTPC2','ilx:EarlyBifurcatingThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('TPC_A','ilx:LateBifurcatingTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype), # these are inconsistent with usages like NGC_DA NGC_SA recomend the NGCDA NGCSA versions since the acronym is better than a/b 1/2
    ('TPC_B','ilx:EarlyBifurcatingTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('UTPC','ilx:UntuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype),
    ('BTC','ilx:BituftedPhenotype', pred.hasMorphologicalPhenotype),
    ('BP','ilx:BipolarPhenotype', pred.hasMorphologicalPhenotype),  # NOTE disjoint from biopolar pyramidal... also collision
    ('BS','ilx:BistratifiedPhenotype', pred.hasMorphologicalPhenotype),
    ('ChC','ilx:ChandelierPhenotype', pred.hasMorphologicalPhenotype),  # AA ??
    ('DBC','ilx:DoubleBouquetPhenotype', pred.hasMorphologicalPhenotype),
    ('DAC','ilx:DescendingAxonPhenotype', pred.hasMorphologicalPhenotype),  # FIXME how to communicate that these are a bit different than actual 'axon' phenotypes? disjoint from P?
    ('HAC','ilx:HorizontalAxonPhenotype', pred.hasMorphologicalPhenotype),
    ('LAC','ilx:LargeAxonPhenotype', pred.hasMorphologicalPhenotype),
    ('SAC','ilx:SmallAxonPhenotype', pred.hasMorphologicalPhenotype),
    ('MC','ilx:MartinottiPhenotype', pred.hasMorphologicalPhenotype),
    ('NGC','ilx:NeurogliaformPhenotype', pred.hasMorphologicalPhenotype),
    ('NGC_DA','ilx:NeurogliaformDenseAxonPhenotype', pred.hasMorphologicalPhenotype),
    ('NGC_SA','ilx:NeurogliaformSparseAxonPhenotype', pred.hasMorphologicalPhenotype),
    ('BC','ilx:BasketPhenotype', pred.hasMorphologicalPhenotype),
    ('SBC','ilx:SmallBasketPhenotype', pred.hasMorphologicalPhenotype),
    ('LBC','ilx:LargeBasketPhenotype', pred.hasMorphologicalPhenotype),
    ('NBC','ilx:NestBasketPhenotype', pred.hasMorphologicalPhenotype),
    ('SSC','ilx:SpinyStellatePhenotype', pred.hasMorphologicalPhenotype),  # SS is used on the website, SSC is used on the spreadsheet
    ('AC','ilx:PetillaSustainedAccomodatingPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('NAC','ilx:PetillaSustainedNonAccomodatingPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('STUT','ilx:PetillaSustainedStutteringPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('IR','ilx:PetillaSustainedIrregularPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('b','ilx:PetillaInitialBurstSpikingPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('c','ilx:PetillaInitialClassicalSpikingPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('d','ilx:PetillaInitialDelayedSpikingPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('FS','ilx:FastSpikingPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('RSNP','ilx:RegularSpikingNonPyramidalPhenotype', pred.hasElectrophysiologicalPhenotype),
    ('L1','UBERON:0005390', pred.hasLayerLocationPhenotype),
    ('L2','UBERON:0005391', pred.hasLayerLocationPhenotype),
    ('L3','UBERON:0005392', pred.hasLayerLocationPhenotype),
    ('L4','UBERON:0005393', pred.hasLayerLocationPhenotype),
    ('L5','UBERON:0005394', pred.hasLayerLocationPhenotype),
    ('L6','UBERON:0005395', pred.hasLayerLocationPhenotype),
    ('L1P','UBERON:0005390', pred.hasProjectionPhenotype),
    ('L4P','UBERON:0005393', pred.hasProjectionPhenotype),
    ('L1D','UBERON:0005390', pred.hasDendriteLocatedIn),
    ('L4D','UBERON:0005393', pred.hasDendriteLocatedIn),
    ('CA2','UBERON:0003882', pred.hasSomaLocatedIn),
    ('CA3','UBERON:0003883', pred.hasSomaLocatedIn),
    #('brain', 'UBERON:0000955', pred.hasLocationPhenotype),  # hasLocationPhenotype a high level
    ('brain', 'UBERON:0000955', pred.hasSomaLocatedIn),
    ('CTX', 'UBERON:0001950', pred.hasSomaLocatedIn),
    ('SO','UBERON:0005371', pred.hasLayerLocationPhenotype),  # WARNING: uberon has precomposed these, which is annoying
    ('SP','UBERON:0002313', pred.hasLayerLocationPhenotype),
    ('SLA','UBERON:0005370', pred.hasLayerLocationPhenotype),
    ('SLM','UBERON:0007640', pred.hasLayerLocationPhenotype),
    ('SLU','UBERON:0007637', pred.hasLayerLocationPhenotype),
    ('SR','UBERON:0005372', pred.hasLayerLocationPhenotype),
    ('SLMP','UBERON:0007640', pred.hasProjectionPhenotype),
    ('ThalP','UBERON:0001897', pred.hasProjectionPhenotype),
    ('CB','PR:000004967', pred.hasExpressionPhenotype),
    ('CCK','PR:000005110', pred.hasExpressionPhenotype),
    ('CR','PR:000004968', pred.hasExpressionPhenotype),
    ('NPY','PR:000011387', pred.hasExpressionPhenotype),
    ('PV','PR:000013502', pred.hasExpressionPhenotype),
    #('PV', 'PR:000013502', pred.hasExpressionPhenotype),  # yes this does cause the error
    #('PVP', 'PR:000013502', pred.hasExpressionPhenotype),  # as does this
    ('SOM','PR:000015665', pred.hasExpressionPhenotype),
    ('VIP','PR:000017299', pred.hasExpressionPhenotype),
    ('GABA','CHEBI:16865', pred.hasExpressionPhenotype),
    ('D1','PR:000001175', pred.hasExpressionPhenotype),
    ('DA','CHEBI:18243', pred.hasExpressionPhenotype),
    ('Th','ilx:ThickPhenotype', pred.hasDendriteMorphologicalPhenotype),
    ('Tu','ilx:TuftedPhenotype', pred.hasDendriteMorphologicalPhenotype),
    ('S','ilx:SlenderPhenotype', pred.hasDendriteMorphologicalPhenotype),
    ('EB','ilx:EarlyBifurcatingPhenotype', pred.hasDendriteMorphologicalPhenotype),
    ('LB','ilx:LateBifurcatingPhenotype', pred.hasDendriteMorphologicalPhenotype),
    ('Sp','ilx:SpinyPhenotype', pred.hasDendriteMorphologicalPhenotype),
    ('PPA','ilx:PerforantPathwayAssociated', pred.hasPhenotype),  # TODO FIXME
    ('TRI','ilx:TrilaminarPhenotype', pred.hasMorphologicalPhenotype),
    ('IVY','ilx:IvyPhenotype', pred.hasMorphologicalPhenotype),  # check syns on this?
    ('SCA','GO:1990021', pred.hasProjectionPhenotype),#'ilx:hasAssociatedTractPhenotype')  # how to model these... also schaffer collaterals are a MESS in the ontology FIXME
    ('STRI','UBERON:0005383', pred.hasSomaLocatedIn),  # VS UBERON:0002435 (always comes up)
    ('MSN','ilx:MediumSpinyPhenotype', pred.hasMorphologicalPhenotype),
    ('INT','ilx:InterneuronPhenotype', pred.hasCircuitRolePhenotype),  # unsatisfactory
    ('CER','UBERON:0002037', pred.hasSomaLocatedIn),
    ('GRAN','ilx:GranulePhenotype', pred.hasMorphologicalPhenotype),  # vs granular?
)
[setLocalNameTrip(*_,g=__g) for _ in __bbp_names]  # OH AND LOOK GLOBALS DOESNT WORK WHEN WE PASS IT IN
setLocalName('U', NegPhenotype(Tu), __g)  # annoying to have to wait for these... but ok
setLocalName('L23', LogicalPhenotype(OR, L2, L3), __g)  # __g is infuriating...
setLocalName('ASp', NegPhenotype(Sp), __g)

