#!/usr/bin/env python3.6
import os
import atexit
import inspect
from pprint import pformat
from pathlib import Path, PurePath as PPath
from urllib.error import HTTPError
import rdflib
from rdflib.extras import infixowl
from git.repo import Repo
from pyontutils.core import Ont, makeGraph
from pyontutils.utils import stack_magic, TermColors as tc, subclasses, injective_dict
from pyontutils.ttlser import natsort
from pyontutils.config import devconfig, checkout_ok as ont_checkout_ok
from pyontutils.scigraph import Graph, Vocabulary
from pyontutils.qnamefix import cull_prefixes
from pyontutils.namespaces import makePrefixes, TEMP, UBERON, ilxtr, PREFIXES as uPREFIXES
from pyontutils.closed_namespaces import rdf, rdfs, owl

__all__ = [
    'AND',
    'OR',
    'getPhenotypePredicates',
    'graphBase',
    'setLocalContext',
    'getLocalContext',
    'LocalNameManager',
    'setLocalNames',
    'getLocalNames',
    'resetLocalNames',
    'Phenotype',
    'NegPhenotype',
    'LogicalPhenotype',
    'Neuron',
    'NeuronCUT',
    'NeuronEBM',
    #'NeuronArranger',
    '_NEURON_CLASS',
    '_CUT_CLASS',
    '_EBM_CLASS',
]

# language constructes
AND = 'owl:intersectionOf'
OR = 'owl:unionOf'

# utility identifiers
_NEURON_CLASS = 'SAO:1417703748'
_CUT_CLASS = 'ilxtr:NeuronCUT'
_EBM_CLASS = 'ilxtr:NeuronEBM'
PHENO_ROOT = 'ilxtr:hasPhenotype'  # needs to be qname representation
DEF_ROOT = 'ilxtr:definedClassNeurons'

# utility functions

def getPhenotypePredicates(graph):
    # put existing predicate short names in the phenoPreds namespace (TODO change the source for these...)
    qstring = ('SELECT DISTINCT ?prop WHERE '
               '{ ?prop rdfs:subPropertyOf* %s . }') % PHENO_ROOT
    out = [_[0] for _ in graph.query(qstring)]
    literal_map = {uri.rsplit('/',1)[-1]:uri for uri in out}  # FIXME this will change
    classDict = {uri.rsplit('/',1)[-1]:uri for uri in out}  # need to use label or something
    classDict['_litmap'] = literal_map
    phenoPreds = type('PhenoPreds', (object,), classDict)  # FIXME this makes it impossible to add fake data
    return phenoPreds

#
# classes

