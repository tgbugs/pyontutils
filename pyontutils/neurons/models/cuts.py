#!/usr/bin/env python3.6
from IPython import embed
import csv
from pprint import pprint
from pathlib import Path
import rdflib
from pyontutils.neurons.compiled import neuron_data_lifted
ndl_neurons = neuron_data_lifted.Neuron.neurons()
from pyontutils.neurons.compiled import basic_neurons
bn_neurons = basic_neurons.Neuron.neurons()
from pyontutils.utils import byCol, relative_path
from pyontutils.core import resSource, OntTerm
from pyontutils.config import devconfig
from pyontutils.namespaces import interlex_namespace
# import these last so that graphBase resets (sigh)
from pyontutils.neurons.lang import *
from pyontutils.neurons import *
from pyontutils.phenotype_namespaces import BBP, Layers, Regions

# TODO
# 1. inheritance for owlClass from python classes
# 2. add ttl serialization for subclasses of EBM
# 3. pv superclass for query example


class PT(OntTerm):  # FIXME subclassing very broken :/ probably because __real_init__ is a __ method
    __firsts = OntTerm._OntTerm__firsts
    def __repr__(self):
        if self.label:
            return f'Phenotype({self.curie}, ilxtr.hasSomaLocatedIn)  # {self.label}'
        else:
            return super().__repr__()

OntTerm.repr_level(verbose=False)

class NeuronSWAN(NeuronEBM):
    owlClass = 'ilxtr:NeuronSWAN'

rename_rules = {'Colliculus inferior': 'Inferior colliculus',
                'Colliculus superior': 'Superior colliculus',
                'Premammillary nucleus dorsal': 'Dorsal premammillary nucleus',
                'Premammillary nucleus ventral': 'Ventral premammillary nucleus',
                'Septal complex lateral': 'Lateral septal complex',
                'Septal complex medial': 'Medial septal complex',
                'Substantia nigra pars reticulata': 'Reticular part of substantia nigra',
                'Thalamic reticular nucleus': 'Reticular thalamic nucleus',
                'Trigeminal nerve motor nucleus': 'Motor nucleus of trigeminal nerve',
                'Trigeminal nerve principal sensory nucleus': 'Principal sensory nucleus of trigeminal nerve',
                'Dorsal root ganglion cell': 'Dorsal root ganglion A alpha-beta non-nociceptive neuron',
                'Neocortex layer 2-3 pyramidal cell': 'Neocortex pyramidal layer 2-3 cell',
                #'Neocortex layer 5 pyramidal cell':  # TODO layer 5-6??
                'Hippocampus CA2 Basket cell': 'Hippocampus CA2 basket cell broad',
                'Neocortex layer 4 spiny stellate cell': 'Neocortex stellate layer 4 cell',
}

class CUT(LocalNameManager):
    Mammalia = Phenotype('NCBITaxon:40674', ilxtr.hasTaxonRank)
    proj = Phenotype(ilxtr.ProjectionPhenotype, ilxtr.hasCircuitRolePhenotype)
    inter = Phenotype(ilxtr.InterneuronPhenotype, ilxtr.hasCircuitRolePhenotype)
    Ach = Phenotype('SAO:185580330', ilxtr.hasExpressionPhenotype)
    Glu = Phenotype('CHEBI:16015', ilxtr.hasExpressionPhenotype)
    Ser = Phenotype('CHEBI:28790', ilxtr.hasExpressionPhenotype)
    TH = Phenotype('PR:000016301', ilxtr.hasExpressionPhenotype)  # NCBIGene:21823
    TRN = Phenotype('UBERON:0001903', ilxtr.hasSomaLocatedIn)
    Thal = Phenotype('UBERON:0001897', ilxtr.hasSomaLocatedIn)


contains_rules = dict(GABAergic=BBP.GABA,
                      cholinergic=CUT.Ach,
                      glutamatergic=CUT.Glu,
                      serotonergic=CUT.Ser,
                      principle=CUT.proj,
                      projection=CUT.proj,
                      intrinsic=CUT.inter,
                      interneuron=CUT.inter,
                      Striatum=Phenotype('UBERON:0002435', ilxtr.hasSomaLocatedIn),
                      #CA1=Regions.CA1,
                      #CA2=Regions.CA2,
                      #CA3=Regions.CA3,
                      neurogliaform=BBP.NGC,  # FIXME
                      parvalbumin=BBP.PV,  # FIXME
                      calbindin=BBP.CB,
                      calretinin=BBP.CR,
                      cholecystokinin=BBP.CCK,
                      somatostatin=BBP.SOM,
                      orexin=Phenotype('PR:000008476', ilxtr.hasExpressionPhenotype),
                      oxytocin=Phenotype('CHEBI:7872', ilxtr.hasExpressionPhenotype),
                      bitufted=BBP.BTC,
                      radiatum=Layers.SR,
                      motor=Phenotype(ilxtr.MotorPhenotype, ilxtr.hasCircuitRolePhenotype),
)

