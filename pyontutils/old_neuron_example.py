#!/usr/bin/env python3
from pyontutils.neuron_lang import *
from IPython import embed

Rat = Phenotype('NCBITaxon:10116', pred.hasInstanceInSpecies, label='Rattus norvegicus')
S1 = Phenotype('UBERON:0008933', pred.hasSomaLocatedIn, label='primary somatosensory cortex')
CA1 = Phenotype('UBERON:0003881', pred.hasSomaLocatedIn)
context = (Rat, S1)
ca1_cont = (Rat, CA1)

#'(Rat S1 L4 P bIR) '(LB Th Tu)
# organism

# pyramidal phenotypes (cortex)
P = P = PC = Phenotype('ilxtr:PyramidalPhenotype', pred.hasMorphologicalPhenotype)  # 
PB = BP = BPC = Phenotype('ilxtr:BiopolarPyramidalPhenotype', pred.hasMorphologicalPhenotype)  # collision
PH = HP = HPC = Phenotype('ilxtr:HorizontalPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PI = IP = IPC = Phenotype('ilxtr:InvertedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PN = NP = NPC = Phenotype('ilxtr:NarrowPyramidalPhenotype', pred.hasMorphologicalPhenotype)  # XXX These are apparently tufted.... so are they NarrowTufted or not? help!
PS = SP = SPC = Phenotype('ilxtr:StarPyramidalPhenotype', pred.hasMorphologicalPhenotype)  # collision with stratum pyramidale
PTN = NTP = NTPC = TPC_C = Phenotype('ilxtr:NarrowTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)  # are this different?  Yes, the Narrow modifieds the tufted... not entirely sure how that is different from when Narrow modifies Pyramidal...
PT = TP = TPC = Phenotype('ilxtr:TuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTS = STP = STPC = Phenotype('ilxtr:SlenderTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTT = TTP = TTPC = Phenotype('ilxtr:ThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTTLB = TTPLB = TTPCLB = TTPC1 = Phenotype('ilxtr:LateBifurcatingThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTTEB = TTPEB = TTPCEB = TTPC2 = Phenotype('ilxtr:EarlyBifurcatingThickTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PTLB = TPLB = TPCLB = TPC_A = Phenotype('ilxtr:LateBifurcatingTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype) # these are inconsistent with usages like NGC_DA NGC_SA recomend the NGCDA NGCSA versions since the acronym is better than a/b 1/2
PTEB = TPEB = TPCEB = TPC_B = Phenotype('ilxtr:EarlyBifurcatingTuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)
PU = UP = UPC = UTPC = Phenotype('ilxtr:UntuftedPyramidalPhenotype', pred.hasMorphologicalPhenotype)

BT = BTC = Phenotype('ilxtr:BituftedPhenotype', pred.hasMorphologicalPhenotype)
B = BP = Phenotype('ilxtr:BipolarPhenotype', pred.hasMorphologicalPhenotype)  # NOTE disjoint from biopolar pyramidal... also collision
BS = Phenotype('ilxtr:BistratifiedPhenotype', pred.hasMorphologicalPhenotype)
Ch = ChC = Phenotype('ilxtr:ChandelierPhenotype', pred.hasMorphologicalPhenotype)  # AA ??
DB = DBC = Phenotype('ilxtr:DoubleBouquetPhenotype', pred.hasMorphologicalPhenotype)
DA = DAC = Phenotype('ilxtr:DescendingAxonPhenotype', pred.hasMorphologicalPhenotype)  # FIXME how to communicate that these are a bit different than actual 'axon' phenotypes? disjoint from P?
HA = HAC = Phenotype('ilxtr:HorizontalAxonPhenotype', pred.hasMorphologicalPhenotype)
LA = LAC = Phenotype('ilxtr:LargeAxonPhenotype', pred.hasMorphologicalPhenotype)
SA = SAC = Phenotype('ilxtr:SmallAxonPhenotype', pred.hasMorphologicalPhenotype)
M = MC = Phenotype('ilxtr:MartinottiPhenotype', pred.hasMorphologicalPhenotype)
NG = NGC = Phenotype('ilxtr:NeurogliaformPhenotype', pred.hasMorphologicalPhenotype)
NGDA = NGCDA = NGC_DA = Phenotype('ilxtr:NeurogliaformDenseAxonPhenotype', pred.hasMorphologicalPhenotype)
NGSA = NGCSA = NGC_SA = Phenotype('ilxtr:NeurogliaformSparseAxonPhenotype', pred.hasMorphologicalPhenotype)
B = BC = Phenotype('ilxtr:BasketPhenotype', pred.hasMorphologicalPhenotype)
SB = SBC = Phenotype('ilxtr:SmallBasketPhenotype', pred.hasMorphologicalPhenotype)
LB = LBC = Phenotype('ilxtr:LargeBasketPhenotype', pred.hasMorphologicalPhenotype)
NB = NBC = Phenotype('ilxtr:NestBasketPhenotype', pred.hasMorphologicalPhenotype)
SS = SSC = Phenotype('ilxtr:SpinyStellatePhenotype', pred.hasMorphologicalPhenotype)  # SS is used on the website, SSC is used on the spreadsheet

# e-types
AC = Phenotype('ilxtr:PetillaSustainedAccomodatingPhenotype', pred.hasElectrophysiologicalPhenotype)
NAC = Phenotype('ilxtr:PetillaSustainedNonAccomodatingPhenotype', pred.hasElectrophysiologicalPhenotype)
STUT = Phenotype('ilxtr:PetillaSustainedStutteringPhenotype', pred.hasElectrophysiologicalPhenotype)
IR = Phenotype('ilxtr:PetillaSustainedIrregularPhenotype', pred.hasElectrophysiologicalPhenotype)
b = Phenotype('ilxtr:PetillaInitialBurstSpikingPhenotype', pred.hasElectrophysiologicalPhenotype)
c = Phenotype('ilxtr:PetillaInitialClassicalSpikingPhenotype', pred.hasElectrophysiologicalPhenotype)
d = Phenotype('ilxtr:PetillaInitialDelayedSpikingPhenotype', pred.hasElectrophysiologicalPhenotype)

# other e-types
FS = Phenotype('ilxtr:FastSpikingPhenotype', pred.hasElectrophysiologicalPhenotype)
RSNP = Phenotype('ilxtr:RegularSpikingNonPyramidalPhenotype', pred.hasElectrophysiologicalPhenotype)

# layers
L1 = Phenotype('UBERON:0005390', pred.hasLayerLocationPhenotype)
L2 = Phenotype('UBERON:0005391', pred.hasLayerLocationPhenotype)
L3 = Phenotype('UBERON:0005392', pred.hasLayerLocationPhenotype)
L23 = LogicalPhenotype(OR, L2, L3)  # if you try to do this inside a dict definition it will fail :/
L23.labelPostRule = lambda l: 'L23' # heh
L4 = Phenotype('UBERON:0005393', pred.hasLayerLocationPhenotype)
L5 = Phenotype('UBERON:0005394', pred.hasLayerLocationPhenotype)
L6 = Phenotype('UBERON:0005395', pred.hasLayerLocationPhenotype)

L1P = Phenotype('UBERON:0005390', pred.hasProjectionPhenotype)
L4P = Phenotype('UBERON:0005393', pred.hasProjectionPhenotype)

L1D = Phenotype('UBERON:0005390', pred.hasDendriteLocatedIn)
L4D = Phenotype('UBERON:0005393', pred.hasDendriteLocatedIn)

CA2 = Phenotype('UBERON:0003882', pred.hasSomaLocatedIn)
CA3 = Phenotype('UBERON:0003883', pred.hasSomaLocatedIn)

SO = Phenotype('UBERON:0005371', pred.hasLayerLocationPhenotype)  # WARNING: uberon has precomposed these, which is annoying
SPy = SP = Phenotype('UBERON:0002313', pred.hasLayerLocationPhenotype)
SLA = Phenotype('UBERON:0005370', pred.hasLayerLocationPhenotype)
SLM = Phenotype('UBERON:0007640', pred.hasLayerLocationPhenotype)
SLU = Phenotype('UBERON:0007637', pred.hasLayerLocationPhenotype)
SR = Phenotype('UBERON:0005372', pred.hasLayerLocationPhenotype)

SLMP = Phenotype('UBERON:0007640', pred.hasProjectionPhenotype)
ThalP = Phenotype('UBERON:0001897', pred.hasProjectionPhenotype)

# expression
CB = Phenotype('PR:000004967', pred.hasExpressionPhenotype)
CCK = Phenotype('PR:000005110', pred.hasExpressionPhenotype)
CR = Phenotype('PR:000004968', pred.hasExpressionPhenotype)
NPY = Phenotype('PR:000011387', pred.hasExpressionPhenotype)
PV = Phenotype('PR:000013502', pred.hasExpressionPhenotype)
SOM = Phenotype('PR:000015665', pred.hasExpressionPhenotype)
VIP = Phenotype('PR:000017299', pred.hasExpressionPhenotype)
GABA = Phenotype('CHEBI:16865', pred.hasExpressionPhenotype)
D1 = Phenotype('PR:000001175', pred.hasExpressionPhenotype)

# dendrite phenotypes
Th = Phenotype('ilxtr:ThickPhenotype', pred.hasDendriteMorphologicalPhenotype)
Tu = Phenotype('ilxtr:TuftedPhenotype', pred.hasDendriteMorphologicalPhenotype)
U = NegPhenotype(Tu)
U.labelPostRule = lambda l: 'Un' + l.lower()
S = Phenotype('ilxtr:SlenderPhenotype', pred.hasDendriteMorphologicalPhenotype)
EB = Phenotype('ilxtr:EarlyBifurcatingPhenotype', pred.hasDendriteMorphologicalPhenotype)
LB = Phenotype('ilxtr:LateBifurcatingPhenotype', pred.hasDendriteMorphologicalPhenotype)
Sp = Phenotype('ilxtr:SpinyPhenotype', pred.hasDendriteMorphologicalPhenotype)
ASp = NegPhenotype(Sp)

# other?
PPA = Phenotype('ilxtr:PerforantPathwayAssociated', pred.hasPhenotype)  # TODO FIXME

#OLM = Phenotype('', pred.hasLayerLocationPhenotype)  # removed since it seems to be a logical of SO and SLM
TRI = Phenotype('ilxtr:TrilaminarPhenotype', pred.hasMorphologicalPhenotype)
#AA = Phenotype('ilxtr:AxoAxonicPhenotype', pred.hasMorphologicalPhenotype)  # axo axonic??!? This is ChC
IVY = Phenotype('ilxtr:IvyPhenotype', pred.hasMorphologicalPhenotype)  # check syns on this?
#IS1 = Phenotype('ilxtr:IS1IHaveNoIdeaPhenotype', pred.hasMorphologicalPhenotype)  # these are NOT morphological types, they are an example of a 'true type' in the sense that you need multiple meausres to confirm them
SCA = Phenotype('GO:1990021', pred.hasProjectionPhenotype)#'ilxtr:hasAssociatedTractPhenotype')  # how to model these... also schaffer collaterals are a MESS in the ontology FIXME
STRI = Phenotype('UBERON:0005383', pred.hasSomaLocatedIn)  # VS UBERON:0002435 (always comes up)
MSN = Phenotype('ilxtr:MediumSpinyPhenotype', pred.hasMorphologicalPhenotype)
#DIRPATH = Phenotype('ilxtr:DirectPathway', pred.hasCircuitRolePhenotype)  # this is fine for a generic neuron, but PR:000001175 is really what we are looking at here
INT = Phenotype('ilxtr:InterneuronPhenotype', pred.hasCircuitRolePhenotype)  # unsatisfactory
CER = Phenotype('UBERON:0002037', pred.hasSomaLocatedIn)
GRAN = Phenotype('ilxtr:GranulePhenotype', pred.hasMorphologicalPhenotype)  # vs granular?


def NeuronC(*args, **kwargs):
    return Neuron(*args, *context, **kwargs)
def NeuronH(*args, **kwargs):
    return Neuron(*args, *ca1_cont, **kwargs)

contn = Neuron(*context)

# TODO switch over to rat parcellation concepts
neurons = {
    #"""
    #'HBP_CELL:0000039': Neuron(*contn.pes, TTPCEB),  # can we identify early/late in other cells?
    #}
    'HBP_CELL:0000013': NeuronC(CCK),
    'HBP_CELL:0000016': NeuronC(PV),
    'HBP_CELL:0000018': NeuronC(PC),
    'HBP_CELL:0000024': NeuronC(U, PC), #NeuronC(UPC),  # untufted... dendrite phenotype?? or what
    'HBP_CELL:0000025': NeuronC(SS),
    'HBP_CELL:0000027': NeuronC(SPC),
    'HBP_CELL:0000028': NeuronC(L23, PC),
    'HBP_CELL:0000030': NeuronC(HPC),  # are phenotypes like this modifiers on _pyramidal_ or are they on the _cell_
    'HBP_CELL:0000031': NeuronC(BPC),  # AAAAAA
    'HBP_CELL:0000032': NeuronC(NPC, ThalP),
    'HBP_CELL:0000035': NeuronC(Tu, PC, L4D), #NeuronC(TPC, L4D),  # looking over the 2015 paper this is ok
    'HBP_CELL:0000036': NeuronC(Tu, PC, L1D), #NeuronC(TPC, L1D),  # looking over the 2015 paper this is ok
    'HBP_CELL:0000038': NeuronC(S, Tu, PC), #NeuronC(STPC),
    'HBP_CELL:0000039': NeuronC(Th, Tu, PC, EB), #NeuronC(TTPC2),  # can we identify early/late in other cells?
    'HBP_CELL:0000040': NeuronC(Th, Tu, PC, LB), #NeuronC(TTPC1),
    'HBP_CELL:0000042': NeuronC(IPC),
    'HBP_CELL:0000044': NeuronC(L5, Th, Tu, PC), # NeuronC(L5, TTPC),
    'HBP_CELL:0000051': NeuronC(L6, Tu, PC, L1D), #NeuronC(L6, TPC, L1D),  # looking over the 2015 paper this is ok
    'HBP_CELL:0000053': NeuronC(BP),
    'HBP_CELL:0000054': NeuronC(BTC),
    'HBP_CELL:0000055': NeuronC(MC),
    'HBP_CELL:0000056': NeuronC(NGC),
    'HBP_CELL:0000057': NeuronC(NGCSA),
    'HBP_CELL:0000058': NeuronC(NGCDA),
    'HBP_CELL:0000059': NeuronC(DBC),
    'HBP_CELL:0000060': NeuronC(ChC),
    'HBP_CELL:0000062': NeuronC(SBC),
    'HBP_CELL:0000063': NeuronC(LBC),
    'HBP_CELL:0000064': NeuronC(NBC),
    'HBP_CELL:0000066': NeuronC(DAC),
    'HBP_CELL:0000068': NeuronC(HAC),
    'HBP_CELL:0000069': NeuronC(SAC),
    'HBP_CELL:0000094': NeuronC(L1, HAC),
    'HBP_CELL:0000099': NeuronC(L5, BP),
    'HBP_CELL:0000101': NeuronC(L23, BTC),
    'HBP_CELL:0000102': NeuronC(L4, BTC),
    'HBP_CELL:0000105': NeuronC(L23, ChC),
    'HBP_CELL:0000109': NeuronC(L23, DBC),
    'HBP_CELL:0000110': NeuronC(L4, DBC),
    'HBP_CELL:0000117': NeuronC(L23, MC),
    'HBP_CELL:0000118': NeuronC(L4, MC),
    'HBP_CELL:0000119': NeuronC(L5, MC),
    'HBP_CELL:0000121': NeuronC(L23, LBC),
    'HBP_CELL:0000122': NeuronC(L4, LBC),
    'HBP_CELL:0000124': NeuronC(L6, LBC),
    'HBP_CELL:0000125': NeuronC(L23, NBC),
    'HBP_CELL:0000126': NeuronC(L23, SBC),
    'HBP_CELL:0000127': NeuronC(L4, SBC),
    'HBP_CELL:0000130': NeuronC(L4, NBC),
    'HBP_CELL:0000135': NeuronH(SLM, PPA),
    'HBP_CELL:0000136': NeuronH(SO, BP),
    'HBP_CELL:0000137': NeuronH(SPy, BS),
    'HBP_CELL:0000138': NeuronH(SO, SLMP),  # see (PMID: 23042082)
    'HBP_CELL:0000139': NeuronH(SPy, TRI),  # TODO
    'HBP_CELL:0000140': NeuronH(ChC),  # see (PMID: 8915675) AA are indeed ChC
    'HBP_CELL:0000141': NeuronH(SPy, BC),
    'HBP_CELL:0000143': NeuronH(SPy, PV, BC),
    'HBP_CELL:0000144': NeuronH(SPy, IVY),
    'HBP_CELL:0000145': NeuronH(SPy, PC),
    'HBP_CELL:0000146': NeuronH(SPy, GABA, CR),  # XXX review please IS-1 see (PMID: 8915675) page 27 these do not have distinctive morphology, they have distinctive connectivity... dendrodendritic connections within type and dendritic arbors in SR ... if these are really morphological then it is not the intrisice morphology, but the connectivity...? help?
    'HBP_CELL:0000147': NeuronH(SPy, SCA),  # TODO schafer collateral projecting?
    'HBP_CELL:0000148': Neuron(Rat, STRI, MSN, D1),  # the original class was direct pathway, but that is generic
    'HBP_CELL:0000149': Neuron(Rat, CA3, PC),
    'HBP_CELL:0000151': NeuronH(INT),  # TODO
    'HBP_CELL:0000152': Neuron(Rat, CER, GRAN),  # TODO
    'HBP_CELL:0000153': Neuron(Rat, CA2, PC),
}

generic_neurons = {
    '0':NeuronC(BC),
    '1':Neuron(Rat, CA1),
    '2':Neuron(NPY, NegPhenotype(PV)),
    '3':Neuron(PV),
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
