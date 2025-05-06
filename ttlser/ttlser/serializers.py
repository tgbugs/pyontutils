import re
import sys
from decimal import Decimal
from datetime import datetime
from rdflib import RDF, RDFS, OWL, XSD, BNode, URIRef, Literal
from rdflib.graph import QuotedGraph
from rdflib.namespace import SKOS, DC, Namespace
from rdflib.plugins.serializers.turtle import TurtleSerializer
from ttlser.utils import subclasses

# XXX WARNING prefixes are not 100% deterministic if there is more than one prefix for namespace
#     the implementation of IOMemory.bind in rdflib means that the last prefix defined in the list
#     will likely be the one that is called when NamespaceManager.compute_qname calls self.store.prefix

NIFRID = Namespace('http://uri.neuinfo.org/nif/nifstd/readable/')
OBOANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#')
BIRNANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#')
oboInOwl = Namespace('http://www.geneontology.org/formats/oboInOwl#')
prov = Namespace('http://www.w3.org/ns/prov#')
#IAO = Namespace('http://purl.obolibrary.org/obo/IAO_')  # won't work because numbers ...

DEBUG = False
SDEBUG = False


def natsort(s, pat=re.compile(r'([0-9]+)')):
    return tuple(int(t) if t.isdigit() else t.lower() for t in pat.split(s))


def make_litsort(sortkey=natsort):
    def litsort(l):
        v = l.value
        if type(v) == bool:
            out = 0, v
        elif type(v) == int:
            out = 1, v, str(l)
        elif type(v) == Decimal:
            out = 1, v, str(l)
        elif type(v) == float:
            n = v
            m, e = '{:e}'.format(n).split('e')
            s = '{}e{}'.format(m.rstrip("0").rstrip("."), e)
            out = 1, n, s
        elif type(v) == datetime:
            # we make no assumptions about the original timestamp so we
            # put zone naieve datetimes first
            out = 2, bool(v.tzinfo), v
        else:
            dt = l.datatype if l.datatype is not None else ''
            lang = l.language if l.language is not None else ''
            out = 3, sortkey(l), dt, lang
        return out

    return litsort


def qname_mp(self, uri):  # for monkey patching Graph
    try:
        prefix, namespace, name = self.compute_qname(uri, False)
    except (ValueError, KeyError) as e:#Exception:  # no prefix no problems
        return uri

    if prefix == '':
        return name
    else:
        return ':'.join((prefix, name))


def makeSymbolPrefixes(n):
    from collections import deque
    symbols = 'AABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-%'
    most_significant = 26 * 2  # aka last base really
    base = len(symbols)
    gap = base - most_significant
    index = -1
    count = 0
    while count < n:
        index += 1
        bd, br = divmod(index, base)
        if br == 0:
            continue
        i = index
        out = deque()
        while i:
            i, r = divmod(i, base)
            out.appendleft(r)
        if out and out[0] >= most_significant:  # forget math use programming
            continue
        out = ''.join(symbols[d] for d in out)
        #print(' '.join('{:>3}'.format(_) for _ in (index, bd, br)), out)
        yield out
        count += 1


class ListRanker:
    def __init__(self, node, serializer):
        self.reorder = self.test_reorder(node, serializer)
        self.node = node
        self.serializer = serializer
        if not self.reorder:
            self.serializer.nosort.add(self.node)
        self.vals = []
        self.nodes = []  # list helper nodes
        l = self.node
        previous = set()
        #count = 0
        #enough = 99999
        while l:  # infinite loop posibility
            item = self.serializer.store.value(l, RDF.first)
            self.add(item, l)
            # if there is a self referential node anywhere in a list
            # beyond the first element this goes infinite
            previous.add(l)
            l = self.serializer.store.value(l, RDF.rest)
            if l in previous:  # cyclical reference case
                break
            # XXX beware lists where there are multiple rdf:rest
            # values for a node, I don't think they will break
            # serialization, but they may produce unexpected ranking
            #count += 1
            #if count > enough:
                #print(self.serializer.store)
                #breakpoint()
        self.vis_vals = [v for v in self.vals if not isinstance(v, BNode)]
        self.bvals = [v for v in self.vals if isinstance(v, BNode)]

    @staticmethod
    def test_reorder(node, serializer):
        try:
            s, linking_predicate = next(serializer.store[::node])
            if linking_predicate in serializer.no_reorder_rdf_star:
                p = serializer.no_reorder_rdf_star[linking_predicate]
                linking_predicate = next(serializer.store[s:p:])

            reorder = linking_predicate not in serializer.no_reorder_list
            return reorder
        except StopIteration:
            return True

    def add(self, item, node):
        if item is not None:
            self.vals.append(item)
            if node != self.node:
                self.nodes.append(node)

    @property
    def rank_vec(self):
        out = tuple(self._vis_val_key(v) for v in self.vis_vals)
        if self.reorder:
            out = tuple(sorted(out))

        if not out:
            return self.serializer.max_or + self.serializer.max_lr + 1,
        else:
            return out

    def irank_vec(self, ranks):
        out = tuple(sorted(self._bval_key(v, ranks) for v in self.bvals))
        return out

    def _vis_val_key(self, val):
        if val in self.serializer.object_rank:
            return self.serializer.object_rank[val]

    def _bval_key(self, val, ranks):
        return ranks[val]


