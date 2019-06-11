#!/usr/bin/env python3.6
import os
import sys
import atexit
import inspect
from pprint import pformat
from pathlib import Path, PurePath as PPath
from importlib import import_module
from collections import defaultdict
from urllib.error import HTTPError
import git
import rdflib
import ontquery as oq
from rdflib.extras import infixowl
from git import Repo
from ttlser import natsort
from pyontutils import combinators as comb
from pyontutils.core import Ont, makeGraph, OntId, OntTerm as bOntTerm
from pyontutils.utils import stack_magic, injective_dict, makeSimpleLogger, cacheout
from pyontutils.utils import TermColors as tc, subclasses, get_working_dir
from pyontutils.config import devconfig, working_dir, checkout_ok as ont_checkout_ok
from pyontutils.scigraph import Graph, Vocabulary
from pyontutils.qnamefix import cull_prefixes
from pyontutils.annotation import AnnotationMixin
from pyontutils.namespaces import makePrefixes, OntCuries, definition, replacedBy
from pyontutils.namespaces import TEMP, UBERON, ilxtr, PREFIXES as uPREFIXES, NIFRID
from pyontutils.closed_namespaces import rdf, rdfs, owl, skos

log = makeSimpleLogger('neurondm')
RDFL = oq.plugin.get('rdflib')

__all__ = [
    'AND',
    'OR',
    'Config',
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
    'OntId',
    'OntTerm',
    'owl',  # FIXME
    'ilxtr',  # FIXME
    '_NEURON_CLASS',
    '_CUT_CLASS',
    '_EBM_CLASS',
    'log',
]

# language constructes
AND = owl.intersectionOf
OR = owl.unionOf

# utility identifiers
_NEURON_CLASS = OntId('SAO:1417703748').URIRef
_CUT_CLASS = ilxtr.NeuronCUT
_EBM_CLASS = ilxtr.NeuronEBM
PHENO_ROOT = ilxtr.hasPhenotype  # needs to be qname representation
MOD_ROOT = ilxtr.hasPhenotypeModifier

# utility functions

def getPhenotypePredicates(graph):
    # put existing predicate short names in the phenoPreds namespace (TODO change the source for these...)
    proot = graph.qname(PHENO_ROOT)
    mroot = graph.qname(MOD_ROOT)
    qstring = ('SELECT DISTINCT ?prop WHERE {'
               f'{{ ?prop rdfs:subPropertyOf* {proot} . }}'
               'UNION'
               f'{{ ?prop rdfs:subPropertyOf* {mroot} . }}'
               '}')
    out = [_[0] for _ in graph.query(qstring)]
    literal_map = {uri.rsplit('/',1)[-1]:uri for uri in out}  # FIXME this will change
    classDict = {uri.rsplit('/',1)[-1]:uri for uri in out}  # need to use label or something
    classDict['_litmap'] = literal_map
    phenoPreds = type('PhenoPreds', (object,), classDict)  # FIXME this makes it impossible to add fake data
    predicate_supers = {s:tuple(o for o in
                                graph.transitive_objects(s, rdfs.subPropertyOf)
                                if o != s) for s in out}

    return phenoPreds, predicate_supers

# label maker

class order_deco:
    """ define functions in order to get order! """
    def __init__(self):
        self.order = tuple()

    def mark(self, cls):
        if not hasattr(cls, '_order'):
            cls._order = self.order
        else:
            cls._order += self.order

        return cls

    def __call__(self, function):
        if function.__name__ not in self.order:
            self.order += function.__name__,
        else:
            raise ValueError(f'Duplicate function name {function.__name__}')

        return function


