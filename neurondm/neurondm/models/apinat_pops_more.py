import augpathlib as aug
from pyontutils.core import OntGraph, OntResPath
from pyontutils.config import auth
from pyontutils.namespaces import makePrefixes, ilxtr


#import json
def path_json(p):
    with open(p, 'rt') as f:
        return json.load(f)


def asObj(r, name=None):
    # SIGH functions and errors do not compose well at all
    d = {h: getattr(r, h)().value for h in r.header}
    errors = [v for v in d.values() if len(v) != len(v.strip())]
    if errors:
        msg = f'BEEP BOOP WHITESPACE VIOLATION IN {name}: {errors!r}'
        raise ValueError(msg)

    return d


def _genlabel(oid):
    x = (oid.rsplit("-", 3)[-3]
         if oid.endswith('-prime')
         else (oid.rsplit("-", 3)[-3] if 'unbranched' in oid else oid.rsplit("-", 2)[-2]))
    l = (oid.rsplit("-", 3)[-3]
         if oid.endswith('-prime')
         else (' '.join(oid.rsplit("-", 3)[-3:-1]) if 'unbranched' in oid else oid.rsplit("-", 2)[-2]))
    t = (oid.rsplit("-", 2)[-2] + "'"
         if oid.endswith('-prime')
         else (oid.rsplit("-", 1)[-1] if 'unbranched' in oid else oid.rsplit("-", 1)[-1]))

    # XXX manual fix for consistency
    if x == 'keast':
        x = 'kblad'
    if l == 'keast':
        l = 'kblad'

    label = f'neuron type {l} {t}'
    return label, x


from pprint import pprint
#from pyontutils.sheets import Sheet
from sparcur.sheets import Sheet  # FIXME move the caching functionality to pyontutils.sheets
# XXX for now if you make a change you can e.g. insts[0].fetch(_refresh_cache=True)

Sheet._do_cache = True

amr = aug.LocalPath("~/git/apinatomy-models").expanduser()
skip = 'too-map', 'dev-layout-conn', 'scaffold-test', 'vagus-nerve', 'wbrcm'
models = [_.name for _ in (amr / 'models').children if _.name not in skip and (_ / f'source/{_.name}.xlsx').exists()]

# might as well just pull the sheets directly at this point
#_json_paths = {name: amr / 'models' / name / 'source' / f'{name}.json' for name in models}
#jsons = {n: path_json(p) for n, p in _json_paths.items()}

classes = []
main_classes = []  # XXX because abbreviation is not included in the json !!!
refs_classes = []
lcnv_classes = []
for model in models:
    c = type(f'{model.replace("-", "_")}groups', (Sheet,), {'name': f'{model}', 'sheet_name': 'groups'})
    classes.append(c)
    c = type(f'{model.replace("-", "_")}main', (Sheet,), {'name': f'{model}', 'sheet_name': 'main'})
    main_classes.append(c)
    c = type(f'{model.replace("-", "_")}references', (Sheet,), {'name': f'{model}', 'sheet_name': 'references'})
    refs_classes.append(c)
    c = type(f'{model.replace("-", "_")}localConventions', (Sheet,), {'name': f'{model}', 'sheet_name': 'localConventions'})
    lcnv_classes.append(c)

insts = [c(fetch=False) for c in classes]
main_insts = [c(fetch=False) for c in main_classes]
refs_insts = [c(fetch=False) for c in refs_classes]
lcnv_insts = [c(fetch=False) for c in lcnv_classes]

#print(block_lines)
from neurondm.lang import Phenotype, Neuron, NeuronEBM, Config, OntId
#i = insts[0]
#pprint(dir(i.row_object(0)))

#pprint([i.values for i in insts])

#para_pre =  'ilxtr:neuron-phenotype-para-pre'
#para_post = 'ilxtr:neuron-phenotype-para-post'
#sym_pre =   'ilxtr:neuron-phenotype-sym-pre'
#sym_post =  'ilxtr:neuron-phenotype-sym-post'

para = Phenotype('ilxtr:ParasympatheticPhenotype', 'ilxtr:hasAnatomicalSystemPhenotype')
sym = Phenotype('ilxtr:SympatheticPhenotype', 'ilxtr:hasAnatomicalSystemPhenotype')
pre = Phenotype('ilxtr:PreGanglionicPhenotype', 'ilxtr:hasAnatomicalSystemPhenotype')
post = Phenotype('ilxtr:PostGanglionicPhenotype', 'ilxtr:hasAnatomicalSystemPhenotype')

