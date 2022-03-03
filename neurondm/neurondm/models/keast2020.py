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
snsp = 'ilxtr:hasSensorySubcellularElementIn'  # XXX new, kind of like axon terminal but for dendrites

fconp = 'ilxtr:hasForwardConnectionPhenotype'

ntkb = rdflib.Namespace(ilxtr[''] + 'neuron-type-keast-')
npkb = rdflib.Namespace(ilxtr[''] + 'neuron-phenotype-keast-')


class NeuronKeast2020(Neuron):  # FIXME should be an EBM but something is a bit off
    owlClass = 'ilxtr:NeuronKeast2020'
    shortname = 'Keast2020'


kNeuron = NeuronKeast2020


def ambig(name):
    return f'{name} of Keast bladder model'


labels = {
1: ambig('pelvic ganglion parasympathetic neuron'),
2: ambig('pelvic ganglion sympathetic neuron'),
3: ambig('inferior mesenteric ganglion neuron'),
4: ambig('sympathetic chain ganglion neuron'),
5: ambig('parasympathetic spinal preganglionic neuron'),
6: 'sympathetic preganglionic neuron innervating pelvic ganglion neuron',
7: 'sympathetic preganglionic neuron innervating inferior mesenteric ganglion neuron',
8: 'sympathetic preganglionic neuron innervating sympathetic chain ganglion neuron',
9: 'urethral rhabdosphincter motor neuron',
10: 'L6-S1 sensory neurons innervating bladder',
11: 'L1-L2 sensory neurons innervating bladder',
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

    # define the inferred parents for neuron populations
    for n in (2, 4, 5, 6, 7, 8, 9, 10, 11, 12):
        NeuronKeast2020(Keast2020[f'ntk_{n}'], id_=ntkb[str(n)], **kld(n))
        # FIXME hack
        config.out_graph.add((npkb[str(n)], rdfs.subClassOf, ilxtr.Phenotype))

    # FIXME spinal cord white matter axons are missing from these bags

    # neuron populations
    neuron_1 = [kNeuron(PG, n_bl, BDWsyn, BNWsyn, para, post, id_=ntkb['1'], **kld(1))]  # pos
    neuron_2 = [kNeuron(PG, n_bl, synloc, sym, post, ntk_2_ent) for synloc in (BDWsyn, BNWsyn)]  # sos # FIXME smooth muslce only
    neuron_3 = [kNeuron(IMG, BDWsyn, BNWsyn, sym, post, id_=ntkb['3'], **kld(3))]  # sos # FIXME smooth muscle only

    neuron_4 = []  # sos
    with Neuron(n_ps, PGax, n_bl, sym, post):
        for soma_location_id in four_soma_locs:
            somaloc = Phenotype(soma_location_id, slp)
            for exits_via in ((L6_gr,), (S1ax, S1_gr,)):
                for synapses_on in (BNVWsyn, BDVWsyn):
                    # 4
                    n4 = kNeuron(somaloc, *exits_via, synapses_on, ntk_4_ent)
                    neuron_4.append(n4)

    neuron_5 = []  # pre
    with Neuron(VII, n_ps, PGax, PGsyn, ntk_1_fcon, para, pre):
        for somaloc, ventral_root_exit in zip((L6,    S1),
                                              (L6_vr, S1_vr)):
            n5 = kNeuron(somaloc, ventral_root_exit, ntk_5_ent)
            neuron_5.append(n5)

    common = {L1: (L1_vr, L1_wr),
              L2: (L2_vr, L2_wr),}
    common67 = {L1: (L1_gr,),
                L2: (L2_gr,),}

    neuron_6 = []  # sre
    neuron_7 = []  # sre
    neuron_8 = []  # sre
    with Neuron(VII, WMax, sos_fcon, sym, pre):
        for i, somaloc in enumerate((L1, L2)):
            soma_index = i + 2  # L1 aligns to the 3rd the sypathetic ganglion
            # which is of course the L1 sypathetic ganglion, but it is
            # the 3rd ganlion in the model with a neuron 4 soma
            with Neuron(somaloc, *common[somaloc]):
                with Neuron(n_ls, *common67[somaloc]):
                    # 6
                    n6 = kNeuron(IMGax, n_hg, PGsyn, ntk_6_ent, )
                    neuron_6.append(n6)  # TODO fcon
                    # 7
                    n7 = kNeuron(IMGsyn, ntk_7_ent, )
                    neuron_7.append(n7)  # TODO fcon

                # 8
                for syn_index, synloc in enumerate(four_soma_locs):
                    axons_in = syn_chain_axons_in(syn_index, soma_index)
                    syn = Phenotype(synloc, synp)
                    n8 = kNeuron(syn, *axons_in, ntk_8_ent)
                    neuron_8.append(n8)

    neuron_9 = []  # slm
    with Neuron(IX, WMax, n_pu, URTsyn, motor):
        for somaloc, ventral_root_exit in zip((L5,    L6),
                                              (L5_vr, L6_vr)):
            n9 = kNeuron(somaloc, ventral_root_exit, ntk_9_ent)
            neuron_9.append(n9)

    neuron_10 = []  # fos
    neuron_11 = []  # fos
    neuron_12 = []  # fos
    with Neuron(Isyn, IIsyn, Vsyn, VIIsyn, Xsyn, sens):  # 10 11 12 XXX layers are wrong, intersection has to come before phenotype
        for somaloc in (L6_dr, S1_dr):
            n10 = kNeuron(somaloc, n_ps_dn, PGdn, n_bl_dn, ntk_10_ent, )  # TODO a bunch of other sensory terminals
            neuron_10.append(n10)

            n12 = kNeuron(somaloc, n_pu_dn, URTdn, ntk_11_ent, )  # TODO URTdn layer is rhabdosphincter
            neuron_12.append(n12)

        for somaloc in (L1_dr, L2_dr):
            n11 = kNeuron(somaloc, n_ls_dn, IMGdn, n_hg_dn, PGdn, n_bl_dn, ntk_12_ent, )  # TODO bladder and layers
            neuron_11.append(n11)

    with Neuron(pons_ax):
        with Neuron(midbrain_ax):
            with Neuron(dienc_ax):
                with Neuron(cn_ax):
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
    VII= Phenotype('ilxtr:spinal-VII', sllp)
    IX = Phenotype('ilxtr:spinal-IX', sllp)

    # soma locations
    L1 = Phenotype('ilxtr:spinal-L1', slp)
    L2 = Phenotype('ilxtr:spinal-L2', slp)
    L5 = Phenotype('ilxtr:spinal-L5', slp)
    L6 = Phenotype('ilxtr:spinal-L6', slp)
    S1 = Phenotype('ilxtr:spinal-S1', slp)
    IMG = Phenotype('UBERON:0005453', slp)  # ilxtr:IMG
    PG = Phenotype('UBERON:0016508', slp)  # ilxtr:PG

    L1_dr = Phenotype('ilxtr:dr-L1', slp) # soma implies ax + dn
    L2_dr = Phenotype('ilxtr:dr-L2', slp)
    L6_dr = Phenotype('ilxtr:dr-L6', slp)
    S1_dr = Phenotype('ilxtr:dr-S1', slp)

    # sort of nerves
    L1_vr = Phenotype('ilxtr:vr-L1', alp)  # ventral root
    L1_wr = Phenotype('ilxtr:wr-L1', alp)  # white ramus
    L1_gr = Phenotype('ilxtr:gr-L1', alp)  # gray ramus

    L2_vr = Phenotype('ilxtr:vr-L2', alp)
    L2_wr = Phenotype('ilxtr:wr-L2', alp)
    L2_gr = Phenotype('ilxtr:gr-L2', alp)

    L5_vr = Phenotype('ilxtr:vr-L5', alp)

    L6_gr = Phenotype('ilxtr:gr-L6', alp)
    L6_vr = Phenotype('ilxtr:vr-L6', alp)

    S1_gr = Phenotype('ilxtr:gr-S1', alp)
    S1_vr = Phenotype('ilxtr:vr-S1', alp)

    IMGax = Phenotype('UBERON:0005453', alp)
    PGax = Phenotype('UBERON:0016508', alp)

    S1ax = Phenotype('ilxtr:sc-S1', alp)

    # ilxtr:spinal-white-matter technically a layer
    # FIXME because axon location does not have cardianlity 1 WMax is
    # ambiguous unless it is composed with a layer of the spinal cord
    # because the operation is not commutative with card > 1
    WMax = Phenotype('ilxtr:spinal-white-matter', alp)

    # sensory dendrite sort of nerves
    IMGdn = Phenotype('UBERON:0005453', dlp)
    PGdn = Phenotype('UBERON:0016508', dlp)

    # XXX FIXME I'm being something of a literalist here, and guessing that
    # the boxes that are drawn for these might not actually be what is intended
    cn_ax = Phenotype('UBERON:0010011', alp)
    dienc_ax = Phenotype('UBERON:0001894', alp)
    midbrain_ax = Phenotype('UBERON:0001891', alp)
    pons_ax = Phenotype('UBERON:0000988', alp)
    medulla_ax = Phenotype('UBERON:0001896', alp)

    # nerves
    n_bl = Phenotype('ilxtr:nerve-bladder', alp)
    #n_hg = Phenotype('ilxtr:nerve-hypogastric', alp)
    #n_ls = Phenotype('ilxtr:nerve-lumbar-splanic', alp)
    #n_ps = Phenotype('ilxtr:nerve-pelvic-splanic', alp) # splanchnic
    #n_pu = Phenotype('ilxtr:nerve-pudendal', alp)
    n_hg = Phenotype('UBERON:0005303', alp)
    n_ls = Phenotype('UBERON:0018683', alp)
    n_ps = Phenotype('UBERON:0018675', alp)
    n_pu = Phenotype('UBERON:0011390', alp)

    # sensory ??ents
    n_bl_dn = Phenotype('ilxtr:nerve-bladder', dlp)
    #n_hg_dn = Phenotype('ilxtr:nerve-hypogastric', dlp)
    #n_ls_dn = Phenotype('ilxtr:nerve-lumbar-splanic', dlp)
    #n_ps_dn = Phenotype('ilxtr:nerve-pelvic-splanic', dlp)
    #n_pu_dn = Phenotype('ilxtr:nerve-pudendal', dlp)
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
    BNWsyn = Phenotype('ilxtr:bladder-neck-wall', synp)

    #URTsyn = Phenotype('ilxtr:urethra', synp)
    URTsyn = Phenotype('UBERON:0000057', synp)

    BNST = Phenotype('UBERON:0001880', slp)
    CeA = Phenotype( 'UBERON:0002883', slp)  # central amygdala
    MPOA = Phenotype('UBERON:0007769', slp)
    MnPO = Phenotype('UBERON:0002625', slp)
    LPOA = Phenotype('UBERON:0001931', slp)
    LHA = Phenotype('UBERON:0002430', slp)
    VLPAG = Phenotype('UBERON:0003040', slp) # vent lat peri aq gray
    BRGTN = Phenotype('UBERON:0007632', slp) # barrington's nucleus

    BRGTNsyn = Phenotype('UBERON:0007632', synp)

    # FIXME synp into layer has the cardinality issue
    # with the fact that (intersection (phenotype layer hp) (phenotype region hp))
    # is not commutative with (phenotype (intersection layer region) hp)
    # when the relationship hp allows cardinality > 1
    Isyn = Phenotype('ilxtr:spinal-I', synp)
    IIsyn = Phenotype('ilxtr:spinal-II', synp)
    Vsyn = Phenotype('ilxtr:spinal-V', synp)
    VIIsyn = Phenotype('ilxtr:spinal-VII', synp)
    Xsyn = Phenotype('ilxtr:spinal-X', synp)

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
    'ilxtr:sc-T12',
    'ilxtr:sc-T13',
    'ilxtr:sc-L1',
    'ilxtr:sc-L2',
    'ilxtr:sc-L3',
    'ilxtr:sc-L4',
    'ilxtr:sc-L5',
    'ilxtr:sc-L6',
    #'ilxtr:sc-S1',
]

[setattr(Keast2020, f'sc{sl.split("-")[-1]}',
         Phenotype(sl, slp))
 for sl in four_soma_locs]

[setattr(Keast2020, f'sc{sl.split("-")[-1]}ax',
         Phenotype(sl, alp))
 for sl in four_soma_locs]

[setattr(Keast2020, f'sc{sl.split("-")[-1]}syn',
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
    config.write_python()
    return config,


if __name__ == '__main__':
    main()
else:
    __globals__ = globals()
