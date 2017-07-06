#!/usr/bin/env python3

import inspect
from IPython import embed
from rdflib import Graph
from pyontutils.utils import makeGraph
from pyontutils.neurons import *  # namesets can only be effectively defined over a specific base...
from neuron_lang import config
#from pyontutils.neuron_lang import *  # namesets can only be effectively defined over a specific base...
# FIXME however it does not help with cases where we want to use someone elses definitions (local) withour own
#  translated naming scheme :/

#def pythonSucks(pred, setLocalName, setLocalNameTrip, NegPhenotype, LogicalPhenotype):

#__g = inspect.stack()[1][0].f_locals  #  get globals of calling scope
__g = globals()

# argh, the way that this works right now everything needs to be initialized and called immeditealy
#graphBase.core_graph = Graph()
#graphBase._predicates = type('PhenoPreds', (object,), {})
#ng = makeGraph('', graph=graphBase.core_graph)
#[ng.add_known_namespace(_) for _ in ('ilx','UBERON','GO')]
#pred = LocalNameManager.pred
config()  # ANNOYING
class BBPNames(LocalNameManager):
    # cat neuron_example.py | grep -v ^# | grep -o "\w\+\ \=\ Pheno.\+" | sed "s/^/('/" | sed "s/\ \=\ /',/" | sed 's/Phenotype(//' | sed 's/)/),/'
    ('Rat','NCBITaxon:10116', 'ilx:hasInstanceInSpecies'),
    ('Mouse','NCBITaxon:10090', 'ilx:hasInstanceInSpecies'),
    ('S1','UBERON:0008933', 'ilx:hasSomaLocatedIn'),
    ('CA1','UBERON:0003881', 'ilx:hasSomaLocatedIn'),
    ('PC','ilx:PyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),  # 
    ('BPC','ilx:BiopolarPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),  # collision
    ('HPC','ilx:HorizontalPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('IPC','ilx:InvertedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('NPC','ilx:NarrowPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),  # XXX These are apparently tufted.... so are they NarrowTufted or not? help!
    ('SPC','ilx:StarPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),  # collision with stratum pyramidale
    ('TPC_C','ilx:NarrowTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),  # are this different?  Yes, the Narrow modifieds the tufted... not entirely sure how that is different from when Narrow modifies Pyramidal...
    ('TPC','ilx:TuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('STPC','ilx:SlenderTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('TTPC','ilx:ThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('TTPC1','ilx:LateBifurcatingThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('TTPC2','ilx:EarlyBifurcatingThickTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('TPC_A','ilx:LateBifurcatingTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'), # these are inconsistent with usages like NGC_DA NGC_SA recomend the NGCDA NGCSA versions since the acronym is better than a/b 1/2
    ('TPC_B','ilx:EarlyBifurcatingTuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('UTPC','ilx:UntuftedPyramidalPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('BTC','ilx:BituftedPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('BP','ilx:BipolarPhenotype', 'ilx:hasMorphologicalPhenotype'),  # NOTE disjoint from biopolar pyramidal... also collision
    ('BS','ilx:BistratifiedPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('ChC','ilx:ChandelierPhenotype', 'ilx:hasMorphologicalPhenotype'),  # AA ??
    ('DBC','ilx:DoubleBouquetPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('DAC','ilx:DescendingAxonPhenotype', 'ilx:hasMorphologicalPhenotype'),  # FIXME how to communicate that these are a bit different than actual 'axon' phenotypes? disjoint from P?
    ('HAC','ilx:HorizontalAxonPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('LAC','ilx:LargeAxonPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('SAC','ilx:SmallAxonPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('MC','ilx:MartinottiPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('NGC','ilx:NeurogliaformPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('NGC_DA','ilx:NeurogliaformDenseAxonPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('NGC_SA','ilx:NeurogliaformSparseAxonPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('BC','ilx:BasketPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('SBC','ilx:SmallBasketPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('LBC','ilx:LargeBasketPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('NBC','ilx:NestBasketPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('SSC','ilx:SpinyStellatePhenotype', 'ilx:hasMorphologicalPhenotype'),  # SS is used on the website, SSC is used on the spreadsheet
    ('AC','ilx:PetillaSustainedAccomodatingPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('NAC','ilx:PetillaSustainedNonAccomodatingPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('STUT','ilx:PetillaSustainedStutteringPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('IR','ilx:PetillaSustainedIrregularPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('b','ilx:PetillaInitialBurstSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('c','ilx:PetillaInitialClassicalSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('d','ilx:PetillaInitialDelayedSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('FS','ilx:FastSpikingPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('RSNP','ilx:RegularSpikingNonPyramidalPhenotype', 'ilx:hasElectrophysiologicalPhenotype'),
    ('L1','UBERON:0005390', 'ilx:hasLayerLocationPhenotype'),
    setLocalNameTrip('L2','UBERON:0005391', 'ilx:hasLayerLocationPhenotype'),
    setLocalNameTrip('L3','UBERON:0005392', 'ilx:hasLayerLocationPhenotype'),
    ('L23', LogicalPhenotype(OR, L2, L3)),
    ('L4','UBERON:0005393', 'ilx:hasLayerLocationPhenotype'),
    ('L5','UBERON:0005394', 'ilx:hasLayerLocationPhenotype'),
    ('L6','UBERON:0005395', 'ilx:hasLayerLocationPhenotype'),
    ('L1P','UBERON:0005390', 'ilx:hasProjectionPhenotype'),
    ('L4P','UBERON:0005393', 'ilx:hasProjectionPhenotype'),
    ('L1D','UBERON:0005390', 'ilx:hasDendriteLocatedIn'),
    ('L4D','UBERON:0005393', 'ilx:hasDendriteLocatedIn'),
    ('CA2','UBERON:0003882', 'ilx:hasSomaLocatedIn'),
    ('CA3','UBERON:0003883', 'ilx:hasSomaLocatedIn'),
    #('brain', 'UBERON:0000955', 'ilx:hasLocationPhenotype'),  # hasLocationPhenotype a high level
    ('brain', 'UBERON:0000955', 'ilx:hasSomaLocatedIn'),
    ('CTX', 'UBERON:0001950', 'ilx:hasSomaLocatedIn'),
    ('SO','UBERON:0005371', 'ilx:hasLayerLocationPhenotype'),  # WARNING: uberon has precomposed these, which is annoying
    ('SP','UBERON:0002313', 'ilx:hasLayerLocationPhenotype'),
    ('SLA','UBERON:0005370', 'ilx:hasLayerLocationPhenotype'),
    ('SLM','UBERON:0007640', 'ilx:hasLayerLocationPhenotype'),
    ('SLU','UBERON:0007637', 'ilx:hasLayerLocationPhenotype'),
    ('SR','UBERON:0005372', 'ilx:hasLayerLocationPhenotype'),
    ('SLMP','UBERON:0007640', 'ilx:hasProjectionPhenotype'),
    ('ThalP','UBERON:0001897', 'ilx:hasProjectionPhenotype'),
    ('CB','PR:000004967', 'ilx:hasExpressionPhenotype'),
    ('CCK','PR:000005110', 'ilx:hasExpressionPhenotype'),
    ('CR','PR:000004968', 'ilx:hasExpressionPhenotype'),
    ('NPY','PR:000011387', 'ilx:hasExpressionPhenotype'),
    ('PV','PR:000013502', 'ilx:hasExpressionPhenotype'),
    #('PV', 'PR:000013502', 'ilx:hasExpressionPhenotype'),  # yes this does cause the error
    #('PVP', 'PR:000013502', 'ilx:hasExpressionPhenotype'),  # as does this
    ('SOM','PR:000015665', 'ilx:hasExpressionPhenotype'),
    ('VIP','PR:000017299', 'ilx:hasExpressionPhenotype'),
    ('GABA','CHEBI:16865', 'ilx:hasExpressionPhenotype'),
    ('D1','PR:000001175', 'ilx:hasExpressionPhenotype'),
    ('DA','CHEBI:18243', 'ilx:hasExpressionPhenotype'),
    ('Th','ilx:ThickPhenotype', 'ilx:hasDendriteMorphologicalPhenotype'),
    setLocalNameTrip('Tu','ilx:TuftedPhenotype', 'ilx:hasDendriteMorphologicalPhenotype'),
    ('U', NegPhenotype(Tu)),
    ('S','ilx:SlenderPhenotype', 'ilx:hasDendriteMorphologicalPhenotype'),
    ('EB','ilx:EarlyBifurcatingPhenotype', 'ilx:hasDendriteMorphologicalPhenotype'),
    ('LB','ilx:LateBifurcatingPhenotype', 'ilx:hasDendriteMorphologicalPhenotype'),
    setLocalNameTrip('Sp','ilx:SpinyPhenotype', 'ilx:hasDendriteMorphologicalPhenotype'),
    ('ASp', NegPhenotype(Sp)),
    ('PPA','ilx:PerforantPathwayAssociated', 'ilx:hasPhenotype'),  # TODO FIXME
    ('TRI','ilx:TrilaminarPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('IVY','ilx:IvyPhenotype', 'ilx:hasMorphologicalPhenotype'),  # check syns on this?
    ('SCA','GO:1990021', 'ilx:hasProjectionPhenotype'),#'ilx:hasAssociatedTractPhenotype')  # how to model these... also schaffer collaterals are a MESS in the ontology FIXME
    ('STRI','UBERON:0005383', 'ilx:hasSomaLocatedIn'),  # VS UBERON:0002435 (always comes up)
    ('MSN','ilx:MediumSpinyPhenotype', 'ilx:hasMorphologicalPhenotype'),
    ('INT','ilx:InterneuronPhenotype', 'ilx:hasCircuitRolePhenotype'),  # unsatisfactory
    ('CER','UBERON:0002037', 'ilx:hasSomaLocatedIn'),
    ('GRAN','ilx:GranulePhenotype', 'ilx:hasMorphologicalPhenotype'),  # vs granular?

    def post(self):
        [self.setLocalNameTrip(*_,g=__g) for _ in names if _]  # OH AND LOOK GLOBALS DOESNT WORK WHEN WE PASS IT IN
        self.setLocalName('U', NegPhenotype(Tu), __g)  # annoying to have to wait for these... but ok
        self.setLocalName('L23', LogicalPhenotype(OR, L2, L3), __g)  # __g is infuriating...
        self.setLocalName('ASp', NegPhenotype(Sp), __g)

print(inspect.getsource(BBPNames).replace(' (\'',' setLocalNameTrip(\''))
embed()