class graphBase:
    core_graph = 'ASSIGN ME AFTER IMPORT!'
    in_graph = 'ASSIGN ME AFTER IMPORT!'
    out_graph = 'ASSIGN ME AFTER IMPORT'

    _predicates = 'ASSIGN ME AFTER IMPORT'

    LocalNames = {}

    _registered = False

    __import_name__ = __name__

    #_sgv = Vocabulary(cache=True)

    def __init__(self):
        if type(self.core_graph) == str:
            raise TypeError('You must have at least a core_graph')

        if type(self.in_graph) == str:
            self.in_graph = self.core_graph

        if type(self.out_graph) == str:
            self.out_graph = self.in_graph

        self._namespaces = {p:rdflib.Namespace(ns) for p, ns in self.in_graph.namespaces()}

    def expand(self, putativeURI):
        if type(putativeURI) == infixowl.Class:
            return putativeURI.identifier
        elif type(putativeURI) == str:
            try: prefix, suffix = putativeURI.split(':',1)
            except ValueError:  # FIXME this is wrong...
                return rdflib.URIRef(putativeURI)
            if prefix in self._namespaces:
                return self._namespaces[prefix][suffix]
            else:
                raise KeyError('Namespace prefix does not exist:', prefix)
        else:  # FIXME need another check probably...
            return putativeURI

    @staticmethod
    def set_repo_state():
        if not hasattr(graphBase, 'original_branch'):
            graphBase.original_branch = repo.active_branch

        if not graphBase._registered:
            #print(tc.blue('OB:'), graphBase.original_branch)
            def reset(ob=graphBase.original_branch):
                # ob prevents late binding to original_branch
                # which can be reset by successive calls to configGraphIO
                try:
                    # anything that will be overwritten by returning is OK to zap
                    graphBase.repo.git.checkout('-f', ob)
                except BaseException as e:
                    #from IPython import embed
                    #embed()
                    raise e

            atexit.register(reset)
            #atexit.register(graphBase.repo.git.checkout, '-f', graphBase.original_branch)
            graphBase._registered = True

        graphBase.repo.git.checkout(graphBase.working_branch)

    @staticmethod
    def reset_repo_state():
        graphBase.repo.git.checkout(graphBase.original_branch)

    @staticmethod
    def configGraphIO(remote_base,
                      local_base=        None,
                      branch=            'master',
                      core_graph_paths=  tuple(),
                      core_graph=        None,
                      in_graph_paths=    tuple(),
                      out_graph_path=    None,
                      out_imports=       tuple(),
                      out_graph=         None,
                      prefixes=          tuple(),
                      force_remote=      False,
                      checkout_ok=       ont_checkout_ok,
                      scigraph=          None,
                      iri=               None,
                      sources=           tuple(),
                      source_file=       None,
                      use_local_import_paths=True):
        # FIXME suffixes seem like a bad way to have done this :/
        """ We set this up to work this way because we can't
            instantiate graphBase, it is a super class that needs
            to be configurable and it needs to do so globally.
            All the default values here are examples and not real.
            You should write a local `def config` function as part
            of your local setup that replicates that arguments of
            configureGraphIO.

            Example:
            def config(remote_base=       'http://someurl.org/remote/ontology/',
                       local_base=        '/home/user/git/ontology/',
                       branch=            'master',
                       core_graph_paths= ['local/path/localCore.ttl',
                                          'local/path/localClasses.ttl'],
                       core_graph=        None,
                       in_graph_paths=    tuple(),
                       out_graph_path=    '/tmp/outputGraph.ttl',
                       out_imports=      ['local/path/localCore.ttl'],
                       out_graph=         None,
                       prefixes=          {'hello':'http://world.org/'}
                       force_remote=      False,
                       checkout_ok=       False,
                       scigraph=          'http://scigraph.mydomain.org:9000/scigraph'):
            graphBase.configGraphIO(remote_base, local_base, branch,
                                    core_graph_paths, core_graph,
                                    in_graph_paths,
                                    out_graph_path, out_imports, out_graph,
                                    force_remote, checkout_ok, scigraph)

        """

        if local_base is None:
            local_base = devconfig.ontology_local_repo
        graphBase.local_base = Path(local_base).expanduser()
        graphBase.remote_base = remote_base

        def makeLocalRemote(suffixes):
            remote = [os.path.join(graphBase.remote_base, branch, s)
                      if '://' not in s else  # 'remote' is file:// or http[s]://
                      s for s in suffixes]
            # TODO the whole thing needs to be reworked to not use suffixes...
            local = [(graphBase.local_base / s).as_posix()
                     if '://' not in s else
                     ((graphBase.local_base / s.replace(graphBase.remote_base, '').strip('/')).as_uri()
                      if graphBase.remote_base in s else s)  # FIXME this breaks the semanics of local?
                      for s in suffixes]
            return remote, local

        # file location setup
        remote_core_paths,  local_core_paths =  makeLocalRemote(core_graph_paths)
        remote_in_paths,    local_in_paths =    makeLocalRemote(in_graph_paths)
        remote_out_imports, local_out_imports = makeLocalRemote(out_imports)

        out_graph_paths = [out_graph_path]
        remote_out_paths, local_out_paths = makeLocalRemote(out_graph_paths)  # XXX fail w/ tmp
        remote_out_paths = local_out_paths  # can't write to a remote server without magic

        if not force_remote and graphBase.local_base.exists():
            repo = Repo(local_base)
            if repo.active_branch.name != branch and not checkout_ok:
                raise FileNotFoundError('Local git repo not on %s branch!\n'
                                        'Please run `git checkout %s` in %s, '
                                        'set NIFSTD_CHECKOUT_OK= via export or '
                                        'at runtime, or set checkout_ok=True.'
                                        % (branch, branch, local_base))
            elif checkout_ok:
                graphBase.repo = repo
                graphBase.working_branch = 'neurons'
                graphBase.original_branch = repo.active_branch
                graphBase.set_repo_state()
            use_core_paths = local_core_paths
            use_in_paths = local_in_paths
        else:
            if not force_remote:
                print("Warning local ontology path '%s' not found!" % local_base)
            use_core_paths = remote_core_paths
            use_in_paths = remote_in_paths

        # core graph setup
        if core_graph is None:
            core_graph = rdflib.Graph()
        for cg in use_core_paths:
            try:
                core_graph.parse(cg, format='turtle')
            except (FileNotFoundError, HTTPError) as e:
                # TODO failover to local if we were remote?
                print(tc.red('WARNING:'), f'no file found for core graph at {cg}')
        graphBase.core_graph = core_graph

        # store prefixes
        if isinstance(prefixes, dict):
            graphBase.prefixes = prefixes
        else:
            graphBase.prefixes = makePrefixes(*prefixes)

        PREFIXES = {**graphBase.prefixes, **uPREFIXES}

        # input graph setup
        in_graph = core_graph
        for ig in use_in_paths:
            in_graph.parse(ig, format='turtle')

        nin_graph = makeGraph('', prefixes=PREFIXES, graph=in_graph)
        graphBase.in_graph = in_graph

        # output graph setup
        if out_graph is None:
            _sources = sources
            _source_file = source_file
            class NeurOnt(Ont):  # FIXME this is super misleading wrt the source ...
                path = 'ttl/generated/neurons/'
                #filename = 'to-be-set-later'
                prefixes = PREFIXES
                sources = _sources
                source_file = _source_file
                # FIXME temp fix for issue with wgb in core
                wasGeneratedBy = ('https://github.com/tgbugs/pyontutils/blob/'
                                  '{commit}/'
                                  '{file}'
                                  '{hash_L_line}')

            no = NeurOnt()
            out_graph = no.graph
            graphBase.ng = no._graph

            #out_graph = rdflib.Graph()
            # in thise case we also want to wipe any existing python Neuron entires
            # that we use to serialize so that behavior is consistent
            NeuronBase.existing_pes = {}
            NeuronBase.existing_ids = {}
        else:
            no = None
            graphBase.ng = makeGraph('', prefixes=PREFIXES, graph=out_graph)
        #new_graph = makeGraph('', prefixes=PREFIXES, graph=out_graph)
        graphBase.out_graph = out_graph

        # makeGraph setup
        new_graph = graphBase.ng #= new_graph
        new_graph.filename = out_graph_path

        if iri is not None:
            ontid = rdflib.URIRef(iri)
        else:
            ontid = rdflib.URIRef('file://' + out_graph_path)  # do not use Path().absolute() it will leak

        if use_local_import_paths:
            new_graph.add_trip(ontid, rdf.type, owl.Ontology)
            for local_out_import in local_out_imports:  # TODO flip switch between local and remote import behavior
                new_graph.add_trip(ontid, owl.imports, rdflib.URIRef(local_out_import))  # core should be in the import closure
        else:
            new_graph.add_trip(ontid, rdf.type, owl.Ontology)
            for remote_out_import in remote_out_imports:  # TODO flip switch between local and remote import behavior
                new_graph.add_trip(ontid, owl.imports, rdflib.URIRef(remote_out_import))  # core should be in the import closure

        if no is not None:
            no()  # populate generated by info

        # set predicates
        graphBase._predicates = getPhenotypePredicates(graphBase.core_graph)

        # scigraph setup
        if scigraph is not None:
            graphBase._sgv = Vocabulary(cache=True, basePath=scigraph)
        else:
            graphBase._sgv = Vocabulary(cache=True)

    @staticmethod
    def write():
        og = cull_prefixes(graphBase.out_graph, prefixes={**graphBase.prefixes, **uPREFIXES})
        og.filename = graphBase.ng.filename
        og.write()

    @staticmethod
    def filename_python():
        p = PPath(graphBase.ng.filename)
        return p.with_name(p.name.replace('-', '_')).with_suffix('.py').as_posix()

    @staticmethod
    def write_python():
        with open(graphBase.filename_python(), 'wt') as f:
            f.write(graphBase.python())

    @staticmethod
    def python():
        out = '#!/usr/bin/env python3.6\n'
        out += f'from {graphBase.__import_name__} import *\n\n'
        _prefixes = {k:str(v) for k, v in graphBase.ng.namespaces.items()
                     if k not in uPREFIXES and k != 'xml' and k != 'xsd'}  # FIXME don't hardcode xml xsd
        len_thing = len(f'Config({graphBase.ng.name!r}, prefixes={{')
        prefixes = (f', prefixes={pformat(_prefixes, 0)}'.replace('\n', '\n' + ' ' * len_thing)
                    if _prefixes
                    else '')
        # FIXME prefixes should be separate so they are accessible in the namespace
        out += f'Config({graphBase.ng.name!r}{prefixes})\n\n'  # FIXME this is from neurons.lang
        _subs = [inspect.getsource(c) for c in subclasses(NeuronEBM)]  # FIXME are cuts sco ebms?
        subs = '\n' + '\n\n'.join(_subs) + '\n\n' if _subs else ''
        out += f'{subs}'
        #out += '\n\n'.join('\n'.join(('# ' + n.label, '# ' + n._origLabel, str(n))) for n in neurons)
        out += '\n\n'.join('\n'.join(('# ' + n.label, str(n))) for n in graphBase.neurons()) # FIXME this does not reset correctly when a new Controller is created, it probably should...
        return out

    @staticmethod
    def ttl():
        og = cull_prefixes(graphBase.out_graph, prefixes=uPREFIXES)
        return og.g.serialize(format='nifttl').decode()

    @staticmethod
    def neurons():
        return sorted(NeuronBase.existing_pes)

    def disjointWith(self, *others):
        for other in others:
            if isinstance(other, self.__class__):
                self.out_graph.add((self.id_, owl.disjointWith, other.id_))
            else:
                self.out_graph.add((self.id_, owl.disjointWith, other))

        return self

    def equivalentClass(self, *others):
        for other in others:
            if isinstance(other, self.__class__):
                #if isinstance(other, NegPhenotype):  # FIXME maybe this is the issue with neg equivs?
                self.out_graph.add((self.id_, owl.equivalentClass, other.id_))
            else:
                self.out_graph.add((self.id_, owl.equivalentClass, other))

        return self

    def subClassOf(self, *others):
        for other in others:
            if isinstance(other, self.__class__):
                self.out_graph.add((self.id_, rdfs.subClassOf, other.id_))
            else:
                self.out_graph.add((self.id_, rdfs.subClassOf, other))

        return self


