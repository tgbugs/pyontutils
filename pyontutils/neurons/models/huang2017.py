#!/usr/bin/env python3
from pyontutils.neurons.lang import *
from pyontutils.neurons import *
from ontquery import rdflibLocal
from pyontutils.core import OntId, OntTerm
from pyontutils.utils import relative_path
from pyontutils.namespaces import makePrefixes, makeNamespaces
from pyontutils.namespaces import NIFRID, ilxtr, hasRole, definition
from pyontutils.closed_namespaces import rdf, rdfs, owl
from pyontutils.phenotype_namespaces import *
import rdflib
from IPython import embed

Config('huang-2017',
       imports=['NIFRAW:neurons/ttl/generated/neurons/phenotype-direct.ttl'],
       source_file=relative_path(__file__))
OntTerm.query.add(rdflibLocal(Neuron.core_graph, OntId))

class NeuronHuang2017(NeuronEBM):
    owlClass = ilxtr.NeuronHuang2017
    shortname = 'Huang2017'


Neuron, Neuron_ = NeuronHuang2017, Neuron

class Genes(LocalNameManager):

    # FIXME ilxtr.hasRNAExpressionPhenotype
    #VIP = Phenotype('PR:000017299', 'ilxtr:hasExpressionPhenotype')
    #CCK = Phenotype('PR:000005110', 'ilxtr:hasExpressionPhenotype')
    #SST = Phenotype('PR:000015665', 'ilxtr:hasExpressionPhenotype')
    #CR = Phenotype('PR:000004968', 'ilxtr:hasExpressionPhenotype')
    #PV = Phenotype('PR:000013502', 'ilxtr:hasExpressionPhenotype')

    # cre lines
    VIP = Phenotype('ilxtr:VIP-flp', 'ilxtr:hasExpressionPhenotype')
    CCK = Phenotype('ilxtr:CCK-cre', 'ilxtr:hasExpressionPhenotype')
    SST = Phenotype('ilxtr:SST-flp', 'ilxtr:hasExpressionPhenotype')
    CR = Phenotype('ilxtr:CR-cre', 'ilxtr:hasExpressionPhenotype')
    PV = Phenotype('ilxtr:PV-cre', 'ilxtr:hasExpressionPhenotype')
    NOS1 = Phenotype('ilxtr:NOS1-creER', 'ilxtr:hasExpressionPhenotype')
    Nkx2_1 = Phenotype('ilxtr:Nkx2.1-creER', 'ilxtr:hasExpressionPhenotype')
    Nkx2_1flp = Phenotype('ilxtr:Nkx2.1-flp', 'ilxtr:hasExpressionPhenotype')

    # Actual genes

    Vip = Phenotype(ilxtr.Vip, ilxtr.hasExpressionPhenotype)
    Cck = Phenotype(ilxtr.Cck, ilxtr.hasExpressionPhenotype)
    Sst = Phenotype(ilxtr.Sst, ilxtr.hasExpressionPhenotype)
    Calb2 = Phenotype(ilxtr.Calb2, ilxtr.hasExpressionPhenotype)
    Pvalb = Phenotype(ilxtr.Pvalb, ilxtr.hasExpressionPhenotype)
    Nos1 = Phenotype('ilxtr:Nos1', 'ilxtr:hasExpressionPhenotype')

    # cre equivalents where appropriate
    PVBCEq = LogicalPhenotype(AND, Pvalb)
    CHCEq = LogicalPhenotype(AND)  # pretty sure this doesn't have any
    CCKCEq = LogicalPhenotype(AND, Vip, Cck)
    MNCEq = LogicalPhenotype(AND, Sst, Calb2)
    ISCEq = LogicalPhenotype(AND, Vip, Calb2)
    LPCEq = LogicalPhenotype(AND, Sst, Nos1)

    # peptides
    Tac1 = Phenotype('ilxtr:Tac1', 'ilxtr:hasExpressionPhenotype')
    Adm = Phenotype('ilxtr:Adm', 'ilxtr:hasExpressionPhenotype')
    Rspn = Phenotype('ilxtr:Rspn', 'ilxtr:hasExpressionPhenotype')
    PVBCPep = LogicalPhenotype(AND, Tac1, Adm, Rspn)

    Pthlh = Phenotype('ilxtr:Pthlh', 'ilxtr:hasExpressionPhenotype')
    Tgfb3 = Phenotype('ilxtr:Tgfb3', 'ilxtr:hasExpressionPhenotype')
    Fgf9 = Phenotype('ilxtr:Fgf91', 'ilxtr:hasExpressionPhenotype')
    CHCPep = LogicalPhenotype(AND, Pthlh, Tgfb3, Fgf9) 

    Igf1 = Phenotype('ilxtr:Igf1', 'ilxtr:hasExpressionPhenotype')
    Edn3 = Phenotype('ilxtr:Edn3', 'ilxtr:hasExpressionPhenotype')
    Prok2 = Phenotype('ilxtr:Prok2', 'ilxtr:hasExpressionPhenotype')
    Pnoc = Phenotype('ilxtr:Pnoc', 'ilxtr:hasExpressionPhenotype')
    Crh = Phenotype('ilxtr:Crh', 'ilxtr:hasExpressionPhenotype')
    Tac2 = Phenotype('ilxtr:Tac2', 'ilxtr:hasExpressionPhenotype')
    CCKCPep = LogicalPhenotype(AND, Vip, Cck, Igf1, Edn3, Prok2, Pnoc, Crh, Tac2)

    Inhbb = Phenotype('ilxtr:Inhbb', 'ilxtr:hasExpressionPhenotype')
    Nppc = Phenotype('ilxtr:Nppc', 'ilxtr:hasExpressionPhenotype')
    MNCPep = LogicalPhenotype(AND, Sst, Inhbb, Nppc)

    Rspo1 = Phenotype('ilxtr:Rspo1', 'ilxtr:hasExpressionPhenotype')
    Wnt5a = Phenotype('ilxtr:Wnt5aae1', 'ilxtr:hasExpressionPhenotype')
    Nrtn = Phenotype('ilxtr:Nrtn', 'ilxtr:hasExpressionPhenotype')
    ISCPep = LogicalPhenotype(AND, Vip, Cck, Rspo1, Wnt5a, Nrtn)

    Ptn = Phenotype('ilxtr:Ptn', 'ilxtr:hasExpressionPhenotype')
    Wnt2 = Phenotype('ilxtr:Wnt2', 'ilxtr:hasExpressionPhenotype')
    Rln1 = Phenotype('ilxtr:Rln1', 'ilxtr:hasExpressionPhenotype')
    Penk = Phenotype('ilxtr:Penk', 'ilxtr:hasExpressionPhenotype')
    Calca = Phenotype('ilxtr:Calca', 'ilxtr:hasExpressionPhenotype')
    Cort = Phenotype('ilxtr:Cort', 'ilxtr:hasExpressionPhenotype')
    LPCPep = LogicalPhenotype(AND, Ptn, Wnt2, Rln1, Penk, Calca, Cort)

    # dendrites
    GluA1 = Phenotype('ilxtr:GluA1', 'ilxtr:hasExpressionPhenotype')
    GluA4 = Phenotype('ilxtr:GluA4', 'ilxtr:hasExpressionPhenotype')
    α1GABAaR = Phenotype('ilxtr:α1GABAaR', 'ilxtr:hasExpressionPhenotype')
    Kv3 = Phenotype('ilxtr:Kv3', 'ilxtr:hasExpressionPhenotype')
    α4GABAaR = Phenotype('ilxtr:α4GABAaR', 'ilxtr:hasExpressionPhenotype')
    δGABAaR = Phenotype('ilxtr:δGABAaR', 'ilxtr:hasExpressionPhenotype')
    Cckbr = Phenotype('ilxtr:Cckbr', 'ilxtr:hasExpressionPhenotype')
    PVBCDend = LogicalPhenotype(AND, GluA1, GluA4, α1GABAaR, Kv3, α4GABAaR, δGABAaR, Cckbr)

    # TODO LOWER
    Lower = Phenotype('ilxtr:LowerExpression', 'ilxtr:hasExpressionPhenotype')
    Higher = Phenotype('ilxtr:HigherExpression', 'ilxtr:hasExpressionPhenotype')
    CHCDend = LogicalPhenotype(AND,
                               GluA1, GluA4, α1GABAaR, Kv3,
                               α4GABAaR, δGABAaR, Cckbr,
                               Lower) # FIXME bad model

    Cnr1 = Phenotype('ilxtr:Cnr1', 'ilxtr:hasExpressionPhenotype')
    Htr2c = Phenotype('ilxtr:Htr2c', 'ilxtr:hasExpressionPhenotype')
    Htr3a = Phenotype('ilxtr:Htr3a', 'ilxtr:hasExpressionPhenotype')
    Chrm3 = Phenotype('ilxtr:Chrm3', 'ilxtr:hasExpressionPhenotype')
    Npy1r = Phenotype('ilxtr:Npy1r', 'ilxtr:hasExpressionPhenotype')
    Vipr1 = Phenotype('ilxtr:Vipr1', 'ilxtr:hasExpressionPhenotype')
    CCKCDend = LogicalPhenotype(AND, Cnr1, Htr2c, Htr3a, Chrm3, Npy1r, Vipr1)

    # high level diverse iGluRs
    # low level few types GABAaRs
    GLUR = Phenotype('ilxtr:glutamateReceptor', 'ilxtr:hasExpressionPhenotype')
    GABAR = Phenotype('ilxtr:GABAReceptor', 'ilxtr:hasExpressionPhenotype')
    # need a clear statement for how to handle cases like this
    # can the current python implementation handle this?
    MNCDend = LogicalPhenotype(AND,
                     LogicalPhenotype(AND, GABAR, Lower),
                     # intersectionOf(ilxtr.GABAReceptor, ilxtr.LowerExpression)
                     LogicalPhenotype(AND, GLUR, Higher))
    Chrna4 = Phenotype('ilxtr:Chrna4', 'ilxtr:hasExpressionPhenotype')
    Adra1b = Phenotype('ilxtr:Adra1b', 'ilxtr:hasExpressionPhenotype')
    Npy2r = Phenotype('ilxtr:Npy2r', 'ilxtr:hasExpressionPhenotype')
    ISCDend = LogicalPhenotype(AND, Htr2c, Htr3a, Chrm3, Chrna4, Adra1b, Npy2r)

    Chrm2 = Phenotype('ilxtr:Chrm2', 'ilxtr:hasExpressionPhenotype')
    Gpr88 = Phenotype('ilxtr:Gpr88', 'ilxtr:hasExpressionPhenotype')
    Oxtr = Phenotype('ilxtr:Oxtr', 'ilxtr:hasExpressionPhenotype')
    Tacr1 = Phenotype('ilxtr:Tacr1', 'ilxtr:hasExpressionPhenotype')
    Hcrtr1 = Phenotype('ilxtr:Hcrtr1', 'ilxtr:hasExpressionPhenotype')
    Opn3 = Phenotype('ilxtr:Opn3', 'ilxtr:hasExpressionPhenotype')
    # low unusual ??? check 4 H and enumerate all the instances of 'unusual'
    LPCDend = LogicalPhenotype(AND, Chrm2, Gpr88, Oxtr, Tacr1, Hcrtr1, Opn3)

    # encode the negative phenotypes 6 C, 6 has lots of useful information
    # specifically with regard to how to encode a thresholded negative phenotype

    # ilxtr:hasSynapticPhenotype
    #FastEPSP = Phenotype('ilxtr:FastEPSP', 'ilxtr:hasElectrophysiologicalPhenotype')

    # signaling
    RGS4 = Phenotype('ilxtr:RGS4', 'ilxtr:hasExpressionPhenotype')
    Adcy8 = Phenotype('ilxtr:Adcy8', 'ilxtr:hasExpressionPhenotype')
    Adcy1 = Phenotype('ilxtr:Adcy1', 'ilxtr:hasExpressionPhenotype')
    Ras111b = Phenotype('ilxtr:Ras111b', 'ilxtr:hasExpressionPhenotype')
    Arhgef10 = Phenotype('ilxtr:Arhgef10', 'ilxtr:hasExpressionPhenotype')
    PVBCSig = LogicalPhenotype(AND, RGS4, Adcy8, Adcy1, Ras111b, Arhgef10)
    Gucy1a3 = Phenotype('ilxtr:Gucy1a3', 'ilxtr:hasExpressionPhenotype')
    Gucy1b3 = Phenotype('ilxtr:Gucy1b3', 'ilxtr:hasExpressionPhenotype')
    Prkg1 = Phenotype('ilxtr:Prkg1', 'ilxtr:hasExpressionPhenotype')
    Pde11a = Phenotype('ilxtr:Pde11a', 'ilxtr:hasExpressionPhenotype')
    Pde5a = Phenotype('ilxtr:Pde5a', 'ilxtr:hasExpressionPhenotype')
    Trpc5 = Phenotype('ilxtr:Trpc5', 'ilxtr:hasExpressionPhenotype')
    Kcnmb2 = Phenotype('ilxtr:Kcnmb2', 'ilxtr:hasExpressionPhenotype')
    CHCSig = LogicalPhenotype(AND, Gucy1a3, Gucy1b3, Prkg1, Pde11a, Pde5a, Trpc5, Kcnmb2)
    Rgs12 = Phenotype('ilxtr:Rgs12', 'ilxtr:hasExpressionPhenotype')
    Adcy9 = Phenotype('ilxtr:Adcy9', 'ilxtr:hasExpressionPhenotype')
    Pde7b = Phenotype('ilxtr:Pde7b', 'ilxtr:hasExpressionPhenotype')
    CCKCSig = LogicalPhenotype(AND, Rgs12, Adcy9, Pde7b)
    RGS6 = Phenotype('ilxtr:RGS6', 'ilxtr:hasExpressionPhenotype')
    RGS7 = Phenotype('ilxtr:RGS7', 'ilxtr:hasExpressionPhenotype')
    Adcy2 = Phenotype('ilxtr:Adcy2', 'ilxtr:hasExpressionPhenotype')
    Pde2a = Phenotype('ilxtr:Pde2a', 'ilxtr:hasExpressionPhenotype')
    MNCSig = LogicalPhenotype(AND, RGS6, RGS7, Adcy2, Pde2a)
    Rgs16 = Phenotype('ilxtr:Rgs16', 'ilxtr:hasExpressionPhenotype')
    Rgs10 = Phenotype('ilxtr:Rgs10', 'ilxtr:hasExpressionPhenotype')
    Rgs8 = Phenotype('ilxtr:Rgs8', 'ilxtr:hasExpressionPhenotype')
    Pde4b = Phenotype('ilxtr:Pde4b', 'ilxtr:hasExpressionPhenotype')
    ISCSig = LogicalPhenotype(AND, Rgs16, Rgs10, Rgs8, Pde4b)
    Slc7a3 = Phenotype('ilxtr:Slc7a3', 'ilxtr:hasExpressionPhenotype')
    #Gucy1a3 = Phenotype('ilxtr:Gucy1a3', 'ilxtr:hasExpressionPhenotype')
    #Gucy1b3 = Phenotype('ilxtr:Gucy1b3', 'ilxtr:hasExpressionPhenotype')
    Prkg2 = Phenotype('ilxtr:Prkg2', 'ilxtr:hasExpressionPhenotype')
    Ped1a = Phenotype('ilxtr:Ped1a', 'ilxtr:hasExpressionPhenotype')
    Trpc6 = Phenotype('ilxtr:Trpc6', 'ilxtr:hasExpressionPhenotype')
    Kcnmb4 = Phenotype('ilxtr:Kcnmb4', 'ilxtr:hasExpressionPhenotype')
    LPCSig = LogicalPhenotype(AND, Slc7a3, Nos1, Gucy1a3, Gucy1b3, Prkg2, Ped1a, Trpc6, Kcnmb4)

    # axons
    Nav1_1 = Phenotype('ilxtr:Nav1_1', 'ilxtr:hasExpressionPhenotype')
    Nav1_6 = Phenotype('ilxtr:Nav1_6', 'ilxtr:hasExpressionPhenotype')
    Nav1_7 = Phenotype('ilxtr:Nav1_7', 'ilxtr:hasExpressionPhenotype')
    Cav2_1_P_Q = Phenotype('ilxtr:Cav2_1_P_Q', 'ilxtr:hasExpressionPhenotype')
    Syt2 = Phenotype('ilxtr:Syt2', 'ilxtr:hasExpressionPhenotype')
    Syt7 = Phenotype('ilxtr:Syt7', 'ilxtr:hasExpressionPhenotype')
    Vamp1 = Phenotype('ilxtr:Vamp1', 'ilxtr:hasExpressionPhenotype')
    Cplx1 = Phenotype('ilxtr:Cplx1', 'ilxtr:hasExpressionPhenotype')
    # FIXME listed as PV but probably means Pvalb?
    #high Snap25, Rab3a, NSF
    PVBCAxon = LogicalPhenotype(AND, Nav1_1, Nav1_6, Nav1_7, Cav2_1_P_Q, Pvalb, Syt2, Syt7, Vamp1, Cplx1)
    # lower Vamp1, Cplx1, Syt1, Syt2, Syt7 vs PVBC, probably want to encode the comparator expicitly
    # NOT generally
    # high Snap25, Rab3a, NSF
    TODO = Phenotype(ilxtr.to, ilxtr.hasPhenotype)
    CHCAxon = LogicalPhenotype(AND, TODO)
    Cplx2 = Phenotype('ilxtr:Cplx2', 'ilxtr:hasExpressionPhenotype')
    Cplx3 = Phenotype('ilxtr:Cplx3', 'ilxtr:hasExpressionPhenotype')
    LDCV = Phenotype('ilxtr:LDCV', 'ilxtr:hasExpressionPhenotype')
    Syt10 = Phenotype('ilxtr:Syt10', 'ilxtr:hasExpressionPhenotype')
    CCKCAxon = LogicalPhenotype(AND, Cplx2, Cplx3, LDCV, Syt10)  # FIXME LDCV release?
    Znt3 = Phenotype('ilxtr:Znt3', 'ilxtr:hasExpressionPhenotype')
    Zip1 = Phenotype('ilxtr:Zip1', 'ilxtr:hasExpressionPhenotype')
    MNCAxon = LogicalPhenotype(AND, Znt3, Zip1)  # FIXME why does he have the names out front?
    ISCAxon = LogicalPhenotype(AND, *CCKCAxon.pes, Phenotype(ilxtr.similarTo, ilxtr.hasPhenotype))  # FIXME similar
    Syt4 = Phenotype('ilxtr:Syt4', 'ilxtr:hasExpressionPhenotype')
    Syt5 = Phenotype('ilxtr:Syt5', 'ilxtr:hasExpressionPhenotype')
    Syt6 = Phenotype('ilxtr:Syt6', 'ilxtr:hasExpressionPhenotype')
    LPCAxon = LogicalPhenotype(AND, Syt4, Syt5, Syt6)

    # other
    PGC1α = Phenotype('ilxtr:PGC1α', 'ilxtr:hasExpressionPhenotype')
    Esrrg = Phenotype('ilxtr:Esrrg', 'ilxtr:hasExpressionPhenotype')
    Mef2c = Phenotype('ilxtr:Mef2c', 'ilxtr:hasExpressionPhenotype')
    Pparg = Phenotype('ilxtr:Pparg', 'ilxtr:hasExpressionPhenotype')
    Cox6c = Phenotype('ilxtr:Cox6c', 'ilxtr:hasExpressionPhenotype')
    Nefh = Phenotype('ilxtr:Nefh', 'ilxtr:hasExpressionPhenotype')
    Slit2 = Phenotype('ilxtr:Slit2', 'ilxtr:hasExpressionPhenotype')
    Slit3 = Phenotype('ilxtr:Slit3', 'ilxtr:hasExpressionPhenotype')
    PVBCOther = LogicalPhenotype(AND, PGC1α, Esrrg, Mef2c, Pparg, Cox6c, Nefh, Slit2, Slit3)
    Unc5b = Phenotype('ilxtr:Unc5b', 'ilxtr:hasExpressionPhenotype')
    Hs3st4 = Phenotype('ilxtr:Hs3st4', 'ilxtr:hasExpressionPhenotype')
    CHCOther = LogicalPhenotype(AND, Unc5b, Hs3st4)
    Hs6st3 = Phenotype('ilxtr:Hs6st3', 'ilxtr:hasExpressionPhenotype')
    CCKCOther = LogicalPhenotype(AND, Hs6st3)
    Grin3a = Phenotype('ilxtr:Grin3a', 'ilxtr:hasExpressionPhenotype')
    MNCOther = LogicalPhenotype(AND, Grin3a)
    Unc5a = Phenotype('ilxtr:Unc5a', 'ilxtr:hasExpressionPhenotype')
    Chst1 = Phenotype('ilxtr:Chst1', 'ilxtr:hasExpressionPhenotype')
    ISCOther = LogicalPhenotype(AND, Unc5a, Chst1)
    #Ptn = Phenotype('ilxtr:Ptn', 'ilxtr:hasExpressionPhenotype')
    Unc5d = Phenotype('ilxtr:Unc5d', 'ilxtr:hasExpressionPhenotype')
    LPCOther = LogicalPhenotype(AND, Ptn, Unc5d)


