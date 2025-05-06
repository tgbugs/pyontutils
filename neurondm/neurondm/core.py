#!/usr/bin/env python3
import os
import sys
import atexit
import inspect
import tempfile
from pprint import pformat
from pathlib import Path, PurePath as PPath
from importlib import import_module, reload
from collections import defaultdict
from urllib.error import HTTPError
import git
import rdflib
import requests
import ontquery as oq
import orthauth as oa
from rdflib.extras import infixowl
from git import Repo
from ttlser import natsort
from augpathlib import RepoPath
from pyontutils import combinators as cmb
from pyontutils.core import Ont, OntId as bOntId, OntTerm as bOntTerm
from pyontutils.core import OntConjunctiveGraph, OntResAny, OntResIri, OntResPath
from pyontutils.utils import stack_magic, injective_dict, makeSimpleLogger, cacheout
from pyontutils.utils import TermColors as tc, subclasses, get_working_dir
from pyontutils.config import auth as pauth, working_dir
from pyontutils.scigraph import Graph, Vocabulary
from pyontutils.qnamefix import cull_prefixes
from pyontutils.annotation import AnnotationMixin
from pyontutils.namespaces import makePrefixes, OntCuries, definition, replacedBy, partOf
from pyontutils.namespaces import TEMP, UBERON, ilxtr, PREFIXES as uPREFIXES, NIFRID
from pyontutils.namespaces import rdf, rdfs, owl, skos
from . import orders

orders.to_rdf, orders.from_rdf = orders.bind_rdflib()

log = makeSimpleLogger('neurondm')
auth = oa.configure_here('auth-config.py', __name__, include=pauth)
cfg = oa.core.ConfigBase(None)  # FIXME hack to expand paths
ont_checkout_ok = auth.get('nifstd-checkout-ok')
RDFL = oq.plugin.get('rdflib')
_SGR = oq.plugin.get('SciGraph')
_done = set()
_partial_order_linker = ilxtr.neuronPartialOrder
offline = False  # FIXME TODO detect and/or set from config

uPREFIXES['neurdf'] = 'http://uri.interlex.org/tgbugs/uris/readable/neurdf/'
uPREFIXES['neurdf.pred'] = 'http://uri.interlex.org/tgbugs/uris/readable/neurdf/pred/'

# iterate over axes to populate prefixes
for prefix_ee, namespace_ee in (
        ('eqv', 'eqv'),
        ('ent', 'ent'),
        ('eqv.neg', 'eqv/neg'),
        ('ent.neg', 'ent/neg'),):
    for prefix_oo, namespace_oo in (
            (None, None),
            ('uo', 'union'),
            ('io', 'intsec'),
            ('iopo', 'intsecpartof'),):

        if prefix_oo is None:
            prefix = 'neurdf.' + prefix_ee
            namespace = uPREFIXES['neurdf.pred'] + namespace_ee + '/'
        else:
            prefix = 'neurdf.' + prefix_ee + '.' + prefix_oo
            namespace = uPREFIXES['neurdf.pred'] + namespace_ee + '/' + namespace_oo + '/'

        uPREFIXES[prefix] = namespace


neurdf = rdflib.Namespace(uPREFIXES['neurdf'])


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

    'UnionOf',
    'IntersectionOf',
    'IntersectionOfPartOf',

    'Phenotype',
    'NegPhenotype',
    'EntailedPhenotype',
    'NegEntailedPhenotype',
    'LogicalPhenotype',
    'EntailedLogicalPhenotype',
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


# helper class
class OntId(bOntId):
    """ explicit instantiation of a distinct OntId """


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

def getPhenotypePredicates(graph, *roots):
    # put existing predicate short names in the phenoPreds namespace (TODO change the source for these...)
    qstring = ('SELECT DISTINCT ?prop WHERE {' +
               ('UNION'.join(f'{{ ?prop rdfs:subPropertyOf* {root} . }}' for root in roots))
               + '}')
    out = [_[0] for _ in graph.query(qstring)]
    literal_map = {uri.rsplit('/',1)[-1]:uri for uri in out}  # FIXME this will change
    classDict = {uri.rsplit('/',1)[-1]:uri for uri in out}  # need to use label or something
    classDict['_litmap'] = literal_map
    class meta(type):
        def __contains__(self, value):
            return value in out

    class whenyoujustneedastaticiterable(metaclass=meta): pass
    phenoPreds = type('PhenoPreds', (whenyoujustneedastaticiterable,), classDict)  # FIXME this makes it impossible to add fake data
    predicate_supers = {s:tuple(o for o in
                                graph.transitive_objects(s, rdfs.subPropertyOf)
                                if o != s) for s in out}

    return phenoPreds, predicate_supers


