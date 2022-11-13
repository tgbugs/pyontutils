#!/usr/bin/env python3
import rdflib
from pyontutils.namespaces import ilxtr, rdfs
from neurondm.core import LocalNameManager
from neurondm.lang import Phenotype, EntailedPhenotype, Neuron, NeuronEBM, Config

slp = 'ilxtr:hasSomaLocatedIn'
sllp = 'ilxtr:hasSomaLocatedInLayer'
alp = 'ilxtr:hasAxonLocatedIn'
dlp = 'ilxtr:hasDendriteLocatedIn'
synp = 'ilxtr:hasAxonPresynapticElementIn'
snsp = 'ilxtr:hasDendriteSensorySubcellularElementIn'  # XXX new, kind of like axon terminal but for dendrites

fconp = 'ilxtr:hasForwardConnectionPhenotype'

ntkb = rdflib.Namespace(ilxtr[''] + 'neuron-type-keast-')
ntku = rdflib.Namespace(ilxtr[''] + 'neuron-type-keast-unbranched-')
ntkh = rdflib.Namespace(ilxtr[''] + 'neuron-type-helper-keast-')
npkb = rdflib.Namespace(ilxtr[''] + 'neuron-phenotype-keast-')


class NeuronKeast2020(Neuron):  # FIXME should be an EBM but something is a bit off
    owlClass = 'ilxtr:NeuronKeast2020'
    shortname = 'Keast2020'


kNeuron = NeuronKeast2020


def ambig(name):
    return f'{name} (kblad)'


labels = {
1: ambig('pelvic ganglion parasympathetic neuron'),
2: ambig('pelvic ganglion sympathetic neuron'),
3: ambig('inferior mesenteric ganglion neuron'),
4: ambig('sympathetic chain ganglion neuron'),
5: ambig('parasympathetic spinal preganglionic neuron'),
6: ambig('sympathetic preganglionic neuron innervating pelvic ganglion neuron'),
7: ambig('sympathetic preganglionic neuron innervating inferior mesenteric ganglion neuron'),
8: ambig('sympathetic preganglionic neuron innervating sympathetic chain ganglion neuron'),
9: 'urethral rhabdosphincter motor neuron',
10: 'L6-S1 sensory neuron innervating bladder',
11: 'L1-L2 sensory neuron innervating bladder',
12: 'sensory neuron innervating urethral rhabdosphincter',}


def kl(n):
    if n in labels:
        return labels[n]

    return f'Neuron population {n} of the Keast bladder model'


def kd(n):
    return ('The neuron type corresponding to all the members of '
            f'neuron population {n} from the keast bladder model.')


def kld(n):
    return {'label': kl(n),
            'definition': kd(n),}