class Huang2017(Genes, Species):
    Neocortex = Phenotype('UBERON:0001950', 'ilxtr:hasSomaLocatedIn')
    Basket = Phenotype('ilxtr:BasketPhenotype', 'ilxtr:hasMorphologicalPhenotype')


with Huang2017:
    with Neuron_(Mouse, Neocortex) as context:
        #context.subClassOf(ilxtr.huang2017)
        # TODO add the names assigned here as abbrevs somehow

        #fig1b
        # FIXME is approach to disjointness VS adding negative phenotypes
        Neuron(Pvalb).disjointWith(Neuron(Sst), Neuron(Htr3a))
        #Neuron(Pvalb).equivalentClass(Neuron(NegPhenotype(Sst)), Neuron(NegPhenotype(Htr3a)))
        # FIXME for some reason the NegPhenotype neurons above fail to be added to the graph!??!
        #a = Neuron(NegPhenotype(Sst))
        #b = Neuron(NegPhenotype(Htr3a))
        #Neuron(Pvalb).equivalentClass(a, b)
        Neuron(Sst).disjointWith(Neuron(Htr3a))
        Neuron(Vip).subClassOf(Neuron(Htr3a))
        Neuron(Cck).subClassOf(Neuron(Htr3a))
        Neuron(Nkx2_1).disjointWith(Neuron(Nos1), Neuron(Htr3a), Neuron(Calb2))
        Neuron(Nos1).disjointWith(Neuron(Htr3a), Neuron(Calb2))

        Neuron(Vip, Cck)
        Neuron(Vip, Calb2, Cck)
        Neuron(Vip, Calb2)
        Neuron(Sst, Calb2)

        fig1a = dict(
        PVBC = Neuron(Basket, PV),
        CHC = Neuron(Nkx2_1),
        CCKC = Neuron(Basket, VIP, CCK),
        MNC = Neuron(SST, CR),
        ISC = Neuron(VIP, CR),
        LPC = Neuron(SST, NOS1),
        )

        f7 = dict(
        equivs = (PVBCEq, CHCEq, CCKCEq, MNCEq, ISCEq, LPCEq),
        peptides = (PVBCPep, CHCPep, CCKCPep, MNCPep, ISCPep, LPCPep),
        signaling = (PVBCSig, CHCSig, CCKCSig, MNCSig, ISCSig, LPCSig),
        dendrite = (PVBCDend, CHCDend, CCKCDend, MNCDend, ISCDend, LPCDend),
        axon = (PVBCAxon, CHCAxon, CCKCAxon, MNCAxon, ISCAxon, LPCAxon),
        other = (PVBCOther, CHCOther, CCKCOther, MNCOther, ISCOther, LPCOther))

        figs7 = {type:Neuron(*(pe for p in phenos for pe in p.pes),
                            label=f'{type} all neuron', override=True)
                for type, *phenos in zip(fig1a, fig1a.values(), *f7.values())}

        for k, v in fig1a.items():
            # FIXME ISC currently classifies as vip cr cck which is incorrect
            # some _subset_ of those have cck, but it is not clear how many
            figs7[k].equivalentClass(v)  # TODO asserted by Josh Huang in figure s7

        peps = [Neuron(*p.pes, label=f'{l} peptides neuron', override=True)
                for l, p in zip(fig1a, f7['peptides'])]
        sigs = [Neuron(*p.pes, label=f'{l} signaling neuron', override=True)
                for l, p in zip(fig1a, f7['signaling'])]
        # asserted by Tom Gillespie interpreting Huang
        [p.equivalentClass(s) for p, s in zip(peps, sigs)]
        # assert that the peptide markers are disjoint
        for dis in (peps, sigs, tuple(fig1a.values())):
            for i, n in enumerate(dis[:-1]):
                for on in dis[i+1:]:
                    n.disjointWith(on)
        #LPCbyPepties = Neuron(*LPCPep.pes)

