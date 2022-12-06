import augpathlib as aug
from pyontutils.config import auth
from pyontutils.core import OntGraph, OntResPath


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


from neurondm.lang import Phenotype, Neuron, Config, OntId
from pprint import pprint
from pyontutils.sheets import Sheet

amr = aug.LocalPath("~/git/apinatomy-models").expanduser()
skip = 'too-map', 'dev-layout-conn', 'scaffold-test', 'vagus-nerve', 'wbrcm'
models = [_.name for _ in (amr / 'models').children if _.name not in skip and (_ / f'source/{_.name}.xlsx').exists()]
classes = []
for model in models:
    c = type(f'{model.replace("-", "_")}groups', (Sheet,), {'name': f'{model}', 'sheet_name': 'groups'})
    classes.append(c)

insts = [c() for c in classes]

#print(block_lines)
from neurondm.lang import Phenotype, Neuron, Config, OntId
#i = insts[0]
#pprint(dir(i.row_object(0)))

#pprint([i.values for i in insts])

#para_pre =  'ilxtr:neuron-phenotype-para-pre'
#para_post = 'ilxtr:neuron-phenotype-para-post'
#sym_pre =   'ilxtr:neuron-phenotype-sym-pre'
#sym_post =  'ilxtr:neuron-phenotype-sym-post'

para = Phenotype('ilxtr:ParasympatheticPhenotype')
sym = Phenotype('ilxtr:SympatheticPhenotype')
pre = Phenotype('ilxtr:PreGanglionicPhenotype')
post = Phenotype('ilxtr:PostGanglionicPhenotype')

sens = Phenotype('ilxtr:SensoryPhenotype', 'ilxtr:hasCircuitRolePhenotype')
motor = Phenotype('ilxtr:MotorPhenotype', 'ilxtr:hasCircuitRolePhenotype')
intrin = Phenotype('ilxtr:IntrinsicPhenotype', 'ilxtr:hasCircuitRolePhenotype')

excite = Phenotype('ILX:0104003', 'ilxtr:hasFunctionalCircuitRolePhenotype')
inhib = Phenotype('ILX:0105486', 'ilxtr:hasFunctionalCircuitRolePhenotype')

asc = Phenotype('ilxtr:SpinalCordAscendingProjectionPhenotype', 'ilxtr:hasProjectionPhenotype')
desc = Phenotype('ilxtr:SpinalCordDescendingProjectionPhenotype', 'ilxtr:hasProjectionPhenotype')
intfug = Phenotype('ilxtr:IntestinoFugalProjectionPhenotype', 'ilxtr:hasProjectionPhenotype')

enteric = Phenotype('ilxtr:EntericPhenotype')  # probably not just partOf some enteric nervous system ... though maybe given developmental origin
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

_id_oid_type = [
    (r.id().value,
     r.ontologyterms().value if hasattr(r, 'ontologyterms') else f'ERROR {inst}',
     r.neurontypes().value if hasattr(r, 'neurontypes') else f'ERROR {inst}')
    for inst in insts for r in inst.rows()[1:]]
id_oid_type = [(i, o, t) for i, o, t in _id_oid_type if o]
#pprint(id_oid_type)
raw_types = sorted(set([t for i, o, t in id_oid_type]))
#pprint(raw_types)
#pprint([(t, normalize_type(t)) for t in raw_types])
bagged_missed = [(normalize_type(t), t, o) for i, o, t in id_oid_type]
bagged = [(a, c, d, b) for ((a, b), c, d) in bagged_missed]
#pprint(bagged, width=240)
neuron_classes = {
    sn: type(f'Neuron{sn.capitalize()}', (Neuron,), {'owlClass': f'ilxtr:Neuron{sn.capitalize()}'})
    for sn in [('kblad' if _ == 'keast' else
                ('bolew' if _ == 'unbranched' else _))
               for _ in
               set(oid.rsplit("-", 3)[-3]
                   if oid.endswith('-prime')
                   else oid.rsplit("-", 2)[-2]
                   for _, oid, _ in id_oid_type)]
}

def dophen(oid, bag):
    label, x = _genlabel(oid)
    neuron_class = neuron_classes[x]
    # FIXME this doesn't work because entailed phenotypes don't work
    # with the correct logic because they are still acting like ec
    # phenotypes which replace eachother, ent neurons should stack
    # so for now we just stick the neuron id itself in and don't worry about it
    u = OntId(oid).u
    up = OntId(oid).u.replace('neuron-type', 'neuron-phenotype')
    return neuron_class(Phenotype(up), *(p.asEntailed() for p in bag),
                        #label=label,
                        id_=u)

# XXX TODO need to ensure that the type phenotype axioms so that the model superclass is included
config = Config('apinat-pops-more')
neus = [dophen(oid, bag) for bag, _, oid, _ in bagged]
pprint(neus)
#sys.modules['__main__'].__file__ = __file__
#import linecache
#linecache.cache[__file__] = size, mtime, lines, fullname
config.write()
config.write_python()

# cleanup
repo_relative_path = 'ttl/generated/neurons/apinat-pops-more.ttl'
olr = aug.LocalPath(auth.get('ontology-local-repo')).expanduser()
og = OntGraph(path=olr / repo_relative_path)
og.parse()
ng = OntGraph().populate_from_triples((t for t in og if 'able' not in t[1] and 'abel' not in t[1]))
ng.namespace_manager.populate_from(og)
ng.write(olr / repo_relative_path)

if False:
    pprint([(a, b, c, d) for a, b, c, d in bagged if not a])
    pprint([(d, b, c) for a, b, c, d in bagged if d])