class Phenotype(graphBase):  # this is really just a 2 tuple...  # FIXME +/- needs to work here too? TODO sorting
    _rank = '0'
    local_names = {
        'NCBITaxon:10116':'Rat',
        'CHEBI:16865':'GABA',
        'PR:000004967':'CB',
        'PR:000004968':'CR',
        'PR:000011387':'NPY',
        'PR:000015665':'SOM',
        #'NIFMOL:nifext_6':'PV',
        'PR:000013502':'PV',
        'PR:000017299':'VIP',
        'PR:000005110':'CCK',
        'ilxtr:PetillaSustainedAccomodatingPhenotype':'AC',
        'ilxtr:PetillaSustainedNonAccomodatingPhenotype':'NAC',
        'ilxtr:PetillaSustainedStutteringPhenotype':'STUT',
        'ilxtr:PetillaSustainedIrregularPhenotype':'IR',
        'ilxtr:PetillaInitialBurstSpikingPhenotype':'b',
        'ilxtr:PetillaInitialClassicalSpikingPhenotype':'c',
        'ilxtr:PetillaInitialDelayedSpikingPhenotype':'d',
        'UBERON:0005390':'L1',
        'UBERON:0005391':'L2',
        'UBERON:0005392':'L3',
        'UBERON:0005393':'L4',
        'UBERON:0005394':'L5',
        'UBERON:0005395':'L6',
        'UBERON:0003881':'CA1',
        'UBERON:0003882':'CA2',
        'UBERON:0003883':'CA3',
        'UBERON:0001950':'Neocortex',
        'UBERON:0008933':'S1',
    }
    def __init__(self, phenotype, ObjectProperty=None, label=None, override=False):
        # label blackholes
        # TODO implement local names here? or at a layer above? (above)
        super().__init__()
        if isinstance(phenotype, Phenotype):  # simplifies negation of a phenotype
            ObjectProperty = phenotype.e
            phenotype = phenotype.p

        self.p = self.checkPhenotype(phenotype)
        if ObjectProperty is None:
            self.e = self.getObjectProperty(self.p)
        else:
            self.e = self.checkObjectProperty(ObjectProperty)  # FIXME this doesn't seem to work

        self._pClass = infixowl.Class(self.p, graph=self.in_graph)
        self._eClass = infixowl.Class(self.e, graph=self.in_graph)
        # do not call graphify here because phenotype edges may be reused in multiple places in the graph

        if label is not None and override:
            self.in_graph.add((self.p, rdfs.label, rdflib.Literal(label)))

        # use this specify consistent patterns for modifying labels
        self.labelPostRule = lambda l: l

    def checkPhenotype(self, phenotype):
        subject = self.expand(phenotype)
        try: next(self.core_graph.predicate_objects(subject))
        except StopIteration:  # is a phenotype derived from an external class
            try:
                if not self._sgv.findById(subject):
                    print(tc.red('WARNING:'), 'Unknown phenotype', subject)
            except ConnectionError:
                print(tc.red('WARNING:'), 'Phenotype unvalidated. No SciGraph was instance found at',
                      self._sgv._basePath)
        return subject

    def getObjectProperty(self, phenotype):
        predicates = list(self.in_graph.objects(phenotype, self.expand('ilxtr:useObjectProperty')))  # useObjectProperty works for phenotypes we control

        if predicates:
            return predicates[0]
        else:
            # TODO check if falls in one of the expression categories
            predicates = [_[1] for _ in self.in_graph.subject_predicates(phenotype) if _ in self._predicates.__dict__.values()]
            mapping = {
                'NCBITaxon':self._predicates.hasInstanceInSpecies,
                'CHEBI':self._predicates.hasExpressionPhenotype,
                'PR':self._predicates.hasExpressionPhenotype,
                'NCBIGene':self._predicates.hasExpressionPhenotype,
                'UBERON':self._predicates.hasSomaLocatedIn,
                #'UBERON':self._predicates.hasLayerLocationPhenotype,  # a very short list is needed here
            }
            prefix = self.in_graph.namespace_manager.qname(phenotype).split(':')[0]  # FIXME DANGERZONE
            if prefix in mapping:
                return mapping[prefix]
            return self.expand(PHENO_ROOT)

    def checkObjectProperty(self, ObjectProperty):  # FIXME this doesn't seem to work
        op = self.expand(ObjectProperty)
        if op in self._predicates.__dict__.values():
            return op
        else:
            raise TypeError('WARNING: Unknown ObjectProperty %s' % repr(op))

    @property
    def eLabel(self):
        return next(self._eClass.label)

    @property
    def pLabel(self):
        l = tuple(self._pClass.label)
        if not l:  # we don't want to load the whole ontology
            try:
                l = self._sgv.findById(self.p)['labels'][0]
            except ConnectionError as e:
                print(e)
                l = self.ng.qname(self.p)
            except TypeError:
                l = self.ng.qname(self.p)
            except IndexError:
                l = self.ng.qname(self.p)
        else:
            l = l[0]
        return self.labelPostRule(l)


    @property
    def pHiddenLabel(self):
        l = tuple(self.in_graph.objects(self.p, rdflib.namespace.SKOS.hiddenLabel))
        if l:
            l = l[0]
        else:
            l = self.pShortName  # FIXME

        return self.labelPostRule(l)

    @property
    def pShortName(self):
        inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
        if self in inj:
            return inj[self]

        pn = self.in_graph.namespace_manager.qname(self.p)
        try:
            resp = self._sgv.findById(pn)
        except ConnectionError as e:
            print(tc.red('WARNING:'), f'Could not set label for {pn}. No SciGraph was instance found at', self._sgv._basePath)
            resp = None

        if resp:  # DERP
            abvs = resp['abbreviations']
        else:
            abvs = None

        if abvs:
            return abvs[0]
        elif pn in self.local_names:
            return self.local_names[pn]
        else:
            return ''

    @property
    def predicates(self):
        yield self.e

    @property
    def objects(self):
        yield self.p

    def _uri_frag(self, index):
        return (self._rank +
                f'-p{index(self.e)}-' +
                self.ng.qname(self.p).replace(':','-'))
        #yield from (self._rank + '/{}/' + self.ng.qname(_) for _ in self.objects)

    def _graphify(self, graph=None):
        if graph is None:
            graph = self.out_graph
        return infixowl.Restriction(onProperty=self.e, someValuesFrom=self.p, graph=graph)

    def __lt__(self, other):
        if type(other) == type(self):
            return sorted((self.p, other.p))[0] == self.p  # FIXME bad...
        elif type(other) == LogicalPhenotype:
            return True
        elif type(self) == Phenotype:
            return True
        else:
            return False

    def __gt__(self, other):
        return not self.__lt__(other)

    def __eq__(self, other):
        return type(self) == type(other) and self.p == other.p and self.e == other.e

    def __hash__(self):
        return hash((self.p, self.e))

    def __expanded__(self):
        pn = self.in_graph.namespace_manager.qname(self.p)
        en = self.in_graph.namespace_manager.qname(self.e)
        lab = self.pLabel
        return "%s('%s', '%s', label='%s')" % (self.__class__.__name__, pn, en, lab)

    def __repr__(self):
        #inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
        #if self in inj:
            #return inj[self]
        #else:
        return self.__expanded__()

    def __str__(self):
        pn = self.in_graph.namespace_manager.qname(self.p)
        en = self.in_graph.namespace_manager.qname(self.e)
        lab = str(self.pLabel)
        t = ' ' * (len(self.__class__.__name__) + 1)
        return f"{self.__class__.__name__}({pn!r},\n{t}{en!r},\n{t}label={lab!r})"
        #return "%s('%s',\n%s'%s',\n%slabel='%s')" % (self.__class__.__name__, pn, t, en, t, lab)