sens = Phenotype('ilxtr:SensoryPhenotype', 'ilxtr:hasCircuitRolePhenotype')
motor = Phenotype('ilxtr:MotorPhenotype', 'ilxtr:hasCircuitRolePhenotype')
intrin = Phenotype('ilxtr:IntrinsicPhenotype', 'ilxtr:hasCircuitRolePhenotype')

excite = Phenotype('ILX:0104003', 'ilxtr:hasFunctionalCircuitRolePhenotype')
inhib = Phenotype('ILX:0105486', 'ilxtr:hasFunctionalCircuitRolePhenotype')

asc = Phenotype('ilxtr:SpinalCordAscendingProjectionPhenotype', 'ilxtr:hasProjectionPhenotype')
desc = Phenotype('ilxtr:SpinalCordDescendingProjectionPhenotype', 'ilxtr:hasProjectionPhenotype')
intfug = Phenotype('ilxtr:IntestinoFugalProjectionPhenotype', 'ilxtr:hasProjectionPhenotype')

enteric = Phenotype('ilxtr:EntericPhenotype', 'ilxtr:hasAnatomicalSystemPhenotype')  # probably not just partOf some enteric nervous system ... though maybe given developmental origin
nos = Phenotype('TEMPIND:Nos1', 'ilxtr:hasMolecularPhenotype')

mapping = {
    'sympathetic': sym,
    'parasympathetic': para,
    'pre-ganglionic': pre,
    'post-ganglionic': post,
    'sensory': sens,
    'motor': motor,
    'local': intrin,
    'interneuron': intrin,
    'excitatory': excite,
    'inhibitory': inhib,

    'intestinofugal': intfug,
    'enteric': enteric,
    'descending': desc,
    'ascending': asc,
    'NOS': nos,
}

bad_bits = {'neuron', '', 'first', 'order', 'circuit', 'lower', 'somatic', 'Vagal'}
bad_sets = (  # from the school of maximum wat
    {'inhibitory', 'motor'},
    # inhibitory motor in the context of the stomach means nitric
    # oxide releaseing, motor usually implies actuating ach, we need
    # to clarify the definition because neuro/myo/modulatory release
    # is usually not what we mean in other systems
    {'primary', 'afferent', 'intrinsic'},
    {'visceral', 'sensory'},  # I think this one is just wrong
)

exact_sets = {
frozenset(('')): 'hello',
}


def normalize_type(string):
    raw_bits = set(string.split(' '))
    bits = raw_bits - bad_bits
    if bits in bad_sets:
        return set()
    id_bits = set([mapping[b] if b in mapping else b for b in bits
                   if b in mapping])
    missed = [b for b in bits if b not in mapping]
    return id_bits, missed


def parse_refs(refs):
    return [_ for _ in [r.strip() for r in refs.split(',')] if _]


_id_oid_type_refs = [
    (r.id().value,
     r.ontologyterms().value if hasattr(r, 'ontologyterms') else f'ERROR {inst}',
     r.neurontypes().value if hasattr(r, 'neurontypes') else f'ERROR {inst}',
     r.references().value if hasattr(r, 'references') else f'ERROR {inst}',)
    for inst in insts if hasattr(inst, '_values') or inst.fetch() for r in inst.rows()[1:]]
id_oid_type_refs = [(i, o, t, refs) for i, o, t, refs in _id_oid_type_refs if o]
#pprint(id_oid_type)
raw_types = sorted(set([t for i, o, t, refs in id_oid_type_refs]))
#pprint(raw_types)
#pprint([(t, normalize_type(t)) for t in raw_types])
bagged_missed = [(normalize_type(t), t, o, parse_refs(refs)) for i, o, t, refs in id_oid_type_refs]
bagged = [(a, c, d, b, r) for ((a, b), c, d, r) in bagged_missed]
#pprint(bagged, width=240)


id_sn = {r.id().value: r.abbreviation().value if hasattr(r, 'abbreviation') else 'MISSING ???'
         for i in main_insts if hasattr(i, '_values') or i.fetch() for r in i.rows()[1:]}