SUBJECT = 0
VERB = 1
OBJECT = 2


class CustomTurtleSerializer(TurtleSerializer):
    """ NIFSTD custom ttl serliziation. See ../docs/ttlser.md for more info. """

    roundtrip_prefixes = '',
    short_name = 'nifttl'
    _name = 'ttlser deterministic'
    __version = 'v1.2.3'
    _newline = True
    _nl = '\n'
    _space = ' '
    sortkey = staticmethod(natsort)
    make_litsortkey = staticmethod(make_litsort)
    no_reorder_list = (OWL.propertyChainAxiom,)
    no_reorder_rdf_star = {
         OWL.annotatedTarget: OWL.annotatedProperty,
    }

    topClasses = [OWL.Ontology,
                  RDF.Property,
                  RDFS.Class,
                  OWL.ObjectProperty,
                  RDFS.Datatype,  # FIXME order in this list matters, so we need to skip BNode cases
                  OWL.AnnotationProperty,
                  OWL.DatatypeProperty,
                  OWL.Class,
                  OWL.NamedIndividual,
                  OWL.AllDifferent,
                 ]

    SECTIONS = ('',
                'rdf Properties',
                'rdfs Classes',
                'Object Properties',
                'Datatypes',
                'Annotation Properties',
                'Data Properties',
                'Classes',
                'Individuals',
                'Axioms',
                'Annotations',
               )

    predicateOrder = [RDF.type,
                      OWL.onProperty,
                      OWL.allValuesFrom,
                      OWL.someValuesFrom,
                      OWL.versionIRI,
                      OWL.imports,
                      OWL.deprecated,
                      OWL.annotatedSource,
                      OWL.annotatedProperty,
                      OWL.annotatedTarget,
                      URIRef('http://purl.obolibrary.org/obo/IAO_0100001'),  # replacedBy:
                      oboInOwl.hasDbXref,
                      OWL.equivalentClass,
                      RDFS.label,
                      SKOS.prefLabel,
                      SKOS.altLabel,
                      NIFRID.synonym,
                      OBOANN.synonym,
                      NIFRID.abbrev,
                      OBOANN.abbrev,
                      DC.title,
                      URIRef('http://purl.obolibrary.org/obo/IAO_0000115'),  # definition:
                      SKOS.definition,
                      SKOS.related,
                      DC.description,
                      RDFS.subClassOf,
                      RDFS.subPropertyOf,
                      RDFS.domain,
                      RDFS.range,
                      OWL.propertyChainAxiom,
                      OWL.intersectionOf,
                      OWL.unionOf,
                      OWL.disjointWith,
                      OWL.disjointUnionOf,
                      OWL.distinctMembers,
                      OWL.inverseOf,
                      RDFS.comment,
                      SKOS.note,
                      SKOS.editorialNote,
                      SKOS.changeNote,
                      OWL.versionInfo,
                      NIFRID.createdDate,
                      OBOANN.createdDate,
                      NIFRID.modifiedDate,
                      OBOANN.modifiedDate,
                      RDFS.isDefinedBy,
                      prov.wasDerivedFrom,
                      prov.qualifiedDerivation,
                      prov.entity,
                      prov.startedAtTime,
                      prov.endedAtTime,
                      prov.used,
                      prov.generated,
                      prov.wasAssociatedWith,
                     ]

    symmetric_predicates = [OWL.disjointWith,  # TODO source externally depending on resource semantics?
                           ]

    @classmethod
    def addTopClasses(cls, *uris):
        """ add rdf:type objects to the list of top classes in order
            such that the first uri in the list will appear first
            note that sequential calls to this class always add in
            such a way that the latest call always appears first in
            the file """
        for uri in reversed(uris):
            if uri not in cls.topClasses:
                cls.topClasses = [uri] + cls.topClasses
                cls.SECTIONS = ('',) + cls.SECTIONS

    def __init__(self, store, reset=True):
        setattr(store.__class__, 'qname', qname_mp)  # monkey patch to fix generate=True
        if reset:
            store.namespace_manager.reset()  # ensure that the namespace_manager cache doesn't lead to non deterministic ser

        self.SECTIONS = ['###' + self._space + s + self._nl if s else s for s in self.SECTIONS]
        self.indentString = self._space * len(self.indentString)

        sym_cases = []
        for p in self.symmetric_predicates:
            for s, o in store.subject_objects(p):
                if isinstance(s, URIRef) and isinstance(o, URIRef):
                    if s < o:
                        pass  # always put disjointness axioms earlier in the file
                    elif o < s:
                        store.remove((s, p, o))
                        store.add((o, p, s))
                    else:
                        raise TypeError('Why do you have a class that is disjoint with itself?')
                elif isinstance(s, URIRef):
                    pass
                elif isinstance(o, URIRef):
                    store.remove((s, p, o))
                    store.add((o, p, s))
                else:  # both bnodes
                    sym_cases.append((s, p, o))
                    store.add((o, p, s))

        super(CustomTurtleSerializer, self).__init__(store)
        self.litsortkey = self.make_litsortkey(self.sortkey)
        self.rank_init = 0
        #self.terminals = set(s for s in self.store.subjects(RDF.type, None) if isinstance(s, URIRef))
        self.predicate_rank = self._PredRank()
        self.object_rank = self._LitUriRank()
        or_values = tuple(self.object_rank.values())
        self.max_or = (max(or_values) + 1) if or_values else 1
        self.nosort = set()
        self.list_rankers = self._ListRank()
        self.max_lr = len(self.list_rankers)
        self._list_helpers = {n:p for p, lr in self.list_rankers.items() for n in lr.nodes}
        self.node_rank = self._BNodeRank()
        for s, p, o in sym_cases:
            if self._globalSortKey(s) > self._globalSortKey(o):  # TODO verify that this does what we expect
                store.remove((s, p, o))
            elif self._globalSortKey(s) < self._globalSortKey(o):  # TODO verify that this does what we expect
                store.remove((o, p, s))
            else:
                # equivalent remove the o p s case
                store.remove((o, p, s))

        def debug():
            lv = [(l.node, l.vals)
                  for l in sorted(self.list_rankers.values(),
                                  key=lambda l:l.rank_vec)]
            wat = sorted(((self.object_rank[s]
                           if s in self.object_rank
                           else self.node_rank[s],
                           self.list_rankers[s].vals
                           if s in self.list_rankers
                           else [],
                           s),
                          (self.object_rank[o]
                           if o in self.object_rank
                           else self.node_rank[o],
                           self.list_rankers[o].vals
                           if o in self.list_rankers
                           else [],
                           o))
                         for s, o in self.store.subject_objects(RDF.type))

            sys.stderr.write('\n')
            [sys.stderr.write('{:<30} {}\n'.format(self.store.qname(p), i))
             for i, p in enumerate(self.predicateOrder)]
        if DEBUG: debug()

        # hopefully reduce any memory load?
        self.list_rankers = None
        self._list_helpers = None

    def _BNodeRank(self):
        empty = []
        bnodes = {v:[[empty for _ in range(self.npreds)],
                     [empty for _ in range(self.npreds)],
                     [[], []]]
                  for t in self.store
                  for v in t
                  if isinstance(v, BNode)
                  # FIXME graph ranks ... wew
                  or isinstance(v, QuotedGraph)}
        max_worst_case = len(bnodes) + self.max_or + 2
        mwc = [max_worst_case]
        mwcm1 = [max_worst_case - 1]
        def smwc(l):
            return [_ if _ else mwc for _ in l]
        def normalize():
            for node, (vl, il, (listlists)) in bnodes.items():
                if node in self.nosort:  # FIXME slow, break out before?
                    continue
                for l in vl + il + listlists:  # FIXME SLOW
                    if not (l is empty or l is mwc):
                        l.sort()
            return {k:[smwc(v), smwc(i), smwc(ll)]
                    for k, (v, i, ll) in bnodes.items()}
        def rank():
            old_ls = None
            out = {}
            i = 0  # skip zero so we don't overwrite it
            for nb, ls in sorted(normalize().items(), key=lambda t: t[1]):
                if ls != old_ls:
                    i += 1
                old_ls = ls
                out[nb] = i
            return out
        def specref(rank_vec, pr):
            rv = rank_vec[pr]
            if rv is empty:
                rv = rank_vec[pr] = []
            elif rv is mwc:
                rv = rank_vec[pr] = [max_worst_case]
            elif rv is mwcm1:
                rv = rank_vec[pr] = [max_worst_case - 1]
            return rv
        def fixedpoint(ranks):
            for n, rank_vecs in bnodes.items():
                if n in self._list_helpers:
                    continue
                rank_vecs[1] = [empty for _ in range(self.npreds)]
                rank_vecs[2][1] = []
                if n in self.list_rankers:
                    rank_vecs[2][1].extend(self.list_rankers[n].irank_vec(ranks))
                for p, o in self.store.predicate_objects(n):
                    # TODO speedup by not looking up from store every time
                    if o not in self.object_rank:
                        if p == RDF.first or p == RDF.rest:
                            continue

                        pr = self.predicate_rank[p]
                        invisible_ranks = rank_vecs[1]
                        rv = specref(invisible_ranks, pr)
                        rv.append(ranks[o])

        def one_time():
            for n, (visible_ranks, invisible_ranks, (list_vis_rank, _list_invis_unused)) in bnodes.items():
                if n in self._list_helpers:
                    continue
                if n in self.list_rankers and self.list_rankers[n].vis_vals:
                    list_vis_rank.extend(self.list_rankers[n].rank_vec)
                for p, o in self.store.predicate_objects(n):
                    if p == RDF.first or p == RDF.rest:
                        continue
                    pr = self.predicate_rank[p]
                    rv = specref(visible_ranks, pr)
                    if o in self.object_rank:
                        or_ = self.object_rank[o]
                        rv.append(or_)
                    else:
                        # presence of a more highly ranked predicate counts
                        if not rv:
                            visible_ranks[pr] = mwcm1
                        else:
                            rv.append(max_worst_case - 1)
            ranks = rank()
            fixedpoint(ranks)

        one_time()
        i = 0
        old_norm = None
        while 1:
            if DEBUG:
                sys.stderr.write('\nfixed point iteration {i}'.format(i=i))
            i += 1
            norm = normalize()
            if old_norm == norm:
                break
            else:
                old_norm = norm
                irank = rank()
                fixedpoint(irank)

        out = {n:i + self.max_or for n, i in irank.items()}
        def debug():
            [sys.stderr.write('\n{v:<4}{k}'.format(v=v, k=k))
             for k, v in sorted(self.object_rank.items(),
                                key=lambda t:t[1])]
            def sss(l):
                return ' '.join(['{:>5}'.format(str(_))
                                 if _ != [max_worst_case] else '-----'
                                 for _ in l])
            r = {o:i for i, o in enumerate(list(zip(*sorted(rank().items(), key=lambda t:t[1])))[0])}
            sys.stderr.write('\n' + ' ' * 5 + sss(range(len(self.predicate_rank))) + '\n')
            [sys.stderr.write('\n' +
                              '{:>4} '.format(r[k]) + sss(a) + '\n' +
                              '{:>4} '.format(out[k]) + sss(b) + '\n' +
                              ' ' * 5 + sss(c))
             for k, (a, b, c) in sorted(normalize().items(),
                                     key=lambda t:t[1])]
            sys.stderr.write('\n' + ' ' * 5 + sss(range(len(self.predicate_rank))) + '\n')
        if DEBUG: debug()
        return out

    def _PredRank(self):
        pr = sorted(sorted(set(self.store.predicates(None, None)),
                           key=self.store.qname),
                    key=lambda p: self.sortkey(self.store.qname(p)))
        # predicates in predicateOrder go first but are not guranteed to arrive
        # in predicateOrder thus a_nord
        a_nord = []
        b = []
        for p in pr:
            # XXX DO NOT iterate over self.predicateOrder and pr separately and
            # the merge to arrive at the new value for self.predicateOrder
            # because if there are duplicate values due to e.g. a subClassOf
            # URIRef being used, then len(a + b) != len(pr) therefore we only
            # iterate over pr to ensure that len(a + b) == len(pr) always
            if p in self.predicateOrder:
                a_nord.append((self.predicateOrder.index(p), p))
            else:
                b.append(p)

        a = [p for i, p in sorted(a_nord)]

        self.predicateOrder = a + b  # predicateOrder first, then any remaining
        self.npreds = len(self.predicateOrder)
        return {o:i for i, o in
                enumerate(
                    sorted(set((_ for _ in self.store.predicates())),
                           key=self.predicateOrder.index))}

    def _LitUriRank(self):
        return {o:i  # global rank for all Literals and URIRefs
                for i, o in
                enumerate(
                    sorted(  # doublesort needed for stability wrt case for literals
                           sorted((_ for _ in self.store.objects()
                                   if isinstance(_, Literal))),
                           key=self.litsortkey) +
                    sorted(
                        sorted(set(_ for t in self.store for _ in t
                                   if isinstance(_, URIRef)),
                               key=self.store.qname),
                        key=lambda _: self.sortkey(self.store.qname(_))))}

    def _ListRank(self):
        list_rankers = {}
        list_starts = (s for s in self.store.subjects(RDF.first, None)
                       if not tuple(self.store.subjects(RDF.rest, s)))
        for s in (*self.store.subjects(RDF.type, RDF.List), *list_starts):
            list_rankers[s] = ListRanker(s, self)
        return list_rankers

    def _globalSortKey(self, bnode):
        if isinstance(bnode, BNode) or isinstance(bnode, QuotedGraph):
            try:
                return self.node_rank[bnode]
            except KeyError as e:
                # This is what we have to contend with here :/
                # ro:proper_part_of oboInOwl:hasDefinition [ oboInOwl:hasDbXref [ ] ] .
                sys.stderr.write(('\nWARNING: some node {bnode} that is an object '
                                  'isnt really an object?\n').format(bnode=bnode))
                sys.stderr.write(str(e) + '\n')
                return -1
        else:  # every Literal and URIRef object has a global rank
            return self.object_rank[bnode]

    _topClassSortKey = _globalSortKey

    def startDocument(self):  # modified to natural sort prefixes
        self._started = True
        ns_list = sorted(sorted(self.namespaces.items()), key=lambda kv: (self.sortkey(kv[0]), kv[1]))
        for prefix, uri in ns_list:
            self.write(self.indent() + '@prefix %s: <%s> .%s' % (prefix, uri, self._nl))
        if ns_list and self._spacious:
            self.write(self._nl)

    def orderSubjects(self):  # modified to enable natural sort of subjects
        seen = {}
        sections = []

        for i, classURI in enumerate(self.topClasses):  # SECTIONS
            members = sorted(self.store.subjects(RDF.type, classURI))
            members.sort(key=self._topClassSortKey)

            subjects = []
            for member in members:
                if isinstance(member, BNode):
                    if classURI == RDFS.Datatype:
                        # rdfs:Datatype shows up before owl:Class in topClasses
                        # we need to avoid pulling anon members out by accident
                        continue
                    elif self._references[member] > 0:
                        # if a member is referenced as an object then
                        # it not a top class and should not be pulled
                        # up since it will expose the raw bnode
                        # UNLESS IT IS IN A CYCLE: which we handle below
                        continue

                subjects.append(member)
                self._topLevels[member] = True
                seen[member] = True
            sections.append(subjects)

        recursable = [
            (isinstance(subject, BNode),
             self._references[subject],
             subject)
            for subject in self._subjects if subject not in seen]

        try:
            recursable.sort(key=lambda t: self._globalSortKey(t[-1]))
        except TypeError as e:
            raise e  # break here if you encounter an issue

        # group bnodes with classes only if they have no refs
        noref = [subject for (isbnode, refs, subject) in recursable
                 if isbnode and not refs]
        sections[-1].extend(noref)

        # annotation targets
        at = [subject for (isbnode, refs, subject) in recursable
              if not isbnode or isbnode and refs >= 1]
        sections.append(at)

        #bc = [(s, sorted(self.store[s::]))  # DEBUG
              #for s in self.store[:RDF.type:OWL.Class]
              #if isinstance(s, BNode)]

        return sections

    def predicateList(self, subject, newline=False):  # modified to sort object lists
        properties = self.buildPredicateHash(subject)
        propList = self.sortProperties(properties)
        if len(propList) == 0:
            return
        self.verb(propList[0], newline=newline)
        self.objectList(sorted(sorted(properties[propList[0]])[::-1], key=self._globalSortKey))  # rdf:type
        whitespace = ('{};{}'.format(self._space, self._nl) + self.indent(1)
                      if self._newline else ';')
        for predicate in propList[1:]:
            self.write(whitespace)
            self.verb(predicate, newline=self._newline)
            self.objectList(sorted(sorted(properties[predicate])[::-1], key=self._globalSortKey))

        return True

    def sortProperties(self, properties):  # modified to sort objects using their global rank
        """Take a hash from predicate uris to lists of values.
           Sort the lists of values.  Return a sorted list of properties."""
        # Sort object lists
        for prop, objects in properties.items():
            objects.sort(key=self._globalSortKey)

        # Make sorted list of properties
        return sorted(properties, key=lambda p: self.predicate_rank[p])

    def _buildPredicateHash(self, subject):  # XXX unmodified
        """
        Build a hash key by predicate to a list of objects for the given
        subject
        """
        properties = {}
        for s, p, o in self.store.triples((subject, None, None)):
            oList = properties.get(p, [])
            oList.append(o)
            properties[p] = oList

        return properties

    def p_squared(self, node, position, newline=False):  # FIXME REMOVE
        if (not isinstance(node, BNode)
                or node in self._serialized
                or self._references[node] > 1
                or position == SUBJECT):
            return False

        if not newline:
            self.write(self._space)

        if self.isValidList(node):
            # this is a list
            self.write('(')
            if SDEBUG:
                self.write('{}# '.format(self._nl) + str(self._globalSortKey(node)) + self._nl)  # FIXME REMOVE
            self.depth += 1  # 2
            self.doList(node)
            self.depth -= 1  # 2
            self.write(' )')
        else:
            self.subjectDone(node)
            self.depth += 2
            # self.write('[{}'.format(self._nl) + self.indent())
            self.write('[')
            if SDEBUG:
                self.write('{}# '.format(self._nl) + str(self._globalSortKey(node)) + self._nl)  # FIXME REMOVE
            self.depth -= 1
            # self.predicateList(node, newline=True)
            if self.predicateList(node, newline=False):
                self.write(self._space)
            # self.write(self._nl + self.indent() + ']')
            self.write(']')
            self.depth -= 1

        return True

    def isValidList(self, l):  # modified to flatten lists specified using [ a rdf:List; ] syntax
        """
        Checks if l is a valid RDF list, i.e. no nodes have other properties.
        """
        try:
            if self.store.value(l, RDF.first) is None:
                return False
        except:
            return False
        while l:
            if l != RDF.nil:
                po = list(self.store.predicate_objects(l))
                if (RDF.type, RDF.List) in po and len(po) == 3:
                    pass
                elif len(po) != 2:
                    return False
            l = self.store.value(l, RDF.rest)
        return True

    def doList(self, l):  # modified to put rdf list items on new lines and to sort by global rank
        reorder = ListRanker.test_reorder(l, self)
        to_sort = []
        while l:
            item = self.store.value(l, RDF.first)
            if item is not None:
                to_sort.append(item)
            self.subjectDone(l)
            l = self.store.value(l, RDF.rest)

        whitespace = self._nl + self.indent(1) if self._newline else ''

        if reorder:
            ordered = sorted(to_sort, key=self._globalSortKey)
        else:
            ordered = to_sort

        for item in ordered:
            self.write(whitespace)
            self.path(item, OBJECT, newline=self._newline)

    def p_default(self, node, position, newline=False):
        if position != SUBJECT and not newline:
            self.write(self._space)
        self.write(self.label(node, position))
        return True

    def p_squared(self, node, position, newline=False):
        if (not isinstance(node, BNode)
                or node in self._serialized
                or self._references[node] > 1
                or position == SUBJECT):
            return False

        if not newline:
            self.write(self._space)

        if self.isValidList(node):
            # this is a list

            if SDEBUG:
                self.write(f'{self._nl}# ' + str(self._globalSortKey(node)) + self._nl)  # FIXME REMOVE
            self.write('(')
            self.depth += 1  # 2
            self.doList(node)
            self.depth -= 1  # 2
            self.write(self._space)
            self.write(')')
        else:
            self.subjectDone(node)
            self.depth += 2
            self.write('[')
            if SDEBUG:
                self.write(f'{self._nl}#{self._space}' +
                           str(self._globalSortKey(node)) +
                           self._nl)  # FIXME REMOVE
            self.depth -= 1
            if self.predicateList(node, newline=False):
                self.write(self._space)
            self.write(']')
            self.depth -= 1

        return True

    def s_default(self, subject):
        self.write(self._nl + self.indent())
        self.path(subject, SUBJECT)
        self.predicateList(subject)
        self.write('{}.'.format(self._space))
        return True

    def s_squared(self, subject):  # modified to enable whitespace switching
        if (self._references[subject] > 0) or not isinstance(subject, BNode):
            return False
        whitespace = self._nl + self.indent() if self._newline else ''
        self.write(whitespace + '[]')
        if SDEBUG:
            self.write('{}#{}'.format(self._nl, self._space) +
                       str(self._globalSortKey(subject)) + self._nl)  # FIXME REMOVE
        self.predicateList(subject)
        self.write('{}.'.format(self._space))
        return True

    def objectList(self, objects):  # modified to use self._nl
        count = len(objects)
        if count == 0:
            return
        depthmod = (count == 1) and 0 or 1
        self.depth += depthmod
        self.path(objects[0], OBJECT)
        for obj in objects[1:]:
            self.write(',{}'.format(self._nl) + self.indent(1))
            self.path(obj, OBJECT, newline=True)
        self.depth -= depthmod

    def getQName(self, uri, gen_prefix=True): # modified to make it possible to block gen_prefix
        return super(CustomTurtleSerializer, self).getQName(uri, gen_prefix and self._gen_prefix)

    def _write(self, value):
        """ rename to write and import inspect to debut the callstack """
        if ' ' in value:
            s = inspect.stack()
            fn = s[1].function
            super().write('%%DEBUG {} %%'.format(fn))
        super().write(value)

    def serialize(self, stream, base=None, encoding=None,  # modified to enable section headers
                  spacious=None, gen_prefix=True, **args):
        self.reset()
        self.stream = stream
        self.base = base

        if spacious is not None:
            self._spacious = spacious

        self._gen_prefix = gen_prefix

        self.preprocess()
        sections_list = self.orderSubjects()

        self.startDocument()

        whitespace = self._nl if self._newline else ''
        firstTime = True
        for header, subjects_list in zip(self.SECTIONS, sections_list):
            if subjects_list and header:
                # check if there is at least one subject that is not done
                # so that we only emit headers when there are things that
                # will live under them, if there is nothing continue to the
                # next section
                for subject in subjects_list:
                    if not self.isDone(subject):
                        self.write(whitespace + header)
                        break
                else:
                    continue

            for subject in subjects_list:
                if self.isDone(subject):
                    continue
                if firstTime:
                    firstTime = False
                if self.statement(subject) and not firstTime:
                    self.write(self._nl)

        self.endDocument()
        stream.write(self._nl.encode('ascii'))
        n, v = self._name, self.__version
        stream.write(u'### Serialized using the {} serializer {}{}'.format(n, v, self._nl).encode('ascii'))


