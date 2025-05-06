#!/usr/bin/env python3
import rdflib
import ontquery
#from pyontutils.core import OntId, OntTerm
from pyontutils.utils import relative_path
from pyontutils.namespaces import makePrefixes, makeNamespaces
from pyontutils.namespaces import NIFRID, ilxtr, hasRole, definition
from pyontutils.closed_namespaces import rdf, rdfs, owl
from neurondm.lang import *
from neurondm import *
from neurondm.phenotype_namespaces import *

extra = False  # construct extra classes
config = Config('huang-2017',
                source_file=relative_path(__file__, no_wd_value=__file__))
OntTerm.query.add(ontquery.plugin.get('rdflib')(Neuron.core_graph, OntId))


class NeuronHuang2017(NeuronEBM):
    owlClass = ilxtr.NeuronHuang2017
    shortname = 'Huang2017'


Neuron, Neuron_ = NeuronHuang2017, Neuron
dex = 'ilxtr:hasDriverExpressionPhenotype'
induced_exp = 'ilxtr:hasDriverExpressionInducedPhenotype'
const_exp = 'ilxtr:hasDriverExpressionConstitutivePhenotype'


def gid(i):
    return OntId(f'npokb:{i}')


class Genes(LocalNameManager):

    # FIXME ilxtr.hasRNAExpressionPhenotype
    #VIP = Phenotype('PR:000017299', 'ilxtr:hasExpressionPhenotype')
    #CCK = Phenotype('PR:000005110', 'ilxtr:hasExpressionPhenotype')
    #SST = Phenotype('PR:000015665', 'ilxtr:hasExpressionPhenotype')
    #CR = Phenotype('PR:000004968', 'ilxtr:hasExpressionPhenotype')
    #PV = Phenotype('PR:000013502', 'ilxtr:hasExpressionPhenotype')

    # cre lines from star methods table
    VIP = Phenotype('JAX:028578', const_exp, label='VIP-Flp', override=True)
    CCK = Phenotype('JAX:012706', const_exp, label='CCK-Cre', override=True)
    SST = Phenotype('JAX:028579', const_exp, label='SST-Flp', override=True)
    CR = Phenotype('JAX:013730', const_exp, label='CR-Cre', override=True)
    PV = Phenotype('JAX:017320', const_exp, label='PV-Cre', override=True)
    NOS1 = Phenotype('JAX:014541', induced_exp, label='NOS1-CreER', override=True)
    Nkx2_1 = Phenotype('JAX:014552', induced_exp, label='Nkx2.1-CreER', override=True)
    Nkx2_1flp = Phenotype('JAX:028577', const_exp, label='Nxk2.1-Flp', override=True)

    # Actual genes

    Vip = Phenotype('NCBIGene:22353', ilxtr.hasExpressionPhenotype)
    Cck = Phenotype('NCBIGene:12424', ilxtr.hasExpressionPhenotype)
    Sst = Phenotype('NCBIGene:20604', ilxtr.hasExpressionPhenotype)
    Calb2 = Phenotype('NCBIGene:12308', ilxtr.hasExpressionPhenotype)
    Pvalb = Phenotype('NCBIGene:19293', ilxtr.hasExpressionPhenotype)
    Nos1 = Phenotype('NCBIGene:18125', 'ilxtr:hasExpressionPhenotype')

    # cre equivalents where appropriate
    PVBCEq = LogicalPhenotype(AND, Pvalb)
    CHCEq = LogicalPhenotype(AND)  # pretty sure this doesn't have any since it is developmental & inducible
    CCKCEq = LogicalPhenotype(AND, Vip, Cck)
    MNCEq = LogicalPhenotype(AND, Sst, Calb2)
    ISCEq = LogicalPhenotype(AND, Vip, Calb2)
    LPCEq = LogicalPhenotype(AND, Sst, Nos1)

    # batch replace with ncbigene
    Adm = Phenotype('NCBIGene:11535', 'ilxtr:hasExpressionPhenotype', label='Adm')
    Calca = Phenotype('NCBIGene:12310', 'ilxtr:hasExpressionPhenotype', label='Calca')
    Chrm2 = Phenotype('NCBIGene:243764', 'ilxtr:hasExpressionPhenotype', label='Chrm2')
    Cnr1 = Phenotype('NCBIGene:12801', 'ilxtr:hasExpressionPhenotype', label='Cnr1')
    Cort = Phenotype('NCBIGene:12854', 'ilxtr:hasExpressionPhenotype', label='Cort')
    Cplx3 = Phenotype('NCBIGene:235415', 'ilxtr:hasExpressionPhenotype', label='Cplx3')
    Crh = Phenotype('NCBIGene:12918', 'ilxtr:hasExpressionPhenotype', label='Crh')
    Edn3 = Phenotype('NCBIGene:13616', 'ilxtr:hasExpressionPhenotype', label='Edn3')
    Htr3a = Phenotype('NCBIGene:15561', 'ilxtr:hasExpressionPhenotype', label='Htr3a')
    Igf1 = Phenotype('NCBIGene:16000', 'ilxtr:hasExpressionPhenotype', label='Igf1')
    Kcnmb2 = Phenotype('NCBIGene:72413', 'ilxtr:hasExpressionPhenotype', label='Kcnmb2')
    Nefh = Phenotype('NCBIGene:380684', 'ilxtr:hasExpressionPhenotype', label='Nefh')
    Nppc = Phenotype('NCBIGene:18159', 'ilxtr:hasExpressionPhenotype', label='Nppc')
    Oxtr = Phenotype('NCBIGene:18430', 'ilxtr:hasExpressionPhenotype', label='Oxtr')
    Penk = Phenotype('NCBIGene:18619', 'ilxtr:hasExpressionPhenotype', label='Penk')
    Pnoc = Phenotype('NCBIGene:18155', 'ilxtr:hasExpressionPhenotype', label='Pnoc')
    Syt6 = Phenotype('NCBIGene:54524', 'ilxtr:hasExpressionPhenotype', label='Syt6')
    Tac1 = Phenotype('NCBIGene:21333', 'ilxtr:hasExpressionPhenotype', label='Tac1')
    Tac2 = Phenotype('NCBIGene:21334', 'ilxtr:hasExpressionPhenotype', label='Tac2')
    Tacr1 = Phenotype('NCBIGene:21336', 'ilxtr:hasExpressionPhenotype', label='Tacr1')
    Trpc6 = Phenotype('NCBIGene:22068', 'ilxtr:hasExpressionPhenotype', label='Trpc6')
    Wnt5a = Phenotype('NCBIGene:22418', 'ilxtr:hasExpressionPhenotype', label='Wnt5a')

    # batch 2
    Adcy1 = Phenotype('NCBIGene:432530', 'ilxtr:hasExpressionPhenotype', label='Adcy1', override=True)
    Adcy2 = Phenotype('NCBIGene:210044', 'ilxtr:hasExpressionPhenotype', label='Adcy2', override=True)
    Adcy8 = Phenotype('NCBIGene:11514', 'ilxtr:hasExpressionPhenotype', label='Adcy8', override=True)
    Adcy9 = Phenotype('NCBIGene:11515', 'ilxtr:hasExpressionPhenotype', label='Adcy9', override=True)
    Adra1b = Phenotype('NCBIGene:11548', 'ilxtr:hasExpressionPhenotype', label='Adra1b', override=True)
    Arhgef10 = Phenotype('NCBIGene:234094', 'ilxtr:hasExpressionPhenotype', label='Arhgef10', override=True)
    Cckbr = Phenotype('NCBIGene:12426', 'ilxtr:hasExpressionPhenotype', label='Cckbr', override=True)
    Chrm3 = Phenotype('NCBIGene:12671', 'ilxtr:hasExpressionPhenotype', label='Chrm3', override=True)
    Chrna4 = Phenotype('NCBIGene:11438', 'ilxtr:hasExpressionPhenotype', label='Chrna4', override=True)
    Chst1 = Phenotype('NCBIGene:76969', 'ilxtr:hasExpressionPhenotype', label='Chst1', override=True)
    Cox6c = Phenotype('NCBIGene:12864', 'ilxtr:hasExpressionPhenotype', label='Cox6c', override=True)
    Cplx1 = Phenotype('NCBIGene:12889', 'ilxtr:hasExpressionPhenotype', label='Cplx1', override=True)
    Cplx2 = Phenotype('NCBIGene:12890', 'ilxtr:hasExpressionPhenotype', label='Cplx2', override=True)
    Esrrg = Phenotype('NCBIGene:26381', 'ilxtr:hasExpressionPhenotype', label='Esrrg', override=True)
    Fgf9 = Phenotype('NCBIGene:14180', 'ilxtr:hasExpressionPhenotype', label='Fgf9', override=True)
    Gpr88 = Phenotype('NCBIGene:64378', 'ilxtr:hasExpressionPhenotype', label='Gpr88', override=True)
    Grin3a = Phenotype('NCBIGene:242443', 'ilxtr:hasExpressionPhenotype', label='Grin3a', override=True)
    Hcrtr1 = Phenotype('NCBIGene:230777', 'ilxtr:hasExpressionPhenotype', label='Hcrtr1', override=True)
    Hs3st4 = Phenotype('NCBIGene:628779', 'ilxtr:hasExpressionPhenotype', label='Hs3st4', override=True)
    Hs6st3 = Phenotype('NCBIGene:50787', 'ilxtr:hasExpressionPhenotype', label='Hs6st3', override=True)
    Htr2c = Phenotype('NCBIGene:15560', 'ilxtr:hasExpressionPhenotype', label='Htr2c', override=True)
    Inhbb = Phenotype('NCBIGene:16324', 'ilxtr:hasExpressionPhenotype', label='Inhbb', override=True)
    Kcnmb4 = Phenotype('NCBIGene:58802', 'ilxtr:hasExpressionPhenotype', label='Kcnmb4', override=True)
    Mef2c = Phenotype('NCBIGene:17260', 'ilxtr:hasExpressionPhenotype', label='Mef2c', override=True)
    Npy1r = Phenotype('NCBIGene:18166', 'ilxtr:hasExpressionPhenotype', label='Npy1r', override=True)
    Npy2r = Phenotype('NCBIGene:18167', 'ilxtr:hasExpressionPhenotype', label='Npy2r', override=True)
    Nrtn = Phenotype('NCBIGene:18188', 'ilxtr:hasExpressionPhenotype', label='Nrtn', override=True)
    Opn3 = Phenotype('NCBIGene:13603', 'ilxtr:hasExpressionPhenotype', label='Opn3', override=True)
    Pde1a = Phenotype('NCBIGene:18573', 'ilxtr:hasExpressionPhenotype', label='Pde1a', override=True)
    Pde2a = Phenotype('NCBIGene:207728', 'ilxtr:hasExpressionPhenotype', label='Pde2a', override=True)
    Pde4b = Phenotype('NCBIGene:18578', 'ilxtr:hasExpressionPhenotype', label='Pde4b', override=True)
    Pde5a = Phenotype('NCBIGene:242202', 'ilxtr:hasExpressionPhenotype', label='Pde5a', override=True)
    Pde7b = Phenotype('NCBIGene:29863', 'ilxtr:hasExpressionPhenotype', label='Pde7b', override=True)
    Pde11a = Phenotype('NCBIGene:241489', 'ilxtr:hasExpressionPhenotype', label='Pde11a', override=True)
    Pparg = Phenotype('NCBIGene:19016', 'ilxtr:hasExpressionPhenotype', label='Pparg', override=True)
    Prkg1 = Phenotype('NCBIGene:19091', 'ilxtr:hasExpressionPhenotype', label='Prkg1', override=True)
    Prkg2 = Phenotype('NCBIGene:19092', 'ilxtr:hasExpressionPhenotype', label='Prkg2', override=True)
    Prok2 = Phenotype('NCBIGene:50501', 'ilxtr:hasExpressionPhenotype', label='Prok2', override=True)
    Pthlh = Phenotype('NCBIGene:19227', 'ilxtr:hasExpressionPhenotype', label='Pthlh', override=True)
    Ptn = Phenotype('NCBIGene:19242', 'ilxtr:hasExpressionPhenotype', label='Ptn', override=True)
    Rgs10 = Phenotype('NCBIGene:67865', 'ilxtr:hasExpressionPhenotype', label='Rgs10', override=True)
    Rgs12 = Phenotype('NCBIGene:71729', 'ilxtr:hasExpressionPhenotype', label='Rgs12', override=True)
    Rgs16 = Phenotype('NCBIGene:19734', 'ilxtr:hasExpressionPhenotype', label='Rgs16', override=True)
    Rgs8 = Phenotype('NCBIGene:67792', 'ilxtr:hasExpressionPhenotype', label='Rgs8', override=True)
    Rln1 = Phenotype('NCBIGene:19773', 'ilxtr:hasExpressionPhenotype', label='Rln1', override=True)
    Rspo1 = Phenotype('NCBIGene:192199', 'ilxtr:hasExpressionPhenotype', label='Rspo1', override=True)
    Slc7a3 = Phenotype('NCBIGene:11989', 'ilxtr:hasExpressionPhenotype', label='Slc7a3', override=True)
    Slit2 = Phenotype('NCBIGene:20563', 'ilxtr:hasExpressionPhenotype', label='Slit2', override=True)
    Slit3 = Phenotype('NCBIGene:20564', 'ilxtr:hasExpressionPhenotype', label='Slit3', override=True)
    Syt10 = Phenotype('NCBIGene:54526', 'ilxtr:hasExpressionPhenotype', label='Syt10', override=True)
    Syt1 = Phenotype('NCBIGene:20979', 'ilxtr:hasExpressionPhenotype', label='Syt1', override=True)
    Syt2 = Phenotype('NCBIGene:20980', 'ilxtr:hasExpressionPhenotype', label='Syt2', override=True)
    Syt4 = Phenotype('NCBIGene:20983', 'ilxtr:hasExpressionPhenotype', label='Syt4', override=True)
    Syt5 = Phenotype('NCBIGene:53420', 'ilxtr:hasExpressionPhenotype', label='Syt5', override=True)
    Syt7 = Phenotype('NCBIGene:54525', 'ilxtr:hasExpressionPhenotype', label='Syt7', override=True)
    Tgfb3 = Phenotype('NCBIGene:21809', 'ilxtr:hasExpressionPhenotype', label='Tgfb3', override=True)
    Trpc5 = Phenotype('NCBIGene:22067', 'ilxtr:hasExpressionPhenotype', label='Trpc5', override=True)
    Unc5a = Phenotype('NCBIGene:107448', 'ilxtr:hasExpressionPhenotype', label='Unc5a', override=True)
    Unc5b = Phenotype('NCBIGene:107449', 'ilxtr:hasExpressionPhenotype', label='Unc5b', override=True)
    Unc5d = Phenotype('NCBIGene:210801', 'ilxtr:hasExpressionPhenotype', label='Unc5d', override=True)
    Vamp1 = Phenotype('NCBIGene:22317', 'ilxtr:hasExpressionPhenotype', label='Vamp1', override=True)
    Vipr1 = Phenotype('NCBIGene:22354', 'ilxtr:hasExpressionPhenotype', label='Vipr1', override=True)
    Wnt2 = Phenotype('NCBIGene:22413', 'ilxtr:hasExpressionPhenotype', label='Wnt2', override=True)

    # batch 3
    GluA1 = Phenotype('NCBIGene:14799', 'ilxtr:hasExpressionPhenotype', label='Gira1', override=True)
    GluA4 = Phenotype('NCBIGene:14802', 'ilxtr:hasExpressionPhenotype', label='Gira4', override=True)
    Rab3a = Phenotype('NCBIGene:19339', 'ilxtr:hasExpressionPhenotype', label='Rab3a', override=True)
    Nsf = Phenotype('NCBIGene:18195', 'ilxtr:hasExpressionPhenotype', label='Nsf', override=True)  # was NSF in sup, but Nsf in paper
    Snap25 = Phenotype('NCBIGene:20614', 'ilxtr:hasExpressionPhenotype', label='Snap25', override=True)
    Rasl11b = Phenotype('NCBIGene:68939', 'ilxtr:hasExpressionPhenotype', label='Rasl11b', override=True)
    Rgs4 = Phenotype('NCBIGene:19736', 'ilxtr:hasExpressionPhenotype', label='Rgs4', override=True)
    Rgs6 = Phenotype('NCBIGene:50779', 'ilxtr:hasExpressionPhenotype', label='Rgs6', override=True)
    Rgs7 = Phenotype('NCBIGene:24012', 'ilxtr:hasExpressionPhenotype', label='Rgs7', override=True)
    Gucy1a3 = Phenotype('NCBIGene:60596', 'ilxtr:hasExpressionPhenotype', label='Gucy1a1', override=True)  # not entirely sure why 3 -> 1 but it is listed as an alternate
    Gucy1b3 = Phenotype('NCBIGene:54195', 'ilxtr:hasExpressionPhenotype', label='Gucy1b1', override=True)  # not entirely sure why 3 -> 1 but it is listed as an alternate
    α1GABAaR = Phenotype('NCBIGene:14394', 'ilxtr:hasExpressionPhenotype', label='Gabra1', override=True)
    α4GABAaR = Phenotype('NCBIGene:14397', 'ilxtr:hasExpressionPhenotype', label='Gabra4', override=True)
    δGABAaR = Phenotype('NCBIGene:14403', 'ilxtr:hasExpressionPhenotype', label='Gabrd', override=True)
    PGC1α = Phenotype('NCBIGene:19017', 'ilxtr:hasExpressionPhenotype', label='Ppargc1a', override=True)

    # stragglers
    Znt3 = Phenotype('NCBIGene:22784', 'ilxtr:hasExpressionPhenotype', label='Slc30a3', override=True)
    Zip1 = Phenotype('NCBIGene:194642', 'ilxtr:hasExpressionPhenotype', label='Slc39a1-ps', override=True)
    Rspn = Phenotype('NCBIGene:239405', 'ilxtr:hasExpressionPhenotype', label='Rspo2', override=True)  # NOTE THAT Rspn is not used ANYWHERE in the literature and is almost certainly a typo

    # peptides
    #Tac1 = Phenotype('ilxtr:Tac1', 'ilxtr:hasExpressionPhenotype')
    #Adm = Phenotype('ilxtr:Adm', 'ilxtr:hasExpressionPhenotype')

    # based on my reading of figure 6C and the random un lettered figure
    # between figure 6 D,B, and C, and the description of the R-spondin family
    # in the paper below, I am ruling that this is actually a reference to Rspo2
    # a reasonable guess at the gene symbol, but the 'din' wasn't what inspired
    # the short name, rather it was the 'spond'
    # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3496018/#S2title
    #Rspn = Phenotype('ilxtr:Rspn', 'ilxtr:hasExpressionPhenotype')  # FIXME this does not seem to exist

    PVBCPep = LogicalPhenotype(AND, Tac1, Adm, Rspn)

    #Pthlh = Phenotype('ilxtr:Pthlh', 'ilxtr:hasExpressionPhenotype')
    #Tgfb3 = Phenotype('ilxtr:Tgfb3', 'ilxtr:hasExpressionPhenotype')
    #Fgf9 = Phenotype('ilxtr:Fgf91', 'ilxtr:hasExpressionPhenotype')
    CHCPep = LogicalPhenotype(AND, Pthlh, Tgfb3, Fgf9) 

    #Igf1 = Phenotype('ilxtr:Igf1', 'ilxtr:hasExpressionPhenotype')
    #Edn3 = Phenotype('ilxtr:Edn3', 'ilxtr:hasExpressionPhenotype')
    #Prok2 = Phenotype('ilxtr:Prok2', 'ilxtr:hasExpressionPhenotype')
    #Pnoc = Phenotype('ilxtr:Pnoc', 'ilxtr:hasExpressionPhenotype')
    #Crh = Phenotype('ilxtr:Crh', 'ilxtr:hasExpressionPhenotype')
    #Tac2 = Phenotype('ilxtr:Tac2', 'ilxtr:hasExpressionPhenotype')
    CCKCPep = LogicalPhenotype(AND, Vip, Cck, Igf1, Edn3, Prok2, Pnoc, Crh, Tac2)

    #Inhbb = Phenotype('ilxtr:Inhbb', 'ilxtr:hasExpressionPhenotype')
    #Nppc = Phenotype('ilxtr:Nppc', 'ilxtr:hasExpressionPhenotype')
    MNCPep = LogicalPhenotype(AND, Sst, Inhbb, Nppc)

    #Rspo1 = Phenotype('ilxtr:Rspo1', 'ilxtr:hasExpressionPhenotype')
    #Wnt5a = Phenotype('ilxtr:Wnt5aae1', 'ilxtr:hasExpressionPhenotype')
    #Nrtn = Phenotype('ilxtr:Nrtn', 'ilxtr:hasExpressionPhenotype')
    ISCPep = LogicalPhenotype(AND, Vip, Cck, Rspo1, Wnt5a, Nrtn)

    #Ptn = Phenotype('ilxtr:Ptn', 'ilxtr:hasExpressionPhenotype')
    #Wnt2 = Phenotype('ilxtr:Wnt2', 'ilxtr:hasExpressionPhenotype')
    #Rln1 = Phenotype('ilxtr:Rln1', 'ilxtr:hasExpressionPhenotype')
    #Penk = Phenotype('ilxtr:Penk', 'ilxtr:hasExpressionPhenotype')
    #Calca = Phenotype('ilxtr:Calca', 'ilxtr:hasExpressionPhenotype')
    #Cort = Phenotype('ilxtr:Cort', 'ilxtr:hasExpressionPhenotype')
    LPCPep = LogicalPhenotype(AND, Ptn, Wnt2, Rln1, Penk, Calca, Cort)

    # dendrites
    #GluA1 = Phenotype('ilxtr:GluA1', 'ilxtr:hasExpressionPhenotype')   # Gira1 NCBIGene:14799
    #GluA4 = Phenotype('ilxtr:GluA4', 'ilxtr:hasExpressionPhenotype')   # Gira4 NCBIGene:14802
    #α1GABAaR = Phenotype('ilxtr:α1GABAaR', 'ilxtr:hasExpressionPhenotype')  # Gabra1 NCBIGene:14394
    Kv3 = Phenotype('ilxtr:Kv3', 'ilxtr:hasExpressionPhenotype')
    #α4GABAaR = Phenotype('ilxtr:α4GABAaR', 'ilxtr:hasExpressionPhenotype')  # Gabra4 NCBIGene:14397
    #δGABAaR = Phenotype('ilxtr:δGABAaR', 'ilxtr:hasExpressionPhenotype')  # Gabrd NCBIGene:14403
    #Cckbr = Phenotype('ilxtr:Cckbr', 'ilxtr:hasExpressionPhenotype')
    PVBCDend = LogicalPhenotype(AND, GluA1, GluA4, α1GABAaR, Kv3, α4GABAaR, δGABAaR, Cckbr)

    # TODO LOWER
    Lower = Phenotype('ilxtr:LowerExpression', 'ilxtr:hasPhenotypeModifier')
    Higher = Phenotype('ilxtr:HigherExpression', 'ilxtr:hasPhenotypeModifier')
    CHCDend = LogicalPhenotype(AND,
                               GluA1, GluA4, α1GABAaR, Kv3,
                               α4GABAaR, δGABAaR, Cckbr,
                               Lower) # FIXME bad model it is not the intersection of the
                                      # restrictions it is a restriction on the intersection
                                      # of the objects

    #Cnr1 = Phenotype('ilxtr:Cnr1', 'ilxtr:hasExpressionPhenotype')
    #Htr2c = Phenotype('ilxtr:Htr2c', 'ilxtr:hasExpressionPhenotype')
    #Htr3a = Phenotype('ilxtr:Htr3a', 'ilxtr:hasExpressionPhenotype')
    #Chrm3 = Phenotype('ilxtr:Chrm3', 'ilxtr:hasExpressionPhenotype')
    #Npy1r = Phenotype('ilxtr:Npy1r', 'ilxtr:hasExpressionPhenotype')
    #Vipr1 = Phenotype('ilxtr:Vipr1', 'ilxtr:hasExpressionPhenotype')
    CCKCDend = LogicalPhenotype(AND, Cnr1, Htr2c, Htr3a, Chrm3, Npy1r, Vipr1)

    # high level diverse iGluRs
    # low level few types GABAaRs
    # FIXME the helper graph is not included for query at the moment so label gen has bad values
    _GLUR = Phenotype('ilxtr:glutamateReceptor', 'ilxtr:hasExpressionPhenotype', label='GluR', override=True)
    _GABAR = Phenotype('ilxtr:GABAReceptor', 'ilxtr:hasExpressionPhenotype', label='GABAR', override=True)
    # need a clear statement for how to handle cases like this
    # can the current python implementation handle this?
    MNCDend = LogicalPhenotype(AND,
                     LogicalPhenotype(AND, _GABAR, Lower),
                     # intersectionOf(ilxtr.GABAReceptor, ilxtr.LowerExpression)
                     LogicalPhenotype(AND, _GLUR, Higher))
    #Chrna4 = Phenotype('ilxtr:Chrna4', 'ilxtr:hasExpressionPhenotype')
    #Adra1b = Phenotype('ilxtr:Adra1b', 'ilxtr:hasExpressionPhenotype')
    #Npy2r = Phenotype('ilxtr:Npy2r', 'ilxtr:hasExpressionPhenotype')
    ISCDend = LogicalPhenotype(AND, Htr2c, Htr3a, Chrm3, Chrna4, Adra1b, Npy2r)

    #Chrm2 = Phenotype('ilxtr:Chrm2', 'ilxtr:hasExpressionPhenotype')
    #Gpr88 = Phenotype('ilxtr:Gpr88', 'ilxtr:hasExpressionPhenotype')
    #Oxtr = Phenotype('ilxtr:Oxtr', 'ilxtr:hasExpressionPhenotype')
    #Tacr1 = Phenotype('ilxtr:Tacr1', 'ilxtr:hasExpressionPhenotype')
    #Hcrtr1 = Phenotype('ilxtr:Hcrtr1', 'ilxtr:hasExpressionPhenotype')
    #Opn3 = Phenotype('ilxtr:Opn3', 'ilxtr:hasExpressionPhenotype')
    # low unusual ??? check 4 H and enumerate all the instances of 'unusual'
    LPCDend = LogicalPhenotype(AND, Chrm2, Gpr88, Oxtr, Tacr1, Hcrtr1, Opn3)

    # encode the negative phenotypes 6 C, 6 has lots of useful information
    # specifically with regard to how to encode a thresholded negative phenotype

    # ilxtr:hasSynapticPhenotype
    #FastEPSP = Phenotype('ilxtr:FastEPSP', 'ilxtr:hasElectrophysiologicalPhenotype')

    # signaling
    #Rgs4 = Phenotype('ilxtr:Rgs4', 'ilxtr:hasExpressionPhenotype')  # ERRATA NOTE in s7 this is RGS4 but is referred to as Rgs4 in the paper itself
    #Adcy8 = Phenotype('ilxtr:Adcy8', 'ilxtr:hasExpressionPhenotype')
    #Adcy1 = Phenotype('ilxtr:Adcy1', 'ilxtr:hasExpressionPhenotype')
    #Rasl11b = Phenotype('ilxtr:Rasl11b', 'ilxtr:hasExpressionPhenotype')  # ERRATA NOTE There is a typo in table s7 where this is Ras111b
    #Arhgef10 = Phenotype('ilxtr:Arhgef10', 'ilxtr:hasExpressionPhenotype')
    PVBCSig = LogicalPhenotype(AND, Rgs4, Adcy8, Adcy1, Rasl11b, Arhgef10)

    #Gucy1a3 = Phenotype('ilxtr:Gucy1a3', 'ilxtr:hasExpressionPhenotype')  # NCBIGene:60596 Gucy1a1
    #Gucy1b3 = Phenotype('ilxtr:Gucy1b3', 'ilxtr:hasExpressionPhenotype')  # NCBIGene:54195 Gucy1b1
    #Prkg1 = Phenotype('ilxtr:Prkg1', 'ilxtr:hasExpressionPhenotype')
    #Pde11a = Phenotype('ilxtr:Pde11a', 'ilxtr:hasExpressionPhenotype')
    #Pde5a = Phenotype('ilxtr:Pde5a', 'ilxtr:hasExpressionPhenotype')
    #Trpc5 = Phenotype('ilxtr:Trpc5', 'ilxtr:hasExpressionPhenotype')
    #Kcnmb2 = Phenotype('ilxtr:Kcnmb2', 'ilxtr:hasExpressionPhenotype')
    CHCSig = LogicalPhenotype(AND, Gucy1a3, Gucy1b3, Prkg1, Pde11a, Pde5a, Trpc5, Kcnmb2)
    #Rgs12 = Phenotype('ilxtr:Rgs12', 'ilxtr:hasExpressionPhenotype')
    #Adcy9 = Phenotype('ilxtr:Adcy9', 'ilxtr:hasExpressionPhenotype')
    #Pde7b = Phenotype('ilxtr:Pde7b', 'ilxtr:hasExpressionPhenotype')
    CCKCSig = LogicalPhenotype(AND, Rgs12, Adcy9, Pde7b)
    #Rgs6 = Phenotype('ilxtr:Rgs6', 'ilxtr:hasExpressionPhenotype')  # ERRATA NOTE in s7 this is RGS6 but is referred to as Rgs6 in the paper itself
    #Rgs7 = Phenotype('ilxtr:Rgs7', 'ilxtr:hasExpressionPhenotype')  # ERRATA NOTE in s7 this is RGS7 but is referred to as Rgs7 in the paper itself
    #Adcy2 = Phenotype('ilxtr:Adcy2', 'ilxtr:hasExpressionPhenotype')
    #Pde2a = Phenotype('ilxtr:Pde2a', 'ilxtr:hasExpressionPhenotype')
    MNCSig = LogicalPhenotype(AND, Rgs6, Rgs7, Adcy2, Pde2a)
    #Rgs16 = Phenotype('ilxtr:Rgs16', 'ilxtr:hasExpressionPhenotype')
    #Rgs10 = Phenotype('ilxtr:Rgs10', 'ilxtr:hasExpressionPhenotype')
    #Rgs8 = Phenotype('ilxtr:Rgs8', 'ilxtr:hasExpressionPhenotype')
    #Pde4b = Phenotype('ilxtr:Pde4b', 'ilxtr:hasExpressionPhenotype')
    ISCSig = LogicalPhenotype(AND, Rgs16, Rgs10, Rgs8, Pde4b)
    #Slc7a3 = Phenotype('ilxtr:Slc7a3', 'ilxtr:hasExpressionPhenotype')
    #Gucy1a3 = Phenotype('ilxtr:Gucy1a3', 'ilxtr:hasExpressionPhenotype')
    #Gucy1b3 = Phenotype('ilxtr:Gucy1b3', 'ilxtr:hasExpressionPhenotype')
    #Prkg2 = Phenotype('ilxtr:Prkg2', 'ilxtr:hasExpressionPhenotype')
    #Pde1a = Phenotype('ilxtr:Pde1a', 'ilxtr:hasExpressionPhenotype')
    #Trpc6 = Phenotype('ilxtr:Trpc6', 'ilxtr:hasExpressionPhenotype')
    #Kcnmb4 = Phenotype('ilxtr:Kcnmb4', 'ilxtr:hasExpressionPhenotype')
    LPCSig = LogicalPhenotype(AND, Slc7a3, Nos1, Gucy1a3, Gucy1b3, Prkg2, Pde1a, Trpc6, Kcnmb4)

    # axons
    Nav1_1 = Phenotype('ilxtr:Nav1_1', 'ilxtr:hasExpressionPhenotype')
    Nav1_6 = Phenotype('ilxtr:Nav1_6', 'ilxtr:hasExpressionPhenotype')
    Nav1_7 = Phenotype('ilxtr:Nav1_7', 'ilxtr:hasExpressionPhenotype')
    Cav2_1_P_Q = Phenotype('ilxtr:Cav2_1_P_Q', 'ilxtr:hasExpressionPhenotype')
    #Syt2 = Phenotype('ilxtr:Syt2', 'ilxtr:hasExpressionPhenotype')
    #Syt7 = Phenotype('ilxtr:Syt7', 'ilxtr:hasExpressionPhenotype')
    #Vamp1 = Phenotype('ilxtr:Vamp1', 'ilxtr:hasExpressionPhenotype')
    #Cplx1 = Phenotype('ilxtr:Cplx1', 'ilxtr:hasExpressionPhenotype')
    # FIXME listed as PV but probably means Pvalb?
    #high Snap25, Rab3a, NSF
    PVBCAxon = LogicalPhenotype(AND,
                                LogicalPhenotype(AND, Nav1_1, Nav1_6, Nav1_7, Cav2_1_P_Q,
                                                 Pvalb, Syt2, Syt7, Vamp1, Cplx1),
                                LogicalPhenotype(AND,
                                                 Snap25,
                                                 Rab3a,
                                                 Nsf,
                                                 Higher))
    # lower Vamp1, Cplx1, Syt1, Syt2, Syt7 vs PVBC, probably want to encode the comparator expicitly
    # NOT generally
    # high Snap25, Rab3a, NSF
    TODO = Phenotype(ilxtr.to, ilxtr.hasPhenotype)
    CHCAxon = LogicalPhenotype(AND,
                               LogicalPhenotype(AND,
                                                Vamp1,
                                                Cplx1,
                                                Syt1,
                                                Syt2,
                                                Syt7,
                                                Lower),
                               LogicalPhenotype(AND,
                                                Snap25,
                                                Rab3a,
                                                Nsf,
                                                Higher))
    #Cplx2 = Phenotype('ilxtr:Cplx2', 'ilxtr:hasExpressionPhenotype')
    #Cplx3 = Phenotype('ilxtr:Cplx3', 'ilxtr:hasExpressionPhenotype')
    #LDCV = Phenotype('ilxtr:LargeDenseCoreVesicleRelease', 'ilxtr:hasSynapticPhenotype')
    #Syt10 = Phenotype('ilxtr:Syt10', 'ilxtr:hasExpressionPhenotype')
    CCKCAxon = LogicalPhenotype(AND, Cplx2, Cplx3, Syt10)
    #Znt3 = Phenotype('ilxtr:Znt3', 'ilxtr:hasExpressionPhenotype')
    #Zip1 = Phenotype('ilxtr:Zip1', 'ilxtr:hasExpressionPhenotype')
    MNCAxon = LogicalPhenotype(AND, Znt3, Zip1)  # FIXME why does he have the names out front?
    ISCAxon = LogicalPhenotype(AND, *CCKCAxon.pes, Phenotype(ilxtr.similarTo, ilxtr.hasPhenotypeModifier))  # FIXME similar
    #Syt4 = Phenotype('ilxtr:Syt4', 'ilxtr:hasExpressionPhenotype')
    #Syt5 = Phenotype('ilxtr:Syt5', 'ilxtr:hasExpressionPhenotype')
    #Syt6 = Phenotype('ilxtr:Syt6', 'ilxtr:hasExpressionPhenotype')
    LPCAxon = LogicalPhenotype(AND, Syt4, Syt5, Syt6)

    # other
    #PGC1α = Phenotype('ilxtr:PGC1α', 'ilxtr:hasExpressionPhenotype')
    #Esrrg = Phenotype('ilxtr:Esrrg', 'ilxtr:hasExpressionPhenotype')
    #Mef2c = Phenotype('ilxtr:Mef2c', 'ilxtr:hasExpressionPhenotype')
    #Pparg = Phenotype('ilxtr:Pparg', 'ilxtr:hasExpressionPhenotype')
    #Cox6c = Phenotype('ilxtr:Cox6c', 'ilxtr:hasExpressionPhenotype')
    #Nefh = Phenotype('ilxtr:Nefh', 'ilxtr:hasExpressionPhenotype')
    #Slit2 = Phenotype('ilxtr:Slit2', 'ilxtr:hasExpressionPhenotype')
    #Slit3 = Phenotype('ilxtr:Slit3', 'ilxtr:hasExpressionPhenotype')
    PVBCOther = LogicalPhenotype(AND, PGC1α, Esrrg, Mef2c, Pparg, Cox6c, Nefh, Slit2, Slit3)
    #Unc5b = Phenotype('ilxtr:Unc5b', 'ilxtr:hasExpressionPhenotype')
    #Hs3st4 = Phenotype('ilxtr:Hs3st4', 'ilxtr:hasExpressionPhenotype')
    CHCOther = LogicalPhenotype(AND, Unc5b, Hs3st4)
    #Hs6st3 = Phenotype('ilxtr:Hs6st3', 'ilxtr:hasExpressionPhenotype')
    CCKCOther = LogicalPhenotype(AND, Hs6st3)
    #Grin3a = Phenotype('ilxtr:Grin3a', 'ilxtr:hasExpressionPhenotype')
    MNCOther = LogicalPhenotype(AND, Grin3a)
    #Unc5a = Phenotype('ilxtr:Unc5a', 'ilxtr:hasExpressionPhenotype')
    #Chst1 = Phenotype('ilxtr:Chst1', 'ilxtr:hasExpressionPhenotype')
    ISCOther = LogicalPhenotype(AND, Unc5a, Chst1)
    #Ptn = Phenotype('ilxtr:Ptn', 'ilxtr:hasExpressionPhenotype')
    #Unc5d = Phenotype('ilxtr:Unc5d', 'ilxtr:hasExpressionPhenotype')
    LPCOther = LogicalPhenotype(AND, Ptn, Unc5d)


