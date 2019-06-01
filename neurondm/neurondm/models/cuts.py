#!/usr/bin/env python3.6
from IPython import embed
import csv
from pprint import pprint
from pathlib import Path
import rdflib
import ontquery as oq
from pyontutils.utils import byCol, relative_path, noneMembers, makeSimpleLogger
from pyontutils.core import resSource, OntId
from pyontutils.config import devconfig
from pyontutils.namespaces import OntCuries
from pyontutils.namespaces import interlex_namespace, definition, NIFRID
from pyontutils.closed_namespaces import rdfs
# import these last so that graphBase resets (sigh)
from neurondm.lang import *
from neurondm import *
from neurondm.phenotype_namespaces import BBP, CUT, Layers, Regions

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
    owlClass = OntId('ilxtr:NeuronSWAN').u


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


def make_contains_rules():
    contains_rules = dict(GABAergic=BBP.GABA,
                          cholinergic=CUT.Ach,
                          glutamatergic=CUT.Glu,
                          serotonergic=CUT.Ser,
                          #principle=CUT.proj,  # NOTE this was a spelling error
                          projection=CUT.proj,
                          intrinsic=CUT.inter,
                          interneuron=CUT.inter,
                          Striatum=Phenotype('UBERON:0002435', ilxtr.hasSomaLocatedIn),
                          #CA1=Regions.CA1,
                          #CA2=Regions.CA2,
                          #CA3=Regions.CA3,
                          trilaminar=BBP.TRI,
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

                          #motor=Phenotype(ilxtr.MotorPhenotype, ilxtr.hasCircuitRolePhenotype),
    )

    contains_rules.update({  # FIXME still need to get some of the original classes from neurolex
        'TH+': CUT.TH,
        'Thalamic reticular nucleus': CUT.TRN,  # FIXME disambiguate with reticular nucleus
        'Midbrain reticular nucleus': CUT.MRN,
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
        'Medial entorhinal  ': Phenotype('UBERON:0007224', ilxtr.hasSomaLocatedIn),
        'Vagus dorsal motor nucleus': Phenotype('UBERON:0002870', ilxtr.hasSomaLocatedIn),
        'Bed nuclei of terminal stria': Phenotype('UBERON:0001880', ilxtr.hasSomaLocatedIn, label='bed nucleus of stria terminalis'),
        'Olfactory cortex': Phenotype('UBERON:0002894', ilxtr.hasSomaLocatedIn, label='olfactory cortex'),
        'Globus pallidus external segment': Phenotype('UBERON:0002476', ilxtr.hasSomaLocatedIn,  label='lateral globus pallidus'),
        'Globus pallidus internal segment': Phenotype('UBERON:0002477', ilxtr.hasSomaLocatedIn,  label='medial globus pallidus'),
        'Septal complex lateral': Phenotype('UBERON:0007628', ilxtr.hasSomaLocatedIn, label='lateral septal complex'),  # FIXME missing synonym in uberon
        'Septal complex medial': Phenotype('UBERON:0007629', ilxtr.hasSomaLocatedIn, label='medial septal complex'),  # FIXME missing synonym in uberon
        'Premammillary nucleus dorsal': OntTerm('UBERON:0007767', label='dorsal premammillary nucleus').as_phenotype(),  # FIXME missing synonym in uberon
        'Premammillary nucleus ventral': OntTerm('UBERON:0007768', label='ventral premammillary nucleus').as_phenotype(),  # FIXME missing synonym in uberon
        'Raphe nucleus dorsal': OntTerm('UBERON:0002043', label='dorsal raphe nucleus').as_phenotype(),  # FIXME missing synonym in uberon
        'Raphe nucleus medial': OntTerm('UBERON:0003004', label='median raphe nucleus').as_phenotype(),  # FIXME missing synonym in uberon
        'Periventricular hypothalamic zone': OntTerm('UBERON:0002271', label='periventricular zone of hypothalamus').as_phenotype(),  # FIXME missing synonym in uberon
        'Lateral lemniscus nuclear complex': OntTerm('UBERON:0006840', label='nucleus of lateral lemniscus').as_phenotype(),  # FIXME wow this was hard to find :/ may synonyms needed
        # 'nuclear complex of lateral lemniscus'
        # 'lateral lemniscus nucleus'
        'Medial hypothalamic zone': OntTerm('UBERON:0002272', label='medial zone of hypothalamus').as_phenotype(),  # SciGraph default search is really bad >_<
        'Incertus nucleus': OntTerm('UBERON:0035973', label='nucleus incertus').as_phenotype(),  # WOW ... that was bad
        'Retroambiguous nucleus': OntTerm('UBERON:0016848', label='retroambiguus nucleus').as_phenotype(),  # spelling ...
        'Trigeminal nerve motor nucleus': OntTerm('UBERON:0002633', label='motor nucleus of trigeminal nerve').as_phenotype(),  # had to cook up my search function to find this
        'Trigeminal nerve principal sensory nucleus': OntTerm('UBERON:0002597', label='principal sensory nucleus of trigeminal nerve').as_phenotype(),  # had to go to wikipedia for this one, and no amount of tweaking seems to help scigraph (sigh)
        'Basolateral amygdalar complex': OntTerm('UBERON:0006107', label='basolateral amygdaloid nuclear complex').as_phenotype(),  # oof
        'Amygdala lateral': OntTerm('UBERON:0002886', label='lateral amygdaloid nucleus').as_phenotype(),  # conclusion: scigraph cannot handle reordering
        'Globus pallidus ventral': OntTerm('UBERON:0002778', label='ventral pallidum').as_phenotype(),
        'Habenula nuclei': OntTerm('UBERON:0008993', label='habenular nucleus').as_phenotype(),  # scigraph can't unpluralize nucleus?
        'Trapezoid Body medial nucleus': OntTerm('UBERON:0002833', label='medial nucleus of trapezoid body').as_phenotype(),
        'Gigantocellular reticular nucleus': OntTerm('UBERON:0002155', label='gigantocellular nucleus').as_phenotype(),
        'Bed nucleus of the stria terminalis': OntTerm('UBERON:0001880', label='bed nucleus of stria terminalis').as_phenotype(),
        'Hypothalamus paraventricular nucleus': OntTerm('UBERON:0001930', label='paraventricular nucleus of hypothalamus').as_phenotype(),
        'Hypothalamus tuberomammillary nucleus': OntTerm('UBERON:0001936', label='tuberomammillary nucleus').as_phenotype(),
        'Subthalamic nucleus': OntTerm('UBERON:0001906', label='subthalamic nucleus').as_phenotype(),

        'Spinocerebellar dorsal tract': OntTerm('UBERON:0002753', label='posterior spinocerebellar tract').as_phenotype(),
        'Spinocerebellar ventral tract': OntTerm('UBERON:0002987', label='anterior spinocerebellar tract').as_phenotype(),
        'Abducens nucleus': OntTerm('UBERON:0002682', label='abducens nucleus').as_phenotype(),
        'Medial amygdalar nucleus': OntTerm('UBERON:0002892', label='medial amygdaloid nucleus').as_phenotype(),  # a creeping madness issue

    })

    for k, v in contains_rules.items():  # ah lack of types
        if v == OntTerm:
            continue
        if not isinstance(v, graphBase):
            raise TypeError(f'{k!r}: {v!r}  # is not a Phenotype or some such')

    return contains_rules