contains_rules.update({  # FIXME still need to get some of the original classes from neurolex
    'TH+': CUT.TH,
    'Thalamic reticular nucleus': CUT.TRN,  # FIXME disambiguate with reticular nucleus
    'reticular nucleus': CUT.TRN,  # FIXME confirm
    'Ambiguous nucleus': Phenotype('UBERON:0001719', ilxtr.hasSomaLocatedIn),
    'Accumbens nucleus': Phenotype('UBERON:0001882', ilxtr.hasSomaLocatedIn),
    'Neocortex layer I': Layers.L1, # FIXME consistency in naming?
    'Neocortex layer 2': Layers.L2,
    'Neocortex layer 3': Layers.L3,
    'Neocortex layer 4': Layers.L4,
    'Neocortex layer 5': Layers.L5,
    'Neocortex layer 6': Layers.L6,
    'cortex layer III': Layers.L3,  # probably needs the cortex to still be attached
    'cortex layer II': Layers.L2,  # FIXME medial entorhinal ...
    'neuropeptide Y': BBP.NPY,
    'vasoactive intestinal peptide': BBP.VIP,
    'Pedunculopontine nucleus': Phenotype('UBERON:0002142', ilxtr.hasSomaLocatedIn),
    #'Incertus nucleus': OntTerm,
    'Raphe nucleus medial': OntTerm,
    'double bouquet': BBP.DBC,
    'Neocortex  ': Regions.CTX,
    'Cuneate nucleus  ': Phenotype('UBERON:0002045', ilxtr.hasSomaLocatedIn),
    'Interstitial nucleus of Cajal  ': Phenotype('UBERON:0002551', ilxtr.hasSomaLocatedIn),
    'Suprachiasmatic nucleus  ': Phenotype('UBERON:0002034', ilxtr.hasSomaLocatedIn),
    'Darkshevich nucleus  ': Phenotype('UBERON:0002711', ilxtr.hasSomaLocatedIn),
    'Spinal cord ventral horn  ': Phenotype('UBERON:0002257', ilxtr.hasSomaLocatedIn),  # FIXME ??? II just hanging out!?
    'Area postrema  ': Phenotype('UBERON:0002162', ilxtr.hasSomaLocatedIn),
    'Sublingual nucleus  ': Phenotype('UBERON:0002881', ilxtr.hasSomaLocatedIn),
    'Arcuate nucleus medulla  ': Phenotype('UBERON:0002865', ilxtr.hasSomaLocatedIn),
    'Hippocampus CA1': Regions.CA1,
    'Hippocampus CA2': Regions.CA2,
    'Hippocampus CA3': Regions.CA3,
    'Hippocampus  ': Phenotype('UBERON:0001954', ilxtr.hasSomaLocatedIn),  # FIXME clarity here
    'Retrotrapezoid nucleus  ': Phenotype('UBERON:0009918', ilxtr.hasSomaLocatedIn),
    'Salivatory nucleus  ': Phenotype('UBERON:0004133', ilxtr.hasSomaLocatedIn),
    'Gracile nucleus  ': Phenotype('UBERON:0002161', ilxtr.hasSomaLocatedIn),
    'Laterodorsal tegmental nucleus  ': Phenotype('UBERON:0002267', ilxtr.hasSomaLocatedIn),

})

exact_rules = {'pyramidal cell': BBP.PC,
               'Neocortex': Regions.CTX,
               'Thalamic': CUT.Thal,
}
terminals = 'cell', 'Cell', 'neuron', 'neurons', 'positive cell'  # TODO flag cell and neurons for inconsistency