class Huang2017(Genes, Species):
    Neocortex = Phenotype('UBERON:0001950', 'ilxtr:hasSomaLocatedIn')
    GABA = Phenotype('CHEBI:16865', 'ilxtr:hasNeurotransmitterPhenotype')
    Basket = Phenotype('ilxtr:BasketPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    Martinotti = Phenotype('ilxtr:MartinottiPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    Chandelier = Phenotype('ilxtr:ChandelierPhenotype', 'ilxtr:hasMorphologicalPhenotype')
    Projection = Phenotype('ilxtr:ProjectionPhenotype', 'ilxtr:hasCircuitRolePhenotype')
    Interneuron = Phenotype('ilxtr:IntrinsicPhenotype', 'ilxtr:hasCircuitRolePhenotype')
    OnToInter = Phenotype('NLXCELL:1003113', 'ilxtr:hasForwardConnectionPhenotype')


with Huang2017:
    with Neuron_(Mouse, Neocortex, GABA, id_=gid(58)) as context:
        #context.subClassOf(ilxtr.huang2017)
        # TODO add the names assigned here as abbrevs somehow

        #fig1b
        # FIXME is approach to disjointness VS adding negative phenotypes
        ns = Neuron(Sst, id_=gid(56))
        nh = Neuron(Htr3a, id_=gid(53))
        Neuron(Pvalb, id_=gid(55)).disjointWith(ns, nh)
        #Neuron(Pvalb).equivalentClass(Neuron(NegPhenotype(Sst)), Neuron(NegPhenotype(Htr3a)))
        # FIXME for some reason the NegPhenotype neurons above fail to be added to the graph!??!
        #a = Neuron(NegPhenotype(Sst))
        #b = Neuron(NegPhenotype(Htr3a))
        #Neuron(Pvalb).equivalentClass(a, b)
        ns.disjointWith(nh)
        nv = Neuron(Vip, id_=gid(57))
        nv.subClassOf(nh)
        nk = Neuron(Cck, id_=gid(52))
        nk.subClassOf(nh)

        nn = Neuron(Nos1, id_=gid(54))
        nb = Neuron(Calb2, id_=gid(50))
        Neuron(Nkx2_1, id_=gid(46)).disjointWith(nn, nh, nb)
        nn.disjointWith(nh, nb)

        Neuron(Vip, Cck, id_=gid(51))
        Neuron(Vip, Calb2, Cck, id_=gid(47))
        Neuron(Vip, Calb2, id_=gid(49))
        Neuron(Sst, Calb2, id_=gid(48))

        # NOTE fig1a and fig1b are subtly different and the driver lines are described as
        # marking a superset of neurons that includes these 6 types "and likely other types"
        # distinct from these 6 for this reason the morphology of the neurons is included
        Inter = Interneuron
        f = lambda *args, label=None, override=None, id_=None: (
            args, dict(label=label, override=override, id_=id_))
        fig1a = dict(
        PVBC = f(Basket,     Inter, PV,        label='PVBC cortical neuron', override=False, id_=gid(43)),
        CHC =  f(Chandelier, Inter, Nkx2_1,    label='CHC cortical neuron', override=False, id_=gid(44)),
        CCKC = f(Basket,     Inter, VIP, CCK,  label='CCKC cortical neuron', override=False, id_=gid(40)),
        MNC =  f(Martinotti, Inter, SST, CR,   label='MNC cortical neuron', override=False, id_=gid(42)),
        ISC =  f(OnToInter,  Inter, VIP, CR,   label='ISC cortical neuron', override=False, id_=gid(41)),
        LPC =  f(Projection,        SST, NOS1, label='LPC cortical neuron', override=False, id_=gid(45)),
        )

        f7 = dict(
        equivs =    (PVBCEq, CHCEq, CCKCEq, MNCEq, ISCEq, LPCEq),
        peptides =  (PVBCPep, CHCPep, CCKCPep, MNCPep, ISCPep, LPCPep),
        signaling = (PVBCSig, CHCSig, CCKCSig, MNCSig, ISCSig, LPCSig),
        dendrite =  (PVBCDend, CHCDend, CCKCDend, MNCDend, ISCDend, LPCDend),
        axon =      (PVBCAxon, CHCAxon, CCKCAxon, MNCAxon, ISCAxon, LPCAxon),
        other =     (PVBCOther, CHCOther, CCKCOther, MNCOther, ISCOther, LPCOther))

        figs7 = {type:Neuron(LogicalPhenotype(AND, *(pe for p in phenos for pe in p.pes)), *args, **kwargs
                            )#label=f'{type} molecular types neuron', override=True)
                 # the zip below packs all PVBC with PVBC, all CHC, etc.
                 #for type, *phenos in zip(fig1a, fig1a.values(), *f7.values())}
                 for (type, (args, kwargs)), *phenos in zip(fig1a.items(), *f7.values())}

        #for k, v in fig1a.items():
            # ISC is in fact corrctly classified as a subClassOf +Cck neurons
            # which is consistent with the overlap between CR and CCK in fig1b
            # some _subset_ of those have cck, but it is not clear how many and
            # if fig s7 columns are interpreted as equivalent to the fig1b as
            # we do here, then the only question is whether the ISC -Cck subset
            # has any additional distinguishing features CCKC doesn't have Calb2
            # on the list, but fig1b suggests that some might
            #figs7[k].equivalentClass(v)  # TODO asserted by Josh Huang in figure s7

        if extra:
            peps = [Neuron(*p.pes, label=f'{l} peptides neuron', override=False)
                    for l, p in zip(fig1a, f7['peptides'])]
            sigs = [Neuron(*p.pes, label=f'{l} signaling neuron', override=False)
                    for l, p in zip(fig1a, f7['signaling'])]
            # asserted by Tom Gillespie interpreting Huang
            [p.equivalentClass(s) for p, s in zip(peps, sigs)]
            # assert that the peptide markers are disjoint
        else:
            peps = []
            sigs = []

        # assert disjointness between top level types based on +fig1a+ figs7 sigh
        for dis in (peps, sigs, tuple(figs7.values())):
            for i, n in enumerate(dis[:-1]):
                for on in dis[i+1:]:
                    n.disjointWith(on)
        #LPCbyPepties = Neuron(*LPCPep.pes)


for n, p in Huang2017.items():
    if isinstance(p, Phenotype) and not n.startswith('_'):
        # FIXME rdflib allows instances but tests type so OntId can go in, but won't ever match
        ident = OntId(p.p)
        if n in Genes.__dict__:
            o = rdflib.Literal(n) if not hasattr(p, '_label') else rdflib.Literal(p._label)
            lt = (rdflib.URIRef(ident), rdfs.label, o)
            Neuron.core_graph.add(lt)
            if ident.prefix != 'NCBIGene':
                Neuron.out_graph.add(lt)  # FIXME maybe a helper graph?

            if ident.prefix == 'JAX':
                sct = (rdflib.URIRef(ident), rdfs.subClassOf, ilxtr.transgenicLine)
                Neuron.core_graph.add(sct)
                Neuron.out_graph.add(sct)
            elif ident.prefix == 'ilxtr':# or ident.prefix == 'NCBIGene':  # FIXME NCBIGene temp fix ...
                if ident.suffix in ('LowerExpression', 'HigherExpression', 'to'):
                    continue
                sct = (rdflib.URIRef(ident), rdfs.subClassOf, ilxtr.gene)
                Neuron.core_graph.add(sct)
                Neuron.out_graph.add(sct)
        else:
            lt = (rdflib.URIRef(ident), rdfs.label, rdflib.Literal(OntTerm(ident).label))
            Neuron.core_graph.add(lt)
            Neuron.out_graph.add(lt)  # FIXME maybe a helper graph?

Neuron.out_graph.add((ilxtr.gene, owl.equivalentClass, OntId('SO:0000704').u))
Neuron.out_graph.add((NeuronHuang2017.owlClass,
                      ilxtr.modelSource,
                      OntId('https://doi.org/10.1016/j.cell.2017.08.032').u))

with Huang2017:
    Neuron.write()
    Neuron.write_python()


def wrap_query(l):
    # FIXME evil hack to work around bad ontquery implementation decision
    try:
        res_gen = OntTerm.query(label=l.toPython())
        for res in res_gen:
            yield res
    except NotImplementedError:
        pass


res = [r for s, l in Neuron.out_graph[:rdfs.label:] if
       OntTerm(s).curie.startswith('ilxtr:')
       for r in wrap_query(l) if
       r is not None and r.curie.startswith('ilxtr:')]
mapped = [r for s, l in Neuron.out_graph[:rdfs.label:] if
          OntTerm(s).curie.startswith('ilxtr:')
          for r in wrap_query(l) if
          r is not None and not r.curie.startswith('ilxtr:')]


def ncbigene():
    from nifstd_tools.utils import ncbigenemapping

    asdf = {n:[qr.OntTerm.asPhenotype()
            for qr in OntTerm.query(term=n, prefix='NCBIGene')]
            for n, p in Genes.items()
            if not isinstance(p, LogicalPhenotype) and OntId(p.p).prefix != 'NCBIGene'}           
    may_need_ncbigene_added = [n for n, p in asdf.items() if not p]

    mapping, to_add, errors = ncbigenemapping(may_need_ncbigene_added)

    if asdf is not None:
        replace = [print(n, '=', repr(p[0])) for n, p in asdf.items()
                if p and p[0].pLabel.toPython() == n]

    breakpoint()


def main():
    #breakpoint()
    pass


if __name__ == '__main__':
    main()