def needs_keast_namespace(config):
    """ define neurons for keast spinal """

    plut = {v:k for k, v in Keast2020.items()}
    def fn(phen):
        return plut[phen]

    # define the inferred parents for neuron populations
    for n in (2, 4, 5, 6, 7, 8, 9, 10, 11, 12):
        NeuronKeast2020(Keast2020[f'ntk_{n}'], id_=ntkb[str(n)], **kld(n))
        # FIXME hack
        config.out_graph.add((npkb[str(n)], rdfs.subClassOf, ilxtr.Phenotype))

    # FIXME spinal cord white matter axons are missing from these bags

    # neuron populations
    neuron_1 = [kNeuron(PG, n_bl, BDWsyn, BNWsyn, para, post, id_=ntkb['1'], **kld(1))]  # pos
    neuron_2 = [kNeuron(PG, n_bl, synloc, sym, post, ntk_2_ent, id_=ntku[f'2-{fn(synloc)}'])
                for synloc in (BDWsyn, BNWsyn)]  # sos # FIXME smooth muslce only
    neuron_3 = [kNeuron(IMG, BDWsyn, BNWsyn, sym, post, id_=ntkb['3'], **kld(3))]  # sos # FIXME smooth muscle only

    neuron_4 = []  # sos
    with Neuron(n_ps, PGax, n_bl, sym, post, id_=ntkh['common-4']):
        for soma_location_id in four_soma_locs:
            somaloc = Phenotype(soma_location_id, slp)
            for exits_via in ((L6_gr,), (S1ax, S1_gr,)):
                for synapses_on in (BNVWsyn, BDVWsyn):
                    # 4
                    n4 = kNeuron(
                        somaloc, *exits_via, synapses_on, ntk_4_ent,
                        id_=ntku[f'4-{fn(somaloc)}-{fn(exits_via[0])}-{fn(synapses_on)}'])
                    neuron_4.append(n4)

    neuron_5 = []  # pre
    with Neuron(VII, n_ps, PGax, PGsyn, ntk_1_fcon, para, pre,
                id_=ntkh['common-5']):
        for somaloc, ventral_root_exit in zip((L6,    S1),
                                              (L6_vr, S1_vr)):
            n5 = kNeuron(somaloc, ventral_root_exit, ntk_5_ent,
                         id_=ntku[f'5-{fn(somaloc)}'])
            neuron_5.append(n5)

    common = {L1: (L1_vr, L1_wr),
              L2: (L2_vr, L2_wr),}
    common67 = {L1: (L1_gr,),
                L2: (L2_gr,),}

    neuron_6 = []  # sre
    neuron_7 = []  # sre
    neuron_8 = []  # sre
    with Neuron(VII, WMax, sos_fcon, sym, pre,
                id_=ntkh['common-6-7-8']):
        for i, somaloc in enumerate((L1, L2)):
            soma_index = i + 2  # L1 aligns to the 3rd the sypathetic ganglion
            # which is of course the L1 sypathetic ganglion, but it is
            # the 3rd ganlion in the model with a neuron 4 soma
            with Neuron(somaloc, *common[somaloc], id_=ntkh[f'common-6-7-8-{fn(somaloc)}']):
                with Neuron(n_ls, *common67[somaloc], id_=ntkh[f'common-6-7-{fn(somaloc)}-extra']):
                    # 6
                    n6 = kNeuron(IMGax, n_hg, PGsyn, ntk_6_ent, ntk_2_fcon,
                                 id_=ntku[f'6-{fn(somaloc)}'])
                    neuron_6.append(n6)
                    # 7
                    n7 = kNeuron(IMGsyn, ntk_7_ent, ntk_3_fcon,
                                 id_=ntku[f'7-{fn(somaloc)}'])
                    neuron_7.append(n7)

                # 8
                for syn_index, synloc in enumerate(four_soma_locs):
                    axons_in = syn_chain_axons_in(syn_index, soma_index)
                    syn = Phenotype(synloc, synp)
                    n8 = kNeuron(syn, *axons_in, ntk_8_ent, ntk_4_fcon,
                                 id_=ntku[f'8-{fn(somaloc)}-{fn(syn)}'])
                    neuron_8.append(n8)

    neuron_9 = []  # slm
    with Neuron(IX, WMax, n_pu, URTsyn, motor, id_=ntkh['common-9']):
        for somaloc, ventral_root_exit in zip((L5,    L6),
                                              (L5_vr, L6_vr)):
            n9 = kNeuron(somaloc, ventral_root_exit, ntk_9_ent, id_=ntku[f'9-{fn(somaloc)}'])
            neuron_9.append(n9)

    neuron_10 = []  # fos
    neuron_11 = []  # fos
    neuron_12 = []  # fos
    with Neuron(Isyn, IIsyn, Vsyn, VIIsyn, Xsyn, sens,
                id_=ntkh['common-10-11-12']):  # 10 11 12 XXX layers are wrong, intersection has to come before phenotype
        for somaloc in (L6_dr, S1_dr):
            n10 = kNeuron(somaloc, n_ps_dn, PGdn, n_bl_dn, ntk_10_ent,
                          id_=ntku[f'10-{fn(somaloc)}'])  # TODO a bunch of other sensory terminals
            neuron_10.append(n10)

            n12 = kNeuron(somaloc, n_pu_dn, URTdn, ntk_12_ent,
                          id_=ntku[f'12-{fn(somaloc)}'])  # TODO URTdn layer is rhabdosphincter
            neuron_12.append(n12)

        for somaloc in (L1_dr, L2_dr):
            n11 = kNeuron(somaloc, n_ls_dn, IMGdn, n_hg_dn, PGdn, n_bl_dn, ntk_11_ent,
                          id_=ntku[f'11-{fn(somaloc)}'])  # TODO bladder and layers
            neuron_11.append(n11)

    # thankfully alphabetical from head to toe
    with Neuron(pons_ax, id_=ntkh['axon-pons']):
        with Neuron(midbrain_ax, id_=ntkh['axon-midbrain']):
            with Neuron(dienc_ax, id_=ntkh['axon-dienceph']):
                with Neuron(cn_ax, id_=ntkh['axon-cernuc']):
                    neuron_13 = [kNeuron(BNST, BRGTNsyn, id_=ntkb['13'], **kld(13))]  # soma in BNST   ???
                    neuron_14 = [kNeuron(CeA, BRGTNsyn, id_=ntkb['14'], **kld(14))]   # soma in CeA    ???
                neuron_15 = [kNeuron(MPOA, BRGTNsyn, id_=ntkb['15'], **kld(15))]  # soma in MPOA   ???
                neuron_16 = [kNeuron(MnPO, BRGTNsyn, id_=ntkb['16'], **kld(16))]  # soma in MnPO   ???
                neuron_17 = [kNeuron(LPOA, BRGTNsyn, id_=ntkb['17'], **kld(17))]  # soma in LPOA   ???
                neuron_18 = [kNeuron(LHA, BRGTNsyn, id_=ntkb['18'], **kld(18))]   # soma in LHA    ???
            neuron_19 = [kNeuron(VLPAG, BRGTNsyn, id_=ntkb['19'], **kld(19))] # soma in VLPAG  ???
        neuron_20 = [kNeuron(BRGTN, id_=ntkb['20'], **kld(20))]  # soma in BRGTN  ??? # TODO many a syntapse


    # implicit types (parents) # FIXME XXX required modelling in many cases
    fos = first_order_sensory = [neuron_10, neuron_11, neuron_12]
    slm = somatic_lower_motor = [neuron_9]

    _pre = parasympathetic_pre_ganglionic = [neuron_5]
    pos = parasympathetic_post_ganglionic = [neuron_1]
    # para pre -> has soma located in some not sympathetic chain and projects to some ganglion that is also projected to by some sym pre
    # para post -> has reverse connection phenotype some para pre

    sre = sympathetic_pre_ganglionic = [neuron_6, neuron_7, neuron_8]
    sos = sympathetic_post_ganglionic = [neuron_2, neuron_3, neuron_4]
    # sym pre -> has forward connection phenotype some neuron population with cell body ni synaptic chain or other sympathetic ganglion???
    # sym post -> has reverse connection phenotype some sym pre
    # XXX these definitions are not good an collide with para I think

    #[print(repr(n)) for n in Neuron.neurons()]


