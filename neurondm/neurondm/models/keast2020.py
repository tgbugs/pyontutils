#!/usr/bin/env python3
from neurondm.core import LocalNameManager
from neurondm.lang import Phenotype, Neuron, Config

slp = 'ilxtr:hasSomaLocatedIn'
alp = 'ilxtr:hasAxonLocatedIn'
synp = 'ilxtr:hasAxonPresynapticElementIn'
fconp = 'ilxtr:hasForwardConnectionPhenotype'


class NeuronKeast2020(Neuron):
    owlClass = 'ilxtr:NeuronKeast2020'
    shortname = 'Keast2020'


def needs_keast_namespace():
    """ define neurons for keast spinal """
    common = {L1: (L1_vr, L1_wr),
              L2: (L2_vr, L2_wr),}
    common67 = {L1: (L1_gr,),
                L2: (L2_gr,),}

    neuron_2 = [Neuron(PG, n_bl, synloc) for synloc in (BNWsyn, BDWsyn)]
    neuron_4 = []

    with Neuron(SPG4, n_ps, PGax, n_bl):
        for soma_location_id in four_soma_locs:
            somaloc = Phenotype(soma_location_id, slp)
            for exits_via in ((L6_gr,), (S1ax, S1_gr,)):
                for synapses_on in (BNVWsyn, BDVWsyn):
                    # 4
                    n4 = Neuron(somaloc, *exits_via, synapses_on)
                    neuron_4.append(n4)

    neuron_6 = []
    neuron_7 = []
    neuron_8 = []
    with NeuronKeast2020(VII, SPGfcon):
        for i, somaloc in enumerate((L1, L2)):
            soma_index = i + 2  # L1 aligns to the 3rd the sypathetic ganglion
            with Neuron(somaloc, *common[somaloc]):
                with Neuron(n_ls, *common67[somaloc]):
                    # 6
                    n6 = Neuron(IMGax, n_hg, PGsyn)
                    neuron_6.append(n6)  # TODO fcon
                    # 7
                    n7 = Neuron(IMGsyn)
                    neuron_7.append(n7)  # TODO fcon

                # 8
                for syn_index, synloc in enumerate(four_soma_locs):
                    axons_in = syn_chain_axons_in(syn_index, soma_index)
                    syn = Phenotype(synloc, synp)
                    n8 = Neuron(syn, *axons_in)
                    neuron_8.append(n8)

    #[print(repr(n)) for n in Neuron.neurons()]


class Keast2020(LocalNameManager):
    # soma layers
    VII= Phenotype('ilxtr:spinal-VII', 'ilxtr:hasSomaLocatedInLayer')

    # soma locations
    L1 = Phenotype('ilxtr:spinal-L1', slp)
    L2 = Phenotype('ilxtr:spinal-L2', slp)
    IMG = Phenotype('ilxtr:IMG', slp)
    PG = Phenotype('ilxtr:PG', slp)

    # sort of nerves
    L1_vr = Phenotype('ilxtr:vr-L1', alp)
    L1_wr = Phenotype('ilxtr:wr-L1', alp)
    L1_gr = Phenotype('ilxtr:gr-L1', alp)

    L2_vr = Phenotype('ilxtr:vr-L2', alp)
    L2_wr = Phenotype('ilxtr:wr-L2', alp)
    L2_gr = Phenotype('ilxtr:gr-L2', alp)

    L6_gr = Phenotype('ilxtr:gr-L6', alp)
    S1_gr = Phenotype('ilxtr:gr-S1', alp)

    IMGax = Phenotype('ilxtr:IMG', alp)
    PGax = Phenotype('ilxtr:PG', alp)

    S1ax = Phenotype('ilxtr:sc-S1', alp)

    # nerves
    n_ls = Phenotype('ilxtr:nerve-lumbar-splanic', alp)
    n_hg = Phenotype('ilxtr:nerve-hypogastric', alp)
    n_ps = Phenotype('ilxtr:nerve-pelvic-splanic', alp)
    n_bl = Phenotype('ilxtr:nerve-bladder', alp)

    # synaptic locations
    IMGsyn = Phenotype('ilxtr:IMG', synp)
    PGsyn = Phenotype('ilxtr:PG', synp)

    BNVWsyn = Phenotype('ilxtr:bladder-neck-vessel-wall', synp)
    BDVWsyn = Phenotype('ilxtr:bladder-dome-vessel-wall', synp)

    BDWsyn = Phenotype('ilxtr:bladder-dome-wall', synp)
    BNWsyn = Phenotype('ilxtr:bladder-neck-wall', synp)

    # target cell types
    SPGfcon = Phenotype('ilxtr:sympathetic-post-ganglionic', fconp)
    SPG4 = Phenotype('ilxtr:keast-neuron-4-type', 'ilxtr:hasPhenotype')  # FIXME what is this really?


four_soma_locs = [
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
                    source_file=relative_path(__file__),)
    with Keast2020:
        needs_keast_namespace()

    config.write()
    config.write_python()
    return config


if __name__ == '__main__':
    main()