exact_rules = {'pyramidal cell': BBP.PC,
               'Neocortex': Regions.CTX,
               'Thalamic': CUT.Thal,
               'principal cell': CUT.proj,
               'principal neuron': CUT.proj,
               'Hypothalamus': Phenotype('UBERON:0001898', ilxtr.hasSomaLocatedIn, label='hypothalamus'),
}
terminals = 'cell', 'Cell', 'neuron', 'neurons', 'positive cell'  # TODO flag cell and neurons for inconsistency

def skip_pred(p):
    """ probably don't need to use this """
    return False
    #if 'ConnectionDetermined' in p:
        #return True


def fixname(name):
    return (name.
            replace('/', '-').
            replace(' ', '-').
            replace('(','-').
            replace(')', '-').
            replace('+','-'))


def make_cut_id(label):
    return 'TEMP:' + fixname(label)


def export_for_review(config, unmapped, partial, nlx_missing,
                      filename='cuts-review.csv',
                      with_curies=False):
    neurons = config.neurons()
    predicates = sorted(set(e for n in neurons
                            for me in n.edges
                            for e in (me if isinstance(me, tuple) else (me,))))  # columns
    q = graphBase.core_graph.transitive_subjects(rdfs.subPropertyOf, ilxtr.hasPhenotype)
    all_predicates = set(s for s in q)
    extra_predicates = sorted(p for p in all_predicates if p not in predicates)

    col_labels = {p.e:p.eLabel for n in neurons
                  for mp in n.pes
                  for p in (mp.pes if isinstance(mp, LogicalPhenotype) else (mp,))}

    header = (['curie', 'label'] +
              [col_labels[p] for p in predicates] +
              ['Status', 'PMID', 'synonyms', 'definition'] +
              [OntId(p).suffix for p in extra_predicates if not skip_pred(p)])

    def neuron_to_review_row(neuron, cols=predicates):  # TODO column names
        _curie = neuron.ng.qname(neuron.id_)
        curie = None if 'TEMP:' in _curie else _curie
        row = [curie, neuron.origLabel]
        for pdim in cols:  # pdim -> phenotypic dimension
            if pdim in neuron:
                #print('>>>>>>>>>>>>>', pdim, neuron)
                #if any(isinstance(p, LogicalPhenotype) for p in neuron):
                    #embed()
                row.append(','.join(sorted([f'{_._pClass.qname}|{_.pLabel}'
                                            if with_curies else
                                            _.pLabel
                                            for _ in neuron[pdim]] if
                                           isinstance(neuron[pdim], list) else
                                           [neuron[pdim].pLabel])))
                #if col == ilxtr.hasLayerLocationPhenotype:
                    #derp = neuron[col]
                    #log = [p for p in derp if isinstance(p, LogicalPhenotype)]
                    #if log:
                        #print(log, row)
                        #embed()
            else:
                row.append(None)

        return row

    #[n for n in neurons]
    resources = Path(devconfig.resources)
    reviewcsv = resources / filename
    rows = [neuron_to_review_row(neuron) for neuron in neurons]

    for i, row in enumerate(rows):
        label = row[1]
        if label in unmapped:
            row.append('Unmapped')
        elif label in partial:
            rem = partial[label]
            row.append(f'Partial: {rem!r}')
        if label in nlx_missing:
            row.append('Could not find NeuroLex mapping')
        else:
            row.append(None)

        row.append(None)  # pmid
        if i < len(neurons):
            n = neurons[i]
            # FIXME
            row.append(','.join(n.config.out_graph[n.id_:NIFRID.synonym:]))  # syn
            row.append(','.join(n.config.out_graph[n.id_:definition:]))  # def

    rows = sorted(rows, key=lambda r:(1 if r[1] is None else 0, str(r[1])))
    incomplete = [[None, u] + [None] * (len(rows[0]) - 2) + ['Unmapped', None, None] for u in unmapped]
    incomplete = sorted(incomplete, key=lambda r:r[1])
    rows += incomplete
    with open(reviewcsv.as_posix(), 'wt', newline='\n') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
        
    return [header] + rows