class HtmlTurtleSerializer(CustomTurtleSerializer):
    """ Produce a htmlized ttl file with working hyperlinks. """

    _nl = '<br>\n'
    _space = '\u00A0'

    def __init__(self, store, *args, **kwargs):
        from htmlfn import atag
        self.atag = atag
        self._labels = {s:str(o) for s, o in store[:RDFS.label:]}
        super(HtmlTurtleSerializer, self).__init__(store, *args, **kwargs)

    def startDocument(self):  # modified to natural sort prefixes + html escape
        self._started = True
        ns_list = sorted(sorted(self.namespaces.items()), key=lambda kv: (self.sortkey(kv[0]), kv[1]))
        for prefix, uri in ns_list:
            self.write(self.indent() + '@prefix %s: &lt;%s&gt; .%s' % (prefix, uri, self._nl))
        if ns_list and self._spacious:
            self.write(self._nl)

    def label(self, node, position):
        if node == RDF.nil:
            return '()'
        if position is VERB and node in self.keywords:
            return self.keywords[node]
        if isinstance(node, Literal):
            return node._literal_n3(
                use_plain=True,
                qname_callback=lambda dt: self.atag(dt, self.getQName(
                    dt, gen_prefix=False), new_tab=True))
        else:
            node = self.relativize(node)

            out = self.getQName(node, position == VERB) or node.n3()
            out = out.replace('<', '&lt;').replace('>', '&gt;')
            label = self._labels[node] if node in self._labels else None
            return self.atag(node, out, new_tab=True, title=label)

    def serialize(self, *args, **kwargs):
        """ Modified to allow additional labels to be passed in. """
        if 'labels' in kwargs:
            # populate labels from outside the local graph
            self._labels.update(kwargs['labels'])
        super(HtmlTurtleSerializer, self).serialize(*args, **kwargs)


