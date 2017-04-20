#!/usr/bin/env python3
from pyontutils.neuron_lang import *
from IPython import embed

context = (
    Phenotype('NCBITaxon:10116', 'ilx:hasInstanceInSpecies', label='Rattus norvegicus'),
    Phenotype('UBERON:0008933', 'ilx:hasSomaLocatedIn', label='primary somatosensory cortex')
)

#'(Rat S1 L4 P bIR) '(LB Th Tu)
P = P = PC = Phenotype('ilx:PyramidalPhenotype', pred.hasMorphologicalPhenotype)  # 
PB = BP = BPC = Phenotype('ilx:BiopolarPyramidalPhenotype', pred.hasMorphologicalPhenotype)  # collision
PI = IP = IPC = Phenotype('ilx:InvertedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PN = NP = NPC = Phenotype('ilx:NarrowPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PS = SP = SPC = Phenotype('ilx:StarPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTN = NTP = NTPC = TPC_C = Phenotype('ilx:NarrowTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)  # are this different?
PT = TP = TPC = Phenotype('ilx:TuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTS = STP = STPC = Phenotype('ilx:SlenderTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTT = TTP = TTPC = Phenotype('ilx:ThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTTLB = TTPLB = TTPCLB = TTPC1 = Phenotype('ilx:LateBifurcatingThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTTEB = TTPEB = TTPCEB = TTPC2 = Phenotype('ilx:EarlyBifurcatingThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTLB = TPLB = TPCLB = TPC_A = Phenotype('ilx:LateBifurcatingTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype) # these are inconsistent with usages like NGC_DA NGC_SA recomend the NGCDA NGCSA versions since the acronym is better than a/b 1/2
PTEB = TPEB = TPCEB = TPC_B = Phenotype('ilx:EarlyBifurcatingTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PU = UP = UPC = Phenotype('ilx:UntuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)

BT = BTC = Phenotype('ilx:BituftedPhenotype', pred.hasMorphologicalPhenotype)
B = BP = Phenotype('ilx:BipolarPhenotype', pred.hasMorphologicalPhenotype)  # NOTE disjoint from biopolar pyramidal... also collision
Ch = ChC = Phenotype('ilx:ChandalierPhenotype', pred.hasMorphologicalPhenotype)
DB = DBC = Phenotype('ilx:DoubleBoquetPhenotype', pred.hasMorphologicalPhenotype)
DA = DAC = Phenotype('ilx:DescendingAxonPhenotype', pred.hasMorphologicalPhenotype)  # FIXME how to communicate that these are a bit different than actual 'axon' phenotypes? disjoint from P?
HA = HAC = Phenotype('ilx:HorizontalAxonPhenotype', pred.hasMorphologicalPhenotype)
LA = LAC = Phenotype('ilx:LargeAxonPhenotype', pred.hasMorphologicalPhenotype)
SA = SAC = Phenotype('ilx:SmallAxonPhenotype', pred.hasMorphologicalPhenotype)
M = MC = Phenotype('ilx:MartinottiPhenotype', pred.hasMorphologicalPhenotype)
NG = NGC = Phenotype('ilx:NeurogliaformPhenotype', pred.hasMorphologicalPhenotype)
NGDA = NGCDA = NGC_DA = Phenotype('ilx:NeurogliaformDenseAxonPhenotype', pred.hasMorphologicalPhenotype)
NGSA = NGCSA = NGC_SA = Phenotype('ilx:NeurogliaformSparseAxonPhenotype', pred.hasMorphologicalPhenotype)
B = BC = Phenotype('ilx:BasketPhenotype', pred.hasMorphologicalPhenotype)
SB = SBC = Phenotype('ilx:SmallBasketPhenotype', pred.hasMorphologicalPhenotype)
LB = LBC = Phenotype('ilx:LargeBasketPhenotype', pred.hasMorphologicalPhenotype)
NB = NBC = Phenotype('ilx:NestBasketPhenotype', pred.hasMorphologicalPhenotype)
SS = SSC = Phenotype('ilx:SpinyStellatePhenotype', pred.hasMorphologicalPhenotype)  # SS is used on the website, SSC is used on the spreadsheet

AC = Phenotype('ilx:PetillaSustainedAccomodatingPhenotype', pred.hasElectrophysiologicalPhenotype)
NAC = Phenotype('ilx:PetillaSustainedNonAccomodatingPhenotype', pred.hasElectrophysiologicalPhenotype)
STUT = Phenotype('ilx:PetillaSustainedStutteringPhenotype', pred.hasElectrophysiologicalPhenotype)
IR = Phenotype('ilx:PetillaSustainedIrregularPhenotype', pred.hasElectrophysiologicalPhenotype)
b = Phenotype('ilx:PetillaInitialBurstSpikingPhenotype', pred.hasElectrophysiologicalPhenotype)
c = Phenotype('ilx:PetillaInitialClassicalSpikingPhenotype', pred.hasElectrophysiologicalPhenotype)
d = Phenotype('ilx:PetillaInitialDelayedSpikingPhenotype', pred.hasElectrophysiologicalPhenotype)

L1 = Phenotype('UBERON:0005390', pred.hasSomaLocatedIn)
L2 = Phenotype('UBERON:0005391', pred.hasSomaLocatedIn)
L3 = Phenotype('UBERON:0005392', pred.hasSomaLocatedIn)
L23 = LogicalPhenotype(OR, L2, L3)  # if you try to do this inside a dict definition it will fail :/
L4 = Phenotype('UBERON:0005393', pred.hasSomaLocatedIn)
L5 = Phenotype('UBERON:0005394', pred.hasSomaLocatedIn)
L6 = Phenotype('UBERON:0005395', pred.hasSomaLocatedIn)

L1P = Phenotype('UBERON:0005390', pred.hasProjectionPhenotype)
L4P = Phenotype('UBERON:0005393', pred.hasProjectionPhenotype)

CA1 = Phenotype('UBERON:0003881', pred.hasSomaLocatedIn)
CA2 = Phenotype('UBERON:0003882', pred.hasSomaLocatedIn)
CA3 = Phenotype('UBERON:0003883', pred.hasSomaLocatedIn)

SO = Phenotype('UBERON:0005371', pred.hasLayerLocationPhenotype)  # WARNING: uberon has precomposed these, which is annoying
SPy = Phenotype('UBERON:0002313', pred.hasLayerLocationPhenotype)
SLA = Phenotype('UBERON:0005370', pred.hasLayerLocationPhenotype)
SLM = Phenotype('UBERON:0007640', pred.hasLayerLocationPhenotype)
SLU = Phenotype('UBERON:0007637', pred.hasLayerLocationPhenotype)
SR = Phenotype('UBERON:0005372', pred.hasLayerLocationPhenotype)

def NeuronC(*args, **kwargs):
    return Neuron(*args, *context, **kwargs)

contn = Neuron(*context)

# TODO switch over to rat parcellation concepts
neurons = {
    'HBP_CELL:0000018': NeuronC(PC),
    'HBP_CELL:0000024': NeuronC(UPC),  # untufted... dendrite phenotype?? or what
    'HBP_CELL:0000025': NeuronC(SS),
    'HBP_CELL:0000027': NeuronC(SPC),
    'HBP_CELL:0000028': NeuronC(L23, PC),
    'HBP_CELL:0000030': NeuronC(Phenotype('ilx:HorizontalPyramidalPhenotype', pred.hasMorphologicalPhenotype)),  # are phenotypes like this modifiers on _pyramidal_ or are they on the _cell_
    'HBP_CELL:0000031': NeuronC(BPC),  # AAAAAA
    #}
    #"""
    'HBP_CELL:0000032': NeuronC(NPC, Phenotype('UBERON:0001897', pred.hasProjectionPhenotype)),
    'HBP_CELL:0000035': NeuronC(TPC, L4P),
    'HBP_CELL:0000036': NeuronC(TPC, L1P),
    'HBP_CELL:0000038': NeuronC(STPC),
    'HBP_CELL:0000039': Neuron(*contn.pes, TTPCEB),  # can we identify early/late in other cells?
    #'HBP_CELL:0000039': NeuronC(TTPCEB),  # can we identify early/late in other cells?
    'HBP_CELL:0000040': NeuronC(),
    'HBP_CELL:0000042': NeuronC(),
    'HBP_CELL:0000051': NeuronC(),
    'HBP_CELL:0000053': NeuronC(),
    'HBP_CELL:0000054': NeuronC(),
    'HBP_CELL:0000055': NeuronC(),
    'HBP_CELL:0000056': NeuronC(),
    'HBP_CELL:0000057': NeuronC(),
    'HBP_CELL:0000058': NeuronC(),
    'HBP_CELL:0000059': NeuronC(),
    'HBP_CELL:0000060': NeuronC(),
    'HBP_CELL:0000062': NeuronC(),
    'HBP_CELL:0000063': NeuronC(),
    'HBP_CELL:0000064': NeuronC(),
    'HBP_CELL:0000066': NeuronC(),
    'HBP_CELL:0000068': NeuronC(),
    'HBP_CELL:0000069': NeuronC(),
    'HBP_CELL:0000099': NeuronC(L5, BP),
    'HBP_CELL:0000101': NeuronC(L23, BTC),
    'HBP_CELL:0000102': NeuronC(L4, BTC),
    'HBP_CELL:0000105': NeuronC(L23, ChC),
    'HBP_CELL:0000109': NeuronC(L23, DBC),
    'HBP_CELL:0000110': NeuronC(),
    'HBP_CELL:0000117': NeuronC(),
    'HBP_CELL:0000118': NeuronC(),
    'HBP_CELL:0000121': NeuronC(),
    'HBP_CELL:0000122': NeuronC(),
    'HBP_CELL:0000125': NeuronC(),
    'HBP_CELL:0000126': NeuronC(),
    'HBP_CELL:0000127': NeuronC(),
    'HBP_CELL:0000130': NeuronC(),
    'HBP_CELL:0000145': NeuronC(),
    'HBP_CELL:0000151': NeuronC(),
}
#"""

#s = set()
#for i in graphBase.existing_ids:
    #print(i)
    #n = Neuron(id_=i)
    #print(n)
    #for a in n.pes:
        #s.add(a)
#s = sorted(s)

#s = list(set([a for i in graphBase.existing_ids for a in Neuron(id_=i).pes]))  # this will insert all existing...

#Neuron(Phenotype())

def main():
    WRITE()
    embed()

if __name__ == '__main__':
    main()