def main():
    ndl_config = Config('neuron_data_lifted')
    ndl_config.load_existing()
    ndl_neurons = ndl_config.neurons()
    bn_config = Config('basic-neurons')
    bn_config.load_existing()
    bn_neurons = bn_config.neurons()

    resources = Path(devconfig.resources)
    cutcsv = resources / 'common-usage-types.csv'
    with open(cutcsv.as_posix(), 'rt') as f:
        rows = [l for l in csv.reader(f)]

    bc = byCol(rows)

    (_, *labels), *_ = zip(*bc)
    labels_set0 = set(labels)
    ns = []
    for n in ndl_neurons:
        l = str(n.origLabel)
        if l is not None:
            for replace, match in rename_rules.items():  # HEH
                l = l.replace(match, replace)

        if l in labels:
            n._origLabel = l
            ns.append(n)

    sns = set(n.origLabel for n in ns)

    labels_set1 = labels_set0 - sns

    agen = [c.label for c in bc if c.autogenerated]
    sagen = set(agen)
    added = [c.label for c in bc if c.added]
    sadded = set(added)
    ans = []
    sans = set()
    missed = set()
    for n in bn_neurons:
        continue  # we actually get all of these with uberon, will map between them later
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

    nlx_labels = [c.label for c in bc if c.neurolex]
    snlx_labels = set(nlx_labels)

    class SourceCUT(resSource):
        sourceFile = 'nifstd/resources/common-usage-types.csv'  # FIXME relative to git workingdir...
        source_original = True

    sources = SourceCUT(),
    swanr = rdflib.Namespace(interlex_namespace('swanson/uris/readable/'))
    config = Config('common-usage-types-raw', sources=sources, source_file=relative_path(__file__),
                    prefixes={'swanr':swanr,
                              'SWAN':interlex_namespace('swanson/uris/neuroanatomical-terminology/terms/'),
                              'SWAA':interlex_namespace('swanson/uris/neuroanatomical-terminology/appendix/'),})
    ins = [None if OntId(n.id_).prefix == 'TEMP' else n.id_ for n in ns]
    ians = [None] * len(ans)
    def zap(pes):
        for pe in pes:
            if pe not in (Phenotype('BIRNLEX:212', ilxtr.hasTaxonRank),
                          Phenotype('NCBITaxon:7742', ilxtr.hasTaxonRank),
                          Phenotype('BIRNLEX:252', ilxtr.hasTaxonRank),
                          Phenotype('BIRNLEX:516', ilxtr.hasTaxonRank),):
                yield pe

    with Neuron(CUT.Mammalia):
        mamns = [NeuronCUT(*zap(n.pes), id_=i, label=n._origLabel, override=bool(i)).adopt_meta(n)
                 for i, n in zip(ins + ians, ns + ans)]

    contains_rules = make_contains_rules()

    skip = set()
    smatch = set()
    rem = {}
    for l in labels_set2:
        pes = tuple()
        l_rem = l
        for match, pheno in contains_rules.items():
            t = None
            if match not in skip and pheno == OntTerm:
                try:
                    t = OntTerm(term=match)
                    print('WTF', match, t)
                    if t.validated:
                        pheno = Phenotype(t.u, ilxtr.hasSomaLocatedIn)
                    else:
                        pheno = None
                except oq.exceptions.NotFoundError:
                    skip.add(match)
                    pheno = None
            if match in skip and pheno == OntTerm:
                pheno = None

            if match in l_rem and pheno:
                l_rem = l_rem.replace(match, '').strip()
                pes += (pheno,)
            
        if l_rem in exact_rules:
            pes += (exact_rules[l_rem],)
            l_rem = ''

        if l_rem == '  neuron':
            l_rem = ''
        elif l_rem.endswith('  cell'):
            l_rem = l_rem[:-len('  cell')]
            #print('l_rem no cell:', l_rem)
        elif l_rem.endswith('  neuron'):
            l_rem = l_rem[:-len('  neuron')]
            #print('l_rem no neuron:', l_rem)

        hrm = [pe for pe in pes if pe.e == ilxtr.hasSomaLocatedIn]
        if '  ' in l_rem:
            #print('l_rem:', l_rem)
            #embed()
            maybe_region, rest = l_rem.split('  ', 1)
        elif noneMembers(l_rem, *terminals) and not hrm:
            maybe_region, rest = l_rem, ''
            #print('MR:', maybe_region)
        else:
            #print(hrm)
            maybe_region = None

        if maybe_region:
            prefix_rank = ('UBERON', 'SWAN', 'BIRNLEX', 'SAO', 'NLXANAT')
            def key(ot):
                ranked = ot.prefix in prefix_rank
                arg = ot._query_result._QueryResult__query_args['term'].lower()
                return (not ranked,
                        prefix_rank.index(ot.prefix) if ranked else 0,
                        not (arg == ot.label.lower()))

            #t = OntTerm(term=maybe_region)
            # using query avoids the NoExplicitIdError
            ots = sorted((qr.OntTerm for qr in OntTerm.query(term=maybe_region,
                                                             exclude_prefix=('FMA',))), key=key)
            if not ots:
                log.error(f'No match for {maybe_region!r}')
            else:
                t = ots[0]
                if 'oboInOwl:id' in t.predicates:  # uberon replacement
                    t = OntTerm(t.predicates['oboInOwl:id'])

                t.set_next_repr('curie', 'label')
                log.info(f'Match for {maybe_region!r} was {t!r}')
                if t.validated:
                    l_rem = rest
                    pheno = Phenotype(t.u, ilxtr.hasSomaLocatedIn)  # FIXME
                    pes += (pheno,)

        if pes:
            smatch.add(l)
            rem[l] = l_rem

            with Neuron(CUT.Mammalia):
                NeuronCUT(*zap(pes), id_=make_cut_id(l), label=l, override=True)

    labels_set3 = labels_set2 - smatch
    added_unmapped = sadded & labels_set3

    # TODO preserve the names from neuronlex on import ...
    Neuron.write()
    Neuron.write_python()
    raw_neurons = config.neurons()
    config = Config('common-usage-types', sources=sources, source_file=relative_path(__file__),
                    prefixes={'swanr':swanr,
                              'SWAN':interlex_namespace('swanson/uris/neuroanatomical-terminology/terms/'),
                              'SWAA':interlex_namespace('swanson/uris/neuroanatomical-terminology/appendix/'),})
    ids_updated_neurons = [n.asUndeprecated() for n in raw_neurons]
    assert len(ids_updated_neurons) == len(raw_neurons)
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
    sos = set(n.origLabel.lower() if n.origLabel else None for n in ndl_neurons)  # FIXME load origLabel
    nlx_review = lnlx - sos
    nlx_missing = sorted(nlx_review)
    print(f'\nNeuroLex listed as source but no mapping (n = {len(nlx_review)}):')
    _ = [print(l) for l in nlx_missing]

    partial = {k:v for k, v in rem.items() if v and v not in terminals}
    print(f'\nPartially mapped (n = {len(partial)}):')
    if partial:
        mk = max((len(k) for k in partial.keys())) + 2
        for k, v in sorted(partial.items()):
            print(f'{k:<{mk}} {v!r}')
            #print(f'{k!r:<{mk}}{v!r}')
        #pprint(partial, width=200)
    unmapped = sorted(labels_set3)
    print(f'\nUnmapped (n = {len(labels_set3)}):')
    _ = [print(l) for l in unmapped]

    if __name__ == '__main__':
        rows = export_for_review(config, unmapped, partial, nlx_missing)
        embed()

    return config, unmapped, partial, nlx_missing


if __name__ == '__main__':
    main()