ntks = {k: v
        for i in range(1,13)
        for (k, v) in (
                (f'ntk_{i}', Phenotype(npkb[str(i)], 'ilxtr:hasPhenotype')),
                (f'ntk_{i}_ent', EntailedPhenotype(npkb[str(i)], 'ilxtr:hasPhenotype')))}


class Keast2020(LocalNameManager):

    locals().update(ntks)  # LOL ?! this works !?

    # soma layers
    VII= Phenotype('UBERON:0016578', sllp)  # 'ilxtr:spinal-VII'
    IX = Phenotype('UBERON:0016580', sllp)  # 'ilxtr:spinal-IX'

    # soma locations

    #L1 = Phenotype('ilxtr:spinal-L1', slp)
    #L2 = Phenotype('ilxtr:spinal-L2', slp)
    #L5 = Phenotype('ilxtr:spinal-L5', slp)
    #L6 = Phenotype('ilxtr:spinal-L6', slp)
    #S1 = Phenotype('ilxtr:spinal-S1', slp)
    L1 = Phenotype('UBERON:0006448', slp)  # XXX fma in sct
    L2 = Phenotype('UBERON:0006450', slp)  # XXX fma in sct
    L5 = Phenotype('UBERON:0006447', slp)  # XXX fma in sct
    L6 = Phenotype('ILX:0738432', slp)  # 'ILX:0793358' was dupe
    S1 = Phenotype('UBERON:0006460', slp)  # XXX fma in sct

    IMG = Phenotype('UBERON:0005453', slp)  # ilxtr:IMG
    PG = Phenotype('UBERON:0016508', slp)  # ilxtr:PG

    #L1_dr = Phenotype('ilxtr:dr-L1', slp)  # soma implies ax + dn
    #L2_dr = Phenotype('ilxtr:dr-L2', slp)
    #L6_dr = Phenotype('ilxtr:dr-L6', slp)
    #S1_dr = Phenotype('ilxtr:dr-S1', slp)
    L1_dr = Phenotype('UBERON:0002855', slp)  # soma implies ax + dn
    L2_dr = Phenotype('UBERON:0002856', slp)
    L6_dr = Phenotype('ILX:0793360', slp)
    S1_dr = Phenotype('UBERON:0002860', slp)

    # sort of nerves
    L1_vr = Phenotype('ILX:0785421', alp)  # ventral root 'ilxtr:vr-L1'  # XXX fma in sct
    L1_wr = Phenotype('ILX:0793220', alp)  # white ramus 'ilxtr:wr-L1'  # XXX FMA in sct

    L1_gr = Phenotype('ILX:0785825', alp)  # gray ramus 'ilxtr:gr-L1'  # XXX fma in sct

    L2_vr = Phenotype('ILX:0788675', alp)  # 'ilxtr:vr-L2'  # XXX fma in sct
    L2_wr = Phenotype('ILX:0793221', alp)  # 'ilxtr:wr-L2'  # XXX FMA in sct

    L2_gr = Phenotype('ILX:0785733', alp)  # 'ilxtr:gr-L2'  # XXX fma in sct

    L5_vr = Phenotype('ILX:0791148', alp)  # 'ilxtr:vr-L5'  # XXX fma in sct

    L6_gr = Phenotype('ILX:0739299', alp)  # 'ilxtr:gr-L6'
    L6_vr = Phenotype('ILX:0793615', alp)  # 'ilxtr:vr-L6'

    S1_gr = Phenotype('ILX:0793228', alp)  # 'ilxtr:gr-S1'  # XXX fma in sct
    S1_vr = Phenotype('ILX:0792853', alp)  # 'ilxtr:vr-S1'  # XXX fma in sct

    IMGax = Phenotype('UBERON:0005453', alp)
    PGax = Phenotype('UBERON:0016508', alp)

    S1ax = Phenotype('ILX:0793350', alp)  # 'ilxtr:sc-S1'

    # ilxtr:spinal-white-matter technically a layer
    # FIXME because axon location does not have cardianlity 1 WMax is
    # ambiguous unless it is composed with a layer of the spinal cord
    # because the operation is not commutative with card > 1
    #WMax = Phenotype('ilxtr:spinal-white-matter', alp)
    WMax = Phenotype('UBERON:0002318', alp)


    # sensory dendrite sort of nerves
    IMGdn = Phenotype('UBERON:0005453', dlp)
    PGdn = Phenotype('UBERON:0016508', dlp)

    # XXX FIXME I'm being something of a literalist here, and guessing that
    # the boxes that are drawn for these might not actually be what is intended
    cn_ax = Phenotype('UBERON:0010011', alp)  # collection of basal ganglia, syn cerebral nuclei ??
    dienc_ax = Phenotype('UBERON:0001894', alp)
    midbrain_ax = Phenotype('UBERON:0001891', alp)
    pons_ax = Phenotype('UBERON:0000988', alp)
    medulla_ax = Phenotype('UBERON:0001896', alp)

    # nerves
    #n_bl = Phenotype('ilxtr:nerve-bladder', alp)
    #n_hg = Phenotype('ilxtr:nerve-hypogastric', alp)
    #n_ls = Phenotype('ilxtr:nerve-lumbar-splanic', alp)
    #n_ps = Phenotype('ilxtr:nerve-pelvic-splanic', alp) # splanchnic
    #n_pu = Phenotype('ilxtr:nerve-pudendal', alp)
    n_bl = Phenotype('ILX:0793559', alp)
    n_hg = Phenotype('UBERON:0005303', alp)
    n_ls = Phenotype('UBERON:0018683', alp)
    n_ps = Phenotype('UBERON:0018675', alp)
    n_pu = Phenotype('UBERON:0011390', alp)

    # sensory ??ents
    #n_bl_dn = Phenotype('ilxtr:nerve-bladder', dlp)
    #n_hg_dn = Phenotype('ilxtr:nerve-hypogastric', dlp)
    #n_ls_dn = Phenotype('ilxtr:nerve-lumbar-splanic', dlp)
    #n_ps_dn = Phenotype('ilxtr:nerve-pelvic-splanic', dlp)
    #n_pu_dn = Phenotype('ilxtr:nerve-pudendal', dlp)
    n_bl_dn = Phenotype('ILX:0793559', dlp)
    n_hg_dn = Phenotype('UBERON:0005303', dlp)
    n_ls_dn = Phenotype('UBERON:0018683', dlp)
    n_ps_dn = Phenotype('UBERON:0018675', dlp)
    n_pu_dn = Phenotype('UBERON:0011390', dlp)

    #URTdn = Phenotype('ilxtr:urethra', dlp)
    URTdn = Phenotype('UBERON:0000057', dlp)

    # synaptic locations
    IMGsyn = Phenotype('UBERON:0005453', synp)
    PGsyn = Phenotype('UBERON:0016508', synp)

    BNVWsyn = Phenotype('ilxtr:bladder-neck-vessel-wall', synp)
    BDVWsyn = Phenotype('ilxtr:bladder-dome-vessel-wall', synp)

    BDWsyn = Phenotype('ilxtr:bladder-dome-wall', synp)
    BNWsyn = Phenotype('ILX:0774144', synp)  # 'ilxtr:bladder-neck-wall'

    #URTsyn = Phenotype('ilxtr:urethra', synp)
    URTsyn = Phenotype('UBERON:0000057', synp)

    BNST = Phenotype('UBERON:0001880', slp)
    CeA = Phenotype('UBERON:0002883', slp)  # central amygdala
    MPOA = Phenotype('UBERON:0007769', slp)
    MnPO = Phenotype('UBERON:0002625', slp)
    LPOA = Phenotype('UBERON:0001931', slp)
    LHA = Phenotype('UBERON:0002430', slp)
    VLPAG = Phenotype('ILX:0793626', slp) # vent lat peri aq gray
    BRGTN = Phenotype('UBERON:0007632', slp) # barrington's nucleus

    BRGTNsyn = Phenotype('UBERON:0007632', synp)

    # FIXME synp into layer has the cardinality issue
    # with the fact that (intersection (phenotype layer hp) (phenotype region hp))
    # is not commutative with (phenotype (intersection layer region) hp)
    # when the relationship hp allows cardinality > 1

    #Isyn = Phenotype('ilxtr:spinal-I', synp)
    #IIsyn = Phenotype('ilxtr:spinal-II', synp)
    #Vsyn = Phenotype('ilxtr:spinal-V', synp)
    #VIIsyn = Phenotype('ilxtr:spinal-VII', synp)
    #Xsyn = Phenotype('ilxtr:spinal-X', synp)
    Isyn = Phenotype('UBERON:0006118', synp)
    IIsyn = Phenotype('ILX:0110092', synp)
    Vsyn = Phenotype('UBERON:0016576', synp)
    VIIsyn = Phenotype('UBERON:0016578', synp)
    Xsyn = Phenotype('ILX:0110100', synp)

    # sensory substructure locations

    # target cell types
    #ntk_4 = Phenotype('ilxtr:neuron-phenotype-keast-4', 'ilxtr:hasPhenotype')  # FIXME what is this really?
    #ntk_4_ent = EntailedPhenotype('ilxtr:neuron-phenotype-keast-4', 'ilxtr:hasPhenotype')  # FIXME what is this really?
    # XXX using a specific phenotype here is undesireable, because it must _always_ be asserted
    # in order for membership to be determined, this is true for individuals as well, therefore this
    # should be used as entailed restriction so that anything that matches the necessary contitions
    # will automatically classify as a result

    # is this a phenotype or a superclass? XXX kind of dirty to do it this way by creating an aribrary
    # phenotype that is borne by these, but being marked as a keast-type-4 neuron is a thing so here we are
    # in a pure type world, this would be the coloring and the numbering, but it is more assertional
    # making it a superclass is probably better than

    ntk_1_fcon = Phenotype('ilxtr:neuron-type-keast-1', fconp)
    ntk_2_fcon = Phenotype('ilxtr:neuron-type-keast-2', fconp)
    ntk_3_fcon = Phenotype('ilxtr:neuron-type-keast-3', fconp)
    ntk_4_fcon = Phenotype('ilxtr:neuron-type-keast-4', fconp)

    # FIXME this is super confusing, but this id is equivalent to all
    # neurons that bear the ilxtr:neuron-phenotype-sym-post phenotype
    sos_fcon = Phenotype('ilxtr:sympathetic-post-ganglionic', fconp)  # FIXME likely overly broad?

    # (para)?sympathetic colorings (until we can get deeper modelling correct)
    #para_pre = Phenotype('ilxtr:neuron-phenotype-para-pre')
    #para_post = Phenotype('ilxtr:neuron-phenotype-para-post')
    #sym_pre = Phenotype('ilxtr:neuron-phenotype-sym-pre')
    #sym_post = Phenotype('ilxtr:neuron-phenotype-sym-post')

    para = Phenotype('ilxtr:ParasympatheticPhenotype')
    sym = Phenotype('ilxtr:SympatheticPhenotype')
    pre = Phenotype('ilxtr:PreGanglionicPhenotype')
    post = Phenotype('ilxtr:PostGanglionicPhenotype')

    sens = Phenotype('ilxtr:SensoryPhenotype')
    motor = Phenotype('ilxtr:MotorPhenotype')
    #intrin = Phenotype('ilxtr:IntrinsicPhenotype')



    # phenotypes over layers do not compose well because the
    # intersection of the layer is ambiguous with regard to which
    # other anatomical structures it applies to, so for example and it
    # does not sufficiently constrain that it must be the same axon
    # segment that is in both the bladder dome wall and epithelium we
    # do not currently have a way to express anatomical intersections
    # in neuron lang, we were able to punt on this for somas because
    # there is at most 1 soma, so the referent is unambiguous

    #SMsyn = Phenotype('ilxtr:smooth-muscle', synp)
    #EPIsyn = Phenotype('ilxtr:epithelium', synp)
    #RABsyn = Phenotype('ilxtr:epithelium', synp)