sn_id = {s:i for i, s in id_sn.items()}

# model level refs
mrefs = {i.name: [asObj(r, i.name) for r in i.rows()[1:]] for i in refs_insts if hasattr(i, '_values') or i.fetch()}

lcnv = {i.name: {r.prefix().value if hasattr(r, 'prefix') else 'AAAA':  # r.namespace().value
                 r.namespace().value if hasattr(r, 'namespace') else 'BBBB'
                 for r in i.rows()[1:]} for i in lcnv_insts if hasattr(i, '_values') or i.fetch()}

neuron_classes = {
    sn: type(f'Neuron{sn.capitalize()}', (NeuronEBM,),
             {'owlClass': ilxtr[f'Neuron{sn.capitalize()}'],
              '_model_refs': mrefs[sn_id[sn]],
              '_model_id': sn_id[sn],
              })
    for sn in [('kblad' if _ == 'keast' else
                ('bolew' if _ == 'unbranched' else _))
               for _ in
               set(oid.rsplit("-", 3)[-3]
                   if oid.endswith('-prime')
                   else oid.rsplit("-", 2)[-2]
                   for _, oid, _, _ in id_oid_type_refs)]
}

# TODO add citations to parent classes or individual neurons, TODO probably also link to the apinatomy model itself
# TODO add links to svgs to the Neuron{Model} classes
svg_template = (
    'https://raw.githubusercontent.com/open-physiology/apinatomy-models/'
    'master/models/{id_model}/docs/{id_model}.svg')


def dophen(oid, bag, refs):
    label, x = _genlabel(oid)
    neuron_class = neuron_classes[x]
    # FIXME this doesn't work because entailed phenotypes don't work
    # with the correct logic because they are still acting like ec
    # phenotypes which replace eachother, ent neurons should stack
    # so for now we just stick the neuron id itself in and don't worry about it
    u = OntId(oid).u
    up = OntId(oid).u.replace('neuron-type', 'neuron-phenotype')
    nc = neuron_class(Phenotype(up, 'ilxtr:hasClassificationPhenotype'), *(p.asEntailed() for p in bag),
                      #label=label,
                      id_=u)
    nc._refs = refs
    return nc


def citations(ncs, neus):
    p = OntId('ilxtr:literatureCitation').u
    #hsa = OntId('ilxtr:hasSourceArtifact').u  # XXX doesn't quite match usage because it is pseudo ontological
    source = OntId('dc:source').u  # more reasonable given the complexity of the process
    for things, attr, idf in ((ncs, '_model_refs', lambda c: OntId(c.owlClass).u),
                              (neus, '_refs', lambda c: c.identifier)):
        for thing in things:
            s = idf(thing)

            if attr == '_model_refs':
                yield s, source, OntId(svg_template.format(id_model=thing._model_id)).u

            for ref in getattr(thing, attr):
                if isinstance(ref, dict):
                    ref = ref['id']  # XXX FIXME WARNING EVIL

                try:
                    o = OntId(ref).u
                except Exception as e:
                    raise ValueError(s) from e

                yield s, p, o


def main():
    # XXX TODO need to ensure that the type phenotype axioms so that the model superclass is included
    config = Config('apinat-pops-more')
    neus = [dophen(oid, bag, refs) for bag, _, oid, _, refs in bagged]
    #test = list(citations(neuron_classes.values(), neus))
    pprint(neus)
    #sys.modules['__main__'].__file__ = __file__
    #import linecache
    #linecache.cache[__file__] = size, mtime, lines, fullname
    config.write()
    config.write_python()

    # cleanup
    ogp = config._written_graph.path  # XXX cannot trust config.out_graph_path() due to failover if path does not exist in graphBase >_< hooray
    og = OntGraph(path=ogp)
    og.parse()
    ng = OntGraph().populate_from_triples((t for t in og if 'able' not in t[1] and 'abel' not in t[1]))
    ng.populate_from(citations(neuron_classes.values(), neus))
    ng.namespace_manager.populate_from(og)
    ng.namespace_manager.populate_from(makePrefixes('PMID', 'doi', 'dc'))
    ng.write(ogp)

    if False:
        pprint([(a, b, c, d) for a, b, c, d in bagged if not a])
        pprint([(d, b, c) for a, b, c, d in bagged if d])

    return config,


if __name__ == '__main__':
    main()