class RacketTurtleSerializer(CustomTurtleSerializer):
    def startDocument(self):
        self.stream.write('#lang rdf/turtle{}'.format(self._nl).encode())
        super().startDocument()


class CompactTurtleSerializer(CustomTurtleSerializer):

    short_name = 'cmpttl'
    _name = 'ttlser compact deterministic'
    _newline = False
    _compact = True

    def __init__(self, store):
        from collections import Counter
        counts = Counter(e for t in store
                         for e in (*t, *(_.datatype
                                        for _ in t
                                        if isinstance(_, Literal)))
                         if isinstance(e, URIRef))
        preds = set(v for v, c in counts.items() if c > 2 and len(v) > 10)
        if not self._compact:
            nm_store = store.store
            real_namespace = getattr(nm_store, f'_{nm_store.__class__.__name__}__namespace')
            real_prefix = getattr(nm_store, f'_{nm_store.__class__.__name__}__prefix')
            for p, n in tuple(real_namespace.items()):
                if n in preds:
                    real_namespace.pop(p)
                    real_prefix.pop(n)
        store.namespace_manager.reset()
        if self._compact:
            #existing = set(n for q, n in store.namespace_manager.namespaces())
            #pne = sorted(sorted((_ for _ in preds if _ not in existing)), key=self.sortkey)
            pne = sorted(sorted(preds), key=self.sortkey)
            for p, q in zip(pne, sorted(sorted(makeSymbolPrefixes(len(pne))), key=self.sortkey)):
                store.bind(q, p, override=False)
        #print(store.namespace_manager._NamespaceManager__trie)
        #print(list(store.namespaces()))
        super(CompactTurtleSerializer, self).__init__(store, reset=False)

    def s_default(self, subject):  # modified from TurtleSerializer to remove newlines
        self.path(subject, SUBJECT)
        self.predicateList(subject)
        self.write('{}.'.format(self._space))
        return True

    def objectList(self, objects):  # modified from TurtleSerializer to remove newlines
        count = len(objects)
        if count == 0:
            return
        depthmod = (count == 1) and 0 or 1
        self.depth += depthmod
        self.path(objects[0], OBJECT)
        for obj in objects[1:]:
            self.write(',')
            self.path(obj, OBJECT, newline=False)
        self.depth -= depthmod