four_soma_locs = [
    # sympathetic chain
    'ILX:0787009',  # 'ilxtr:sc-T12'
    'ILX:0739295',  # 'ilxtr:sc-T13'
    'ILX:0789862',  # 'ilxtr:sc-L1'
    'ILX:0786933',  # 'ilxtr:sc-L2'
    'ILX:0788315',  # 'ilxtr:sc-L3'
    'ILX:0786049',  # 'ilxtr:sc-L4'
    'ILX:0739296',  # 'ilxtr:sc-L5'
    'ILX:0790472',  # 'ilxtr:sc-L6'
    #'ILX:0789109',  # 'ilxtr:sc-S1'
]

osl = {
    'ILX:0787009': 'ilxtr:sc-T12',
    'ILX:0739295': 'ilxtr:sc-T13',
    'ILX:0789862': 'ilxtr:sc-L1',
    'ILX:0786933': 'ilxtr:sc-L2',
    'ILX:0788315': 'ilxtr:sc-L3',
    'ILX:0786049': 'ilxtr:sc-L4',
    'ILX:0739296': 'ilxtr:sc-L5',
    'ILX:0790472': 'ilxtr:sc-L6',
    #'ILX:0789109': 'ilxtr:sc-S1',
}

_osl_chain = {
    'ILX:0793342': 'ilxtr:sc-T12',
    'ILX:0793343': 'ilxtr:sc-T13',
    'ILX:0793344': 'ilxtr:sc-L1',
    'ILX:0793345': 'ilxtr:sc-L2',
    'ILX:0793346': 'ilxtr:sc-L3',
    'ILX:0793347': 'ilxtr:sc-L4',
    'ILX:0793348': 'ilxtr:sc-L5',
    'ILX:0793349': 'ilxtr:sc-L6',
    # 'ILX:0793350': 'ilxtr:sc-S1',
}