def main():
    resources = Path(devconfig.resources)
    cutcsv = resources / 'common-usage-types.csv'
    with open(cutcsv.as_posix(), 'rt') as f:
        rows = [l for l in csv.reader(f)]

    bc = byCol(rows)

    labels, *_ = zip(*bc)
    labels_set0 = set(labels)
    ns = []
    for n in ndl_neurons:
        l = n._origLabel
        if l is not None:
            for replace, match in rename_rules.items():  # HEH
                l = l.replace(match, replace)

        if l in labels:
            n._origLabel = l
            ns.append(n)

    sns = set(n._origLabel for n in ns)

    labels_set1 = labels_set0 - sns

    agen = [c.label for c in bc if c.Autogenerated]
    sagen = set(agen)
    ans = []
    sans = set()
    missed = set()
    for n in bn_neurons:
        # can't use capitalize here because there are proper names that stay uppercase
        l = n.label.replace('(swannt) ',
                            '').replace('Intrinsic',
                                        'intrinsic').replace('Projection',
                                                             'projection')
        for replace, match in rename_rules.items():  # HEH
            l = l.replace(match, replace)

        if l in agen:
            n._origLabel = l
            ans.append(n)
            sans.add(l)
        else:
            missed.add(l)

    agen_missing = sagen - sans
    labels_set2 = labels_set1 - sans

    nlx_labels = [c.label for c in bc if c.Neurolex]
    snlx_labels = set(nlx_labels)

    class SourceCUT(resSource):
        sourceFile = 'pyontutils/resources/common-usage-types.csv'  # FIXME relative to git workingdir...
        source_original = True

    sources = SourceCUT(),
    swanr = rdflib.Namespace(interlex_namespace('swanson/uris/readable/'))
    Config('common-usage-types', sources=sources, source_file=relative_path(__file__),
           prefixes={'swanr':swanr,
                     'SWAN':interlex_namespace('swanson/uris/neuroanatomical-terminology/terms/'),
                     'SWAA':interlex_namespace('swanson/uris/neuroanatomical-terminology/appendix/'),})
    ins = [None] * len(ns)  # [n.id_ for n in ns]  # TODO
    ians = [None] * len(ans)
    with Neuron(CUT.Mammalia):
        new = [NeuronCUT(*n.pes, id_=i, label=n._origLabel, override=True) for i, n in zip(ins + ians, ns + ans)]
    smatch = set()
    rem = {}
    for l in labels_set2:
        pes = tuple()
        l_rem = l
        for match, pheno in contains_rules.items():
            t = None
            if pheno == OntTerm:
                t = OntTerm(term=match)
                if t.validated:
                    pheno = Phenotype(t.u, ilxtr.hasSomaLocatedIn)
                else:
                    pheno = None
            if match in l_rem and pheno:
                l_rem = l_rem.replace(match, '').strip()
                pes += (pheno,)
            
        if l_rem in exact_rules:
            pes += (exact_rules[l_rem],)
            l_rem = ''

        if '  ' in l_rem:
            print(l_rem)
            #embed()
            maybe_region, *rest = l_rem.split('  ')
            try:
                t = OntTerm(term=maybe_region)

                print(maybe_region, t)
                if t.validated:
                    l_rem = rest
                    pheno = Phenotype(t.u, ilxtr.hasSomaLocatedIn)  # FIXME
                    pes += (pheno,)

            except ValueError as e:  # FIXME this needs to be a custom error
                pass
                #raise e
        if pes:
            smatch.add(l)
            rem[l] = l_rem

            with Neuron(CUT.Mammalia):
                NeuronCUT(*pes, label=l, override=True)

    labels_set3 = labels_set2 - smatch

    # TODO preserve the names from neuronlex on import ...
    Neuron.write()
    Neuron.write_python()

    progress = len(labels_set0), len(sns), len(sans), len(smatch), len(labels_set1), len(labels_set2), len(labels_set3)
    print('\nProgress:\n'
          f'total:            {progress[0]}\n'
          f'from nlx:         {progress[1]}\n'
          f'from basic:       {progress[2]}\n'
          f'from match:       {progress[3]}\n'
          f'TODO after nlx:   {progress[4]}\n'
          f'TODO after basic: {progress[5]}\n'
          f'TODO after match: {progress[6]}\n')
    assert progress[0] == progress[1] + progress[4], 'neurolex does not add up'
    assert progress[4] == progress[2] + progress[5], 'basic does not add up'

    lnlx = set(n.lower() for n in snlx_labels)
    sos = set(n._origLabel.lower() if n._origLabel else None for n in ndl_neurons)  # FIXME load origLabel
    nlx_review = lnlx - sos
    print('\nNeuroLex listed as source but no mapping:', len(nlx_review))
    _ = [print(l) for l in sorted(nlx_review)]

    partial = {k:v for k, v in rem.items() if v and v not in terminals}
    print(f'\nPartially mapped (n = {len(partial)}):')
    pprint(partial, width=200)
    print('\nUnmapped:')
    _ = [print(l) for l in sorted(labels_set3)]

    if __name__ == '__main__':
        embed()


if __name__ == '__main__':
    main()