od = order_deco()
@od.mark
class LabelMaker:
    """ disregard existing data acquire raw from identifiers """
    predicate_namespace = ilxtr
    field_separator = ' '
    def __init__(self, local_conventions=False):
        """ `local_conventions=True` -> serialize using current LocalNamingConventions """
        self.local_conventions = local_conventions
        if self.local_conventions:
            self._label_property = '__humanSortKey__'
            self._convention_lookup = {v:k for k, v in graphBase.LocalNames.items()}
        else:
            #self._label_property = 'pLongName'
            self._label_property = 'pName'
            # FIXME yay circular imports
            self._convention_lookup = OntologyGlobalConventions.inverted()

        def _key(phen):
            if phen in self._convention_lookup:
                return self._convention_lookup[phen]
            else:
                return getattr(phen, self._label_property)

        self._key = _key

        (self.functions,
         self.predicates) = zip(*((getattr(self, function_name),
                                   self.predicate_namespace[function_name])
                                  for function_name in self._order))

    def __call__(self, neuron):
        # FIXME consider creating a new class every time
        # it will allow state to propagate more easily?
        labels = []
        for function_name, predicate in zip(self._order, self.predicates):
            if predicate in neuron._pesDict:
                phenotypes = neuron._pesDict[predicate]
                function = getattr(self, function_name)
                # TODO resolve and warn on duplicate phenotypes in the same hierarchy
                # TODO negative phenotypes
                sub_labels = list(function(phenotypes))
                labels += sub_labels

        if (isinstance(neuron, Neuron) and  # is also used to render LogicalPhenotype collections
            self.predicate_namespace['hasCircuitRolePhenotype'] not in neuron._pesDict):
            labels += ['neuron']

        if isinstance(neuron, NeuronEBM):
            labels += [neuron._shortname]

        return self.field_separator.join(labels)

    def _default(self, phenotypes):
        for p in sorted(phenotypes, key=self._key):
            if isinstance(p, NegPhenotype):
                prefix = '-'
            else:
                prefix = ''

            if p in self._convention_lookup:
                yield prefix + self._convention_lookup[p]
            else:
                yield prefix + getattr(p, self._label_property)

    @od
    def hasTaxonRank(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasInstanceInSpecies(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasBiologicalSex(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasDevelopmentalStage(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasLocationPhenotype(self, phenotypes):  # FIXME
        yield from self._default(phenotypes)
    @od
    def hasSomaLocatedIn(self, phenotypes):  # hasSomaLocation?
        yield from self._default(phenotypes)
    @od
    def hasLayerLocationPhenotype(self, phenotypes):  # TODO soma naming...
        yield from self._default(phenotypes)
    @od
    def hasDendriteLocatedIn(self, phenotypes):
        yield from self._with_thing_located_in('with-dendrite{}-in', phenotypes)

    @od
    def hasAxonLocatedIn(self, phenotypes):
        yield from self._with_thing_located_in('with-axon{}-in', phenotypes)

    def _with_thing_located_in(self, prefix_template, phenotypes):
        # TODO consider field separator here as well ... or string quotes ...
        lp = len(phenotypes)
        if phenotypes:
            plural = 's' if '{}' in prefix_template and lp > 1 else ''
            yield '(' + prefix_template.format(plural)

        for i, phenotype in enumerate(phenotypes):
            l = next(self._default((phenotype,)))
            if i + 1 == lp:
                l += ')'

            yield l

    @od
    def hasMorphologicalPhenotype(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasDendriteMorphologicalPhenotype(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasSomaPhenotype(self, phenotypes):  # FIXME probably hasSomaMorpohologicalPhenotype
        yield from self._default(phenotypes)
    @od
    def hasElectrophysiologicalPhenotype(self, phenotypes):
        yield from self._default(phenotypes)
    #self._predicates.hasSpikingPhenotype,  # TODO do we need this?
    #def hasSpikingPhenotype(self, phenotypes)  # legacy support
    def _plus_minus(self, phenotypes):
        for phenotype in phenotypes:
            if isinstance(phenotype, NegPhenotype):
                prefix = ''  # now handled in _default
            elif isinstance(phenotype, Phenotype):
                prefix = '+'
            else:  # logical phenotypes aren't phenotypes confusingly enough
                prefix = ''

            yield prefix + next(self._default((phenotype,)))
    @od
    def hasMolecularPhenotype(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasNeurotransmitterPhenotype(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasExpressionPhenotype(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasDriverExpressionPhenotype(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasReporterExpressionPhenotype(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasProjectionPhenotype(self, phenotypes):  # consider inserting after end, requires rework of code...
        yield from self._with_thing_located_in('projecting to', phenotypes)
    @od
    def hasConnectionPhenotype(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasExperimentalPhenotype(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasClassificationPhenotype(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasPhenotype(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasPhenotypeModifier(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasCircuitRolePhenotype(self, phenotypes):
        def suffix(phenotypes):
            if phenotype.p == self.predicate_namespace['IntrinsicPhenotype']:
                return  'neuron'
            elif phenotype.p == self.predicate_namespace['InterneuronPhenotype']:
                return  # interneuron is already in the label
            elif phenotype.p == self.predicate_namespace['MotorPhenotype']:
                return 'neuron'
            else:  # principle, projection, etc. 
                return 'neuron'

        for phenotype in phenotypes:
            yield next(self._default((phenotype,))).lower()

        suffix = suffix(phenotypes)
        if suffix:
            yield suffix

# helper classes

class OntTerm(bOntTerm):
    def as_phenotype(self, predicate=None):
        if self.prefix == 'UBERON':  # FIXME layers
            predicate = ilxtr.hasSomaLocatedIn
        return Phenotype(self, ObjectProperty=predicate, label=self.label, override=bool(self.label))

    def triples(self, predicate):
        if predicate not in self.predicates:
            objects = self(predicate)
        else:
            objects = self.predicates[predicate]

        s = self.u
        p = OntId(predicate).u
        for o in objects:
            o = OntId(o)  # FIXME the parent OntId sneaks in and sews madness :/
            yield s, p, o.u

    @property
    def triples_simple(self):
        skips = 'pheno:parvalbumin',
        bads = ('TEMP', 'ilxtr', 'rdf', 'rdfs', 'owl', '_', 'prov', 'ILX', 'BFO1SNAP', 'NLXANAT',
                'BFO', 'MBA', 'JAX', 'MMRRC', 'ilx', 'CARO', 'NLX', 'BIRNLEX', 'NIFEXT', 'obo', 'NIFRID')
        s = self.URIRef
        if self.type is None:
            yield s, rdf.type, owl.Class  # FIXME ... IAO terms fail on this ... somehow
        else:
            yield s, rdf.type, self.type.u
        if self.label:
            _label = self.label 
            label = rdflib.Literal(_label)
            yield s, rdfs.label, label

        if self.synonyms is not None:  # FIXME this should never happen :/
            for syn in self.synonyms:
                yield s, NIFRID.synonym, rdflib.Literal(syn)

        if self('rdfs:subClassOf', as_term=True):
            for superclass in self.predicates['rdfs:subClassOf']:
                if superclass.curie in skips:
                    continue
                elif superclass.prefix in bads:
                    if superclass.prefix == 'BFO' or self.prefix in bads or 'interlex' in self.iri:
                        yield s, rdfs.subClassOf, superclass.URIRef
                        break
                    else:
                        continue
                if superclass.curie != 'owl:Thing':
                    yield s, rdfs.subClassOf, superclass.URIRef

        predicates = 'partOf:', #'ilxtr:labelPartOf', 'ilxtr:isDelineatedBy', 'ilxtr:delineates'
        done = []
        for predicate in predicates:
            if self(predicate, as_term=True):
                for superpart in self.predicates[predicate]:
                    if superpart.prefix in bads:
                        continue
                    if (predicate, superpart) not in done:
                        yield from comb.restriction(OntId(predicate).URIRef, superpart.URIRef)(s)
                        done.append((predicate, superpart))


OntTerm.query_init(*bOntTerm.query.services)
# initializing this way leads to a race condition on calling
# service.setup since the first OntTerm to call setup on a shared
# service is the one that will be attached to the query result
# fortunately in some cases we cache at a level below this


class OntTermOntologyOnly(OntTerm):
    __firsts = ('curie', 'label')  # FIXME why do I need this here but didn't for OntTerm ??


IXR = oq.plugin.get('InterLex')
OntTermOntologyOnly.query_init(*(s for s in OntTerm.query.services if not isinstance(s, IXR)))


class GraphOpsMixin:
    # TODO this could be populated automatically in a OntComplete case
    # given a graph and an id and possibly the set of all possible
    # edges, give access to that id as an object, I'm sure this has been
    # done before

    # TODO even if it is the same underlying graph (conjuctive?) we should
    # still separate the read and write aspects

    default_properties = 'definition', 'synonyms', 'abbrevs'
    # TODO label ...

    class ObjectTypeError(Exception):
        pass

    def adopt_meta(self, other, properties=None):
        # TODO FIXME annotations
        if properties is None:
            properties = self.default_properties
        for p in properties:
            o = getattr(other, p)
            if o:  # '' False 0 should all be wrapped in rdflib.Literal
                setattr(self, p, o)

        return self  # allow chaining in the event this is called at construction

    @property
    def _load_graph(self):
        return self.config.load_graph

    @property
    def _out_graph(self):
        return self.config.out_graph

    @property
    def identifier(self):
        return self.id_  # fix for current graphBase subclasses

    def objects(self, *predicates):
        graph = (self._load_graph if
                 # FIXME this is a hack that could cause massive confusion
                 # depending on when this is called
                 # maybe we can protect this by making sure that out_graph
                 # has been written?
                 hasattr(self.config, 'load_graph') else
                 self._out_graph)
        for predicate in predicates:
            yield from graph[self.identifier:predicate]

    def add_objects(self, predicate, *objects):
        bads = []
        for object in objects:
            if not isinstance(object, rdflib.URIRef) and not isinstance(object, rdflib.Literal):
                bads.append(object)

        if bads:
            raise self.ObjectTypeError(', '.join(str(type(object)) + ' ' + str(object)
                                                 for object in bads))

        [self.out_graph.add((self.identifier, predicate, object)) for object in objects]

    @property
    def definition(self):
        try:
            return next(self.definitions)
        except StopIteration:
            pass

    @definition.setter
    def definition(self, value):
        # TODO ccardinality 1
        self.add_objects(definition, value)

    @property
    def definitions(self):
        yield from self.objects(definition, skos.definition)

    @property
    def synonyms(self):
        yield from self.objects(NIFRID.synonym)

    @synonyms.setter
    def synonyms(self, values):
        self.add_objects(NIFRID.synonym, *values)

    @property
    def abbrevs(self):
        yield from self.objects(NIFRID.abbrev)

    @abbrevs.setter  # adder really
    def abbrevs(self, value):
        self.add_objects(NIFRID.abbrev, *value)

# config

class Config:
    _subclasses = set()

    class ExistingNeuronsError(Exception):
        pass

    class NotCurrentConifgError(Exception):
        """ graphBase has moved on! """

    def __init__(self,
                 name =                 'test-neurons',
                 prefixes =             tuple(),  # dict or list
                 imports =              tuple(),  # iterable
                 import_as_local =      False,  # also load from local?
                 load_from_local =      True,
                 branch =               devconfig.neurons_branch,
                 sources =              tuple(),
                 source_file =          None,
                 ignore_existing =      False,
                 py_export_dir=         None,
                 ttl_export_dir=        Path(devconfig.ontology_local_repo,  # FIXME neurondm.lang for this?
                                             'ttl/generated/neurons'),  # subclass with defaults from cls?
                 git_repo=              None,
                 file =                 None,
                 local_conventions =    False,
                ):

        if ttl_export_dir is not None:
            if not isinstance(ttl_export_dir, Path):
                ttl_export_dir = Path(ttl_export_dir).resolve()

            local_base = get_working_dir(ttl_export_dir)
            # FIXME there are cases where ttl_export_dir
            # and local_base will both be None???
            # reasonable failover?
        else:
            local_base = None

        if file is not None:
            file = Path(file).resolve()
            compiled_location = file.parent
            #local_base = get_working_dir(compiled_location)  # FIXME conflates python repo and turtle repo
        else:
            # FIXME deal with case where get_working_dir -> None
            compiled_location = py_export_dir

        if git_repo is not None:
            git_repo = Path(git_repo).resolve()
            if local_base is None:
                local_base = git_repo
            if ttl_export_dir is None:
                ttl_export_dir = git_repo
            elif ttl_export_dir.relative_to(git_repo):
                pass  # just make sure that if export loc is not in the repo we fail

        import os  # FIXME probably should move some of this to neurons.py?

        self.__name = name  # TODO allow reload from owl to get the load graph? how to handle this

        graphBase.python_subclasses = list(subclasses(NeuronEBM)) + [Neuron, NeuronCUT]
        graphBase.knownClasses = [OntId(c.owlClass).u
                                  for c in graphBase.python_subclasses]

        imports = list(imports)
        remote = OntId('NIFTTL:') if branch == 'master' else OntId(f'NIFRAW:{branch}/')
        imports += [remote.iri + 'ttl/phenotype-core.ttl', remote.iri + 'ttl/phenotypes.ttl']
        remote_path = '' if local_base is None else ttl_export_dir.resolve().relative_to(local_base.resolve())
        out_remote_base = os.path.join(remote.iri, remote_path)
        imports = [OntId(i) for i in imports]

        remote_base = remote.iri.rsplit('/', 2)[0] if branch == 'master' else remote

        if local_base is None:
            local = Path(devconfig.ontology_local_repo, 'ttl')
            local_base = local.parent
        else:
            local_base = Path(local_base).resolve()
            local = local_base

        out_local_base = ttl_export_dir
        out_base = out_local_base if False else out_remote_base  # TODO switch or drop local?

        if import_as_local:
            # NOTE: we currently do the translation more ... inelegantly inside of config so we
            # have to keep the translation layer out here (sigh)
            core_graph_paths = [Path(local, i.iri.replace(remote.iri, '')).relative_to(local_base).as_posix()
                                if remote.iri in i.iri else
                                i for i in imports]
        else:
            core_graph_paths = imports

        out_graph_path = (out_local_base / f'{name}.ttl')

        class lConfig(self.__class__):
            iri = os.path.join(out_remote_base, f'{name}.ttl')

        self.__class__._subclasses.add(lConfig)


        kwargs = dict(remote_base = remote_base,  # leave it as raw for now?
                      local_base = local_base.as_posix(),
                      core_graph_paths = core_graph_paths,
                      out_graph_path = out_graph_path.as_posix(),
                      out_imports = imports, #[i.iri for i in imports],
                      prefixes = prefixes,
                      force_remote = not load_from_local,
                      branch = branch,
                      iri = lConfig.iri,
                      sources = sources,
                      source_file = source_file,
                      # FIXME conflation of import from local and render with local
                      use_local_import_paths = import_as_local,
                      ignore_existing = ignore_existing,
                      local_conventions = local_conventions)

        # don't klobber defaults set below
        if compiled_location is not None:
            compiled_location = Path(compiled_location).resolve()
            kwargs['compiled_location'] = compiled_location

        for name, value in kwargs.items():
            # FIXME only works if we do this in __new__
            #@property
            def nochangepls(v=value):
                return v

            setattr(self, name, nochangepls)
            # FIXME need a way to make it clear that changing kwargs values
            # will only confuse you ...
            #setattr(self, name, value)

        graphBase.configGraphIO(**kwargs)  # FIXME KILL IT WITH FIRE

        graphBase.config = self  # a nice hack ... can do this for self.activate() too
        # temporary fix to persist graphs and neurons with a config
        # until I have time to rewrite Config so that multiple configs
        # can co-exist but only one config at a time can be operated on
        # when creating new neurons (since only CUTs can be modified)
        # the 'proper' way to move neurons from one config to another
        # is not to switch everything behind the scenes, which is very confusin
        # but simply to take neurons that are statically tied to another config
        # and add them to another config, or just recreate them under the current
        # config, this means that we will do away with the in graph and out graph
        # every config will only have one graph and it will be in or out not both
        # note that different configs can read and write to the same file
        # NOTE that we will need to modify how the superclass is handled as well
        # because at the moment the code assumes that the superclass is invariant
        # this is not the case, and we need equality with and without the superclass
        # we are currently missing equality with the superclass
        # we can probably us a conjuctive graph to 
        self.out_graph = graphBase.out_graph
        self.existing_pes = NeuronBase.existing_pes

    def ttl(self):
        # FIXME do this correctly
        return graphBase.ttl()

    def python(self):
        # FIXME do this correctly
        return graphBase.python()

    @property
    def name(self):
        return self.__name

    @property
    def core_graph(self):
        return graphBase.core_graph  # FIXME :/

    def neurons(self):
        return sorted(self.existing_pes)

    def activate(self):
        """ set this config as the active config """
        raise NotImplemented

    def write(self):
        # FIXME per config prefixes using derived OntCuries?
        og = cull_prefixes(self.out_graph, prefixes={**graphBase.prefixes, **uPREFIXES})
        og.filename = graphBase.ng.filename
        og.write()

    def write_python(self):
        # FIXME hack, will write other configs if call after graphbase has switched
        graphBase.write_python()

    def load_existing(self):
        """ advanced usage allows loading multiple sets of neurons and using a config
            object to keep track of the different graphs """
        from pyontutils.closed_namespaces import rdfs
        # bag existing

        try:
            next(iter(self.neurons()))
            raise self.ExistingNeuronsError('Existing neurons detected. Please '
                                            'load from file before creating neurons!')
        except StopIteration:
            pass

        def getClassType(s):
            graph = self.load_graph
            Class = infixowl.Class(s, graph=graph)
            for ec in Class.equivalentClass:
                if isinstance(ec.identifier, rdflib.BNode):
                    bc = infixowl.CastClass(ec, graph=graph)
                    if isinstance(bc, infixowl.BooleanClass):
                        for id_ in bc._rdfList:
                            if isinstance(id_, rdflib.URIRef):
                                yield id_  # its one of our types

        # bug is that I am not wiping graphBase.knownClasses and swapping it for each config
        # OR the bug is that self.load_graph is persisting, either way the call to type()
        # below seems to be the primary suspect for the issue
        if not graphBase.ignore_existing:
            ogp = Path(graphBase.ng.filename)  # FIXME ng.filename <-> out_graph_path property ...
            if ogp.exists():
                from itertools import chain
                from rdflib import Graph  # FIXME
                self.load_graph = Graph().parse(graphBase.ng.filename, format='turtle')
                graphBase.load_graph = self.load_graph
                # FIXME memory inefficiency here ...
                _ = [graphBase.in_graph.add(t) for t in graphBase.load_graph]  # FIXME use conjuctive ...
                if len(graphBase.python_subclasses) == 2:  # FIXME magic number for Neuron and NeuronCUT
                    ebms = [type(OntId(s).suffix, (NeuronCUT,), dict(owlClass=s))
                            for s in self.load_graph[:rdfs.subClassOf:NeuronEBM.owlClass]
                            if not graphBase.knownClasses.append(s)]
                else:
                    ebms = []

                class_types = [(type, s) for s in self.load_graph[:rdf.type:owl.Class]
                               for type in getClassType(s) if type]
                sc = None
                for sc in chain(graphBase.python_subclasses, ebms):
                    sc.owlClass
                    iris = [s for type, s in class_types if type == sc.owlClass]
                    if iris:
                        sc._load_existing(iris)

                if sc is None:
                    raise ImportError(f'Failed to find any neurons to load in {graphBase.ng.filename}')

    def load_python(self):
        try:
            next(iter(self.neurons()))
            raise self.ExistingNeuronsError('Existing neurons detected. Please '
                                            'load from file before creating neurons!')
        except StopIteration:
            pass

        if not graphBase.ignore_existing:
            # FIXME ideally we want to be able to call self.compiled_location
            # but so long as THERE CAN BE ONLY ONE graphBase then we are going
            if self.compiled_location() != graphBase.compiled_location:
                raise self.NotCurrentConifgError('This config is not the active config!')
            containing = graphBase.compiled_location.parent.as_posix()
            if containing not in sys.path:
                sys.path.append(containing)
            full_path = graphBase.compiled_location / graphBase.filename_python()
            module_path = graphBase.compiled_location.name + '.' + full_path.stem
            module = import_module(module_path)  # this returns the submod

            # for some reason out_graph and existing_pes do not stick to graphBase
            # correctly despite the fact that module.graphBase is graphBase -> True
            # this is a temporary hack fix, the correct fix is to have a single ConjunctiveGraph
            # input, and a single Graph output, PER CONFIG, and the Neuron classes just dump
            # their contents into the current out_graph for that config if it switches, or
            # the current config can populte the current set of python represented neurons
            # they are too coupled at the moment due to how we use infixowl
            # basically pes are eternal Class can be whatever it needs to be
            self.out_graph = graphBase.out_graph = module.config.out_graph
            self.existing_pes = NeuronBase.existing_pes = module.config.existing_pes

            #graphBase.existing_pes = module.config.existing_pes
            #self.load_graph = module.config.load_graph
            #graphBase.load_graph = self.load_graph

# the monstrosity

class graphBase:
    core_graph = 'ASSIGN ME AFTER IMPORT!'
    in_graph = 'ASSIGN ME AFTER IMPORT!'
    out_graph = 'ASSIGN ME AFTER IMPORT'

    _predicates = 'ASSIGN ME AFTER IMPORT'

    LocalNames = {}

    _registered = False

    __import_name__ = __name__

    #_sgv = Vocabulary(cache=True)

    class owlClassMismatch(Exception):
        pass

    class GitRepoOnWrongBranch(Exception):
        """ Git repo is checked out to the wrong branch. """

    class ShouldNotHappenError(Exception):
        """ big oops """

    def __init__(self):
        if type(self.core_graph) == str:
            raise TypeError('You must have at least a core_graph')

        if type(self.in_graph) == str:
            self.in_graph = self.core_graph

        if type(self.out_graph) == str:
            self.out_graph = self.in_graph

        self._namespaces = {p:rdflib.Namespace(ns) for p, ns in self.in_graph.namespaces()}

    def expand(self, putativeURI):
        if isinstance(putativeURI, rdflib.URIRef):
            return putativeURI

        if type(putativeURI) == infixowl.Class:
            return putativeURI.identifier
        elif type(putativeURI) == str:
            return OntId(putativeURI).u
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
            graphBase.original_branch = graphBase.repo.active_branch

        if not hasattr(graphBase, 'working_branch'):
            graphBase.working_branch = graphBase.repo.active_branch

        if not graphBase._registered:
            #print(tc.blue('OB:'), graphBase.original_branch)
            def reset(ob=graphBase.original_branch):
                # ob prevents late binding to original_branch
                # which can be reset by successive calls to configGraphIO
                try:
                    # anything that will be overwritten by returning is OK to zap
                    if Path(graphBase.repo.working_dir).exists():
                        graphBase.repo.git.checkout('-f', ob)
                except BaseException as e:
                    #from IPython import embed
                    #embed()
                    raise e

            if graphBase.original_branch != graphBase.working_branch:
                atexit.register(reset)

            #atexit.register(graphBase.repo.git.checkout, '-f', graphBase.original_branch)
            graphBase._registered = True

        if graphBase.original_branch != graphBase.working_branch:
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
                      use_local_import_paths=True,
                      compiled_location= (PPath('/tmp/neurondm/compiled')
                                          if working_dir is None else
                                          PPath(working_dir, 'neurondm/neurondm/compiled')),
                      ignore_existing=   False,
                      local_conventions= False,):
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

        graphBase.local_conventions = local_conventions

        if local_base is None:
            local_base = devconfig.ontology_local_repo
        graphBase.local_base = Path(local_base).expanduser().resolve()
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

        if (not force_remote
            and graphBase.local_base == Path(devconfig.ontology_local_repo)
            and graphBase.local_base.exists()):

            repo = Repo(graphBase.local_base.as_posix())
            if repo.active_branch.name != branch and not checkout_ok:
                raise graphBase.GitRepoOnWrongBranch(
                    'Local git repo not on %s branch!\n'
                    'Please run `git checkout %s` in %s, '
                    'set NIFSTD_CHECKOUT_OK= via export or '
                    'at runtime, or set checkout_ok=True.'
                    % (branch, branch, repo.working_dir))
            elif checkout_ok:
                graphBase.repo = repo
                graphBase.working_branch = next(h for h in repo.heads
                                                if h.name == branch)
                graphBase.original_branch = repo.active_branch
                graphBase.set_repo_state()
            use_core_paths = local_core_paths
            use_in_paths = local_in_paths
        else:
            if not force_remote and not graphBase.local_base.exists():
                log.warning(f'Warning local ontology path {local_base!r} not found!')
            use_core_paths = remote_core_paths
            use_in_paths = remote_in_paths

            if local_base is not None:
                log.warning(f'Warning local base has been set manually you are on your own!')
                try:
                    repo = Repo(graphBase.local_base.as_posix())
                except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError) as e:
                    local_working_dir = get_working_dir(graphBase.local_base)
                    if local_working_dir is None:
                        raise e
                    else:
                        msg = (f'{graphBase.local_base} is already contained in a git repository '
                               'located in {local_working_dir} if you wish to use this repo please '
                               'set local_base to {local_working_dir}.')
                        raise git.exc.InvalidGitRepositoryError(msg) from e

                graphBase.repo = repo
                # FIXME repo init when branch set still an issue
                # ideally remove _all_ of this code though because WOW
                # it is a mess
                graphBase.set_repo_state()

        # core graph setup
        if core_graph is None:
            core_graph = rdflib.ConjunctiveGraph()
        for cg in use_core_paths:
            try:
                core_graph.parse(cg, format='turtle')
            except (FileNotFoundError, HTTPError) as e:
                # TODO failover to local if we were remote?
                #print(tc.red('WARNING:'), f'no file found for core graph at {cg}')
                log.warning(f'no file found for core graph at {cg}')
        graphBase.core_graph = core_graph
        if RDFL not in [type(s) for s in OntTerm.query.services]:
            # FIXME ah subtle differences between graphs >_<
            # need a much more consistent way to handle the local graphs
            # switching everything out for a single RDFL instance seems
            # the most attractive ...
            OntTerm.query.ladd(RDFL(core_graph, OntId))  # ladd for higher priority

        # store prefixes
        if isinstance(prefixes, dict):
            graphBase.prefixes = prefixes
        else:
            graphBase.prefixes = makePrefixes(*prefixes)

        PREFIXES = {**graphBase.prefixes, **uPREFIXES}
        OntCuries(PREFIXES)

        # input graph setup
        in_graph = core_graph
        for ig in use_in_paths:
            in_graph.parse(ig, format='turtle')

        nin_graph = makeGraph('', prefixes=PREFIXES, graph=in_graph)
        graphBase.in_graph = in_graph
        graphBase.ignore_existing = ignore_existing

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
                #wasGeneratedBy = ('https://github.com/tgbugs/pyontutils/blob/'
                                  #'{commit}/'
                                  #'{filepath}'
                                  #'{hash_L_line}')

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

        # python output setup
        graphBase.compiled_location = compiled_location

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
        preds, pred_supers = getPhenotypePredicates(graphBase.core_graph)
        graphBase._predicates, graphBase._predicate_supers = preds, pred_supers

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
        return ((graphBase.compiled_location / p.name.replace('-', '_'))
                .with_suffix('.py')
                .as_posix())

    @staticmethod
    def write_python():
        python = graphBase.python()
        # if you try to read from a source file that already exists
        # while also writing to that file linecache will be smart and
        # tell you that there is no source! therefore we generate all
        # the python before potentially opening (and thus erasing) the
        # original file from which some of the code was sourced
        with open(graphBase.filename_python(), 'wt') as f:
            f.write(python)

    @classmethod
    def python_header(cls):
        out = '#!/usr/bin/env python3.6\n'
        out += f'from {cls.__import_name__} import *\n\n'

        all_types = set(type(n) for n in cls.neurons())
        _subs = [inspect.getsource(c) for c in subclasses(Neuron)
                 if c in all_types and Path(inspect.getfile(c)).exists()]
        subs = '\n' + '\n\n'.join(_subs) + '\n\n' if _subs else ''
        #log.debug(str(all_types))
        #log.debug(f'python header for {cls.filename_python()}:\n{subs}')
        out += subs

        ind = '\n' + ' ' * len('config = Config(')
        _prefixes = {k:str(v) for k, v in cls.ng.namespaces.items()
                     if k not in uPREFIXES and k != 'xml' and k != 'xsd'}  # FIXME don't hardcode xml xsd
        len_thing = len(f'config = Config({cls.ng.name!r}, prefixes={{')
        '}}'
        prefixes = (f',{ind}prefixes={pformat(_prefixes, 0)}'.replace('\n', '\n' + ' ' * len_thing)
                    if _prefixes
                    else '')

        tel = ttl_export_dir = Path(cls.ng.filename).parent.as_posix()
        ttlexp = f',{ind}ttl_export_dir={tel!r}'

        # FIXME prefixes should be separate so they are accessible in the namespace
        # FIXME ilxtr needs to be detected as well
        # FIXME this doesn't trigger when run as an import?
        out += f'config = Config({cls.ng.name!r},{ind}file=__file__{ttlexp}{prefixes})\n\n'  # FIXME this is from neurons.lang

        return out

    @classmethod
    def python(cls):
        out = cls.python_header()
        #out += '\n\n'.join('\n'.join(('# ' + n.label, '# ' + n._origLabel, str(n))) for n in neurons)
        out += '\n\n'.join(n.python() for n in cls.neurons()) # FIXME this does not reset correctly when a new Controller is created, it probably should...
        return out + '\n'

    @classmethod
    def ttl(cls):
        # trying this as a class method to see whether it makes it
        # easier to reason about which graph is being exported
        og = cull_prefixes(cls.out_graph, prefixes=uPREFIXES)
        return og.g.serialize(format='nifttl').decode()

    @staticmethod
    def neurons():
        return sorted(NeuronBase.existing_pes)

    def disjointWith(self, *others):
        # FIXME this makes the data model mutable!
        # TODO symmetry here

        # is it possible in all cases to expand this
        # to a neuron where you (map neg-phenotype (neuron-phenotypes other-neuron)) ?
        for other in others:
            if isinstance(other, self.__class__):
                otherid = other.id_
            else:
                otherid = other

            self.out_graph.add((self.id_, owl.disjointWith, otherid))
            self._disjoint_bags_ids.add(otherid)

        return self

    def equivalentClass(self, *others):
        """ as implemented this acts as a permenant bag union operator
            and therefore should be used with extreme caution since
            in any given context the computed label/identifier will
            no longer reflect the entailed/reasoned bag

            In a static context this means that we might want to have
            an ilxtr:assertedAlwaysImplies -> bag union neuron
        """
        # FIXME this makes the data model mutable!
        # TODO symmetry here

        # serious modelling issue
        # If you make two bags equivalent to eachother
        # then in the set theory model it becomes impossible
        # to have a set that is _just_ one or the other of the bags
        # which I do not think that we want
        for other in others:
            if isinstance(other, self.__class__):
                #if isinstance(other, NegPhenotype):  # FIXME maybe this is the issue with neg equivs?
                otherid = other.id_
            else:
                otherid = other

            self.out_graph.add((self.id_, owl.equivalentClass, otherid))
            self._equivalent_bags_ids.add(otherid)

        return self

    def subClassOf(self, *others):
        for other in others:
            if isinstance(other, self.__class__):
                self.out_graph.add((self.id_, rdfs.subClassOf, other.id_))
            else:
                self.out_graph.add((self.id_, rdfs.subClassOf, other))

        return self

    @property
    def label_maker(self):
        """ needed to defer loading of local conventions to avoid circular dependency issue """
        if (not hasattr(graphBase, '_label_maker') or
            graphBase._label_maker.local_conventions != graphBase.local_conventions):
            graphBase._label_maker = LabelMaker(graphBase.local_conventions)

        return graphBase._label_maker

# neurons and phenotypes

class Phenotype(graphBase):  # this is really just a 2 tuple...  # FIXME +/- needs to work here too? TODO sorting
    _rank = '0'
    local_names = {}
    _local_names = {
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
    def __init__(self, phenotype, ObjectProperty=None, label=None, override=False, check=True):
        # FIXME allow ObjectProperty or predicate? keyword?
        # label blackholes
        # TODO implement local names here? or at a layer above? (above)
        self.do_check = check
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
            self._label = label  # I cannot wait to get rid of this premature graph integration >_<
            self.in_graph.add((self.p, rdfs.label, rdflib.Literal(label)))

        # use this specify consistent patterns for modifying labels
        self.labelPostRule = lambda l: l

    def checkPhenotype(self, phenotype):
        subject = self.expand(phenotype)
        if self.do_check:
            try:
                next(self.core_graph.predicate_objects(subject))
            except StopIteration:  # is a phenotype derived from an external class
                prefix, suffix = phenotype.split(':', 1)
                if 'swanson' in subject:
                    return subject
                if prefix not in ('SWAN', 'TEMP'):  # known not registered  FIXME abstract this
                    try:
                        ois = OntId(subject)
                        if ois.prefix == 'ilxtr':
                            return subject

                        t = OntTerm(subject)
                        #if not self._sgv.findById(subject):
                        if not t.label:
                            log.info(f'Unknown phenotype {subject}')
                            #print(tc.red('WARNING:'), 'Unknown phenotype', subject)
                        else:
                            self.in_graph.add((subject, rdfs.label, rdflib.Literal(t.label)))
                    except ConnectionError:
                        #print(tc.red('WARNING:'), 'Phenotype unvalidated. No SciGraph was instance found at',
                            #self._sgv._basePath)
                        log.warning(f'Phenotype unvalidated. No SciGraph was instance found at {self._sgv._basePath}')

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

        if isinstance(self._predicates, str):
            if not hasattr(cls, '_first_time'):
                log.warning('No reference predicates have been set, you are on your own!')
                self._first_time = False

            return op

        if op in self._predicates.__dict__.values():
            return op
        else:
            raise TypeError(f'WARNING: Unknown ObjectProperty {op!r}')
            #t = OntTerm(ObjectProperty)  # will fail here?
            #if t.label:
                #setattr(self._predicates, t.curie.replace(':', '_'), op)
            #else:

    @property
    def eLabel(self):
        return next(self._eClass.label)

    @property
    def pLabel(self):
        l = tuple(self._pClass.label)
        if not l:  # we don't want to load the whole ontology
            try:
                p = OntId(self.p)
                if p.prefix != 'ilxtr' and p.prefix != 'TEMP' and 'swanson' not in p.iri:
                    t = OntTerm(p)
                    if t.label:
                        l = t.label
                    else:
                        l = t.curie
                else:
                    l = p.curie
            except ConnectionError as e:
                log.error(str(e))
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
    @cacheout
    def pShortName(self):
        if hasattr(self, '_cache_pShortName'):
            return self._cache_pShortName

        if self.local_conventions:
            inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
            if self in inj:
                return inj[self]

        pn = self.in_graph.namespace_manager.qname(self.p)
        try:
            resp = self._sgv.findById(pn)
        except ConnectionError as e:
            #print(tc.red('WARNING:'), f'Could not set label for {pn}. No SciGraph was instance found at', self._sgv._basePath)
            log.info(f'Could not set label for {pn}. No SciGraph was instance found at ' + self._sgv._basePath)
            resp = None

        if hasattr(self, '_label'):
            return self._label

        if pn.startswith('NCBITaxon'):
            return resp['labels'][0]

        if resp:  # DERP
            abvs = resp['abbreviations']
            if not abvs:
                abvs = sorted([s for s in resp['synonyms'] if 1 < len(s) < 5], key=lambda s :(len(s), s))
                if (not abvs or 'Pva' in abvs) and resp['labels']:
                    try:
                        t = next(OntTerm.query(term=resp['labels'][0], prefix='NCBIGene'))  # worth a shot
                        abvs = [_ for _ in sorted(t.synonyms, key= lambda s: (len(s), s)) if 1 < len(_) < 5]
                        if abvs:
                            log.info(f'found shortnames for {pn} from NCBIGene {abvs}')
                    except StopIteration:
                        pass
        else:
            abvs = None

        if abvs:
            abv = abvs[0]
            if abv == 'Glu,':
                return 'Glu'  # FIXME tempfix for bad glutamate abv
            elif abv == '4Abu':  # sigh
                return 'GABA'
            else:
                return abv

        elif pn in self.local_names:
            return self.local_names[pn]

        elif self in OntologyGlobalConventions.inverted():
            # layer issues
            return OntologyGlobalConventions.inverted()[self]

        else:
            #log.error(f'No short name for {pn}')
            return None  # self.pLongName

    @property
    def pLongName(self):
        if hasattr(self, '_label'):
            return self._label

        p = OntId(self.p)

        r = OntTerm.query.services[0]  # rdflib local
        try:
            l = next(r.query(iri=p.iri)).OntTerm.label
        except StopIteration:
            if p.prefix == 'ilxtr' or 'swanson' in p.iri or p.prefix == 'TEMP':
                return p.curie

            t = OntTerm(p)
            l = t.label

        if not l:
            return t.curie

        return (l
                .replace('phenotype', '')
                .replace('Phenotype', '')
                .strip())

    @property
    def pName(self):
        name = self.pShortName
        return name if name else self.pLongName

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
        return (type(self) == type(other) and
                self.p == other.p and
                self.e == other.e)

    def __hash__(self):
        return hash((self.__class__.__name__, self.p, self.e))

    def __expanded__(self):
        if hasattr(self, 'ng'):
            pn = self.ng.qname(self.p)
            en = self.ng.qname(self.e)
        else:
            pn = self.in_graph.namespace_manager.qname(self.p)
            en = self.in_graph.namespace_manager.qname(self.e)
        lab = self.pLabel
        return "%s('%s', '%s', label='%s')" % (self.__class__.__name__, pn, en, lab)

    @property
    def __humanSortKey__(self):
        return (self.pShortName if
                self.pShortName else
                (self.pHiddenLabel if
                 self.pHiddenLabel else
                 self.pLabel))

    def __repr__(self):
        #inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
        #if self in inj:
            #return inj[self]
        #else:
        return self.__expanded__()

    def __str__(self):
        if hasattr(self, 'ng'):
            pn = self.ng.qname(self.p)
            en = self.ng.qname(self.e)
        else:
            pn = self.in_graph.namespace_manager.qname(self.p)
            en = self.in_graph.namespace_manager.qname(self.e)
        lab = str(self.pLabel)
        t = ' ' * (len(self.__class__.__name__) + 1)
        return f"{self.__class__.__name__}({pn!r},\n{t}{en!r},\n{t}label={lab!r})"
        #return "%s('%s',\n%s'%s',\n%slabel='%s')" % (self.__class__.__name__, pn, t, en, t, lab)


class NegPhenotype(Phenotype):
    _rank = '1'
    """ Class for Negative Phenotypes to simplfy things """


class UnionPhenotype(graphBase):  # not ready
    """ Class for expressing unions of phenotypes.
        There is no intersection phenotype because the bagging process
        operates as intersection by default. """

    # TODO can't quite implement this yet because logical phenotypes are
    # still to tied in to the local naming conventions, allowing
    # neurons to be input as intersectional phenotypes for other neurons
    # might be one way around this, however note that it is nice to have
    # a distinction between the collection of phenotypes and their binding
    # to a neuron type ...
    _rank = '9'


class LogicalPhenotype(graphBase):
    # FIXME the interpretation of logical phenotypes is hard
    # for exampe, Neuron(LP(OR, A, B)) expands into two subgroups
    # (AND Neuron(P(A)) Neuron(P(B))) at the set level (as expected from basic set theory)
    # We do want to be able to talk about sets of _neurons_ in addition to sets of phenotypes
    # Neuron(LP(AND, A, B)) is just Neuron(P(A), P(B)) so we can drop that representation

    # On the other hand logical phenotypes are useful for local naming rules such as bAC
    # I think it is better to implement that as part of the label generation logic though
    _rank = '2'
    local_names = {
        AND:'AND',
        OR:'OR',
    }
    def __init__(self, op, *edges):
        super().__init__()
        self.op = op  # TODO more with op
        self.pes = tuple(sorted(edges))
        self._pesDict = {}
        for pe in self.pes:
            if pe.e in self._pesDict:
                self._pesDict[pe.e].append(pe)
            else:
                self._pesDict[pe.e] = [pe]

        self.labelPostRule = lambda l: l

    @property
    def p(self):
        return tuple((pe.p for pe in self.pes))

    @property
    def e(self):
        return tuple((pe.e for pe in self.pes))

    @property
    def _pClass(self):
        class OpClass(tuple):
            local_names = self.local_names
            @property
            def qname(self):  # a not entirely unreasonably way to define qnames for collections
                op, *rest = self
                return (self.local_names[op], *(r.qname for r in rest))

        return OpClass((self.op, *(p._pClass for p in self.pes)))

    def _lkey(self, attr):
        def key(pe):
            try:
                # FIXME this is dumb should be using OntId internally
                # the convert to URIRef only for the graph ...
                return self.label_maker._order.index(OntId(pe.e).suffix), getattr(pe, attr)
            except ValueError as e:
                log.error(pe)
                raise e

        return key

    @property
    def pLabel(self):
        spes = sorted(self.pes, key=self._lkey('pLabel'))
        #return f'({self.local_names[self.op]} ' + ' '.join(self.ng.qname(p) for p in self.p) + ')'
        return f'({self.local_names[self.op]} ' + ' '.join(f'"{p.pLabel}"' for p in spes) + ')'

    @property
    def pHiddenLabel(self):
        spes = sorted(self.pes, key=self._lkey('pHiddenLabel'))
        label = ' '.join([pe.pHiddenLabel for pe in spes])  # FIXME we need to catch non-existent phenotypes BEFORE we try to get their hiddenLabel because the errors you get here are completely opaque
        op = self.local_names[self.op]
        return self.labelPostRule(f'({op} {label})')

    @property
    def pShortName(self):
        if self.local_conventions:
            inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
            if self in inj:
                return inj[self]

        spes = sorted(self.pes, key=self._lkey('pShortName'))
        label = ' '.join([pe.pShortName if pe.pShortName else pe.pLongName
                          for pe in spes])
        op = OntId(self.op).suffix
        return self.labelPostRule(f'({op} {label})')

    @property
    def pLongName(self):
        # FIXME this should just be the usual neuron name
        # amusingly and annoying this reveals the serious need to
        # be able to construct neurons on the fly without having them
        # put into the graph (a known issue with the current coupled implementation)
        l = self.label_maker(self)
        op = OntId(self.op).suffix

        return f'({op} {l})'

    @property
    def pName(self):
        name = self.pShortName
        return name if name else self.pLongName

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
        return (type(self) == type(other) and
                self.op == other.op and
                self.pes == other.pes)

    def __hash__(self):
        return hash((self.__class__.__name__, self.op, *self.pes))

    @property
    def __humanSortKey__(self):
        return (self.pShortName if
                self.pShortName else
                (self.pHiddenLabel if
                 self.pHiddenLabel else
                 self.pLabel))
    @property
    def __repr_tuple__(self):
        op = self.local_names[self.op]  # FIXME inefficient but safe
        pes = ', '.join([_.__repr__() for _ in self.pes])
        return f'({op}, {pes})'

    def __repr__(self):
        return f'{self.__class__.__name__}{self.__repr_tuple__}'

    def __str__(self):
        op = self.local_names[self.op]  # FIXME inefficient but safe
        t =  ' ' * (len(self.__class__.__name__) + 1)
        base =',\n%s' % t
        pes = base.join([_.__str__().replace('\n', '\n' + t) for _ in self.pes])
        return '%s(%s%s%s)' % (self.__class__.__name__, op, base, pes)


class NeuronBase(AnnotationMixin, GraphOpsMixin, graphBase):
    owlClass = _NEURON_CLASS
    shortname = None
    preserve_predicates = NIFRID.synonym, definition
    existing_pes = {}
    existing_ids = {}
    ids_pes = {}
    pes_ids = {}
    __context = tuple()  # this cannot be changed after __init__, neurons are not dynamic
    _ocTrip = owlClass, rdf.type, owl.Class
    _loading = False

    def __new__(cls, *args, **kwargs):
        parent = cls.mro()[1]  # FIXME EVIL
        if (hasattr(parent, 'owlClass') and
            cls.owlClass != parent.owlClass and
            cls not in (NeuronBase, Neuron, NeuronCUT, NeuronEBM) and
            not hasattr(cls, '_runonce')):
            cls._runonce = True
            cls.ng.add_trip(cls.owlClass, rdf.type, owl.Class)
            cls.ng.add_trip(cls.owlClass, rdfs.subClassOf, _EBM_CLASS)

        return super().__new__(cls)

    def asUndeprecated(self):
        replace = {
            'NIFEXT:5': 'NCBIGene:12308',  # cr
            'NIFEXT:6': 'NCBIGene:19293',  # pv these are technically incorrect because they are mouse
            'NIFEXT:5116': 'NCBIGene:20604',  # sst
            'NLX:69833': 'PR:000008235',  # GluR3
            'NLX:70371': 'UBERON:0002567',  # basal pons is not a synonym in ubron wat
            'NIFEXT:5068': 'PR:000005110',  # cholecysokinin
            'NIFEXT:5090': 'PR:000011387',  # npy
            'NLXMOL:1006001': 'ilxtr:GABAReceptor',  # gaba receptor role -> gaba receptor itself
            'SAO:1164727693': 'ilxtr:glutamateReceptor',
            'NLXMOL:20090301': 'CHEBI:132943',  # aspartate
            'NLXORG:110506': 'BIRNLEX:2',  # organism, except with actual lexical information attached to it  # FIXME automate this?
            #'NIFEXT:6':'PTHR:11653',  #  pv 'NCBIGene:19293'
            #'NIFEXT:5116': 'PTHR:10558', #  'NCBIGene:20604',
        }
        new = []
        deprecated = False
        for phenotype in self.pes:
            if isinstance(phenotype, LogicalPhenotype):
                new.append(phenotype)  # FIXME recurse
                continue


            t = OntTerm(phenotype.p)
            if t.curie in replace:
                np = phenotype.__class__(replace[t.curie], phenotype.e)
                new.append(np)
                deprecated = True
                log.debug(f'Found deprecated phenotype {phenotype} -> {np}')
                continue

            if hasattr(t, 'deprecated') and t.deprecated:  # FIXME why do we not have cases without?
                rb = t('replacedBy:', as_term=True)
                if rb:
                    nt = rb[0]
                    np = phenotype.__class__(nt, phenotype.e)
                    new.append(np)
                    deprecated = True
                    log.debug(f'Found deprecated phenotype {phenotype} -> {np}')
                    continue

            elif not hasattr(t, 'deprecated'):
                log.error(f'{t.source}')

            new.append(phenotype)

        id_ = (self.id_ if not hasattr(self, 'temp_id') or
               self.id_ != self.temp_id else None)
        nn = self.__class__(*new, id_=id_, label=self.origLabel)
        nid = nn.Class.identifier
        oid = self.Class.identifier
        log.debug(str((id_, nid, oid)))
        if deprecated and nid != oid:  # FIXME
            nn.out_graph.add((nid, ilxtr.termReplaces, oid))
            nn.out_graph.add((oid, replacedBy, nid))
            nn.out_graph.add((oid, owl.deprecated, rdflib.Literal(True)))

        nn.adopt_meta(self)  # FIXME consider persisting ids?
        return nn

    @classmethod
    def _load_existing(cls, iris):
        # TODO rename pes -> phenotypes
        if not cls._loading:
            NeuronBase._loading = True  # block all other neuron loading
            try:
                log.debug(str([i for i in iris if '4164' in i or '100212' in i]))
                for iri in iris:
                        # rod/cone issue
                        #breakpoint()
                    try:
                        n = cls(id_=iri, override=True)#, out_graph=cls.config.load_graph)  # I think we can get away without this
                        if iri.endswith('4164') or iri.endswith('100212'):
                            log.debug(f'{iri} -> {n}')

                        # because we just call Config again an everything resets
                    except cls.owlClassMismatch as e:
                        log.exception(e)
                        continue
                    except AttributeError as e:
                        log.critical(str(e))
                        raise e
            finally:
                NeuronBase._loading = False

    def __init__(self, *phenotypeEdges, id_=None, label=None, override=False,
                 equivalentNeurons=tuple(), disjointNeurons=tuple()):

        if id_ and (equivalentNeurons or disjointNeurons):
            # FIXME does this work!?
            raise TypeError('Neurons defined by id may not use equivalent or disjoint')

        super().__init__()
        self.ORDER = [
            # FIXME it may make more sense to manage this in the NeuronArranger
            # so that it can interconvert the two representations
            # this is really high overhead to load this here
            ilxtr.hasTaxonRank,
            ilxtr.hasInstanceInSpecies,
            ilxtr.hasBiologicalSex,
            ilxtr.hasDevelopmentalStage,
            ilxtr.hasLocationPhenotype,  # FIXME
            ilxtr.hasSomaLocatedIn,  # hasSomaLocation?
            ilxtr.hasLayerLocationPhenotype,  # TODO soma naming...
            ilxtr.hasDendriteLocatedIn,
            ilxtr.hasAxonLocatedIn,
            ilxtr.hasMorphologicalPhenotype,
            ilxtr.hasDendriteMorphologicalPhenotype,
            ilxtr.hasSomaPhenotype,  # FIXME probably hasSomaMorpohologicalPhenotype
            ilxtr.hasElectrophysiologicalPhenotype,
            #self._predicates.hasSpikingPhenotype,  # TODO do we need this?
            self.expand('ilxtr:hasSpikingPhenotype'),  # legacy support
            ilxtr.hasMolecularPhenotype,
            ilxtr.hasNeurotransmitterPhenotype,
            ilxtr.hasExpressionPhenotype,
            ilxtr.hasDriverExpressionPhenotype,
            ilxtr.hasReporterExpressionPhenotype,
            ilxtr.hasCircuitRolePhenotype,
            ilxtr.hasProjectionPhenotype,  # consider inserting after end, requires rework of code...
            ilxtr.hasConnectionPhenotype,
            ilxtr.hasExperimentalPhenotype,
            ilxtr.hasClassificationPhenotype,
            ilxtr.hasPhenotype,
            ilxtr.hasPhenotypeModifier,
        ]

        self._localContext = self.__context
        self.config = self.__class__.config  # persist the config a neuron was created with
        __pes = tuple(set(self._localContext + phenotypeEdges))  # remove dupes
        phenotypeEdges = self.removeDuplicateSuperProperties(__pes)

        if phenotypeEdges:
            frag = '-'.join(sorted((pe._uri_frag(self.ORDER.index)
                                    for pe in phenotypeEdges),
                                    key=natsort))
                                        #*(f'p{self.ORDER.index(p)}/{self.ng.qname(o)}'
                                            #for p, o in sorted(zip(pe.predicates,
                                                                #pe.objects)))))
            self.temp_id = TEMP[frag]  # XXX beware changing how __str__ works... really need to do this

        if id_ and phenotypeEdges:
            self.id_ = self.expand(id_)
            #print('WARNING: you may be redefining a neuron!')
            log.warning(f'you may be redefining a neuron! {id_}')
            #raise TypeError('This has not been implemented yet. This could serve as a way to validate a match or assign an id manually?')
        elif id_:
            self.id_ = self.expand(id_)
        elif phenotypeEdges:
            #asdf = str(tuple(sorted((_.e, _.p) for _ in phenotypeEdges)))  # works except for logical phenotypes

            self.id_ = self.temp_id
        else:
            raise TypeError('Neither phenotypeEdges nor id_ were supplied!')

        # TODO serialize these
        self._equivalent_bags_ids = set()
        self._disjoint_bags_ids = set()

        if not phenotypeEdges and id_ is not None and id_ not in self.knownClasses:
            self.Class = infixowl.Class(self.id_, graph=self.in_graph)  # IN
            phenotypeEdges = self.bagExisting()  # rebuild the bag from the -class- id
            if label is None:
                try:
                    # FIXME this is a mess, I have too many ways to persist this stuff :/
                    label =next(self.Class.graph[self.Class.identifier:ilxtr.origLabel:])
                except StopIteration:
                    try:
                        label, *_extra = self.Class.label
                    except ValueError:
                        pass  # no label in the graph

        else:
            self.equivalentClass(*equivalentNeurons)
            self.disjointWith(*disjointNeurons)

        self.pes = tuple(sorted(sorted(phenotypeEdges),
                                key=lambda pe: self.ORDER.index(pe.e) if pe.e in self.ORDER else len(self.ORDER) + 1))
        self.validate()

        self.Class = infixowl.Class(self.id_, graph=self.out_graph)  # once we get the data from existing, prep to dump OUT


        self.phenotypes = set(pe.p for pe in self.pes)  # NOTE the valence is NOT included here
        self.edges = set(pe.e for pe in self.pes)
        self._pesDict = {}
        for pe in self.pes:  # FIXME TODO
            if isinstance(pe, LogicalPhenotype):  # FIXME
                # FIXME hpm should actually be an inclusive subclass query on hasPhenotype
                dimensions = set(_.e for _ in pe.pes if _.e != ilxtr.hasPhenotypeModifier)
                if len(dimensions) == 1:
                    dimension = next(iter(dimensions))
                else:
                    dimension = tuple(sorted(dimensions))

                if dimension not in self._pesDict:
                    self._pesDict[dimension] = []

                self._pesDict[dimension].append(pe)

            else:
                if pe.e not in self._pesDict:
                    self._pesDict[pe.e] = []

                self._pesDict[pe.e].append(pe)  # don't have to check for dupes here

        self._origLabel = label
        self._override = override

        if self in self.existing_pes and self.Class.graph is self.existing_pes[self].graph and not override:
            self.Class = self.existing_pes[self]
        else:
            self.Class = self._graphify()
            self.Class.label = rdflib.Literal(self.label)  # FIXME this seems... broken?
            self.existing_pes[self] = self.Class

        self.ttl = self._instance_ttl
        self.python = self._instance_python


    def removeDuplicateSuperProperties(self, rawpes):
        # find any duplicate phenotype values
        # check their dimensions to see if one is a subProperty of the other
        # keep only the most granular
        _cands = defaultdict(set)
        for pe in rawpes:
            _cands[pe.p].add(pe)

        cands = tuple(pes for pes in _cands.values() if len(pes) > 1)
        if cands:
            skip = set()
            for pes in cands:
                for pe in pes:
                    if pe not in skip:
                        supers = self._predicate_supers[pe.e]
                        for ope in pes:
                            if ope != pe and ope.e in supers:
                                skip.add(ope)

            if skip:
                log.warning(f'Phenotype subsumbed by more specific predicate {skip}')
                return tuple(pe for pe in rawpes if pe not in skip)

        return rawpes

    def _tuplesToPes(self, pes):
        for p, e in pes:
            yield Phenotype(p, e)

    @property
    def _existing(self):  # TODO
        if hasattr(self.config, 'load_graph'):
            for p in self.preserve_predicates:
                for o in self.config.load_graph[self.id_:p:]:
                    yield self.id_, p, o

    def populate_from(self, neuron):
        [self.out_graph.add(t) for t in neuron._existing]
        if self.id_ != neuron.id_:
            self.out_graph.add((self.id_, ilxtr.populatedFrom, neuron.id_))

    def _subgraph(self):
        def f(t, g):
            subject, predicate, object = t
            for p, o in g[object]:
                yield object, p, o

        g = rdflib.Graph()
        _ = [g.add(t) for t in self.out_graph.transitiveClosure(f, (None, None, self.id_))]
        _ = [g.add(t) for t in self._existing]


        og = cull_prefixes(g, prefixes=uPREFIXES)  # FIXME local prefixes?
        return og

    def _instance_ttl(self):
        og = self._subgraph()
        return og.g.serialize(format='nifttl').decode()

    def _instance_python(self):
        return '\n'.join(('# ' + self.label, str(self)))
        #return self.python_header() + str(self)

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
        return self.genLabel

        # for now we are not going to switch on this, display issues will be display issues
        if self._override and self._origLabel is not None:
            self.Class.label = (rdflib.Literal(self._origLabel),)
            return self._origLabel
        else:
            return self.genLabel

    @property
    def origLabel(self):
        return self._origLabel

    @property
    def genLabel(self):
        # TODO predicate actions are the right way to implement the transforms here
        return self.label_maker(self)

    @property
    def localLabel(self):
        # TODO predicate actions are the right way to implement the transforms here
        return LabelMaker(True)(self)

    @property
    def HiddenLabel(self):
        return f'({self.__class__.__name__} ' + ' '.join(pe.pHiddenLabel for pe in self.pes) + ')'

    def realize(self):  # TODO use ilx_utils
        """ Get an identifier """
        self.id_ = 'ILX:1234567'

    def validate(self):
        raise TypeError('Your neuron is bad and you should feel bad.')

    def getPredicate(self, object):
        for p in self.pes:
            if p.p == object:  # FIXME probably need to munge the object
                return p.e
            # FIXME warn/error on ambiguous?

        raise AttributeError(f'{self} has no aspect with the phenotype {OntId(object)!r}')  # FIXME AttributeError seems wrong

    def getObject(self, predicate):
        for p in self.pes:
            if p.e == predicate:  # FIXME probably need to munge the object
                return p.p  # just to confuse you, the second p here is phenotype not predicate >_<

        return rdf.nil  # FIXME how to indicate all values?
        # predicate is different than object in the sense that it is possible
        # for neurons to have aspects (aka phenotype dimensions) without anyone
        # having measured those values, also handy when we don't know how to parse a value
        # but there is note attached
        #raise AttributeError(f'{self} has no phenotype for {predicate}')  # FIXME AttributeError seems wrong

    def __expanded__(self):
        args = '(' + ', '.join([_.__expanded__() for _ in self.pes]) + ')'
        return '%s%s' % (self.__class__.__name__, args)

    def __repr__(self):  # TODO use local_names (since we will bind them in globals, but we do need a rule, and local names do need to be to pairs or full logicals? eg L2L3 issue
        inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
        sn = self._shortname
        if sn:
            sn = ' ' + sn

        id_ = (f", id_={str(self.id_)!r}" if not hasattr(self, 'temp_id') or
               self.id_ != self.temp_id else '')
        lab =  f", label={str(self.origLabel) + sn!r}" if self.origLabel else ''
        args = '(' + ', '.join([inj[_] if _ in inj else repr(_) for _ in self.pes]) + f'{id_}{lab})'
        #args = self.pes if len(self.pes) > 1 else '(%r)' % self.pes[0]  # trailing comma
        return '%s%s' % (self.__class__.__name__, args)

    def __str__(self):
        asdf = '%s(' % self.__class__.__name__
        for i, pe in enumerate(self.pes):
            t = ' ' * (len(self.__class__.__name__) + 1)
            if i:
                asdf += ',\n' + t + str(pe).replace('\n', '\n' + t)
            else:
                asdf += str(pe).replace('\n', '\n' + t)

        sn = self._shortname
        if sn:
            sn = ' ' + sn
        id_ = (',\n' + t + f"id_={str(self.id_)!r}"
               if not hasattr(self, 'temp_id') or
               self.id_ != self.temp_id else '')
        asdf += id_
        lab =  ',\n' + t + f"label={str(self.origLabel) + sn!r}" if self._origLabel else ''
        asdf += lab
        asdf += ')'
        return asdf

    def __hash__(self):
        return hash((self.__class__.__name__, *self.pes))  # FIXME bad hashing

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.pes == other.pes)
        #return hash(self) == hash(other)

    def __lt__(self, other):
        try:
            return repr(self.pes) < repr(other.pes)
        except AttributeError as e:
            from IPython import embed
            embed()
            raise e

    def __gt__(self, other):
        return not self.__lt__(other)

    def __add__(self, other):
        return self.__class__(*self.pes, *other.pes)

    def __radd__(self, other):
        if type(other) is int:  # sum() starts at 0
            return self
        else:
            return self.__class__(*self.pes, *other.pes)

    def __contains__(self, thing):
        if isinstance(thing, type(self)):
            raise NotImplemented
        elif isinstance(thing, Phenotype) or isinstance(thing, LogicalPhenotype):
            return thing in self.pes
        else:
            return thing in self._pesDict  # FIXME make it clear that this allows neurons to behavie like _pesDict ...

    def __iter__(self):
        yield from self.pes

    def __getitem__(self, predicate):
        return self._pesDict[predicate]

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
            phenos = [pe for pe in self.pes if pe.e == disjoint and type(pe) == Phenotype]
            if len(phenos) > 1:
                raise TypeError(f'Disjointness violated for {disjoint} due to {phenos}')

        # species matched identifiers TODO
        # developmental stages (if we use the uberon associated ones)
        # parcellation schemes
        # NCBIGene ilxtr:definedForTaxon  # FIXME this needs to be a real OP!
        # PR ??

    def bagExisting(self):  # TODO intersections
        #if self.ng.qname(self.id_).startswith('TEMP'):
            #raise TypeError('TEMP id, no need to bag')
        out = set()  # prevent duplicates in cases where phenotypes are duplicated in the hierarchy
        embeddedKnownClasses = set()
        for c in self.Class.equivalentClass:
            if isinstance(c.identifier, rdflib.URIRef):
                # FIXME this is entailment stuff
                # also prevents potential infinite recursion
                self._equivalent_bags_ids.add(c.identifier)
                continue

            pe = self._unpackPheno(c)
            if pe:
                if isinstance(pe, tuple):
                    for p in pe:
                        if p in self.knownClasses:
                            embeddedKnownClasses.add(p)

                    # strip out any known iris
                    out.update([_ for _ in pe if _ not in self.knownClasses])
                else:
                    if pe in self.knownClasses:
                        embeddedKnownClasses.add(pe)

                    out.add(pe)
            else:
                raise self.ShouldNotHappenError('bah!')

        if not embeddedKnownClasses:
            cf = [_ for _ in self.Class.graph[:rdf.type:owl.Ontology]
                  if 'phenotype' not in _]
            raise self.owlClassMismatch(f'\nowlClass {embeddedKnownClasses} '
                                        f'does not match {self.owlClass} {c}\n'
                                        f'the current file is {cf}')

        for c in self.Class.disjointWith:  # replaced by complementOf for most use cases
            if isinstance(c.identifier, rdflib.URIRef):
                self._disjoint_bags_ids.add(c.identifier)
            else:
                # prefer to use complementOf
                log.warning(f'what is this disjoint thing? {c}')

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
        # this is super slow ...

        def restriction_to_phenotype(r, ptype=type_):
            p = r.someValuesFrom  # if _NEURON_CLASS is not a owl:Class > problems
            e = r.onProperty
            return ptype(p, e)

        if c.identifier == self.id_ or c.identifier == self.owlClass:
            return

        if isinstance(c.identifier, rdflib.BNode):
            putativeBooleanClass = infixowl.CastClass(c, graph=self.in_graph)
            if isinstance(putativeBooleanClass, infixowl.BooleanClass):
                bc = putativeBooleanClass
                op = bc._operator  # we only use intersection so maybe error on union?
                pes = []
                for id_ in bc._rdfList:  # FIXME should be getting the base class before ...
                    pr = infixowl.CastClass(id_, graph=self.in_graph)
                    if isinstance(pr, infixowl.BooleanClass):
                        lpe = self._unpackLogical(pr)
                        pes.append(lpe)
                    elif type(pr) == infixowl.Class:  # restriction is sco class so use type
                        if id_ in self.knownClasses:
                            pes.append(id_)
                        elif id_ == self.owlClass:  # this can fail ...
                            # in case we didn't catch it before
                            pes.append(id_)
                        elif isinstance(id_, rdflib.URIRef):  # FIXME this never runs?
                            log.error(f'Wrong owl:Class, expected: {self.id_} got: {id_}')
                            return
                        else:
                            if pr.complementOf:
                                coc = infixowl.CastClass(pr.complementOf, graph=self.in_graph)
                                if isinstance(coc, infixowl.Restriction):
                                    pes.append(restriction_to_phenotype(coc, ptype=NegPhenotype))
                                else:
                                    log.critical(str(coc))
                                    raise BaseException('wat')
                            else:
                                log.critical(str(pr))
                                raise BaseException('wat')
                    elif isinstance(pr, infixowl.Restriction):
                        pes.append(restriction_to_phenotype(pr))
                    elif id_ == self.owlClass:
                        pes.append(id_)
                    elif pr is None:
                        log.warning('dangling reference', id_)
                    else:
                        log.critical(str(pr))
                        raise BaseException('wat')

                return tuple(pes)
            else:
                log.critical('WHAT')  # FIXME something is wrong for negative phenotypes...
                pr = putativeBooleanClass
                p = pr.someValuesFrom
                e = pr.onProperty
                if p and e:
                    return type_(p, e)
                else:
                    log.critical(str(putativeBooleanClass))
        else:
            # TODO make sure that Neuron is in there somehwere...
            # objects = sorted(c.graph.transitive_objects(c.identifier, None))
            # cryptic errors are due to the fact that infixowl still has
            # lingering byte/string issues
            log.warning(f'Could not convert class to Neuron {c}')

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

        ################## LABELS ARE DEFINED HERE ##################
        gl = self.genLabel
        ll = self.localLabel
        ol = self.origLabel
        graph.add((self.id_, ilxtr.genLabel, rdflib.Literal(gl)))
        if ll != gl:
            graph.add((self.id_, ilxtr.localLabel, rdflib.Literal(ll)))

        if ol and ol != gl:
            graph.add((self.id_, ilxtr.origLabel, rdflib.Literal(ol)))

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

    def validate(self):
        # EBM's probably should not be using UBERON ids since they are not species specific
        # subClassOf restrictions (hacked impl using curie prefixes as a proxy)
        # no panther
        # no uberon
        super().validate()
        usage_ok = {UBERON['0000955'], UBERON['0001950']}
        for invalid_superclass, predicate in (('UBERON', self._predicates.hasSomaLocatedIn),):
            for pe in self.pes:
                if pe.e == predicate and pe.p not in usage_ok and invalid_superclass in pe.p:
                    log.warning(tc.red(f'subClassOf restriction violated '
                                       '(please use a more specific identifier) '
                                       'for {invalid_superclass} due to\n{pe}'))
                    #raise TypeError(f'subClassOf restriction violated for {invalid_superclass} due to {pe}')  # TODO can't quite switch this on yet, breaks too many examples


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
        log.debug(str(out))
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
        log.debug(key)
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

    _ORDER = (
        'ilxtr:hasInstanceInSpecies',
        'ilxtr:hasTaxonRank',
        'ilxtr:hasSomaLocatedIn',  # hasSomaLocation?
        'ilxtr:hasLayerLocationPhenotype',  # TODO soma naming...
        'ilxtr:hasDendriteLocatedIn',
        'ilxtr:hasAxonLocatedIn',
        'ilxtr:hasMorphologicalPhenotype',
        'ilxtr:hasDendriteMorphologicalPhenotype',
        'ilxtr:hasElectrophysiologicalPhenotype',
        'ilxtr:hasSpikingPhenotype',  # legacy support
        'ilxtr:hasExpressionPhenotype',
        'ilxtr:hasDriverExpressionPhenotype',
        'ilxtr:hasReporterExpressionPhenotype',
        'ilxtr:hasProjectionPhenotype',  # consider inserting after end, requires rework of code...
        ilxtr.hasConnectionPhenotype,
        ilxtr.hasExperimentalPhenotype,
        ilxtr.hasClassificationPhenotype,
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


# FIXME this needs to go in another file when this file gets broken up
# to solve import issues
"""
All work towards a common standard for neuron type naming conventions
should be implemented here. This is only in the case where the underlying
rules cannot be implemented in a consistent way in the ontology. The ultimate
objective for any entry here should be to have it ultimately implemented as
a rule plus operating from single standard ontology file. """
Config()  # explicitly load the core graph TODO need a lighter weight way to do this
OntologyGlobalConventions = _ogc = injective_dict(
    L1 = Phenotype('UBERON:0005390', 'ilxtr:hasLayerLocationPhenotype'),
    L2 = Phenotype('UBERON:0005391', 'ilxtr:hasLayerLocationPhenotype'),
    L3 = Phenotype('UBERON:0005392', 'ilxtr:hasLayerLocationPhenotype'),
    L4 = Phenotype('UBERON:0005393', 'ilxtr:hasLayerLocationPhenotype'),
    L5 = Phenotype('UBERON:0005394', 'ilxtr:hasLayerLocationPhenotype'),
    L6 = Phenotype('UBERON:0005395', 'ilxtr:hasLayerLocationPhenotype'),

    CR = Phenotype('PR:000004968', 'ilxtr:hasMolecularPhenotype'),
    CB = Phenotype('PR:000004967', 'ilxtr:hasMolecularPhenotype'),
    NPY = Phenotype('PR:000011387', 'ilxtr:hasMolecularPhenotype'),
    SOM = Phenotype('PR:000015665', 'ilxtr:hasMolecularPhenotype'),
    PV = Phenotype('PR:000013502', 'ilxtr:hasMolecularPhenotype'),
    VIP = Phenotype('PR:000017299', 'ilxtr:hasMolecularPhenotype'),
    CCK = Phenotype('PR:000005110', 'ilxtr:hasMolecularPhenotype'),
    GABA = Phenotype('CHEBI:16865', 'ilxtr:hasNeurotransmitterPhenotype'),

    AC = Phenotype('ilxtr:PetillaSustainedAccomodatingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),
    NAC = Phenotype('ilxtr:PetillaSustainedNonAccomodatingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),
    STUT = Phenotype('ilxtr:PetillaSustainedStutteringPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),
    IR = Phenotype('ilxtr:PetillaSustainedIrregularPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),
    b = Phenotype('ilxtr:PetillaInitialBurstSpikingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),
    c = Phenotype('ilxtr:PetillaInitialClassicalSpikingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),
    d = Phenotype('ilxtr:PetillaInitialDelayedSpikingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),

)
{
        #Rat = Phenotype('NCBITaxon:10116', _PHEN),


        #PV = Phenotype('NIFMOL:nifext_6', 'ilxtr:hasMolecularPhenotype'),
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
_ogc['L2/3'] = LogicalPhenotype(OR, _ogc['L2'], _ogc['L3'])
_ogc['L5/6'] = LogicalPhenotype(OR, _ogc['L5'], _ogc['L6'])