class NegPhenotype(Phenotype):
    _rank = '1'
    """ Class for Negative Phenotypes to simplfy things """


class LogicalPhenotype(graphBase):
    _rank = '2'
    local_names = {
        AND:'AND',
        OR:'OR',
    }
    def __init__(self, op, *edges):
        super().__init__()
        self.op = op  # TODO more with op
        self.pes = edges
        self.labelPostRule = lambda l: l

    @property
    def p(self):
        return tuple((pe.p for pe in self.pes))

    @property
    def e(self):
        return tuple((pe.e for pe in self.pes))

    @property
    def pLabel(self):
        return f'({self.op} ' + ' '.join(self.ng.qname(p) for p in self.p) + ')'

    @property
    def pHiddenLabel(self):
        label = ' '.join([pe.pHiddenLabel for pe in self.pes])  # FIXME we need to catch non-existent phenotypes BEFORE we try to get their hiddenLabel because the errors you get here are completely opaque
        op = self.local_names[self.op]
        return self.labelPostRule('(%s %s)' % (op, label))

    @property
    def pShortName(self):
        inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
        if self in inj:
            return inj[self]
        return self.labelPostRule(''.join([pe.pShortName for pe in self.pes]))

    @property
    def predicates(self):
        for pe in sorted(self.pes):
            yield pe.e

    @property
    def objects(self):
        for pe in sorted(self.pes):
            yield pe.p

    def _uri_frag(self, index):
        rank = '4' if self.op == AND else '5'  # OR
        return '-'.join(sorted((rank + f'-p{index(pe.e)}-' + self.ng.qname(pe.p).replace(':','-')
                                for pe in sorted(self.pes)), key=natsort))

    def _graphify(self, graph=None):
        if graph is None:
            graph = self.out_graph
        members = []
        for pe in self.pes:  # FIXME fails to work properly for negative phenotypes...
            members.append(pe._graphify(graph=graph))
        return infixowl.BooleanClass(operator=self.expand(self.op), members=members, graph=graph)

    def __lt__(self, other):
        if type(other) == type(self):
            return sorted((self.p, other.p))[0] == self.p  # FIXME bad...
        else:
            return False

    def __gt__(self, other):
        return not self.__lt__(other)

    def __eq__(self, other):
        if type(other) == type(self):
            for a, b in zip(sorted(self.pes), sorted(other.pes)):
                if a != b:
                    return False
            return True
        else:
            return False

    def __hash__(self):
        return hash(tuple(sorted(self.pes)))

    def __repr__(self):
        op = self.local_names[self.ng.qname(self.expand(self.op))]  # FIXME inefficient but safe
        pes = ", ".join([_.__repr__() for _ in self.pes])
        return "%s(%s, %s)" % (self.__class__.__name__, op, pes)

    def __str__(self):
        op = self.local_names[self.ng.qname(self.expand(self.op))]  # FIXME inefficient but safe
        t =  ' ' * (len(self.__class__.__name__) + 1)
        base =',\n%s' % t
        pes = base.join([_.__str__().replace('\n', '\n' + t) for _ in self.pes])
        return '%s(%s%s%s)' % (self.__class__.__name__, op, base, pes)