class UncompactTurtleSerializer(CompactTurtleSerializer):

    short_name = 'uncmpttl'
    _name = 'ttlser uncompact deterministic'
    _newline = False
    _compact = False


class DeterministicTurtleSerializer(UncompactTurtleSerializer):
    """ Serializer used for ranking triples for calculating hashes of graphs.  """

    predicateOrder = []
    sortkey = staticmethod(lambda v:v)


class SubClassOfTurtleSerializer(CustomTurtleSerializer):

    short_name = 'scottl'
    _name = 'ttlser subClassOf deterministic'

    def __init__(self, store):
        super(SubClassOfTurtleSerializer, self).__init__(store)
        self.topclass_rank = self._TCRank()

    def _topClassSortKey(self, bnode):
        if isinstance(bnode, BNode):
            return self._globalSortKey(bnode)
        return self.topclass_rank[bnode]

    def _TCRank(self):

        class wrapsort(URIRef):
            """ steal their identitiy and force them to sort using ulterior methods """
            def __call__(self, uriref):
                return self.__class__(uriref)
            def __eq__(self, other):
                return str(self) == str(other)
            def __lt__(self, other):  # recall that lower ranked goes first
                return ((self in supers[other]
                         if other in self.supers
                         else False) or
                        (any(other > mysuper #mysuper < other
                             if mysuper != self  # FIXME longer cycles?
                             else False
                             for mysuper in self.supers[self])
                         if self in supers else False) or  # oof could be slow
                        nq(self) < nq(other))
            def __gt__(self, other):
                return ((other in self.supers[self]
                         if self in self.supers
                         else False) or
                        (any(othersuper < self
                             if othersuper != other  # FIXME longer cycles?
                             else False
                             for othersuper in self.supers[other])
                         if other in supers else False) or  # oof could be slow
                        nq(self) > nq(other))
            __hash__ = URIRef.__hash__

        uris = set(s for e in self.topClasses for s in self.store.subjects(RDF.type, e))
        def supersOf(predicate, object_is_child):
            supers = {}
            for s, o in self.store.subject_objects(predicate):
                if object_is_child:
                    o, s = s, o
                if isinstance(s, URIRef):
                    if not isinstance(o, URIRef):
                        continue
                    s, o = wrapsort(s), wrapsort(o)
                    if s not in supers:
                        supers[s] = set()
                    supers[s].add(o)
            return supers

        supers = {k:v for p, oic in
                  ((RDFS.subClassOf, False),
                   (RDFS.subPropertyOf, False),
                   (OWL.imports, False))
                  for k, v in supersOf(p, oic).items()}
        wrapsort.supers = supers
        qname = self.store.qname

        def nq(n):
            if isinstance(n, BNode):
                return '',
            return self.sortkey(qname(n))


        #for k, v in supers.items():
            #print(repr(k), v)

        return {o:i  # global rank for all Literals and URIRefs
                for i, o in
                enumerate(
                    sorted(  # doublesort needed for stability wrt case for literals
                           sorted((_ for _ in self.store.objects()
                                   if isinstance(_, Literal))),
                           key=self.litsortkey) +
                    sorted(
                        sorted(uris, key=self.store.qname),
                        key=wrapsort))}


__all__ = ['natsort', CustomTurtleSerializer.__name__] + [
    c.__name__ for c in subclasses(CustomTurtleSerializer)
]