def add_partial_orders(graph, nested):
    for s, nst in nested.items():
        bn = orders.to_rdf(graph, nst)
        graph.add((s, _partial_order_linker, bn))

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
    def __init__(self, local_conventions=False, render_entailed=True):
        """ `local_conventions=True` -> serialize using current LocalNamingConventions """
        self._do_ent = False
        self.render_entailed = render_entailed
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
                return phen.__class__._rank, self._convention_lookup[phen]
            else:
                label = getattr(phen, self._label_property)
                if isinstance(label, tuple):
                    # duplicate labels issues
                    msg = f'bad label {label!r} for {phen}'
                    raise TypeError(msg)
                return phen.__class__._rank, label

        self._key = _key

        (self.functions,
         self.predicates) = zip(*((getattr(self, function_name),
                                   self.predicate_namespace[function_name])
                                  for function_name in self._order))

    def __call__(self, neuron, render_entailed=None):
        # FIXME consider creating a new class every time
        # it will allow state to propagate more easily?
        render_entailed = self.render_entailed and (render_entailed is None or render_entailed)
        labels = []
        entailed = []
        for function_name, predicate in zip(self._order, self.predicates):
            if predicate in neuron._pesDict:
                #phenotypes = sorted(neuron._pesDict[predicate], key=self._key)
                phenotypes = neuron._pesDict[predicate]
                if not phenotypes:
                    log.warning('wat: {neuron}')
                    continue

                function = getattr(self, function_name)
                # TODO resolve and warn on duplicate phenotypes in the same hierarchy
                # TODO negative phenotypes
                less_entailed = [p for p in phenotypes
                                 if not isinstance(p, EntailedPhenotype)]
                _sl = list(function(less_entailed))  # must express to get -1
                if function_name == 'hasCircuitRolePhenotype':
                    sub_labels = _sl
                elif _sl and _sl[-1] == ')':
                    # don't sort the parens, only the contents
                    _ssl = sorted(_sl[1:-1])
                    _ssl[-1] = _ssl[-1] + ')'
                    sub_labels = _sl[:1] + _ssl
                else:
                    sub_labels = sorted(_sl)

                labels += sub_labels

                yes_entailed = [p for p in phenotypes
                                if isinstance(p, EntailedPhenotype)]
                try:
                    self._do_ent = True
                    elabels = list(function(yes_entailed))
                    if elabels and elabels[-1] == ')':
                        _el = sorted(elabels[1:-1])
                        _el[-1] = _el[-1] + ')'
                        elabels = elabels[:1] + _el
                finally:
                    self._do_ent = False
                entailed += elabels

        if (isinstance(neuron, Neuron) and  # is also used to render LogicalPhenotype collections
            self.predicate_namespace['hasCircuitRolePhenotype'] not in neuron._pesDict):
            labels += ['neuron']

        if isinstance(neuron, NeuronEBM):
            if neuron._shortname:
                labels += [neuron._shortname]

        label = self.field_separator.join(labels)

        if entailed and render_entailed:
            ent_labels = '(implies ' + self.field_separator.join(entailed) + ')'
            label += ' ' + ent_labels

        return label

    def _default(self, phenotypes):
        #log.debug([self._key(p) for p in phenotypes])
        for p in sorted(phenotypes, key=self._key):
            if isinstance(p, EntailedPhenotype) and not self._do_ent:
                # FIXME TODO I think it is correct to drop these
                raise TypeError('entailed should have been filtered '
                                'before arriving here')

            if isinstance(p, NegPhenotype):
                prefix = '-'
            else:
                prefix = ''

            if isinstance(p, LogicalPhenotype):
                yield self._logical_default(p)
                return

            if p in self._convention_lookup:
                yield prefix + self._convention_lookup[p]
            elif self._do_ent and Phenotype(p) in self._convention_lookup:
                yield prefix + self._convention_lookup[Phenotype(p)]
            else:
                yield prefix + getattr(p, self._label_property)

    def _logical_default(self, lp):
        if self.local_conventions:
            inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
            if lp in inj:
                return inj[lp]

        label = self(lp)
        op = OntId(lp.op).suffix
        return f'({op} {label})'

    @od
    def hasTaxonRank(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasInstanceInTaxon(self, phenotypes):
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
    def hasSomaLocationLaterality(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasSomaLocatedIn(self, phenotypes):  # hasSomaLocation?
        yield from self._default(phenotypes)
    @od
    def hasLayerLocationPhenotype(self, phenotypes):  # TODO soma naming...
        yield from self._default(phenotypes)
    @od
    def hasSomaLocatedInLayer(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasDendriteLocatedIn(self, phenotypes):
        yield from self._with_thing_located_in('with-dendrite{}-in', phenotypes)

    @od
    def hasAxonLocatedIn(self, phenotypes):
        yield from self._with_thing_located_in('with-axon{}-in', phenotypes)  # FIXME terminating too early

    @od
    def hasPresynapticElementIn(self, phenotypes):
        yield from self._with_thing_located_in('with-presynaptic-element-in', phenotypes)

    @od
    def hasAxonPresynapticElementIn(self, phenotypes):
        yield from self._with_thing_located_in('with-axon-presynaptic-element-in', phenotypes)

    @od
    def hasPresynapticTerminalsIn(self, phenotypes):
        yield from self._with_thing_located_in('with-presynaptic-terminals-in', phenotypes)

    @od
    def hasSensorySubcellularElementIn(self, phenotypes):
        yield from self._with_thing_located_in('with-sensory-subcellular-element-in', phenotypes)

    @od
    def hasDendriteSensorySubcellularElementIn(self, phenotypes):
        yield from self._with_thing_located_in('with-dendrite-sensory-subcellular-element-in', phenotypes)

    def _with_thing_located_in(self, prefix_template, phenotypes):
        # TODO consider field separator here as well ... or string quotes ...
        if phenotypes:
            lp = len(phenotypes)
            plural = 's' if '{}' in prefix_template and lp > 1 else ''
            yield '(' + prefix_template.format(plural)

            for i, phenotype in enumerate(phenotypes):
                l = next(self._default((phenotype,)))

                yield l

            yield ')'

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

    def _molecular(self, phenotypes):
        if self.local_conventions:
            yield from self._plus_minus(phenotypes)
        else:
            yield from self._plus_minus([p.asIndicator() for p in phenotypes])
    @od
    def hasMolecularPhenotype(self, phenotypes):
        yield from self._molecular(phenotypes)
    @od
    def hasNeurotransmitterPhenotype(self, phenotypes):
        yield from self._molecular(phenotypes)
    @od
    def hasExpressionPhenotype(self, phenotypes):
        yield from self._molecular(phenotypes)
    @od
    def hasDriverExpressionPhenotype(self, phenotypes):
        yield from self._molecular(phenotypes)
    @od
    def hasDriverExpressionConstitutivePhenotype(self, phenotypes):
        yield from self._molecular(phenotypes)
    @od
    def hasDriverExpressionInducedPhenotype(self, phenotypes):
        yield from self._molecular(phenotypes)
    @od
    def hasReporterExpressionPhenotype(self, phenotypes):
        yield from self._molecular(phenotypes)
    @od
    def hasComputedMolecularPhenotype(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasComputedMolecularPhenotypeFromDNA(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasComputedMolecularPhenotypeFromRNA(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasComputedMolecularPhenotypeFromProtein(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasComputedPhenotype(self, phenotypes):
        yield from self._plus_minus(phenotypes)
    @od
    def hasProjectionLaterality(self, phenotypes):  # TODO where should this go in the order?
        yield from self._with_thing_located_in('projecting', phenotypes)
    @od
    def hasProjectionPhenotype(self, phenotypes):  # consider inserting after end, requires rework of code...
        yield from self._with_thing_located_in('projecting-to', phenotypes)
    @od
    def hasReverseConnectionPhenotype(self, phenotypes):
        yield from self._with_thing_located_in('projected-onto-by', phenotypes)
    @od
    def hasForwardConnectionPhenotype(self, phenotypes):
        yield from self._with_thing_located_in('projecting-onto', phenotypes)
    @od
    def hasConnectionPhenotype(self, phenotypes):
        yield from self._with_thing_located_in('connecting-to', phenotypes)
    @od
    def hasExperimentalPhenotype(self, phenotypes):
        yield from self._default(phenotypes)
    @od
    def hasAnatomicalSystemPhenotype(self, phenotypes):
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
        interneuron_phenotype = self.predicate_namespace['InterneuronPhenotype']
        def suffix():
            # reminder that the phenotype loop variable below binds in here
            if phenotype.p == self.predicate_namespace['IntrinsicPhenotype']:
                return  'neuron'
            elif phenotype.p == interneuron_phenotype:
                return  # interneuron is already in the label
            elif phenotype.p == self.predicate_namespace['MotorPhenotype']:
                return 'neuron'
            else:  # principle, projection, etc.
                return 'neuron'

        # put interneuron last if it is in the phenotypes list
        if interneuron_phenotype in phenotypes:
            phenotypes.remove(interneuron_phenotype)
            phenotypes = phenotypes + [interneuron_phenotype]

        have_neuron = False
        for phenotype in phenotypes:
            value = next(self._default((phenotype,))).lower()
            if not have_neuron:
                have_neuron = 'neuron' in value

            yield value

        if self.local_conventions and have_neuron:
            return

        if phenotypes:  # and not self.local_conventions:
            suffix = suffix()
            if suffix:
                yield suffix


# helper classes

class OntTerm(bOntTerm, OntId):

    _cache_ind = dict()

    def traverse(self, *predicates):
        """ return the graph closure when traversing multiple edge types """
        done = set()
        def inner(term):
            if term in done:
                return term

            done.add(term)
            for predicate in predicates:
                if term(predicate, asTerm=True):
                    for obj in term.predicates[predicate]:
                        if obj.prefix not in ('BFO', 'NLX', 'BIRNLEX', 'NIFEXT'):
                            # avoid continuant and occurent form a cycle >_<
                            yield obj
                            yield from inner(obj)  # FIXME just call traverse again ...

        yield from inner(self)

    def asPhenotype(self, predicate=None, phenotype_class=None):
        if phenotype_class is None:
            phenotype_class = Phenotype

        if predicate is None and self.prefix == 'UBERON':  # FIXME layers
            predicate = ilxtr.hasSomaLocatedIn
        return phenotype_class(self, ObjectProperty=predicate, label=self.label, override=bool(self.label))

    def asIndicator(self):
        if self in self._cache_ind:
            return self._cache_ind[self]

        sco = self(rdfs.subClassOf, depth=2, asTerm=True)
        uris = [t.URIRef for t in sco]
        if ilxtr.PhenotypeIndicator in uris:
            if uris[0] == ilxtr.PhenotypeIndicator:
                return self

            done = False
            for ind in sco:
                if ind.URIRef == ilxtr.PhenotypeIndicator:
                    continue
                elif ind.predicates and ind.predicates['rdfs:subClassOf']:
                    for _sco in ind.predicates['rdfs:subClassOf']:
                        if _sco.URIRef == ilxtr.PhenotypeIndicator:
                            done = True
                            self._cache_ind[self] = ind
                            break

                    if done:
                        break

                else:
                    msg = f'missing predicates {ind}'
                    log.debug(msg)

            assert done
            return ind
        else:
            self._cache_ind[self] = self  # avoid repeated lookup cost which is quite high
            if (self.prefix in ('UBERON', 'PATO', 'FMA', 'ilxtr')):
                pass
            else:
                log.debug(f'No indicator for {self.curie} {self.label}')

            return self

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
        skips = 'pheno:parvalbumin', 'owl:Thing', self.curie
        bads = ('TEMP', 'ilxtr', 'rdf', 'rdfs', 'owl', '_', 'prov', 'ILX', 'BFO1SNAP', 'NLXANAT',
                'NLXCELL', 'NLXNEURNT', 'BFO', 'MBA', 'JAX', 'MMRRC', 'ilx', 'CARO', 'NLX',
                'BIRNLEX', 'NIFEXT', 'obo', 'NIFRID', 'TEMPIND', 'npokb')
        s = self.URIRef
        if self.type is None:
            yield s, rdf.type, owl.Class  # FIXME ... IAO terms fail on this ... somehow
        else:
            _t = self.type
            yield s, rdf.type, (_t if _t.__class__ == rdflib.URIRef else _t.u)

        if self.label:
            _label = self.label
            label = rdflib.Literal(_label)
            yield s, rdfs.label, label

        if not self.validated:
            log.warning(f'{self!r}')
            return

        if self.synonyms is not None:  # FIXME this should never happen :/
            for syn in self.synonyms:
                yield s, NIFRID.synonym, rdflib.Literal(syn)

        if self('rdfs:subClassOf', asTerm=True):
            maybe_use = []
            have_other = False
            for superclass in self.predicates['rdfs:subClassOf']:
                if superclass.curie in skips:
                    continue
                elif 'UBERON' in s and superclass.prefix == 'FMA': # XXX FIXME hardcoded hack
                    continue
                elif superclass.prefix in bads:
                    if (superclass.prefix == 'BFO' or
                        self.prefix in bads or
                        'interlex' in self.iri):
                        maybe_use.append((s, rdfs.subClassOf, superclass.URIRef))
                        continue
                    else:
                        continue
                if superclass.curie != 'owl:Thing':
                    have_other = True
                    yield s, rdfs.subClassOf, superclass.URIRef
                    # ensure that all superclasses are closed for type and label
                    yield superclass.URIRef, rdf.type, owl.Class
                    if superclass.label:
                        _l = rdflib.Literal(superclass.label)
                        yield superclass.URIRef, rdfs.label, _l

            if not have_other and maybe_use:
                # we're not worrying about deduplication here
                yield from maybe_use

        predicates = 'partOf:', 'RO:0002433', 'ilx.partOf:' #'ilxtr:labelPartOf', 'ilxtr:isDelineatedBy', 'ilxtr:delineates'
        done = []
        for predicate in predicates:
            if self(predicate, asTerm=True):
                for superpart in self.predicates[predicate]:
                    if (superpart.prefix in bads or
                        superpart.prefix == 'FMA' and 'UBERON' in s or  # XXX FIXME hardcoded hack to work around bad sparc community terms cross hierarchy issues
                        superpart.curie == self.curie):  # prevent partOfSelf polution
                        continue

                    if (predicate, superpart) not in done:
                        yield from cmb.restriction(OntId(predicate).URIRef,
                                                   superpart.URIRef)(s)

                        # ensure that all superparts are closed for type and label
                        yield superpart.URIRef, rdf.type, owl.Class
                        if superpart.label:
                            _l = rdflib.Literal(superpart.label)
                            yield superpart.URIRef, rdfs.label, _l

                        done.append((predicate, superpart))


if offline:
    bOntTerm.query._services = [  # offline testing
        s for s in bOntTerm.query.services if not
        isinstance(s, oq.plugins.services.interlex.InterLexRemote)]

OntTerm.query_init(*bOntTerm.query.services)
# initializing this way leads to a race condition on calling
# service.setup since the first OntTerm to call setup on a shared
# service is the one that will be attached to the query result
# fortunately in some cases we cache at a level below this


class OntTermOntologyOnly(OntTerm):
    __firsts = ('curie', 'label')  # FIXME why do I need this here but didn't for OntTerm ??

class OntTermInterLexOnly(OntTerm):
    pass

IXR = oq.plugin.get('InterLex')
OntTermOntologyOnly.query_init(*(s for s in OntTerm.query.services if not isinstance(s, IXR)))
if offline:
    OntTermInterLexOnly.query_init()  # offline testing
else:
    OntTermInterLexOnly.query_init(*(s for s in OntTerm.query.services if isinstance(s, IXR)))


class GraphOpsMixin:
    # TODO this could be populated automatically in a OntComplete case
    # given a graph and an id and possibly the set of all possible
    # edges, give access to that id as an object, I'm sure this has been
    # done before

    # TODO even if it is the same underlying graph (conjuctive?) we should
    # still separate the read and write aspects

    default_properties = 'definition', 'synonyms', 'abbrevs', 'hasTemporaryId'
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
        self._replay.append((predicate, *objects))
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
    def abbrevs(self, values):
        self.add_objects(NIFRID.abbrev, *values)

    @property
    def hasTemporaryId(self):
        yield from self.objects(ilxtr.hasTemporaryId)

    @hasTemporaryId.setter
    def hasTemporaryId(self, values):
        self.add_objects(ilxtr.hasTemporaryId, *values)


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
                 import_as_local =      offline,  # also load from local? XXX FIXME offline hack?
                 load_from_local =      True,
                 branch =               auth.get('neurons-branch'),  # FIXME rename to ref
                 sources =              tuple(),
                 source_file =          None,
                 ignore_existing =      False,
                 py_export_dir=         None,
                 ttl_export_dir=        (auth.get_path('ontology-local-repo') /  # FIXME neurondm.lang for this?
                                         'ttl/generated/neurons'),  # subclass with defaults from cls?
                 git_repo=              None,
                 file =                 None,
                 local_conventions =    False,
                 import_no_net =        offline,  # ugh XXX FIXME very dumb offline hack
                ):

        olr = auth.get_path('ontology-local-repo')  # we get this again because it might have changed
        if ttl_export_dir is not None:
            if not isinstance(ttl_export_dir, Path):
                ttl_export_dir = Path(ttl_export_dir).resolve()

            _lbwd = get_working_dir(ttl_export_dir)
            local_base = ttl_export_dir if _lbwd is None else _lbwd
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
            import augpathlib as aug
            if local_base is None:  # FIXME ttl vs python ... read vs write :/
                local_base = git_repo
            if ttl_export_dir is None:
                ttl_export_dir = git_repo
            elif aug.AugmentedPath(ttl_export_dir).relative_path_to(git_repo):
                pass  # just make sure that if export loc is not in the repo we fail

        import os  # FIXME probably should move some of this to neurons.py?

        self.__name = name  # TODO allow reload from owl to get the load graph? how to handle this

        graphBase.python_subclasses = list(subclasses(NeuronEBM)) + [Neuron, NeuronCUT]
        graphBase.knownClasses = [OntId(c.owlClass).u
                                  for c in graphBase.python_subclasses]

        imports = list(imports)
        remote = OntId('NIFTTL:') if branch == 'master' else (
            # XXX EVIL HARDCODED defaulting to dev/ by convention KILL IT WITH FIRE
            # DO NOT CHANGE branch IN THIS CASE
            OntId(f'NIFRAW:dev/') if branch is None else OntId(f'NIFRAW:{branch}/'))
        imports += [remote.iri + 'ttl/phenotype-core.ttl',
                    remote.iri + 'ttl/phenotypes.ttl',
                    remote.iri + 'ttl/phenotype-indicators.ttl']
        remote_path = ('' if local_base is None
                       else (ttl_export_dir
                             .resolve()
                             .relative_to(local_base.resolve())))
        out_remote_base = remote.iri.rstrip('/') + '/' + remote_path.as_posix()
        imports = [OntId(i) for i in imports]
        imports = sorted(set(imports))

        remote_base = remote.iri.rsplit('/', 2)[0] if branch == 'master' else remote

        if local_base is None:
            local = olr / 'ttl'
            local_base = local.parent
        else:
            local_base = Path(local_base).resolve()
            local = local_base

        out_local_base = ttl_export_dir
        out_base = out_local_base if False else out_remote_base  # TODO switch or drop local?
        if import_as_local or import_no_net:
            if local.exists() and (local.name == 'NIF-Ontology' or local.parent.name == 'NIF-Ontology'):
                # NOTE: we currently do the translation more ... inelegantly inside of config so we
                # have to keep the translation layer out here (sigh)
                log.debug(f'local ont {local}')
                core_graph_paths = [(Path(local,
                                        i.iri.replace(remote.iri, ''))
                                    .relative_to(local_base).as_posix())
                                    if remote.iri in i.iri else
                                    i for i in imports]

                # part of graph
                # FIXME hardcoded ...
                partofpath = RepoPath(olr, 'ttl/generated/part-of-self.ttl')
                repo = partofpath.repo
                ref_name = repo.currentRefName()
                if ref_name != branch and not ont_checkout_ok:
                    if ref_name is None:
                        ref_name = repo.head.commit.hexsha
                    raise graphBase.GitRepoOnWrongBranch(
                        f'Local git repo not on {branch} branch!\n'
                        f'It is on {ref_name} instead.\n'
                        f'Please run `git checkout {branch}` in '
                        f'{repo.working_dir}, '
                        'set NIFSTD_CHECKOUT_OK= via export or '
                        'at runtime, or set checkout_ok=True.')

                elif ont_checkout_ok:
                    graphBase.repo = repo
                    graphBase.working_branch = next(h for h in repo.heads
                                                    if h.name == branch)
                    graphBase.original_branch = repo.active_branch
                    graphBase.set_repo_state()

                graphBase.part_of_graph = OntResAny(partofpath).graph
                [_done.add(s) for s, o in graphBase.part_of_graph[:rdfs.subClassOf:]]

            else:
                log.debug('local share')
                udp = cfg._pathit('{:user-data-path}/neurondm/')
                search_paths = [
                    udp,
                    cfg._pathit('{:prefix}/share/neurondm/'),
                    Path('./share/neurondm/').absolute(),
                ]
                for base in search_paths:
                    if (base / 'phenotypes.ttl').exists():
                        core_graph_paths = [(base / Path(iri).name).as_uri() for iri in imports]
                        break
                else:
                    msg = '\n' + '\n'.join([p.as_posix() for p in search_paths])
                    # has to be a ValueError because the way imports are set up is awful
                    # fortunately we only have to deal with this for building a release
                    # or, unfortunately if someone tries to build from git without
                    # reading the instructions that they need the NIF-Ontology installed
                    # in order to do the build :/
                    raise ValueError(f'no core paths ... {msg}')

                # part of graph
                # FIXME hardcoded ...

                partofpath = base / 'part-of-self.ttl'
                graphBase.part_of_graph = OntResPath(partofpath.as_posix()).graph  # FIXME temp fix for pyontutils 1.6.0
                [_done.add(s) for s, o in graphBase.part_of_graph[:rdfs.subClassOf:]]

        else: # XXX this branch always triggers if Config is called with only a path/name
            log.debug('remote')
            core_graph_paths = imports

            partofpath = remote.iri + 'ttl/generated/part-of-self.ttl'
            _opg = graphBase.part_of_graph if hasattr(graphBase, 'part_of_graph') else None
            graphBase.part_of_graph = OntResIri(partofpath).graph
            if _opg is not None:
                _opg.namespace_manager.populate(graphBase.part_of_graph.namespace_manager)

            if local.exists() and (local.name == 'NIF-Ontology' or local.parent.name == 'NIF-Ontology'):
                _writepath = RepoPath(olr, 'ttl/generated/part-of-self.ttl')
            else:
                _writepath = cfg._pathit('{:user-data-path}/neurondm/part-of-self.ttl')
                if not _writepath.parent.exists():
                    _writepath.parent.mkdir(parents=True)

            graphBase.part_of_graph.path = _writepath
            [_done.add(s) for s, o in graphBase.part_of_graph[:rdfs.subClassOf:]]

        log.debug(core_graph_paths)

        out_graph_path = (out_local_base / f'{name}.ttl')

        class lConfig(self.__class__):
            iri = out_remote_base.rstrip('/') + f'/{name}.ttl'

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

        for _name, value in kwargs.items():
            # FIXME only works if we do this in __new__
            #@property
            def nochangepls(v=value):
                return v

            setattr(self, _name, nochangepls)
            # FIXME need a way to make it clear that changing kwargs values
            # will only confuse you ...
            #setattr(self, _name, value)

        try:
            graphBase.configGraphIO(**kwargs)  # FIXME KILL IT WITH FIRE
        except graphBase.GitRepoOnWrongBranch as e:
            #breakpoint()
            log.exception(e)
            # XXX ALSO KILL THIS WITH FIRE
            # XXX NOTE that since _lb will not be a git repo baring some insanity
            # the path {:user-data-path}/neurondm/git-repo set above in configGraphIO
            # will take precedence (UGH what a mess), _lb is forced to match the behavior above
            # otherwise this will get out of sync an be even more confusing than they already are
            _lb = cfg._pathit('{:user-data-path}/neurondm/git-repo')  # XXX isn't actually used
            # this whole layer should never care about where a graph will be serialized, unfortunately
            # the legacy codebase assumes that this layer does handle it, so we need a stopgap
            sigh = Config(
                 name =                 name,
                 prefixes =             prefixes,
                 imports =              imports,
                 import_as_local =      import_as_local,
                 load_from_local =      load_from_local,
                 branch =               None,
                 sources =              sources,
                 source_file =          source_file,
                 ignore_existing =      ignore_existing,
                 py_export_dir=         py_export_dir,
                 ttl_export_dir=        _lb,
                 git_repo=              None,
                 file =                 file,
                 local_conventions =    local_conventions,
                 import_no_net =        import_no_net,
            )
            self.__dict__ = sigh.__dict__
            return

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

    def neurdf_graph(self, graph=None):
        if graph is None:
            graph = OntConjunctiveGraph()
            graph.namespace_manager.populate_from(uPREFIXES)

        for n in self.neurons():
            for t in n._instance_neurdf():
                try:
                    graph.add(t)
                except Exception as e:
                    msg = f'problem with instance neurdf for\n{neuron}\n{t}'
                    log.error(msg)
                    #log.exception(e)
                    raise e

        return graph

    def neurdf_ttl(self):
        g = self.neurdf_graph()
        neurdf_ttl = g.serialize(format='nifttl').decode()
        return neurdf_ttl

    def python(self):
        # FIXME do this correctly
        return graphBase.python()

    @property
    def name(self):
        return self.__name

    @property
    def core_graph(self):
        return graphBase.core_graph  # FIXME :/

    @property
    def part_of_graph(self):
        return graphBase.part_of_graph

    def neurons(self):
        return sorted(self.existing_pes)  # FIXME stupidly slow

    def activate(self):
        """ set this config as the active config """
        raise NotImplementedError()

    def write(self):
        # FIXME per config prefixes using derived OntCuries?
        # FIXME code duplication with graphBase
        [n._sigh() for n in self.existing_pes]  # ugh
        og = cull_prefixes(self.out_graph, prefixes={**graphBase.prefixes, **uPREFIXES})
        og.filename = graphBase.ng.filename
        path = Path(og.filename)
        ppath = path.parent
        if not ppath.exists():
            ppath.mkdir(parents=True)

        og.write()
        og.g.path = path
        self._written_graph = og.g  # FIXME HACK
        self.part_of_graph.write()
        log.debug(f'Neurons ttl file written to {path}')

    def write_python(self):
        # FIXME hack, will write other configs if call after graphbase has switched
        graphBase.write_python()

    def load_existing(self, load_graph=None):
        """ advanced usage allows loading multiple sets of neurons and using a config
            object to keep track of the different graphs """
        # bag existing

        try:
            next(iter(self.neurons()))
            raise self.ExistingNeuronsError('Existing neurons detected. Please '
                                            'load from file before creating neurons!')
        except StopIteration:
            pass

        def getClassType(s, graph):
            Class = infixowl.Class(s, graph=graph)

            for cls in Class.subClassOf:
                if isinstance(cls.identifier, rdflib.URIRef):
                    yield cls.identifier

            for ec in Class.equivalentClass:
                if isinstance(ec.identifier, rdflib.BNode):
                    bc = infixowl.CastClass(ec, graph=graph)
                    if isinstance(bc, infixowl.BooleanClass):
                        for id_ in bc._rdfList:
                            if isinstance(id_, rdflib.URIRef):
                                yield id_  # its one of our types

        ranked = sorted(graphBase.python_subclasses, key=oq.utils.SubClassCompare, reverse=True)
        ranked_ids = [r.owlClass for r in ranked]

        def mostDerived(classes):
            def key(cid):
                inrid = cid in ranked_ids
                return not inrid, (ranked_ids.index(cid) if inrid else 0)

            return sorted(classes, key=key)[:1]

        # bug is that I am not wiping graphBase.knownClasses and swapping it for each config
        # OR the bug is that self.load_graph is persisting, either way the call to type()
        # below seems to be the primary suspect for the issue

        if not graphBase.ignore_existing:
            ogp = Path(graphBase.ng.filename)  # FIXME ng.filename <-> out_graph_path property ...
            if ogp.exists() or load_graph is not None:
                from itertools import chain
                if load_graph is None:
                    #from rdflib import Graph  # FIXME
                    self.load_graph = OntConjunctiveGraph().parse(graphBase.ng.filename, format='turtle')
                else:
                    self.load_graph = load_graph

                graphBase.load_graph = self.load_graph
                # FIXME memory inefficiency here ...
                _ = [graphBase.in_graph.add(t) for t in graphBase.load_graph]  # FIXME use conjuctive ...
                if len(graphBase.python_subclasses) == 2:  # FIXME magic number for Neuron and NeuronCUT
                    ebms = [type(OntId(s).suffix, (NeuronCUT,), dict(owlClass=s))
                            for s in self.load_graph[:rdfs.subClassOf:NeuronEBM.owlClass]
                            if not graphBase.knownClasses.append(s)]
                else:
                    ebms = []

                graphBase._nested = orders.from_rdf(self.load_graph, _partial_order_linker)

                class_types = [(type, s) for s in self.load_graph[:rdf.type:owl.Class]
                               for type in mostDerived(getClassType(s, self.load_graph)) if type]
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
                sys.path = [containing] + sys.path
            full_path = graphBase.compiled_location / graphBase.filename_python()
            module_path = graphBase.compiled_location.name + '.' + full_path.stem
            module = import_module(module_path)  # this returns the submod
            #log.debug('\n' + inspect.getsource(module) + '\n')

            # module caching breaks tests for this because import_module
            # assumes that nothing has changed :/ so we have to reload
            if module_path in graphBase._force_reload:
                # FIXME TODO SIGH yeah, if we hit something with the exact
                # same name reload it, for now for testing, but in general
                # because someone might modify a file by hand and want to
                # reload in an existing session ...
                module = reload(module)
                #log.debug('\n' + inspect.getsource(module) + '\n')
            else:
                graphBase._force_reload[module_path] = True

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


class AcceptAllPreds:
    def __getattr__(self, attr):
        log.warning(f'fake predicate! {attr}')
        return TEMP[attr]


class AcceptAllKeys:
    def __getitem__(self, key):
        log.warning(f'fake super! {key}')
        return tuple()

# classes for complex owl objects


class OwlObject:
    operator = None
    _osn = None
    _rank = '5'
    def __init__(self, *members):
        # FIXME conversion iris really needs to happen at this step and not be deferred becaues
        # the semantics can be changed as a result and also because unexpanded won't match
        _members = members
        members = [self.expand(m) for m in members]  # XXX MUST normalize here or all sanity is lost, local conventions thus must be known from the context and not be implicit, should probably passed to Config?
        self._sm = frozenset(members)
        self._members = tuple(sorted(self._sm))
        if len(self._members) != len(members):
            raise ValueError(f'duplicates in members! {members}')

    def _instance_neurdf(self, subject, neuron=None):
        # mapping of the operator to predicate is handled in the calling scope
        yield subject, rdf.type, rdf.List
        members = self.members()
        lmmo = len(members) - 1
        for i, m in enumerate(members):
            if isinstance(m, OwlObject):
                msg = f'cannot serialize nested OwlObjects to neurdf right now {m}'
                raise NotImplementedError(msg)

            yield subject, rdf.first, m
            if i == lmmo:
                # we're done here terminate the list
                new_subject = rdf.nil
            else:
                new_subject = rdflib.BNode()

            yield subject, rdf.rest, new_subject
            subject = new_subject

    def __hash__(self):
        return hash(self._sm)

    def __eq__(self, other):
        out = type(self) == type(other) and self._sm == other._sm
        #if not out:
            # YEP it's str vs rdflib.URIRef issues
            #print('AAAAAAAAAAAAA', out, self, other)
        return out

    def __gt__(self, other):
        return not self <= other

    def __gte__(self, other):
        return self == other or self > other

    def __lt__(self, other):
        # by doing the type check in __lt__ if the types do not match
        # then OwlObject will be determined to be greater than the other value
        # meaning that it will appear later in a sorted list
        return type(self) == type(other) and self._members < other._members

    def __lte__(self, other):
        return self == other or self < other

    def __str__(self, parent=None):
        if parent is None:
            fmt = lambda x: x
        else:
            if hasattr(parent, 'ng'):
                fmt = parent.ng.qname
            else:
                fmt = parent.in_graph.namespace_manager.qname

        members = [m.__str__(parent=parent) if isinstance(m, OwlObject) else repr(fmt(m)) for m in self.members()]
        fmem = ', '.join(members)
        return f'{self.__class__.__name__}({fmem})'

    def _uri_frag(self, parent, nest=0):
        phenotype_class = parent.__class__
        if hasattr(phenotype_class.in_graph, 'namespace_manager'):
            qname = phenotype_class.in_graph.namespace_manager.qname
        else:
            qname = lambda x: x

        ps = [m._uri_frag(parent, nest=nest + 1)
              if isinstance(m, OwlObject) else phenotype_class(m)
              for m in self.members()]

        def eff(p):
            return qname(p.p).replace(':', '-') if isinstance(p, phenotype_class) else p

        return f'{self._rank}-{nest}-{self._osn}-' + '-'.join([f'{self._rank}-{nest}-{eff(p)}' for p in ps])

    def _for_thing(self, parent, thing, call=False, join=' ', wrap=True):
        phenotype_class = parent.__class__
        if hasattr(phenotype_class.in_graph, 'namespace_manager'):
            qname = phenotype_class.in_graph.namespace_manager.qname
        else:
            qname = lambda x: x

        ps = [phenotype_class(m, parent.e) for m in self.members()]
        pls = []
        for p in ps:
            _v = getattr(p, thing)
            if call:
                v = _v()
            else:
                v = _v
            pls.append(qname(p.p) if v is None else v)

        #print(pls)
        derp = join.join(pls)
        asdf = f'{self._osn}{join}{derp}'
        if wrap:
            return f'({asdf})'
        else:
            return asdf

    def members(self):
        return self._members

    def _graphify(self, parent=None, members=None, graph=None):
        if self.operator is None:
            msg = 'implement in subclass'
            raise NotImplementedError(msg)

        if members is None:
            # make it possible to modify members, e.g. by wrapping them inside a restriction
            members = [m._graphify(parent=parent, graph=graph) if isinstance(m, OwlObject)
                       # FIXME we really shouldn't be doing this here right ???
                       else (parent.in_graph.namespace_manager.expand(m) if type(m) == str else m)
                       for m in self.members()]

        if graph is None:
            graph = OntConjunctiveGraph()

        return infixowl.BooleanClass(
            operator=self.operator, members=members, graph=graph)

    @staticmethod  # FIXME FIXME FIXME EVIL EVIL EVIL TEMP WORKAROUND
    def expand(putativeURI):
        # FIXME FIXME
        # this is exactly the same as graphBase except that it is static
        # and fully stateful which is stupid and evil (and known to be such)
        # implicit local conventions are stupid and need to be fixed
        if isinstance(putativeURI, OwlObject):
            return putativeURI  # already dealt with in init of that object
        elif isinstance(putativeURI, OntId):
            return putativeURI.u
        elif isinstance(putativeURI, rdflib.URIRef):
            return putativeURI

        if type(putativeURI) == infixowl.Class:
            return putativeURI.identifier
        elif type(putativeURI) == str:
            return OntId(putativeURI).u
            try: prefix, suffix = putativeURI.split(':',1)
            except ValueError:  # FIXME this is wrong...
                return rdflib.URIRef(putativeURI)
            if prefix in graphBase._namespaces:  # XXX EVIL HAPPENS HERE
                return graphBase._namespaces[prefix][suffix]  # XXX EVIL HAPPENS HERE
            else:
                raise KeyError('Namespace prefix does not exist:', prefix)
        else:  # FIXME need another check probably...
            return putativeURI


class UnionOf(OwlObject):
    operator = owl.unionOf
    _osn = 'union-of'
    _rank = '6'


class IntersectionOf(OwlObject):
    operator = owl.intersectionOf
    _osn = 'intersection-of'
    _rank = '7'
    def _for_thing(self, parent, thing, call=False, **kwargs):
        if parent.e in parent._location_predicates:
            return IntersectionOfPartOf(*self.members())._for_thing(parent, thing, call=call, **kwargs)
        else:
            return super()._for_thing(parent, thing, call=call, **kwargs)

    def _graphify(self, parent=None, graph=None):
        if graph is None:
            graph = OntConjunctiveGraph()

        if parent.e in parent._location_predicates:
            return IntersectionOfPartOf(*self.members())._graphify(
                graph=graph,
                parent=parent)
        else:
            return super()._graphify(graph=graph, parent=parent)


class IntersectionOfPartOf(OwlObject):
    operator = owl.intersectionOf
    _osn = 'intersection-of-part-of'
    _rank = '8'
    def _graphify(self, graph=None, parent=None):
        if graph is None:
            graph = OntConjunctiveGraph()

        members = []
        expand = parent.in_graph.namespace_manager.expand  # FIXME SIGH
        for m in self.members():
            if type(m) == str:
                m = expand(m)  # FIXME SIGH

            if isinstance(m, OwlObject):
                res = m._graphify(graph=graph, parent=parent)
            else:
                res = infixowl.Restriction(onProperty=partOf,
                                           someValuesFrom=m,
                                           graph=graph)
            members.append(res.identifier)

        return super()._graphify(graph=graph, members=members, parent=parent)


# the monstrosity

class graphBase:
    core_graph = 'ASSIGN ME AFTER IMPORT!'
    in_graph = 'ASSIGN ME AFTER IMPORT!'
    out_graph = 'ASSIGN ME AFTER IMPORT'

    _predicates = AcceptAllPreds()
    LocalNames = {}

    _registered = False

    __import_name__ = __name__

    # variables that cause errors if they are not present at the class level
    # when trying to use graphBase before configGraphIO has been called (sigh)
    config = None  # XXX ICK avoid AttributeError when no call to Config()
    _predicate_supers = AcceptAllKeys()  # XXX also ick
    _location_predicates = tuple()  # XXX SIGH
    _location_predicate_supers = {}  # XXX SIGH
    local_conventions = False  # XXX SIGH

    _force_reload = {}  # super sigh

    #_sgv = Vocabulary(cache=True)

    class owlClassMismatch(Exception):
        pass

    class GitRepoOnWrongBranch(Exception):
        """ Git repo is checked out to the wrong branch. """

    class ShouldNotHappenError(Exception):
        """ big oops """

    def __init__(self):
        if type(self.core_graph) == str:
            raise TypeError(f'You must have at least a core_graph: {self.core_graph!r}')

        if type(self.in_graph) == str:
            # FIXME AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            # this is assigned many may times for every instance
            # which is usually probably what we want in cases where
            # phenotypes are defined before a call to config
            # XXX HOWEVER this means breakage can happen if Config
            # is not called before first using ANY of the subclasses
            # which is DUMB, specifically misaligned namespace_managers
            self.in_graph = self.core_graph

        if type(self.out_graph) == str:
            self.out_graph = self.in_graph

        self._namespaces = {p:rdflib.Namespace(ns) for p, ns in self.in_graph.namespaces()}

    def expand(self, putativeURI):
        if isinstance(putativeURI, OntId):
            return putativeURI.u
        elif isinstance(putativeURI, rdflib.URIRef):
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
                    # breakpoint()
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
                      compiled_location= (cfg._pathit('{:user-data-path}/neurondm/compiled')
                                          if working_dir is None else
                                          Path(working_dir, 'neurondm/neurondm/compiled')),
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
        olr = auth.get_path('ontology-local-repo')

        if local_base is None:
            local_base = olr
        graphBase.local_base = Path(local_base).expanduser().resolve()
        graphBase.remote_base = remote_base

        def makeLocalRemote(suffixes):
            remote = [(graphBase.remote_base.rstrip('/') + '/' + s)  # XXX WHY was branch passed here ?!??! HOW DID THIS EVER WORK !?
                      if '://' not in s else  # 'remote' is file:// or http[s]://
                      s for s in suffixes]
            # TODO the whole thing needs to be reworked to not use suffixes...
            local = [(graphBase.local_base / s).as_uri()
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
            and graphBase.local_base == olr
            and graphBase.local_base.exists()):

            repo = Repo(graphBase.local_base.as_posix())
            ref_name = repo.currentRefName()
            if ref_name != branch and not checkout_ok:
                if ref_name is None:
                    ref_name = repo.head.commit.hexsha
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
                        log.exception(e)
                        udp = cfg._pathit('{:user-data-path}/neurondm/git-repo')  # XXX hardcoded
                        trp = RepoPath(udp)
                        if not trp.exists():
                            trp.init()

                        graphBase.local_base = trp
                        # FIXME this is a stupid hack, and a reminder that the whole
                        # set up inside graphBase was a horrible mistake
                        # all sorts of things are thrown out of sync because of this
                        out_graph_path = (graphBase.local_base /
                                          'ttl/generated/neurons' /
                                          Path(out_graph_path).name)
                        if hasattr(graphBase, 'part_of_graph'):
                            graphBase.part_of_graph.path = (
                                graphBase.local_base /
                                'ttl/generated' /
                                graphBase.part_of_graph.path.name)

                        repo = trp.repo
                        msg = f'No NIF-Ontology repo found. Using a temporary repo at {trp}'
                        log.critical(msg)
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
            core_graph = OntConjunctiveGraph()

        if use_local_import_paths:
            _use_core_paths = local_out_imports
        else:
            _use_core_paths = use_core_paths

        for cg in _use_core_paths:
            try:
                #core_graph.parse(cg, format='turtle')
                if cg.startswith('file://'):
                    cg = cg[(8 if os.name == 'nt' else 7):]  # FIXME ... from_uri ...
                    ora = OntResAny(RepoPath(cg))
                else:
                    ora = OntResIri(cg)

                giri = ora.identifier_bound
                core_graph.addN(((*t, giri) for t in ora.graph))
            except (FileNotFoundError,
                    HTTPError,
                    requests.exceptions.ConnectionError) as e:
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

        in_graph.namespace_manager.populate_from(PREFIXES)
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
            out_graph.namespace_manager.populate_from(PREFIXES)

        graphBase.out_graph = out_graph

        # python output setup
        graphBase.compiled_location = compiled_location

        new_graph = graphBase.ng  # FIXME remove this usage
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

        proot = graphBase.core_graph.qname(PHENO_ROOT)
        mroot = graphBase.core_graph.qname(MOD_ROOT)
        preds, pred_supers = getPhenotypePredicates(graphBase.core_graph, proot, mroot)
        graphBase._predicates, graphBase._predicate_supers = preds, pred_supers
        lp, lps = getPhenotypePredicates(graphBase.core_graph, 'ilxtr:hasLocationPhenotype')
        graphBase._location_predicates, graphBase._location_predicate_supers = lp, lps
        mp, mps = getPhenotypePredicates(graphBase.core_graph, 'ilxtr:hasMolecularPhenotype')
        graphBase._molecular_predicates, graphBase._molecular_predicate_supers = mp, mps

        # scigraph setup
        if not hasattr(graphBase, '_sgv'):
            if scigraph is not None:
                graphBase._sgv = Vocabulary(cache=True, basePath=scigraph)
            else:
                graphBase._sgv = Vocabulary(cache=True)

    @staticmethod
    def write():
        [n._sigh() for n in graphBase.neurons()]  # ugh
        og = cull_prefixes(graphBase.out_graph,
                           prefixes={**graphBase.prefixes, **uPREFIXES})
        og.filename = graphBase.ng.filename
        path = Path(og.filename)
        ppath = path.parent
        if not ppath.exists():
            ppath.mkdir(parents=True)

        og.write()
        graphBase.part_of_graph.write()
        log.debug(f'Neurons ttl file written to {path}')

    @staticmethod
    def filename_python():
        p = Path(graphBase.ng.filename)
        return ((graphBase.compiled_location / p.name.replace('-', '_'))
                .with_suffix('.py'))

    @staticmethod
    def write_python():
        python = graphBase.python()
        # if you try to read from a source file that already exists
        # while also writing to that file linecache will be smart and
        # tell you that there is no source! therefore we generate all
        # the python before potentially opening (and thus erasing) the
        # original file from which some of the code was sourced
        fp = graphBase.filename_python()

        ppath = fp.parent
        if not ppath.exists():
            ppath.mkdir(parents=True)

        with open(fp, 'wt') as f:
            f.write(python)

        log.debug(f'Neurons python file written to {fp}')

    @classmethod
    def python_header(cls):
        out = '#!/usr/bin/env python3\n'
        out += f'from {cls.__import_name__} import *\n\n'

        all_types = set(type(n) for n in cls.neurons())
        def getfe(c):  # handle repl case (SIGH)
            # FIXME this will cause errors when we try to read the class back in
            try:
                inspect.getsource(c)
                return Path(inspect.getfile(c)).exists()
            except (OSError, TypeError) as e:
                return False

        _subs = [inspect.getsource(c) for c in subclasses(Neuron)
                 if c in all_types and getfe(c)
                 and c.__name__ not in __all__]
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
        [n._sigh() for n in cls.neurons()]  # ugh
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
    _neurdf_prefix_type = 'eqv'
    local_names = {}
    __cache = {}
    __pcache = {}
    def __init__(self, phenotype, ObjectProperty=None, label=None, override=True, check=False):
        # FIXME allow ObjectProperty or predicate? keyword?
        # label blackholes
        # TODO implement local names here? or at a layer above? (above)
        self.do_check = check

        super().__init__()
        if isinstance(phenotype, Phenotype):  # simplifies negation of a phenotype
            ObjectProperty = phenotype.e
            phenotype = phenotype.p

        self.p = self.checkPhenotype(phenotype)  # FIXME do this after construction
        if ObjectProperty is None:
            self.e = self.getObjectProperty(self.p)
        else:
            self.e = self.checkObjectProperty(ObjectProperty)  # FIXME this doesn't seem to work

        if isinstance(self.p, OwlObject):
            return

        if isinstance(self.p, rdflib.BNode):
            # TODO now they can! because OwlObjects
            def bnentry(pred, _internal=False):
                hrm = infixowl.CastClass(pred, graph=self.in_graph)
                _type = next(hrm.type)
                if _type == owl.Class:
                    def procmems(mems):
                        # FIXME not quite right
                        return [o for m in mems
                                for o in ((m,) if isinstance(m, rdflib.URIRef)
                                          else bnentry(m, _internal=True))]
                    _op = hrm._operator
                    _oo = {owl.unionOf: UnionOf,
                           owl.intersectionOf: IntersectionOf,}[_op]
                    _members = list(hrm._rdfList)
                    _mems = procmems(_members)
                    logical = _oo(*_mems)
                    if _internal:
                        return logical,
                    else:
                        return logical
                elif _type == owl.Restriction:
                    if _internal:
                        # onValues partOf some thing usually
                        hrm.onProperty == partOf
                        i = hrm.someValuesFrom.identifier
                        # FIXME typecheck
                        return i,
                    else:
                        msg = 'process this before getting here ie _members above'
                        raise ValueError(msg)
                        pass
                else:
                    msg = f'{_type} not an owl:Class or owl:Restriction'
                    raise TypeError(msg)

            self.p = bnentry(self.p)
            #raise TypeError(f'Phenotypes cannot be bnodes! {self.p}')
        else:
            self._pClass = infixowl.Class(self.p, graph=self.in_graph)

        self._eClass = infixowl.Class(self.e, graph=self.in_graph)
        # do not call graphify here because phenotype edges may be reused in multiple places in the graph

        if label is not None and override:
            self._label = label  # I cannot wait to get rid of this premature graph integration >_<
            self.in_graph.add((self.p, rdfs.label, rdflib.Literal(label)))

    def asIndicator(self):
        t = OntTerm(self.p)
        it = t.asIndicator()
        if t != it:
            return it.asPhenotype(self.e, phenotype_class=self.__class__)
        else:
            return self

    def asPosEntailed(self):
        """ have to have this since asEntailed preserved +/- """
        return EntailedPhenotype(self)

    def asEntailed(self):
        if isinstance(self, NegPhenotype):
            return self.asNegativeEntailed()

        return EntailedPhenotype(self)

    def asNegative(self):
        return NegPhenotype(self)

    def asNegativeEntailed(self):
        return NegEntailedPhenotype(self)

    def checkPhenotype(self, phenotype):
        if isinstance(phenotype, infixowl.Class):
            # fix for dumb infixowl code that asserts type equality
            # rather than you know, just testing for it >_<
            # massively breaking interoperatlibity >_<
            phenotype = phenotype.identifier
        elif isinstance(phenotype, OwlObject):
            return phenotype

        if phenotype in self.__cache:
            return self.__cache[phenotype]  # FIXME use a cross-instance caching decorator?

        subject = self.expand(phenotype)
        if self.do_check:
            try:
                next(self.core_graph.predicate_objects(subject))
            except StopIteration:  # is a phenotype derived from an external class
                prefix, suffix = phenotype.split(':', 1)
                if 'swanson' in subject:
                    self.__cache[phenotype] = subject
                    return subject
                if prefix not in ('SWAN', 'TEMP'):  # known not registered  FIXME abstract this
                    try:
                        ois = OntId(subject)
                        if ois.prefix == 'ilxtr':
                            self.__cache[phenotype] = subject
                            return subject

                        t = OntTerm(subject)
                        #if not self._sgv.findById(subject):
                        if not t.label:
                            log.info(f'Unknown phenotype {subject}')
                            #print(tc.red('WARNING:'), 'Unknown phenotype', subject)
                        else:
                            # because in_graph is queried first by OntTerm.query.services
                            # we cannot add this triple, otherwise it will mask the other
                            # services, which we do not want, it is also hard to avoid this
                            # at some point query may be able to merge information from
                            # multiple sources, or at least merge remote data with local,
                            # taking local as authoritative or something like that
                            #self.in_graph.add((subject, rdfs.label, rdflib.Literal(t.label)))
                            pass
                    except ConnectionError:
                        #print(tc.red('WARNING:'), 'Phenotype unvalidated. No SciGraph was instance found at',
                            #self._sgv._basePath)
                        msg = ('Phenotype unvalidated. No SciGraph was instance '
                               f'found at {self._sgv._basePath}')
                        log.warning(msg)

        self.__cache[phenotype] = subject
        return subject

    def getObjectProperty(self, phenotype):
        if isinstance(phenotype, OwlObject):
            _op = phenotype
            return self.getObjectProperty(_op.members()[0])  # FIXME assumes homogenous type ...
        elif type(phenotype) == str:
            log.error('FIXME SIGH')
            phenotype = self.in_graph.namespace_manager.expand(phenotype)
            # XXX SHOULD ALREADY BE EXPANDED :/

        predicates = list(self.in_graph.objects(phenotype, self.expand('ilxtr:useObjectProperty')))  # useObjectProperty works for phenotypes we control

        if predicates:
            return predicates[0]
        else:
            # TODO check if falls in one of the expression categories
            predicates = [_[1] for _ in self.in_graph.subject_predicates(phenotype)
                          if _ in self._predicates.__dict__.values()]
            mapping = {
                'NCBITaxon':self._predicates.hasInstanceInTaxon,
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
            if not hasattr(self, '_first_time'):
                log.warning('No reference predicates have been set, you are on your own!')
                self._first_time = False

            return op

        if op in self._predicates.__dict__.values():
            return op
        elif isinstance(self._predicates, AcceptAllPreds):
            return op  # XXX possibly warn?
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
        if isinstance(self.p, OwlObject):
            return self.p._for_thing(self, 'pLabel')

        l = tuple(self._pClass.label)
        if not l:  # we don't want to load the whole ontology
            try:
                p = OntId(self.p)
                if p.prefix != 'ilxtr' and p.prefix != 'TEMP' and 'swanson' not in p.iri:
                    t = OntTerm(p)
                    if t.label:
                        l = t.label
                        if isinstance(l, tuple) or isinstance(l, list):
                            log.warning(f'multiple labels for {t.curie}: {l}')
                            _l = l
                            l = l[0]
                    else:
                        l = t.curie
                else:
                    l = p.curie
            except ConnectionError as e:
                log.error(str(e))
                l = self.ng.qname(self.p)
        else:
            l = l[0]

        return l


    @property
    def pHiddenLabel(self):
        l = tuple(self.in_graph.objects(self.p, rdflib.namespace.SKOS.hiddenLabel))
        if l:
            l = l[0]
        else:
            l = self.pShortName  # FIXME

        return l

    @property
    @cacheout
    def pShortName(self):
        if hasattr(self, '_cache_pShortName'):
            return self._cache_pShortName

        if self.local_conventions:
            inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
            if self in inj:
                return inj[self]

        if isinstance(self.p, OwlObject):
            return self.p._for_thing(self, 'pShortName')

        pn = self.in_graph.namespace_manager.qname(self.p)
        try:
            if hasattr(self, '_sgv'):
                resp = self._sgv.findById(pn)
            else:
                msg = ('no scigraph instance bound, graphBase.configGraphIO '
                       'probably has not been called')
                log.warning(msg)
                resp = None
        except ConnectionError as e:
            #print(tc.red('WARNING:'), f'Could not set label for {pn}. No SciGraph was instance found at', self._sgv._basePath)
            log.info(f'Could not set label for {pn}. No SciGraph was instance found at ' + self._sgv._basePath)
            resp = None

        if pn.startswith('TEMPIND'):
            return next(self.in_graph[self.p:skos.hiddenLabel])

        if hasattr(self, '_label'):
            return self._label

        if pn.startswith('NCBITaxon'):
            return resp['labels'][0]

        if resp:  # DERP
            abvs = resp['abbreviations']
            if not abvs:
                abvs = sorted([s for s in resp['synonyms']
                               if 1 < len(s) < 5], key=lambda s :(len(s), s))

            # handle cases where a label is quite short
            if resp['labels'] and 1 < len(resp['labels'][0]) < 5:
                abvs = [resp['labels'][0]] + abvs

        else:
            abvs = None

        if abvs:
            abv = abvs[0]
            if abv == 'Glu,':
                return 'Glu'  # FIXME tempfix for bad glutamate abv
            elif abv == '4Abu':  # sigh
                return 'GABA'
            elif abv == 'Pva':  # a very strange synonym on the PR entry for parvalbumin
                return 'PV'
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

    @classmethod
    def _pterm(cls, p):
        if p not in cls.__pcache:
            cls.__pcache[p] = p.asTerm()

        return cls.__pcache[p]

    @property
    @cacheout
    def pLongName(self):
        if hasattr(self, '_label'):
            return self._label

        if hasattr(self, '_cache_pLongName'):
            # FIXME hack for the fact that the rdflibLocal service
            # changes from config to config
            return self._cache_pLongName

        p = OntId(self.p)

        r = OntTerm.query.services[0]  # rdflib local FIXME WARNING doing this can skip setup
        try:
            l = next(r.query(iri=p.iri)).label
            if l is None:
                raise StopIteration('somehow bare terms are making it it, which is bad')
        except StopIteration:
            if p.prefix == 'ilxtr' or 'swanson' in p.iri or p.prefix == 'TEMP':
                return p.curie

            t = self._pterm(p)
            l = t.label
        except AttributeError as e:
            # FIXME ick
            # we aren't set up yet and we are doing something stupid
            try:
                OntTerm(p.iri)  # force setup
            except ConnectionError as e:
                log.exception(e)
                return p.iri

            return self.pLongName

        if not l:
            return t.curie

        if isinstance(l, tuple) or isinstance(l, list):
            log.warning(f'multiple labels for {t.curie}: {l}')
            _l = l
            l = l[0]

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

    def _uri_frag(self):
        return (self._rank
                + '-' +
                OntId(self.e).curie.replace(':', '-')
                + '-' +
                (self.p._uri_frag(self)
                 if isinstance(self.p, OwlObject) else
                 OntId(self.p).curie.replace(':','-')))
        #yield from (self._rank + '/{}/' + self.ng.qname(_) for _ in self.objects)

    def _graphify(self, graph=None, **kwargs):
        if graph is None:
            graph = self.out_graph

        if isinstance(self.p, OwlObject):
            p = self.p._graphify(graph=graph, parent=self)
        else:
            p = self.p

        return infixowl.Restriction(onProperty=self.e, someValuesFrom=p, graph=graph)

    def _graphify_expand_location(self, graph=None, **kwargs):
        if graph is None:
            graph = self.out_graph

        if self.e in self._location_predicates:
            #restn = cmb.restrictionN(self.e,
                                     #cmb.oc_.full_combinator(
                                         #cmb.unionOf(self.p,
                                                     #cmb.restrictionN(partOf,
                                                                      #self.p))))
            if isinstance(self.p, OwlObject):
                p = self.p._graphify(graph=graph, parent=self)
                expand = self.in_graph.namespace_manager.expand
                def recu(p):
                    return [expand(m) if type(m) == str else m  # FIXME should not be converting from string here
                            for mm in p.members()
                            for m in (recu(mm) if isinstance(mm, OwlObject) else (mm,)) ]

                ps_for_parts = recu(self.p)
            else:
                p = self.p
                ps_for_parts = [p]

            por = infixowl.Restriction(onProperty=partOf,
                                       someValuesFrom=p,
                                       graph=graph)
            members = p, por
            #uo = infixowl.BooleanClass(operator=owl.unionOf, members=members, graph=graph)
            for pfp in ps_for_parts:
                if pfp not in _done:
                    _done.add(pfp)
                    eff = infixowl.Restriction(onProperty=partOf,
                                               someValuesFrom=pfp,
                                               graph=self.part_of_graph)
                    self.part_of_graph.add((pfp, rdfs.subClassOf, eff.identifier))

            return infixowl.Restriction(onProperty=self.e, someValuesFrom=por, graph=graph)

        else:
            return self._graphify(graph)

    _replace_prefix_cache = {}
    def _instance_neurdf(self, subject, parent_logical=False, neuron=None):
        qname = self.in_graph.namespace_manager.qname
        def replace_prefix(pred, prefix):
            if (pred, prefix) in self._replace_prefix_cache:
                return self._replace_prefix_cache[(pred, prefix)]

            c = qname(pred)
            old_prefix, suffix = c.split(':', 1)
            new = self.expand(prefix + ':' + suffix)
            self._replace_prefix_cache[(pred, prefix)] = new
            return new

        def pred_to_neurdf(pred, phen, ee):
            if isinstance(phen, OwlObject):
                nonstr = [m for m in phen.members() if not isinstance(m, str)]
                if nonstr:
                    # FIXME maybe test isinstance(m, OwlObject) directly?
                    # or even flag nesting at creation time
                    msg = f'nesting detected {nonstr}'
                    raise TypeError(msg)

                # TODO intersectionOf and unionOf
                # TODO raise if there is nesting
                # io uo prefix on the predicate and then each set/pair is its own rdf list
                # io:hasLocationPhenotype (ilxtr:region ilxtr:layer), (ilxtr:other-region ilxtr:other-layer)
                # uo:hasSomaLocatedIn (ilxtr:soma-loc-1 ilxtr:soma-loc-2 ilxtr:soma-loc-3)

                # FIXME hardcoding of prefixes here bad
                if type(phen) == UnionOf:
                    return replace_prefix(pred, f'neurdf.{ee}.uo')
                elif type(phen) == IntersectionOf:
                    return replace_prefix(pred, f'neurdf.{ee}.io')
                elif type(phen) == IntersectionOfPartOf:
                    return replace_prefix(pred, f'neurdf.{ee}.iopo')
                else:
                    msg = f'unknown OwlObject type {type(phen)}'
                    raise TypeError(msg)

            return replace_prefix(pred, f'neurdf.{ee}')

        def phen_to_neurdf(phen):
            if isinstance(phen, OwlObject):
                list_subject = rdflib.BNode()
                extra = phen._instance_neurdf(list_subject)
                return list_subject, extra
            else:
                return phen, False

        if isinstance(self, LogicalPhenotype):
            if parent_logical and (parent_logical != AND or self.op != AND):
                msg = 'neurdf not implemented for nested logical phenotypes'
                raise NotImplementedError(msg)
            # TODO turns out we have a BUNCH of these we might be able
            # to convert them to use UnionOf objects instead since in
            # nearly all cases all combined restrictions share the
            # same object property (probably not surprising) but we
            # need to confirm that the two representations are in face
            # equivalent under the owl reasoner(s)

            # XXX answer: fact++ can do it, elk cannot and part of
            # self axioms don't help in this case even if they are
            # made between the anonymous unionOf classes
            # what this means is that we can handle the unnested cases
            # and we should go ahead and warn that the AND case is
            # redundant at the top level and that the OR case should
            # be converted to use UnionOf since roundtripping through
            # neurdf will cause the grouping via AND to be dropped and
            # UnionOf will parse back to UnionOf not LogicalPhenotype(OR, ...)
            if self.op == AND:
                # this is safe becase we don't support nesting and AND is thus redundant
                for phenotype in self.pes:
                    yield from phenotype._instance_neurdf(subject, parent_logical=self.op, neuron=neuron)

                msg = ('LogicalPhenotype(AND, ...) flattened! '
                       f'roundtrip through neurdf will fail!\n{self}')
                #log.warning(msg)  # XXX TOO VERBOSE and doesn't flag the neuron
                return

            elif self.op == OR:
                if len(self._pesDict) > 1:
                    msg = f'cannot serializes non-homogenous logical phenotypes {list(self._pesDict)}'
                    raise NotImplementedError(msg)
                else:
                    ntypes = set([type(phenotype) for phenotype in self.pes])
                    if len(ntypes) > 1:
                        msg = f'union over different phenotypes not implemented {ntypes}'
                        raise NotImplementedError(msg)
                    else:
                        e = list(self._pesDict)[0]
                        npt = next(iter(ntypes))._neurdf_prefix_type
                        hrm = UnionOf(*[pe.p for pe in self.pes])
                        predicate = pred_to_neurdf(e, hrm, npt)
                        object, _extra = phen_to_neurdf(hrm)
                        yield subject, predicate, object
                        extra = list(_extra)
                        if extra:
                            # FIXME somehow duplicating the list?
                            # this isn't the problem, the problem is the double yield
                            # of the primary subject and predicate ?
                            # XXX ah no, it is probably that multiple files define the same neuron
                            #log.debug(neuron.id_)
                            #print(pformat(extra))
                            yield from extra

                        msg = ('LogicalPhenotype(OR, ...) converted to UnionOf! '
                               f'roundtrip through neurdf will fail!\n{self}')
                        #log.warning(msg)  # XXX TOO VERBOSE and doesn't flag the neuron

                    return
            else:
                raise ValueError(f'wat {self.op}')

            msg = f'neurdf not implemented for logical phenotypes {self.__class__}'
            raise NotImplementedError(msg)


        predicate = pred_to_neurdf(self.e, self.p, self._neurdf_prefix_type)
        object, extra = phen_to_neurdf(self.p)

        t = subject, predicate, object
        yield t
        if extra:
            yield from extra

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
            en = self.ng.qname(self.e)
            if isinstance(self.p, OwlObject):
                pn = self.p.__str__(parent=self)  # FIXME __expanded__ ?
            else:
                _pn = self.ng.qname(self.p)
                pn = repr(_pn)
        else:
            en = self.in_graph.namespace_manager.qname(self.e)
            if isinstance(self.p, OwlObject):
                pn = self.p.__str__(parent=self)
            else:
                _pn = self.in_graph.namespace_manager.qname(self.p)
                pn = repr(_pn)

        lab = self.pLabel
        return "%s(%s, '%s', label='%s')" % (self.__class__.__name__, pn, en, lab)

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
            en = self.ng.qname(self.e)
            if isinstance(self.p, OwlObject):
                pn = self.p.__str__(parent=self)
                #pn = self.p._for_thing(self, '__str__', call=True)
            else:
                _pn = self.ng.qname(self.p)
                pn = repr(_pn)
        else:
            en = self.in_graph.namespace_manager.qname(self.e)
            if isinstance(self.p, OwlObject):
                pn = self.p.__str__(parent=self)
            else:
                _pn = self.in_graph.namespace_manager.qname(self.p)
                pn = repr(_pn)

        lab = str(self.pLabel)
        t = ' ' * (len(self.__class__.__name__) + 1)
        return f"{self.__class__.__name__}({pn},\n{t}{en!r},\n{t}label={lab!r})"
        #return "%s('%s',\n%s'%s',\n%slabel='%s')" % (self.__class__.__name__, pn, t, en, t, lab)


class NegPhenotype(Phenotype):
    _rank = '1'
    """ Class for Negative Phenotypes to simplfy things """
    _neurdf_prefix_type = 'eqv.neg'


class EntailedPhenotype(Phenotype):
    """ render as subClassOf rather than equivalentClass """
    _rank = '8'
    _neurdf_prefix_type = 'ent'


class NegEntailedPhenotype(NegPhenotype, EntailedPhenotype):
    _rank = '8.5'
    _neurdf_prefix_type = 'ent.neg'


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

    _replace_prefix_cache = Phenotype._replace_prefix_cache

    def __init__(self, op, *edges):
        super().__init__()
        self.op = op  # TODO more with op
        self.pes = tuple(sorted(set(edges)))  # XXX SIGH must use set here
        _pesDict = {}
        for e in self.e:
            for pe in self.pes:
                if pe.e == e:
                    if e in _pesDict:
                        _pesDict[e].add(pe)
                    else:
                        _pesDict[e] = {pe}

        self._pesDict = {k:sorted(v) for k, v in _pesDict.items()}

    def asIndicator(self):
        return self.__class__(self.op, *[pe.asIndicator() for pe in self.pes])

    def asEntailed(self):
        if isinstance(self, NegPhenotype):
            raise NotImplementedError('TODO')
            return self.asNegativeEntailed()

        return EntailedLogicalPhenotype(self.op, *self.pes)

    @property
    def p(self):
        out = tuple((p for pe in self.pes for p in
                     (pe.p if isinstance(pe, LogicalPhenotype) else (pe.p,))))
        return tuple(set(out))
        #return tuple((pe.p for pe in self.pes))

    @property
    def e(self):
        out = tuple((e for pe in self.pes for e in
                     (pe.e if isinstance(pe, LogicalPhenotype) else (pe.e,))))
        out = tuple(set(out))
        return out
        #return tuple((pe.e for pe in self.pes))

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
                return (tuple(self.label_maker._order.index(OntId(e).suffix)
                              for e in (pe.e if isinstance(pe, LogicalPhenotype) else (pe.e,))),
                        getattr(pe, attr))
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
        return f'({op} {label})'

    @property
    def pShortName(self):
        if self.local_conventions:
            inj = {v:k for k, v in graphBase.LocalNames.items()}  # XXX very slow...
            if self in inj:
                return inj[self]

        label = self.label_maker(self)
        op = OntId(self.op).suffix
        return f'({op} {label})'

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

    def _uri_frag(self):
        rank = '4' if self.op == AND else '5'  # OR
        return rank + '_' + '-'.join(sorted((pe._uri_frag() for pe in self.pes), key=natsort)) + '_'
        #return '-'.join(sorted((rank
                                #+ '-' +
                                #OntId(pe.e).curie.replace(':','-')
                                #+ '-' +
                                #OntId(pe.p).curie.replace(':','-')
                                #for pe in sorted(self.pes)), key=natsort))

    def _graphify(self, graph=None, method='_graphify'):
        if graph is None:
            graph = self.out_graph
        members = []
        for pe in self.pes:  # FIXME fails to work properly for negative phenotypes...
            members.append(getattr(pe, method)(graph=graph, method=method))

        return infixowl.BooleanClass(operator=self.expand(self.op), members=members, graph=graph)

    _graphify_expand_location = _graphify

    _instance_neurdf = Phenotype._instance_neurdf

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
        # TODO there is a risk of sort order instability for
        # phenotypes containing OwlObjects it has not currently
        # manifest, but it could, using frozenset means we wouldn't
        # actually have to require ordering rules for all classes that
        # can appear as part of pes which would be preferable to the
        # current situation where types have to have an order with
        # other types which makes composition difficult/annoying, this
        # was already recognized long ago when I started working on
        # neurondm.simple but could be implemented here, probably in
        # __init__, separating the deterministic serialization we want
        # from the identity function used

        #return hash((self.__class__.__name__, self.op, frozenset(self.pes)))
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


class EntailedLogicalPhenotype(LogicalPhenotype):
    _rank = '3'


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

    def asIndicator(self):
        newself = self.__class__(*[pe.asIndicator() for pe in self.pes])
        newself.adopt_meta(self)
        return newself

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
            if not t.validated:  # FIXME masking the _source issue
                new.append(phenotype)  # essentially an unknown phenotype
                continue

            if t.curie in replace:
                np = phenotype.__class__(replace[t.curie], phenotype.e)
                new.append(np)
                deprecated = True
                log.debug(f'Found deprecated phenotype {phenotype} -> {np}')
                continue

            if hasattr(t, 'deprecated') and t.deprecated:  # FIXME why do we not have cases without?
                rb = t('replacedBy:', asTerm=True)
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
                #log.debug(str([i for i in iris if '4164' in i or '100212' in i]))
                for iri in iris:
                        # rod/cone issue
                        #breakpoint()
                    try:
                        _po = cls._nested[iri] if iri in cls._nested else None
                        n = cls(id_=iri, override=True, partialOrder=_po)#, out_graph=cls.config.load_graph)  # I think we can get away without this
                        #if iri.endswith('4164') or iri.endswith('100212'):
                            #log.debug(f'{iri} -> {n}')

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
                 equivalentNeurons=tuple(), disjointNeurons=tuple(), partialOrder=None, definition=None):
        self._sighed = False
        self._nested_partial_order = partialOrder
        if id_ and (equivalentNeurons or disjointNeurons):
            # FIXME does this work!?
            raise TypeError('Neurons defined by id may not use equivalent or disjoint')

        super().__init__()
        self._replay = []  # fix for idiocy of using setters to write to the graph
        self._localContext = self.__context
        self.config = self.__class__.config  # persist the config a neuron was created with
        __pes = tuple(set(self._localContext + phenotypeEdges))  # remove dupes
        phenotypeEdges = self.removeDuplicateSuperProperties(__pes)

        if phenotypeEdges:
            _oic = OntId(self.owlClass).curie.replace(':','-')
            frag = f'{_oic}-' + '-'.join(sorted((pe._uri_frag()
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

        ORDER = [ilxtr[suffix] for suffix in LabelMaker._order]
        lop1 = len(ORDER) + 1
        self.pes = tuple(sorted(sorted(phenotypeEdges),
                                key=lambda pe: ORDER.index(pe.e) if pe.e in ORDER else lop1))
        #self.validate()  # FIXME this should only be called AFTER construction

        self.Class = infixowl.Class(self.id_, graph=self.out_graph)  # once we get the data from existing, prep to dump OUT


        self.phenotypes = set(pe.p for pe in self.pes)  # NOTE the valence is NOT included here
        self.unique_objects = set(p for p_or_tup in self.phenotypes
                                  for p in (p_or_tup
                                            if isinstance(p_or_tup, tuple)
                                            else (p_or_tup,)))

        self.edges = set(pe.e for pe in self.pes)
        self.unique_predicates = set(e for e_or_tup in self.edges
                                     for e in (e_or_tup
                                               if isinstance(e_or_tup, tuple)
                                               else (e_or_tup,)))
        self._pesDict = {}
        for pe in self.pes:  # FIXME TODO
            if isinstance(pe, LogicalPhenotype):  # FIXME
                # FIXME hpm should actually be an inclusive subclass query on hasPhenotype
                dimensions = set([e for e in pe.e if e != ilxtr.hasPhenotypeModifier])
                #dimensions = set(_.e for _ in pe.pes if _.e != ilxtr.hasPhenotypeModifier)
                if len(dimensions) == 1:
                    dimension = next(iter(dimensions))
                else:
                    _key = lambda d: ((not isinstance(d, tuple)), d)
                    dimension = tuple(sorted(dimensions, key=_key))

                if dimension not in self._pesDict:
                    self._pesDict[dimension] = []

                self._pesDict[dimension].append(pe)

            else:
                if pe.e not in self._pesDict:
                    self._pesDict[pe.e] = []

                self._pesDict[pe.e].append(pe)  # don't have to check for dupes here

        self._origLabel = label
        self._override = override
        if definition is not None:
            # FIXME nasty side effecting behavior
            self.definition = rdflib.Literal(definition)  # TODO check to make sure we aren't fighting with existing

        if (not override and
            self in self.existing_pes and
            self.existing_pes[self] is not None and  # sigh support
            self.Class.graph is self.existing_pes[self].graph):
            self.Class = self.existing_pes[self]
        else:
            self.existing_pes[self] = None
            #log.warning('self._sigh has not been called')

        self.ttl = self._instance_ttl
        self.python = self._instance_python

    def _sigh(self):
        if self._sighed:
            return

        # FIXME check on whether setting self.Class = self.existing_pes[self]
        # causes issues
        #if self in self.existing_pes and self.existing_pes[self] is not None:
        graph = self.out_graph
        self.Class = self.Class.__class__(self.id_, graph=graph)  # in the event we wiped the graph
        self.Class = self._graphify(graph=graph)
        self.Class.label = rdflib.Literal(self.label)  # FIXME this seems... broken?
        self.existing_pes[self] = self.Class
        if self._replay:
            rep = self._replay
            self._replay = []
            for p, *os in rep:
                self.add_objects(p, *os)

        if self._nested_partial_order is not None:
            bn = orders.to_rdf(graph, self._nested_partial_order)
            graph.add((self.id_, ilxtr.neuronPartialOrder, bn))

        self._sighed = True

    def partialOrder(self, nested=None):
        """ nested is a the nested list version of the partial order

            if you have an adj list use orders.adj_to_nst before
            passing in here """

        if self._nested_partial_order is None and nested is not None:
            self._nested_partial_order = nested

        return self._nested_partial_order

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

        g = OntConjunctiveGraph()  #rdflib.Graph()  # FIXME
        _ = [g.add(t) for t in self.out_graph.transitiveClosure(f, (None, None, self.id_))]
        _ = [g.add(t) for t in self._existing]


        og = cull_prefixes(g, prefixes=uPREFIXES)  # FIXME local prefixes?
        return og

    def _instance_ttl(self):
        self._sigh()
        og = self._subgraph()
        return og.g.serialize(format='nifttl').decode()

    def _instance_python(self):
        return '\n'.join(('# ' + self.label, str(self)))
        #return self.python_header() + str(self)

    def _instance_neurdf(self):
        # TODO partial orders come out on the owl portion but need to
        # determine where we want these triples to be serialized to
        id = self.id_
        yield id, rdf.type, neurdf.Neuron
        object = OntId(self.owlClass).u  # FIXME vs self.expand etc.
        yield id, rdfs.subClassOf, object  # FIXME this is where the neuron level intersection and union come in sort of
        for pe in self.pes:
            yield from pe._instance_neurdf(id, neuron=self)

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

    _label_hack = False
    @property
    def label(self):  # FIXME for some reasons this doesn't always make it to the end?
        if self._label_hack:
            return self.genLabel

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

    @property
    def simpleLabel(self):
        if hasattr(self, 'commonName'):
            return self.commonName
        else:
            return self.genLabel

    @property
    def simpleLocalLabel(self):
        if hasattr(self, 'commonName'):
            return self.commonName
        else:
            return self.localLabel

    @property
    def prefLabel(self):
        ol = self.origLabel
        if ol:
            if ol == self.label:
                return

            return ol

        return self.genLabel

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

        t = OntTerm(object)
        t.set_next_repr('curie', 'label')
        raise AttributeError(f'{self} has no aspect with the phenotype {t!r}')  # FIXME AttributeError seems wrong

    def getObject(self, predicate):
        msg = 'deprecated, use .getObjects'
        raise NotImplementedError(msg)
        #return rdf.nil  # FIXME how to indicate all values?
        # predicate is different than object in the sense that it is possible
        # for neurons to have aspects (aka phenotype dimensions) without anyone
        # having measured those values, also handy when we don't know how to parse a value
        # but there is note attached
        #raise AttributeError(f'{self} has no phenotype for {predicate}')  # FIXME AttributeError seems wrong

    def getObjects(self, predicate):
        for p in self.pes:
            if p.e == predicate:  # FIXME probably need to munge the object
                yield p.p  # just to confuse you, the second p here is phenotype not predicate >_<

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
        lab =  ((',\n' + t + (f"label={str(self.origLabel)!r}"
                              if self._override else
                              f"label={str(self.origLabel) + sn!r}"))
                if self._origLabel else '')
        asdf += lab
        asdf += ')'
        return asdf

    def __hash__(self):
        #return hash((self.__class__.__name__, frozenset(self.pes)))
        return hash((self.__class__.__name__, *self.pes))  # FIXME bad hashing

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.pes == other.pes)
        #return hash(self) == hash(other)

    def __lt__(self, other):
        try:
            return repr(self.pes) < repr(other.pes)
        except AttributeError as e:
            breakpoint()
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
            self._predicates.hasInstanceInTaxon,
            self._predicates.hasSomaLocatedIn,
            self._predicates.hasLayerLocationPhenotype,  # FIXME coping with cases that force unionOf?
            self._predicates.hasSomaLocationLaterality,
            self._predicates.hasSomaLocatedInLayer,
            self._predicates.hasMorphologicalPhenotype,
        ]

        sgd = [s for s in OntTerm.query.services if isinstance(s, _SGR)][0].sgd
        sgg = [s for s in OntTerm.query.services if isinstance(s, _SGR)][0].sgg
        def multiquery(term):
            blob = (sgd._get('GET',(sgd._basePath + '/dynamic/multiquery/{relationship}/{id}')
                             .format(relationship='BFO:0000050', id=term.curie)))
            return blob

        def merge(term, blob):
            edges = [e for e in blob['edges'] if not e['obj'].startswith('_:')]
            ordered = list(sgg.ordered(term.curie, edges))
            parts = [e for e in ordered if e['pred'] == 'BFO:0000050' and not e['obj'].startswith('_:')]
            nodes = set(e for p in parts for e in [p['sub'], p['obj']])
            #[e for e in blob['edges'] if e['pred'] == 'subClassOf' and e['obj'] in nodes]

        for disjoint in disjoints:
            phenos = [pe for pe in self.pes if pe.e == disjoint and type(pe) == Phenotype]
            if len(phenos) > 1:
                raw_terms = [OntTerm(p.p) for p in phenos]
                oterms = terms = set(t.asPreferred() for t in raw_terms)
                if 'Loc' in disjoint:  # FIXME ... subPropertyOf hasLocationPhenotype
                    #resp = [merge(t, multiquery(t)) for t in terms]
                    #breakpoint()
                    _oq = OntTerm.query
                    OntTerm.query = OntTermInterLexOnly.query
                    po = [(t('ilx.partOf:', depth=10, asPreferred=True, include_supers=True),
                           [t2 for t2 in oterms if t2 != t])
                          for t in terms]
                    OntTerm.query = _oq
                    po += [(t('partOf:', depth=10, asTerm=True, include_supers=True),
                            [t2 for t2 in oterms if t2 != t]) for t in
                           terms]
                    po += [(t('rdfs:subClassOf', depth=10, asTerm=True),
                            [t2 for t2 in oterms if t2 != t])
                           for t in terms]
                    accounted_for = 0
                    all_supers = []
                    for supers, others in po:
                        other_supers = [other for other in others if other in supers]
                        accounted_for += len(other_supers)
                        all_supers.extend(other_supers)

                    if accounted_for >= len(phenos) - 1:
                        continue

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
        def process_pe(pe):
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

        c = None
        # support CUT pattern  # FIXME maybe reimplement this method on NeuronCUT?
        for c in self.Class.subClassOf:
            if c.identifier in self.knownClasses:
                embeddedKnownClasses.add(c.identifier)
            else:
                epe = self._unpackPheno(c, type_=EntailedPhenotype)
                if epe:
                    process_pe(epe)
                else:
                    log.error(f'hrm!? {epe}')

        for c in self.Class.equivalentClass:
            if isinstance(c.identifier, rdflib.URIRef):
                # FIXME this is entailment stuff
                # also prevents potential infinite recursion
                self._equivalent_bags_ids.add(c.identifier)
                continue

            pe = self._unpackPheno(c)
            if pe:
                process_pe(pe)
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

            if e == NIFRID.has_neurotransmitter:  # FIXME the very old model
                e = self._predicates.hasNeurotransmitterPhenotype
            elif e == NIFRID.has_proper_part:  # FIXME the very old model
                return old_nif_location(r, ptype=ptype)

            return ptype(p, e)

        def location_restriction_to_phenotype(r, ptype=type_):
            bc = infixowl.CastClass(r.someValuesFrom, graph=self.in_graph)
            if type(bc) == infixowl.BooleanClass:
                p = [e for e in bc._rdfList if isinstance(e, rdflib.URIRef)][0]
            elif type(bc) == infixowl.Restriction:
                p = bc.someValuesFrom.identifier

            e = r.onProperty
            return ptype(p, e)

        def old_nif_location(r, ptype=type_):
            # not quite correct
            e = self._predicates.hasSomaLocatedIn
            bc = infixowl.CastClass(r.someValuesFrom, graph=self.in_graph)
            cs = [infixowl.CastClass(e, graph=self.in_graph)
                  for e in bc._rdfList if isinstance(e, rdflib.BNode)]
            p = cs[0].someValuesFrom.identifier
            return ptype(p, e)

        def expand_restriction(r, pes, ptype=type_):
            if (r.onProperty in self._location_predicates and
                isinstance(r.someValuesFrom.identifier, rdflib.BNode)):
                _pe = location_restriction_to_phenotype(r, ptype=ptype)
                pes.append(_pe)

            elif r.onProperty in self._location_predicates:
                log.warning(f'Old location model for {c}')
                pes.append(restriction_to_phenotype(r, ptype=ptype))

            else:
                pes.append(restriction_to_phenotype(r, ptype=ptype))

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
                            # FIXME this could error for CUTs at some point
                            log.error(f'Wrong owl:Class, expected: {self.id_} got: {id_}')
                            return
                        else:
                            if pr.complementOf:
                                coc = infixowl.CastClass(pr.complementOf, graph=self.in_graph)
                                if isinstance(coc, infixowl.Restriction):
                                    expand_restriction(coc, pes, ptype=NegPhenotype)
                                else:
                                    log.critical(str(coc))
                                    raise BaseException('wat')
                            else:
                                log.critical(str(pr))
                                raise BaseException('wat')
                    elif isinstance(pr, infixowl.Restriction):
                        expand_restriction(pr, pes)
                    elif id_ == self.owlClass:
                        pes.append(id_)
                    elif id_ == _NEURON_CLASS:  # CUT case
                        pes.append(id_)
                    elif pr is None:
                        log.warning(f'dangling reference {id_}')
                    else:
                        log.critical(str(pr))
                        raise BaseException('wat')

                return tuple(pes)
            else:
                pr = putativeBooleanClass
                if isinstance(pr, infixowl.Restriction):
                    # entailed case is nearly always direct subClassOf restriction
                    pes = []
                    expand_restriction(pr, pes)
                    if len(pes) > 1:
                        log.error(f'unexpected multiple phenotypes for: {self.id_}\n{pes}')
                    return pes[0]
                elif type(pr) == infixowl.Class:  # restriction is sco class so use type
                    # FIXME copied from above
                    id_ = pr.identifier
                    pes = []
                    if id_ in self.knownClasses:
                        pes.append(id_)
                    elif id_ == self.owlClass:  # this can fail ...
                        # in case we didn't catch it before
                        pes.append(id_)
                    elif isinstance(id_, rdflib.URIRef):  # FIXME this never runs?
                        # FIXME this could error for CUTs at some point
                        log.error(f'Wrong owl:Class, expected: {self.id_} got: {id_}')
                        return
                    else:
                        if pr.complementOf:
                            coc = infixowl.CastClass(pr.complementOf, graph=self.in_graph)  # FIXME in_graph vs load_graph
                            if isinstance(coc, infixowl.Restriction):
                                expand_restriction(coc, pes, ptype=NegEntailedPhenotype)
                            else:
                                log.critical(str(coc))
                                raise BaseException('wat')
                        else:
                            log.critical(str(pr))
                            raise BaseException('wat')
                    return tuple(pes)

                else:
                    log.critical(f'WHAT\n{list(c.graph.subject_triples(c.identifier))!r}')  # FIXME something is wrong for negative phenotypes...

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

    def _unpackLogical(self, bc, type_=Phenotype):
        op = bc._operator
        pes = self._unpackPheno(bc, type_=type_)
        return LogicalPhenotype(op, *pes)

    def _graphify_labels(self, graph):
        ################## LABELS ARE DEFINED HERE ##################
        gl = self.genLabel
        ll = self.localLabel
        ol = self.origLabel
        graph.add((self.id_, ilxtr.genLabel, rdflib.Literal(gl)))
        #if ll != gl:
        graph.add((self.id_, ilxtr.localLabel, rdflib.Literal(ll)))

        if ol and ol != gl:
            graph.add((self.id_, ilxtr.origLabel, rdflib.Literal(ol)))

        if self.prefLabel:
            pl = rdflib.Literal(self.prefLabel)
            graph.add((self.id_, skos.prefLabel, pl))

        sl = rdflib.Literal(self.simpleLabel)
        graph.add((self.id_, ilxtr.simpleLabel, sl))
        sll = rdflib.Literal(self.simpleLocalLabel)
        graph.add((self.id_, ilxtr.simpleLocalLabel, sll))
        if hasattr(self, 'commonName'):
            cn = self.commonName
            graph.add((self.id_, ilxtr.commonName, rdflib.Literal(cn)))

    def _graphify_pes(self, graph, members, method='_graphify_expand_location'):
        for pe in self.pes:
            target = getattr(pe, method)(graph=graph, method=method)
            if isinstance(pe, NegEntailedPhenotype):
                djc = infixowl.Class(graph=graph)  # TODO for generic neurons this is what we need
                djc.complementOf = target
                restr = djc
                _sco = list(self.Class.subClassOf)
                _sco.append(restr)
                self.Class.subClassOf = _sco
            elif isinstance(pe, NegPhenotype):  # isinstance will match NegPhenotype -> Phenotype
                #self.Class.disjointWith = [target]  # FIXME for defined neurons this is what we need and I think it is strong than the complementOf version
                djc = infixowl.Class(graph=graph)  # TODO for generic neurons this is what we need
                djc.complementOf = target
                members.append(djc)
            elif (isinstance(pe, EntailedPhenotype) or
                  isinstance(pe, EntailedLogicalPhenotype)):
                restr = target
                _sco = list(self.Class.subClassOf)
                _sco.append(restr)
                self.Class.subClassOf = _sco
            else:
                members.append(target)  # FIXME negative logical phenotypes :/

        intersection = infixowl.BooleanClass(members=members, graph=graph)  # FIXME dupes
        #existing = list(self.Class.equivalentClass)
        #if existing or str(pe.pLabel) == 'Htr3a':
            #breakpoint()
        ec = [intersection]
        self.Class.equivalentClass = ec
        return self.Class

    def _graphify(self, *args, graph=None): #  defined
        """ Lift phenotypeEdges to Restrictions """
        if graph is None:
            graph = self.out_graph

        self._graphify_labels(graph)
        members = [self.expand(self.owlClass)]
        return self._graphify_pes(graph, members)


class NeuronCUT(Neuron):
    """ Phenotypes listed as part of a CUT are all necessary. """
    owlClass = _CUT_CLASS

    #def _unpackPheno(self, c, type_=Phenotype):
        #return super()._unpackPheno(c, type_=type_)

    def _graphify(self, *args, graph=None): #  defined
        """ Lift phenotypeEdges to Restrictions """
        if graph is None:
            graph = self.out_graph

        self._graphify_labels(graph)
        members = [Neuron.owlClass]
        Class = self._graphify_pes(graph, members)
        Class.subClassOf = [self.owlClass]
        return Class

    @property
    def commonName(self):
        return self.origLabel


class NeuronEBM(Neuron):
    owlClass = _EBM_CLASS

    def _graphify(self, *args, graph=None):
        """ Lift phenotypeEdges to Restrictions """
        if graph is None:
            graph = self.out_graph

        self._graphify_labels(graph)
        members = [self.owlClass]
        # use _graphify_expand_location to get the location + part of location behavior
        return self._graphify_pes(graph, members)

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
                    log.warning(tc.red('subClassOf restriction violated '
                                       '(please use a more specific identifier) '
                                       f'for {invalid_superclass} due to\n{pe}'))
                    #raise TypeError(f'subClassOf restriction violated for {invalid_superclass} due to {pe}')  # TODO can't quite switch this on yet, breaks too many examples

    @property
    def prefLabel(self):
        ol = self.origLabel
        if ol:
            if ol == self.label:
                return

            if self._shortname and not self._override:
                ol += f' {self._shortname}'

            return ol

        return self.genLabel


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
        # we cast back to dict here so that inj_dict doesn't cause
        # errors if the same name is used in the class namespace
        # even if not for assignment
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
        It is possible to subclass to add your custom names to a core.

        NOTE: If you plan use the context manager functionality of a LNM
        anywhere other than at top level, then you need to assign
        __globals__ = globals() """

    # TODO context dependent switches for making PAXRAT/PAXMOUSE transitions transparent

    render_types = Phenotype, LogicalPhenotype


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
if False:  # calling Config at top level breaks import for all normal users
    Config(import_no_net=True)  # explicitly load the core graph TODO need a lighter weight way to do this
else:
    # note: this solves part of the problem, but mostly defers it until later
    _g = OntConjunctiveGraph()
    _g.namespace_manager.populate_from(uPREFIXES)
    graphBase.core_graph = _g


OntologyGlobalConventions = _ogc = injective_dict(
    Vertebrata = Phenotype('NCBITaxon:7742', 'ilxtr:hasInstanceInTaxon'),  # fix annoying labels

    L1 = Phenotype('UBERON:0005390', 'ilxtr:hasSomaLocatedInLayer'),
    L2 = Phenotype('UBERON:0005391', 'ilxtr:hasSomaLocatedInLayer'),
    L3 = Phenotype('UBERON:0005392', 'ilxtr:hasSomaLocatedInLayer'),
    L4 = Phenotype('UBERON:0005393', 'ilxtr:hasSomaLocatedInLayer'),
    L5 = Phenotype('UBERON:0005394', 'ilxtr:hasSomaLocatedInLayer'),
    L6 = Phenotype('UBERON:0005395', 'ilxtr:hasSomaLocatedInLayer'),

    CR = Phenotype('PR:000004968', 'ilxtr:hasMolecularPhenotype'),
    CB = Phenotype('PR:000004967', 'ilxtr:hasMolecularPhenotype'),
    NPY = Phenotype('PR:000011387', 'ilxtr:hasMolecularPhenotype'),
    SOM = Phenotype('PR:000015665', 'ilxtr:hasMolecularPhenotype'),
    PV = Phenotype('PR:000013502', 'ilxtr:hasMolecularPhenotype'),
    VIP = Phenotype('PR:000017299', 'ilxtr:hasMolecularPhenotype'),
    CCK = Phenotype('PR:000005110', 'ilxtr:hasMolecularPhenotype'),
    GABA = Phenotype('CHEBI:16865', 'ilxtr:hasNeurotransmitterPhenotype'),

    AC = Phenotype('ilxtr:PetillaSustainedAccommodatingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),
    NAC = Phenotype('ilxtr:PetillaSustainedNonAccommodatingPhenotype', 'ilxtr:hasElectrophysiologicalPhenotype'),
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