# common usage types
# allen 2016 hongwei

#embed()
for n, p in Huang2017.items():
    if isinstance(p, Phenotype):
        # FIXME rdflib allows instances but tests type so OntId can go in, but won't ever match
        ident = OntId(p.p)
        if n in Genes.__dict__:
            lt = (rdflib.URIRef(ident), rdfs.label, rdflib.Literal(n))
            Neuron.core_graph.add(lt)
            Neuron.out_graph.add(lt)  # FIXME maybe a helper graph?
            if ident.curie.startswith('ilxtr:'):
                sct = (rdflib.URIRef(ident), rdfs.subClassOf, ilxtr.gene)
                Neuron.core_graph.add(sct)
                Neuron.out_graph.add(sct)
        else:
            lt = (rdflib.URIRef(ident), rdfs.label, rdflib.Literal(OntTerm(ident).label))
            Neuron.core_graph.add(lt)
            Neuron.out_graph.add(lt)  # FIXME maybe a helper graph?

Neuron.write()
Neuron.write_python()
res = [r for s, l in Neuron.out_graph[:rdfs.label:] if
       OntTerm(s).curie.startswith('ilxtr:')
       for r in OntTerm.query(label=l.toPython()) if
       r.curie.startswith('ilxtr:')]
mapped = [r.OntTerm for s, l in Neuron.out_graph[:rdfs.label:] if
          OntTerm(s).curie.startswith('ilxtr:')
          for r in OntTerm.query(label=l.toPython()) if
          not r.curie.startswith('ilxtr:')]

def main():
    embed()

if __name__ == '__main__':
    main()