[setattr(Keast2020, f'sc{osl[sl].split("-")[-1]}',
         Phenotype(sl, slp))
 for sl in four_soma_locs]

[setattr(Keast2020, f'sc{osl[sl].split("-")[-1]}ax',
         Phenotype(sl, alp))
 for sl in four_soma_locs]

[setattr(Keast2020, f'sc{osl[sl].split("-")[-1]}syn',
         Phenotype(sl, synp))
 for sl in four_soma_locs]

sympathetic_chain_axons = [Phenotype(l, alp) for l in four_soma_locs]  # FIXME intersegmental


def syn_chain_axons_in(syn_index, soma_index):
    """ determine which regions a single collateral must pass through """
    if syn_index < soma_index:
        axons_in = sympathetic_chain_axons[syn_index + 1:soma_index + 1]
    elif syn_index == soma_index:
        axons_in = sympathetic_chain_axons[soma_index],
    else:
        axons_in = sympathetic_chain_axons[soma_index:syn_index]

    return axons_in


def main():
    from pyontutils.utils import relative_path
    config = Config('keast-2020',
                    source_file=relative_path(__file__, no_wd_value=__file__))

    with Keast2020:
        needs_keast_namespace(config)

    config.write()
    labels = (
        rdfs.label,
        #ilxtr.genLabel, ilxtr.localLabel, ilxtr.simpleLabel,
        #ilxtr.simpleLocalLabel, skos.prefLabel
    )
    to_remove = [t for t in config._written_graph
                 if t[1] in labels and '/neuron-type-keast-' in t[0]]
    [config._written_graph.remove(t) for t in to_remove]
    config._written_graph.write()
    config.write_python()
    return config,


if __name__ == '__main__':
    main()
else:
    __globals__ = globals()