class NeuronBase(graphBase):
    owlClass = _NEURON_CLASS
    shortname = None
    existing_pes = {}
    existing_ids = {}
    ids_pes = {}
    pes_ids = {}
    __context = tuple()  # this cannot be changed after __init__, neurons are not dynamic
    def __init__(self, *phenotypeEdges, id_=None, label=None, override=False):
        super().__init__()
        self.ORDER = [
            # FIXME it may make more sense to manage this in the NeuronArranger
            # so that it can interconvert the two representations
            # this is really high overhead to load this here
            self._predicates.hasInstanceInSpecies,
            self._predicates.hasTaxonRank,
            # TODO hasDevelopmentalStage   !!!!! FIXME
            self._predicates.hasLocationPhenotype,  # FIXME
            self._predicates.hasSomaLocatedIn,  # hasSomaLocation?
            self._predicates.hasLayerLocationPhenotype,  # TODO soma naming...
            self._predicates.hasDendriteMorphologicalPhenotype,
            self._predicates.hasDendriteLocatedIn,
            self._predicates.hasAxonLocatedIn,
            self._predicates.hasMorphologicalPhenotype,
            self._predicates.hasElectrophysiologicalPhenotype,
            #self._predicates.hasSpikingPhenotype,  # TODO do we need this?
            self.expand('ilxtr:hasSpikingPhenotype'),  # legacy support
            self._predicates.hasExpressionPhenotype,
            self._predicates.hasNeurotransmitterPhenotype,
            self._predicates.hasCircuitRolePhenotype,
            self._predicates.hasProjectionPhenotype,  # consider inserting after end, requires rework of code...
            self._predicates.hasExperimentalPhenotype,
            self._predicates.hasPhenotype,  # last
        ]

        self._localContext = self.__context
        phenotypeEdges = tuple(set(self._localContext + phenotypeEdges))  # remove dupes

        if id_ and phenotypeEdges:
            self.id_ = self.expand(id_)
            print('WARNING: you may be redefining a neuron!')
            #raise TypeError('This has not been implemented yet. This could serve as a way to validate a match or assign an id manually?')
        elif id_:
            self.id_ = self.expand(id_)
        elif phenotypeEdges:
            #asdf = str(tuple(sorted((_.e, _.p) for _ in phenotypeEdges)))  # works except for logical phenotypes
            #self.id_ = self.expand(ILXREPLACE(str(tuple(sorted(phenotypeEdges)))))  # XXX beware changing how __str__ works... really need to do this
            #self.id_ = TEMP[str(tuple(sorted(phenotypeEdges))).replace(' ','_').replace("'","=")]  # XXX beware changing how __str__ works... really need to do this

            frag = '-'.join(sorted((pe._uri_frag(self.ORDER.index)
                                    for pe in phenotypeEdges),
                                   key=natsort))
                                       #*(f'p{self.ORDER.index(p)}/{self.ng.qname(o)}'
                                         #for p, o in sorted(zip(pe.predicates,
                                                                #pe.objects)))))
            self.id_ = TEMP[frag]  # XXX beware changing how __str__ works... really need to do this
        else:
            raise TypeError('Neither phenotypeEdges nor id_ were supplied!')


        if not phenotypeEdges and id_ is not None:
            self.Class = infixowl.Class(self.id_, graph=self.in_graph)  # IN
            phenotypeEdges = self.bagExisting()  # rebuild the bag from the -class- id

        self.pes = tuple(sorted(sorted(phenotypeEdges), key=lambda pe: self.ORDER.index(pe.e) if pe.e in self.ORDER else len(self.ORDER) + 1))
        self.validate()

        self.Class = infixowl.Class(self.id_, graph=self.out_graph)  # once we get the data from existing, prep to dump OUT


        self.phenotypes = set((pe.p for pe in self.pes))
        self.edges = set((pe.e for pe in self.pes))
        self._pesDict = {}
        for pe in self.pes:  # FIXME TODO
            if pe.e in self._pesDict:
                self._pesDict[pe.e].append(pe)
            else:
                self._pesDict[pe.e] = [pe]

        self._origLabel = label
        self._override = override

        if self in self.existing_pes and self.Class.graph is self.existing_pes[self].graph:
            self.Class = self.existing_pes[self]
        else:
            self.Class = self._graphify()
            self.Class.label = rdflib.Literal(self.label)  # FIXME this seems... broken?
            self.existing_pes[self] = self.Class

    def _tuplesToPes(self, pes):
        for p, e in pes:
            yield Phenotype(p, e)

    @staticmethod
    def setContext(*neuron_or_phenotypeEdges):
        # this is a trade off, depending on what was passed in here when it
        # was last called the same 'looking' neuron definition will produce
        # a different result
        # of course this can be very powerful if we have a set of neurons that
        # we want to instantiate in different contexts

        # we are implementing this in this way so that it is clear that you cannot
        # change the context of a neuron after it has been created
        if not neuron_or_phenotypeEdges:
            NeuronBase._NeuronBase__context = tuple()
        else:
            def getPhenotypeEdges(thing):
                if isinstance(thing, NeuronBase):
                    return (*thing.pes,)
                elif isinstance(thing, Phenotype) or isinstance(thing, LogicalPhenotype):
                    return thing,
                else:
                    raise TypeError('%s is neither a Neuron nor a Phenotype.' % thing)

            if hasattr(neuron_or_phenotypeEdges, '__iter__'):
                pes = tuple(pe for nope in neuron_or_phenotypeEdges for pe in getPhenotypeEdges(nope))
            else:
                pes = getPhenotypeEdges(neuron_or_phenotypeEdges)

            NeuronBase._NeuronBase__context = pes

    @staticmethod
    def getContext():
        return NeuronBase.__context

    @property
    def context(self):
        """ No touching! """
        return self._localContext

    @context.setter
    def context(self, neuron_or_phenotypeEdges):
        raise TypeError('Cannot change the context of an instantiated neuron.')

    @property
    def _shortname(self):
        return f'({self.shortname})' if self.shortname else ''


    @property
    def label(self):  # FIXME for some reasons this doesn't always make it to the end?
        if self._override and self._origLabel is not None:
            self.Class.label = (rdflib.Literal(self._origLabel),)
            return self._origLabel
        else:
            return self.genLabel

    @property
    def genLabel(self):
        # TODO predicate actions are the right way to implement the transforms here
        def sublab(edge):
            sublabs = []
            if edge in self._pesDict:
                for pe in self._pesDict[edge]:
                    l = pe.pShortName
                    if not l:
                        l = pe.pHiddenLabel
                    if not l:
                        l = pe.pLabel

                    if pe.e == self._predicates.hasExpressionPhenotype:
                        if type(pe) == NegPhenotype:
                            l = '-' + l
                        else:
                            l = '+' + l  # this is backward from the 'traditional' placement of the + but it makes this visually much cleaner and eaiser to understand
                    elif pe.e == self._predicates.hasProjectionPhenotype:
                        l = 'Projecting To ' + l
                    elif pe.e == self._predicates.hasDendriteLocatedIn:
                        l = 'With dendrite in ' + l  # 'Toward' in bbp speak

                    sublabs.append(l)

            return sublabs

        label = []
        for edge in self.ORDER:
            label += sorted(sublab(edge))
            logical = (edge, edge)
            if logical in self._pesDict:
                label += sorted(sublab(logical))

        # species
        # developmental stage
        # brain region
        # morphology
        # ephys
        # expression
        # dendrites
        # projection
        # cell type specific connectivity?
        # circuit role? (principle interneuron...)
        if not label:
            label.append('????')
        nin_switch = 'interneuron' if Phenotype('ilxtr:InterneuronPhenotype', self._predicates.hasCircuitRolePhenotype) in self.pes else 'neuron'
        label.append(nin_switch)
        if self._shortname:
            label.append(self._shortname)

        new_label = ' '.join(label)
        if not self._override:
            self.Class.label = (rdflib.Literal(new_label),)
        #try:
            #print(next(self.Class.label))  # FIXME need to set the label once we generate it and overwrite the old one...
        #except StopIteration:
            #print(new_label)
        return new_label

    def realize(self):  # TODO use ilx_utils
        """ Get an identifier """
        self.id_ = 'ILX:1234567'

    def validate(self):
        raise TypeError('Ur Neuron Sucks')

    def __expanded__(self):
        args = '(' + ', '.join([_.__expanded__() for _ in self.pes]) + ')'
        return '%s%s' % (self.__class__.__name__, args)

    def __repr__(self):  # TODO use local_names (since we will bind them in globals, but we do need a rule, and local names do need to be to pairs or full logicals? eg L2L3 issue
        inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
        lab =  f", label={str(self._origLabel) + ' ' + self._shortname!r}" if self._origLabel else ''
        args = '(' + ', '.join([inj[_] if _ in inj else repr(_) for _ in self.pes]) + f'{lab})'
        #args = self.pes if len(self.pes) > 1 else '(%r)' % self.pes[0]  # trailing comma
        return '%s%s' % (self.__class__.__name__, args)

    def __str__(self):
        asdf = '%s(' % self.__class__.__name__
        for i, pe in enumerate(self.pes):
            t = ' ' * (len(self.__class__.__name__) + 1)
            if i:
                asdf += ',\n' + t + ('%s' % pe).replace('\n', '\n' + t)
            else:
                asdf += ('%s' % pe).replace('\n', '\n' + t)
        lab =  ',\n' + t + f"label={str(self._origLabel) + ' ' + self._shortname!r}" if self._origLabel else ''
        asdf += lab
        asdf += ')'
        return asdf

    def __hash__(self):
        return hash((self.__class__.__name__, self.pes))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __lt__(self, other):
        return repr(self.pes) < repr(other.pes)

    def __gt__(self, other):
        return not self.__lt__(other)

    def __add__(self, other):
        return self.__class__(*self.pes, *other.pes)

    def __radd__(self, other):
        if type(other) is int:  # sum() starts at 0
            return self
        else:
            return self.__class__(*self.pes, *other.pes)

    def __enter__(self):
        """ Using a neuron in a context manager treats it as context! """
        self._old_context = self.getContext()
        self.setContext(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.setContext(*self._old_context)
        del self._old_context


class Neuron(NeuronBase):
    """ Class that takes a bag of phenotypes and adds equivalentClass axioms"""

    def validate(self):
        # Fact++ factpp can do some reasoning bits, but struggles with disjoint classes that are SubClasses of themselves :/
        # until factpp is working more seemlessly (tricky given the size of certain phenotype proxy ontologies)
        # we will use a set of huristics to validate whether certain basic invariants are met

        # invariants
        # disjoint species
        # disjoint brain regions (force explicit use of LogicalPhenotype(OR, a, b))
        # disjoint layers
        # disjoint morphological phenotypes
        # NO disjoint ephys types we settle on allowing multiple, since we can't reasonably expect users
        #  to dissociate a neuron at time 1 and time 2 as being distinct (even if that is true)
        #  can't use logical OR for this because BOTH are present in the same neuron under different conditions

        disjoints = [  # FIXME there has got to be a better place to do this :/
            self._predicates.hasInstanceInSpecies,
            self._predicates.hasSomaLocatedIn,
            self._predicates.hasLayerLocationPhenotype,  # FIXME coping with cases that force unionOf?
            self._predicates.hasMorphologicalPhenotype,
        ]

        for disjoint in disjoints:
            phenos = [pe for pe in self.pes if pe.e == disjoint]
            if len(phenos) > 1:
                raise TypeError(f'Disjointness violated for {disjoint} due to {phenos}')

        # subClassOf restrictions (hacked impl using curie prefixes as a proxy)
        # no panther
        # no uberon
        usage_ok = {UBERON['0000955'], UBERON['0001950']}
        for invalid_superclass, predicate in (('UBERON', self._predicates.hasSomaLocatedIn),):
            for pe in self.pes:
                if pe.e == predicate and pe.p not in usage_ok and invalid_superclass in pe.p:
                    print(tc.red(f'WARNING: subClassOf restriction violated for {invalid_superclass} due to {pe}'))
                    #raise TypeError(f'subClassOf restriction violated for {invalid_superclass} due to {pe}')  # TODO can't quite switch this on yet, breaks too many examples

        # species matched identifiers TODO
        # developmental stages (if we use the uberon associated ones)
        # parcellation schemes
        # NCBIGene ilxtr:definedForTaxon  # FIXME this needs to be a real OP!
        # PR ??

    def bagExisting(self):  # TODO intersections
        out = set()  # prevent duplicates in cases where phenotypes are duplicated in the hierarchy
        for c in self.Class.equivalentClass:
            pe = self._unpackPheno(c)
            if pe:
                if isinstance(pe, tuple):  # we hit a case where we need to inherit phenos from above
                    out.update(pe)
                else:
                    out.add(pe)

        for c in self.Class.disjointWith:
            print(c)
            pe = self._unpackPheno(c, NegPhenotype)
            if pe:
                out.add(pe)

        return tuple(out)

        # the SPARQL equivalent that we are not using
        # qname = self.out_graph.namespace_manager.qname(self.id_)
        # qstring = """
        # SELECT DISTINCT ?match ?edge WHERE {
        # %s owl:equivalentClass/owl:intersectionOf/rdf:rest*/rdf:first ?item .
        # ?item rdf:type owl:Restriction .
        # ?edge rdfs:subPropertyOf* %s .
        # ?item owl:onProperty ?edge .
        # ?item owl:someValuesFrom ?match . }""" % (qname, PHENO_ROOT)
        # pes = self.in_graph.query(qstring)
        # out = tuple(self._tuplesToPes(pes))
        # return out

    def _unpackPheno(self, c, type_=Phenotype):  # FIXME need to deal with intersections
        if isinstance(c.identifier, rdflib.BNode):
            putativeRestriction = infixowl.CastClass(c, graph=self.in_graph)
            if isinstance(putativeRestriction, infixowl.BooleanClass):
                bc = putativeRestriction
                op = bc._operator
                pes = []
                for id_ in bc._rdfList:
                    #print(id_)
                    pr = infixowl.CastClass(id_, graph=self.in_graph)
                    if isinstance(pr, infixowl.BooleanClass):
                        lpe = self._unpackLogical(pr)
                        pes.append(lpe)
                        continue
                    if isinstance(pr, infixowl.Class):
                        if id_ == self.expand(self.owlClass):
                            #print('we got neuron root', id_)
                            continue
                        else:
                            pass  # it is a restriction

                    p = pr.someValuesFrom  # if _NEURON_CLASS is not a owl:Class > problems
                    e = pr.onProperty
                    pes.append(type_(p, e))
                return tuple(pes)
            else:
                print('WHAT')  # FIXME something is wrong for negative phenotypes...
                pr = putativeRestriction
                p = pr.someValuesFrom
                e = pr.onProperty
                if p and e:
                    return type_(p, e)
                else:
                    print(putativeRestriction)
        else:
            # TODO make sure that Neuron is in there somehwere...
            print('what is this thing?', c)

    def _unpackLogical(self, bc, type_=Phenotype):  # TODO this will be needed for disjoint as well
        op = bc._operator
        pes = []
        for id_ in bc._rdfList:
            pr = infixowl.CastClass(id_, graph=self.in_graph)
            p = pr.someValuesFrom
            e = pr.onProperty
            pes.append(type_(p, e))
        return LogicalPhenotype(op, *pes)

    def _graphify(self, *args, graph=None): #  defined
        """ Lift phenotypeEdges to Restrictions """
        if graph is None:
            graph = self.out_graph

        if self._origLabel and self._override:
            graph.add((self.id_, ilxtr.genLabel, rdflib.Literal(self.genLabel)))

        members = [self.expand(self.owlClass)]
        for pe in self.pes:
            target = pe._graphify(graph=graph)
            if isinstance(pe, NegPhenotype):  # isinstance will match NegPhenotype -> Phenotype
                #self.Class.disjointWith = [target]  # FIXME for defined neurons this is what we need and I think it is strong than the complementOf version
                djc = infixowl.Class(graph=graph)  # TODO for generic neurons this is what we need
                djc.complementOf = target
                members.append(djc)
            else:
                members.append(target)  # FIXME negative logical phenotypes :/
        intersection = infixowl.BooleanClass(members=members, graph=graph)  # FIXME dupes
        #existing = list(self.Class.equivalentClass)
        #if existing or str(pe.pLabel) == 'Htr3a':
            #embed()
        ec = [intersection]
        self.Class.equivalentClass = ec
        return self.Class


class NeuronCUT(Neuron):
    owlClass = _CUT_CLASS


class NeuronEBM(Neuron):
    owlClass = _EBM_CLASS

    def __new__(cls, *args, **kwargs):
        if cls.owlClass != _EBM_CLASS:
            cls.ng.add_trip(cls.owlClass, rdfs.subClassOf, _EBM_CLASS)
        return super().__new__(cls)

class TypeNeuron(Neuron):  # TODO
    """ TypeNeurons modify how NegPhenotype works, shifting to disjointWith.
        TypeNeurons can be use to construct rules based taxonomies from
        collections of bindary phenotypes. """


class MeasuredNeuron(NeuronBase):  # XXX DEPRECATED retained for loading from some existing ontology files
    """ Class that takes a bag of phenotypes and adds subClassOf axioms"""
    # these should probably require a species and brain region bare minimum?
    # these need to check to make sure the species specific identifiers are being used
    # and warn on mismatch

    def bagExisting(self):  # FIXME intersection an union?
        out = set()  # prevent duplicates in cases where phenotypes are duplicated in the hierarchy
        for c in self.Class.subClassOf:
            pe = self._unpackPheno(c)
            if pe:
                if isinstance(pe, tuple):  # we hit a case where we need to inherit phenos from above
                    out.update(pe)
                else:
                    out.add(pe)
        for c in self.Class.disjointWith:
            pe = self._unpackPheno(c, NegPhenotype)
            if pe:
                out.add(pe)
        return tuple(out)

        # alternate SPARQL version
        # while using the qstring is nice from a documentation standpoint... it is sllllooowww
        # check out infixowl Class.__repr__ for a potentially faster way use CastClass...
        # qname = self.in_graph.namespace_manager.qname(self.id_)
        # qstring = """
        # SELECT DISTINCT ?match ?edge WHERE {
        # %s rdfs:subClassOf ?item .
        # ?item rdf:type owl:Restriction .
        # ?item owl:onProperty ?edge .
        # ?item owl:someValuesFrom ?match . }""" % qname
        # #print(qstring)
        # pes = list(self.in_graph.query(qstring))
        # #assert len(test) == 1, "%s" % test
        # if not pes:
        #     return self._getIntersectionPhenos(qname)
        # else:
        #     out = tuple(self._tuplesToPes(pes))
        #     #print(out)
        #     return out

    def _unpackPheno(self, c, type_=Phenotype):
        if isinstance(c.identifier, rdflib.BNode):
            putativeRestriction = infixowl.CastClass(c, graph=self.in_graph)
            if isinstance(putativeRestriction, infixowl.BooleanClass):
                bc = putativeRestriction
                op = bc._operator
                pes = []
                for id_ in bc._rdfList:
                    pr = infixowl.CastClass(id_, graph=self.in_graph)
                    p = pr.someValuesFrom
                    e = pr.onProperty
                    pes.append(type_(p, e))
                    #print(id_)
                return LogicalPhenotype(op, *pes)
            else:
                pr = putativeRestriction
                p = pr.someValuesFrom
                e = pr.onProperty
            if p and e:
                return type_(p, e)
            else:
                raise TypeError('Something is wrong', putativeRestriction)
        elif isinstance(c.identifier, rdflib.URIRef):
            pes = MeasuredNeuron(id_=c.identifier).pes  # FIXME cooperate with neuron manager?
            if pes:
                return pes

    def _getIntersectionPhenos(self, qname):
        qstring = """
        SELECT DISTINCT ?match ?edge WHERE {
        %s rdfs:subClassOf/owl:intersectionOf/rdf:rest*/rdf:first ?item .
        ?item rdf:type owl:Restriction .
        ?item owl:onProperty ?edge .
        ?item owl:someValuesFrom ?match . }""" % qname
        #print(qstring)
        pes = self.in_graph.query(qstring)
        out = tuple(self._tuplesToPes(pes))
        #print('------------------------')
        print(out)
        #print('------------------------')
        return out

    def _graphify(self):
        class_ = infixowl.Class(self.id_, graph=self.out_graph)
        class_.delete()  # delete any existing annotations to prevent duplication
        for pe in self.pes:
            target = pe._graphify()  # restriction or intersection
            if isinstance(pe, NegPhenotype):
                class_.disjointWith = [target]
            else:
                class_.subClassOf = [target]

        return class_

    def validate(self):
        'I am validated'

    def addEvidence(self, pe, evidence):
        # add an evidence structure...
        # should also be possible to pass in a pee (phenotype edge evidence) structure at __ini__
        pass


class NeuronArranger:  # TODO should this write the graph?
    """ Class that takes a list of data neurons and optimizes their taxonomy."""
    def __init__(self, *neurons, graph):
        pass

    def loadDefined(self):
        pass


# local naming and ordering


class injective(type):
    render_types = tuple()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return injective_dict()

    def __new__(cls, name, bases, inj_dict):
        self = super().__new__(cls, name, bases, dict(inj_dict))
        self.debug = False
        return self

    def __len__(self):
        return len([v for k in dir(self) for v in (getattr(self, k),)
                    if any(isinstance(v, t) for t in self.render_types)])

    def items(self):
        for k in dir(self):
            v = getattr(self, k)
            if any(isinstance(v, t) for t in self.render_types):
                yield k, v

    def __contains__(self, key):
        try:
            self.__getitem__(key)
            return True
        except:
            return False

    def __getitem__(self, key):
        print(key)
        v = getattr(self, key)
        if any(isinstance(v, t) for t in self.render_types):
            return v
        else:
            raise KeyError(f'{key} not in self.__class__.__name__')

    def __repr__(self):
        newline = '\n'
        t = ' ' * 4
        lnm = self.mro()[-2].__name__
        cname = 'class ' + self.__name__ + f'({lnm}):' + '\n'
        return  cname + '\n'.join(f'{t}{k:<8} = {repr(v).replace(newline, " ")}'
                                  for k in dir(self)
                                  for v in (getattr(self, k),)
                                  if any(isinstance(v, t) for t in self.render_types))

    def __enter__(self):
        stack = inspect.stack(0)
        if self.debug:
            s0 = stack[0]
            print(s0.function, Path(s0.filename).name, s0.lineno)
        g = stack_magic(stack)
        self._existing = set()
        setLocalNameBase(f'setBy_{self.__name__}', self.__name__, g)
        for k in dir(self):
            v = getattr(self, k)  # use this instead of __dict__ to get parents
            if any(isinstance(v, t) for t in self.render_types):
                if k in graphBase.LocalNames:  # name was in enclosing scope
                    self._existing.add(k)
                setLocalNameBase(k, v, g)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        stack = inspect.stack(0)
        if self.debug:
            s0 = stack[0]
            print(s0.function, Path(s0.filename).name, s0.lineno)
        g = stack_magic(stack)
        #g = inspect.stack(0)[-1][0].f_locals  #  get globals of calling scope
        for k in dir(self):
            v = getattr(self, k)  # use this instead of __dict__ to get parents
            if k not in self._existing and any(isinstance(v, t) for t in self.render_types):
                try:
                    g.pop(k)
                    graphBase.LocalNames.pop(k)  # this should only run if g pops correctly? XXX FIXME?
                except KeyError:
                    raise KeyError('%s not in globals, are you calling resetLocalNames from a local scope?' % k)


class LocalNameManager(metaclass=injective):
    """ Base class for sets of local names for phenotypes.
        Local name managers are singletons and do not need to be instantiated.
        Can be used in a context manager or globally via setLocalNames.
        It is possible to subclass to add your custom names to a core. """

    # TODO context dependent switches for making PAXRAT/PAXMOUSE transitions transparent

    render_types = Phenotype, LogicalPhenotype

    ORDER = (
        'ilxtr:hasInstanceInSpecies',
        'ilxtr:hasTaxonRank',
        'ilxtr:hasSomaLocatedIn',  # hasSomaLocation?
        'ilxtr:hasLayerLocationPhenotype',  # TODO soma naming...
        'ilxtr:hasDendriteMorphologicalPhenotype',
        'ilxtr:hasDendriteLocatedIn',
        'ilxtr:hasAxonLocatedIn',
        'ilxtr:hasMorphologicalPhenotype',
        'ilxtr:hasElectrophysiologicalPhenotype',
        'ilxtr:hasSpikingPhenotype',  # legacy support
        'ilxtr:hasExpressionPhenotype',
        'ilxtr:hasProjectionPhenotype',  # consider inserting after end, requires rework of code...
        'ilxtr:hasPhenotype',
    )

    #def __getitem__(self, key):  # just in case someone makes an instance by mistake
        #return self.__class__.__dict__[key]


def checkCalledInside(classname, stack):
    """ Fantastically inefficient! """
    ok = False
    for s in stack[1:]:
        cc = s.code_context[0]
        if 'class' in cc:
            if '(' in cc:
                bases = [b.strip() for b in cc.split('(')[1].split(')')[0].split(',')]
                for base_name in bases:
                    if base_name in s.frame.f_globals:
                        base = s.frame.f_globals[base_name]
                        for cls in base.__class__.mro(base):
                            if cls.__name__ == classname:
                                ok = True
                                break
                        if ok:
                            break
                if ok:
                    break
    if not ok:
        name = stack[0].function
        raise SyntaxError('%s not called inside a class inheriting from LocalNameManager' % name)

def addLNBase(LocalName, phenotype, g=None):
    inj = {v:k for k, v in graphBase.LocalNames.items()}
    if not LocalName.isidentifier():
        raise NameError('LocalName \'%s\' is no a valid python identifier' % LocalName)
    if g is None:
        raise TypeError('please pass in the globals for the calling scope')
    if LocalName in g and g[LocalName] != phenotype:
        raise NameError('%r is already in use as a LocalName for %r' % (LocalName, g[LocalName]))
    elif phenotype in inj and inj[phenotype] != LocalName:
        raise ValueError(('Mapping between LocalNames and phenotypes must be injective.\n'
                          'Cannot cannot bind %r to %r.\n'
                          'It is already bound to %r') % (LocalName, phenotype, inj[phenotype]))
    g[LocalName] = phenotype

def addLN(LocalName, phenotype, g=None):  # XXX deprecated
    if g is None:
        s = inspect.stack(0)  # horribly inefficient
        checkCalledInside('LocalNameManager', s)
        g = s[1][0].f_locals  # get globals of calling scope
    addLNBase(LocalName, phenotype, g)

def addLNT(LocalName, phenoId, predicate, g=None):  # XXX deprecated
    """ Add a local name for a phenotype from a pair of identifiers """
    if g is None:
        s = inspect.stack(0)  # horribly inefficient
        checkCalledInside('LocalNameManager', s)
        g = s[1][0].f_locals  # get globals of calling scope
    addLN(LocalName, Phenotype(phenoId, predicate), g)

def setLocalNameBase(LocalName, phenotype, g=None):
    addLNBase(LocalName, phenotype, g)
    graphBase.LocalNames[LocalName] = phenotype

def setLocalNames(*LNMClass, g=None):
    if g is None:
        g = inspect.stack(0)[1][0].f_globals  # get globals of calling scope
    if not LNMClass:
        resetLocalNames(g)
    for names in LNMClass:
        for k in dir(names):
            v = getattr(names, k)  # use this instead of __dict__ to get parents
            if isinstance(v, Phenotype) or isinstance(v, LogicalPhenotype):
                setLocalNameBase(k, v, g)

def resetLocalNames(g=None):
    """ WARNING: Only call from top level! THIS DOES NOT RESET NAMES in an embeded IPython!!!
        Remove any local names that have already been defined. """
    if g is None:
        g = inspect.stack(0)[1][0].f_locals  #  get globals of calling scope
    for k in list(graphBase.LocalNames.keys()):
        try:
            g.pop(k)
        except KeyError:
            raise KeyError('%s not in globals, are you calling resetLocalNames from a local scope?' % k)
        graphBase.LocalNames.pop(k)

def getLocalNames():
    return {k:v for k, v in graphBase.LocalNames.items()}

def setLocalContext(*neuron_or_phenotypeEdges):
    NeuronBase.setContext(*neuron_or_phenotypeEdges)

def getLocalContext():
    return NeuronBase.getContext()
