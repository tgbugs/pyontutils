#!/usr/bin/env python3.6
import re
import sys
from datetime import datetime
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib import RDF, RDFS, OWL, XSD, BNode, URIRef, Literal
from rdflib.namespace import SKOS, DC, Namespace
from IPython import embed

NIFRID = Namespace('http://uri.neuinfo.org/nif/nifstd/readable/')
OBOANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#')
BIRNANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#')
oboInOwl = Namespace('http://www.geneontology.org/formats/oboInOwl#')
#IAO = Namespace('http://purl.obolibrary.org/obo/IAO_')  # won't work because numbers ...

DEBUG = False
SDEBUG = False

def natsort(s, pat=re.compile(r'([0-9]+)')):
    return tuple(int(t) if t.isdigit() else t.lower() for t in pat.split(s))

def litsort(l):
    dt = l.datatype if l.datatype is not None else ''
    lang = l.language if l.language is not None else ''
    if dt == XSD.boolean:
        out = 0, tuple(), (0 if l == 'false' else 1)
    elif dt == XSD.integer:
        out = 1, tuple(), int(l), str(l)
    elif dt == XSD.decimal:
        out = 1, tuple(), float(l), str(l)
    elif dt == XSD.double:
        out = 1, tuple(), float(l), str(l)
    else:
        out = 2, natsort(l), 0, dt, lang
    return out

# XXX WARNING prefixes are not 100% deterministic if there is more than one prefix for namespace
#     the implementation of IOMemory.bind in rdflib means that the last prefix defined in the list
#     will likely be the one that is called when NamespaceManager.compute_qname calls self.store.prefix

SUBJECT = 0
VERB = 1
OBJECT = 2

def qname_mp(self, uri):  # for monkey patching Graph
    try:
        prefix, namespace, name = self.compute_qname(uri, False)
    except Exception:  # no prefix no problems
        return uri

    if prefix == "":
        return name
    else:
        return ":".join((prefix, name))

class ListRanker:
    def __init__(self, node, serializer):
        self.node = node
        self.serializer = serializer
        self.vals = []
        self.nodes = []  # list nodes
        l = self.node
        while l:
            item = self.serializer.store.value(l, RDF.first)
            self.add(item, l)
            l = self.serializer.store.value(l, RDF.rest)
        self.vis_vals = [v for v in self.vals if not isinstance(v, BNode)]
        self.bvals = [v for v in self.vals if isinstance(v, BNode)]

    def add(self, item, node):
        if item is not None:
            self.vals.append(item)
            if node != self.node:
                self.nodes.append(node)

    @property
    def rank_vec(self):
        out = tuple(sorted(self._vis_val_key(v) for v in self.vis_vals))
        if not out:
            return self.serializer.max_lr + 1,
        else:
            return out

    def _vis_val_key(self, val):
        if val in self.serializer.object_rank:
            return self.serializer.object_rank[val]

    def _b_val_rank(self, val):
        if val in self.serializer.node_rank:
            return 1, self.serializer.node_rank[val]
        elif val in self.serializer.list_rank:
            return 2, self.serializer.list_rank[val]
        else:
            raise BaseException('Not upulated yet...')
            return self.max_or

    def __hash__(self):
        return hash(self.node)

class CustomTurtleSerializer(TurtleSerializer):
    """ NIFSTD custom ttl serliziation. See ../docs/ttlser.md for more info. """

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
                '\n### rdf Properties\n',
                '\n### rdfs Classes\n',
                '\n### Object Properties\n',
                '\n### Datatypes\n',
                '\n### Annotation Properties\n',
                '\n### Data Properties\n',
                '\n### Classes\n',
                '\n### Individuals\n',
                '\n### Axioms\n',
                '\n### Annotations\n',
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
                     ]

    def __init__(self, store):
        setattr(store.__class__, 'qname', qname_mp)  # monkey patch to fix generate=True
        store.namespace_manager.reset()  # ensure that the namespace_manager cache doesn't lead to non deterministic ser
        super(CustomTurtleSerializer, self).__init__(store)
        self.rank_init = 0
        self.terminals = set(s for s in self.store.subjects(RDF.type, None) if isinstance(s, URIRef))
        self.predicate_rank = self._PredRank()
        self.object_rank = self._LitUriRank()
        self.max_or = max(self.object_rank.values()) + 1
        self._ListRank()
        self._firsts = {n:p for p, lr in self.list_rankers.items() for n in lr.nodes}
        self.node_rank = self.round2()
        if DEBUG:
            [l.vals for l in sorted(self.list_rankers.values(), key=lambda l:l.rank_vec)]
            sys.stderr.write('\n')
            [sys.stderr.write(f'{self.store.qname(p):<30} {i}\n')
             for i, p in enumerate(self.predicateOrder)]
        #embed()
        return
        # first rank by the 'visible' nodes
        # build a map of nodes that have blank node children
        # second rank by the ranks of the BNodes that have been ranked by the visible nodes
        self.need_prank = {}
        self.node_rank_vec = {}
        self._ListRank()
        self._BNodeRank()
        self.max_nr = max(self._node_rank.values())
        self.resolve_ranks()
        self.node_rank = self._node_rank
        self.list_rank = self._list_rank  # FIXME TODO
        def debug():
            parents = {}
            if DEBUG:
                max_worst_case = self.nr_worst_case
                old_nr = [(k,tuple(v)) for k, v in self.normalized_node_rank_vec.items()]
                sys.stderr.write('\n')
                [sys.stderr.write(f'{self.store.qname(p):<30} {i}\n')
                 for i, p in enumerate(self.predicateOrder)]
                [sys.stderr.write(f'{a:<10}' + (f'{parents[a] if a in parents else "None":<40} '
                                  f'{self.node_rank[a]} ') +
                                  ' '.join('-' * 4
                                           if c == max_worst_case
                                           else f'{c:>4}' for c in b) + '\n')
                 for a, b in sorted(old_nr, key=lambda t:t[1])]
                sys.stderr.write('Object Ranks\n')
                [sys.stderr.write(f'{repr(o)}\n') for o, i in
                 sorted(self.object_rank.items(), key=lambda t:t[1])]
        debug()

    def round2(self):
        bnodes = {v:[[[] for _ in range(self.npreds)],  # [[]] * n produces 10 of the same list!
                     [[] for _ in range(self.npreds)],
                     [[], []]]
                  for t in self.store
                  for v in t
                  if isinstance(v, BNode)}
        mwc = len(bnodes) + self.max_or + 2
        def smwc(l):
            return [_ if _ else [mwc] for _ in l]
        def normalize():
            for vl, il, (listlists) in bnodes.values():
                for l in vl + il + listlists:
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
        def fixedpoint(ranks):
            for n, rank_vecs in bnodes.items():
                rank_vecs[1] = [[] for _ in range(self.npreds)]
                rank_vecs[2][1] = []
                for p, o in self.store.predicate_objects(n):  # TODO speedup by not looking up every time
                    if o not in self.object_rank:
                        if p == RDF.first:
                            if o in self._list_rank:
                                if n not in self._list_rank:
                                    print('hit', n, o, ranks[n], ranks[o])
                                rank_vecs[2][1].append(ranks[o])  # FIXME Y U NO PROPAGATE?
                            continue
                        elif p == RDF.rest:
                            continue
                        rank_vecs[1][self.predicate_rank[p]].append(ranks[o])
        def one_time():
            for n, (visible_ranks, invisible_ranks, (lvr, lir)) in bnodes.items():
                for p, o in self.store.predicate_objects(n):
                    if p == RDF.first:
                        if n in self._list_rank and self.list_rankers[n].vis_vals:
                            lvr.append(self._list_rank[n])  # FIXME list of just lists will have weird rank
                            #else:
                                #print(self.list_rankers[n].vals)
                        continue
                    elif p == RDF.rest:
                        continue
                    pr = self.predicate_rank[p]
                    if o in self.object_rank:
                        or_ = self.object_rank[o]
                        visible_ranks[pr].append(or_)
                    else:
                        visible_ranks[pr].append(mwc - 1)  # presence of a more highly ranked predicate counts
            vranks = rank()
            #print(sorted(vranks.items(), key=lambda t:(t[1], t[0])))
            fixedpoint(vranks)
        one_time()
        i = 0
        old_norm = None
        while 1:
            sys.stderr.write(str(i))
            i += 1
            norm = normalize()
            if old_norm == norm:
                break
            else:
                old_norm = norm
                irank = rank()
                fixedpoint(irank)
                #irank = rank()
                #fixedpoint(irank)
        def debug():
            [sys.stderr.write(f'\n{v:<4}{k}')
             for k, v in sorted(self.object_rank.items(),
                                key=lambda t:t[1])]
            def sss(l):
                return ' '.join([f'{str(_):>5}' if _ != [mwc] else '-----'
                                 for _ in l])
            r = {o:i for i, o in enumerate(list(zip(*sorted(rank().items(), key=lambda t:t[1])))[0])}
            [sys.stderr.write('\n' +
                              f'{r[k]:>4} ' + sss(a) + '\n' +
                              ' ' * 5 + sss(b) + '\n' +
                              ' ' * 5 + sss(c))
             for k, (a, b, c) in sorted(normalize().items(),
                                     key=lambda t:t[1])]
        if DEBUG: debug()
        return {n:i + self.max_or for n, i in irank.items()}

    def _PredRank(self):
        pr = sorted(sorted(set(self.store.predicates(None, None))), key=natsort)
        a = [p for p in self.predicateOrder if p in pr]  # remove predicateOrder not in pr
        b = [p for p in pr if p not in self.predicateOrder]  # dedupe pr before merging
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
                           key=litsort) +
                    sorted(
                        sorted(set(_ for t in self.store for _ in t
                                   if isinstance(_, URIRef)),
                               key=self.store.qname),
                        key=lambda _: natsort(self.store.qname(_))))}

    def _recurse(self, rank, node, pred, depth=0, start=tuple()):
        #print(rank, node, pred, depth)#, start)
        if isinstance(node, BNode):
            node = BNode(node)
            if node not in self.node_rank_vec:
                # len is predicates + parent + list cols
                # TODO optimization: skip predicates never used with BNodes
                self.node_rank_vec[node] = [self.rank_init] * (self.npreds + 1 + 1)
            orp = self.predicate_rank[pred]
            pindex = orp
            crank = self.node_rank_vec[node][pindex]
            if not rank and crank == self.rank_init:
                # edge case where rank is 0 and pred rank is 0
                # results in trips with multiple types first
                self.node_rank_vec[node][pindex] -= 1
            else:
                # summing ranks of all children could be an issue
                # if you can find graph structures whose leaf
                # counts sum to exactly the same amount at every
                # node in the graph all the way up to the terminal
                self.node_rank_vec[node][pindex] += rank
        pd = 0
        for s, p in sorted(self.store.subject_predicates(node),
                           # sort on predicate required for stability
                           key=lambda t:(self.predicate_rank[t[1]], t[0])):
            if isinstance(node, BNode) and s in self._list_rank:
                self.node_rank_vec[node][-2] = self._list_rank[s]  # tie breaker 0 on vis nodes
                continue
            elif p == RDF.rest or p == RDF.first:
                continue
            elif not start:
                start = [node]
            elif node not in start:
                start.append(node)

            if s not in start:
                if s in self.terminals and isinstance(node, BNode):
                    self.node_rank_vec[node][-1] = self.object_rank[s]  # tie breaker 0 on vis nodes
                    continue
                parent, d = self._recurse(rank, s, p, depth + 1, start)  # XXX recursion is here
                if isinstance(node, BNode) and d > pd:
                    pd = d
                    if isinstance(parent, BNode):
                        out = BNode(parent)  # XXX rdflib bug
                    else:
                        # rdflib.term.URIRef and URIRef hash to different values :/
                        out = URIRef(parent) # XXX rdflib bug
                    if out in self.object_rank:
                        self.node_rank_vec[node][-1] = self.object_rank[out]  # tie breaker 1
                    else:
                        self.need_prank[node] = out
        try:
            return out, pd
        except NameError:
            return node, depth  # no more parents

    def _BNodeRank(self):
        for o, r in sorted(self.object_rank.items(), key=lambda t:t[1]):
            if o != RDF.List:
                self._recurse(r, o, None)

    def resolve_ranks(self):
        node_rank = self._node_rank
        for node, parent in self.need_prank.items():
            self.node_rank_vec[node][-3] = node_rank[parent]  # tie breaker 2
            parents[node] = parent

    def getPrank(self, node, start=tuple()):
        if not start:
            start = {node}
        else:
            start.add(node)
        prank = -100
        subs = list(self.store.subjects(None, node))
        for s in subs:
            if s in self.terminals:
                or_ = self.object_rank[s]
                if or_ > prank:
                    prank = or_
            elif s in self.node_rank_vec:
                return self.node_rank_vec[s][-3]
        if prank < 0:
            for s in subs:
                if s not in start:
                    prank = self.getPrank(s, start)
        return prank

    def getAnonParents(self, node, start=tuple()):
        if not start:
            start = {node}
        else:
            start.add(node)
        parents = list(self.store.subjects(None, node))
        if not parents:
            raise StopIteration
        else:
            for s in parents:
                if isinstance(s, BNode):
                    yield s
                if s not in start:
                    yield from self.getAnonParents(s, start)

    @property
    def nr_worst_case(self):
        if self.node_rank_vec:
            return max(max(v) for v in self.node_rank_vec.values()) + 1
        else:
            return 1

    @property
    def normalized_node_rank_vec(self):
        max_worst_case = self.nr_worst_case
        return {k:tuple(_ if _ else max_worst_case
                   for _ in v)
                for k, v in self.node_rank_vec.items()}

    @property
    def _node_rank(self):
        return {k:v + self.max_or for v, k in
                enumerate(k for k, v in
                          sorted(self.normalized_node_rank_vec.items(),
                                 key=lambda t:t[-1]))}

    def _ListRank(self):
        # FIXME lists inside lists will be a problem...
        # when printing lists the nodes will always come second
        # but when computing list ranks if there is a tie need to split
        # on the ranks for the nodes inside and then the ranks of the lists inside
        # we need a sort column for children for each of these
        # literal
        # uri
        # BNode propertyList -> bnode [
        # collection -> bnode (
        # [self.rank_init] * self.npreds + [prank] + [lit, uri, bnPL, collection]
        #node_rank = self._node_rank

        def lkey(t):
            if t in self.object_rank:
                return self.object_rank[t]
            else:
                return self.max_or
                #try:
                    #return node_rank[t]
                #except KeyError:
                    #sys.stderr.write(f'KeyError on {t}\n')
                    #sys.stderr.write(str(list(self.store.subject_predicates(t)) +
                                         #list(self.store.predicate_objects(t))) + '\n\n')
                    #self.need_rank[sub] = t
                    #return -100

        def lrkey(t):
            return tuple(lkey(v) for v in t[1]['vals'])

        lists = {}
        list_starts = (s for s in self.store.subjects(RDF.first, None)
                       if not tuple(self.store.subjects(RDF.rest, s)))

        for s in (*self.store.subjects(RDF.type, RDF.List), *list_starts):
            #prank = self.getPrank(s)
            #l = s
            #print(s)
            lists[s] = ListRanker(s, self)

        self.list_rankers = lists
        self.max_lr = len(self.list_rankers)
        self.list_rank_vec = {n:lr.rank_vec for n, lr in self.list_rankers.items()}


        old_ls = None
        list_rank = {}
        i = 0  # skip zero so we don't overwrite it
        for nb, ls in sorted(self.list_rank_vec.items(), key=lambda t: t[1]):
            if ls != old_ls:
                i += 1
            old_ls = ls
            list_rank[nb] = i
        #list_rank = {o:i + 1 for i, o in  # i + 1 to avoid renormalization of rank zero
                     #enumerate(
                         #list(
                             #zip(*sorted(self.list_rank_vec.items(),
                                         #key=lambda t:t[1])))[0])}
        self._list_rank = list_rank
        #self.max_lr = max(list_rank.values())
        return

        def debug():
            if DEBUG:
                sys.stderr.write('\n[\n')
                [[sys.stderr.write('\n[\n')] +
                 [sys.stderr.write(f'{self.store.qname(_)}\n')
                  for _ in v['vals']] +
                 [sys.stderr.write(']')]
                 for k, v in
                 sorted(lists.items(),
                        key=lrkey)]
                 #sorted(lists.values(),
                        #key=lambda v: [self.object_rank[_] if _ in self.object_rank else self.max_or for _ in v['vals']])]
                sys.stderr.write('\n]\n')
        debug()

        list_rank_vec = {}
        if lists:
            # we have natsort for the internal list order from object_rank
            # the we natsort again here for the between-list ordering
            list_rank = {o:i + 1 for i, o in  # i + 1 to avoid renormalization of rank zero
                         enumerate(
                             list(
                                 zip(*sorted(lists.items(),
                                     key=lrkey)))[0])}
            #[print(i, v, lists[i]['vals']) for i, v in list_rank_vecs.items()]
            for l, r in sorted(list_rank.items(), key=lambda t: t[1]):
                total_list_rank = 1
                prank = lists[l]['prank']
                #prank = self.rank_init
                list_rank_vec[l] = [rank_init, r, total_list_rank]
                #for p in self.getAnonParents(l):
                    # propagate list rank information to parent BNodes
                    # FIXME this won't work in cases there is more than one list :/
                    # we would need a whole additional set of vectors for
                    # TODO keep all the *_rank_vec orthogonal
                    # even though lists are technically nodes, they have different semantics
                    # can pull this bit of code out into resolve ranks
                    #if p in self.node_rank_vec and p not in list_rank:
                        #self.node_rank_vec[p][-2] = r  # FIXME += ???? instead of last one wins?
                total_list_rank += 1
                nodes = lists[l]['nodes']
                for node in nodes:
                    list_rank_vec[node] = [r, total_list_rank]
                    total_list_rank += 1
                #print(node_rank[l])

        return list_rank_vec

    def _globalSortKey(self, bnode):
        if isinstance(bnode, BNode):
            if bnode in self.node_rank:
                return self.node_rank[bnode]
            #elif bnode in self.list_rank:
                #return self.list_rank[bnode]
            else:
                # This is what we have to contend with here :/
                # ro:proper_part_of oboInOwl:hasDefinition [ oboInOwl:hasDbXref [ ] ] .
                sys.stderr.write(f'WARNING: some node {bnode} that is an object isnt really an object?\n')
                #sys.stderr.write(str(e) + '\n')
                #embed()
                #return (-1, -1, -1, -1)
                #return (-1,) * (self.npreds + 1)
                return -1
        else:  # every Literal and URIRef object has a global rank now
            return self.object_rank[bnode]

    def startDocument(self):  # modified to natural sort prefixes
        self._started = True
        ns_list = sorted(sorted(self.namespaces.items()), key=lambda kv: (natsort(kv[0]), kv[1]))
        for prefix, uri in ns_list:
            self.write(self.indent() + '@prefix %s: <%s> .\n' % (prefix, uri))
        if ns_list and self._spacious:
            self.write('\n')

    def orderSubjects(self):  # modified to enable natural sort of subjects
        seen = {}
        sections = []

        for i, classURI in enumerate(self.topClasses):  # SECTIONS
            members = sorted(self.store.subjects(RDF.type, classURI))
            members.sort(key=self._globalSortKey)

            subjects = []
            for member in members:
                if classURI == RDFS.Datatype:
                    if isinstance(member, BNode):
                        continue  # rdfs:Datatype shows up before owl:Class in the topClasses list, so we need to avoid pulling anon members out by accident
                subjects.append(member)
                self._topLevels[member] = True
                seen[member] = True
            sections.append(subjects)

        recursable = [
            (isinstance(subject, BNode),
             self._references[subject], subject)
            for subject in self._subjects if subject not in seen]

        try:
            recursable.sort(key=lambda t: self._globalSortKey(t[-1]))
        except TypeError as e:
            embed()

        sections[-1].extend([subject for (isbnode, refs, subject) in recursable if isbnode and not refs])  # group bnodes with classes only if they have no refs
        sections.append([subject for (isbnode, refs, subject) in recursable if not isbnode])  # annotation targets

        return sections

    def predicateList(self, subject, newline=False):  # modified to sort object lists
        properties = self.buildPredicateHash(subject)
        propList = self.sortProperties(properties)
        if len(propList) == 0:
            return
        self.verb(propList[0], newline=newline)
        self.objectList(sorted(sorted(properties[propList[0]])[::-1], key=self._globalSortKey))  # rdf:Type
        for predicate in propList[1:]:
            self.write(' ;\n' + self.indent(1))
            self.verb(predicate, newline=True)
            self.objectList(sorted(sorted(properties[predicate])[::-1], key=self._globalSortKey))

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
            self.write(' ')

        if self.isValidList(node):
            # this is a list
            self.write('(')
            if SDEBUG:
                self.write('\n# ' + str(self._globalSortKey(node)) + '\n')  # FIXME REMOVE
            self.depth += 1  # 2
            self.doList(node)
            self.depth -= 1  # 2
            self.write(' )')
        else:
            self.subjectDone(node)
            self.depth += 2
            # self.write('[\n' + self.indent())
            self.write('[')
            if SDEBUG:
                self.write('\n# ' + str(self._globalSortKey(node)) + '\n')  # FIXME REMOVE
            self.depth -= 1
            # self.predicateList(node, newline=True)
            self.predicateList(node, newline=False)
            # self.write('\n' + self.indent() + ']')
            self.write(' ]')
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
        to_sort = []
        while l:
            item = self.store.value(l, RDF.first)
            if item is not None:
                to_sort.append(item)
            self.subjectDone(l)
            l = self.store.value(l, RDF.rest)

        for item in sorted(to_sort, key=self._globalSortKey):
            self.write('\n' + self.indent(1))
            self.path(item, OBJECT, newline=True)

    def _p_default(self, node, position, newline=False):  # XXX unmodified
        if position != SUBJECT and not newline:
            self.write(' ')
        self.write(self.label(node, position))
        return True

    def _p_squared(self, node, position, newline=False):  # XXX unmodified
        if (not isinstance(node, BNode)
                or node in self._serialized
                or self._references[node] > 1
                or position == SUBJECT):
            return False

        if not newline:
            self.write(' ')

        if self.isValidList(node):
            # this is a list

            if SDEBUG:
                self.write('\n# ' + str(self._globalSortKey(node)) + '\n')  # FIXME REMOVE
            self.write('(')
            self.depth += 1  # 2
            self.doList(node)
            self.depth -= 1  # 2
            self.write(' )')
        else:
            self.subjectDone(node)
            self.depth += 2
            # self.write('[\n' + self.indent())
            self.write('[')
            if SDEBUG:
                self.write('\n# ' + str(self._globalSortKey(node)) + '\n')  # FIXME REMOVE
            self.depth -= 1
            # self.predicateList(node, newline=True)
            self.predicateList(node, newline=False)
            # self.write('\n' + self.indent() + ']')
            self.write(' ]')
            self.depth -= 1

        return True

    def _s_default(self, subject):  # XXX unmodified, ordering issues start here
        self.write('\n' + self.indent())
        self.path(subject, SUBJECT)
        self.predicateList(subject)
        self.write(' .')
        return True

    def s_squared(self, subject):  # modified to make anon topClasses behave like anon nested classes
        if (self._references[subject] > 0) or not isinstance(subject, BNode):
            return False
        self.write('\n' + self.indent() + '[')
        if SDEBUG:
            self.write('\n# ' + str(self._globalSortKey(subject)) + '\n')  # FIXME REMOVE
        self.predicateList(subject)
        self.write(' ] .')
        return True

    def serialize(self, stream, base=None, encoding=None,  # modified to enable section headers
                  spacious=None, **args):
        self.reset()
        self.stream = stream
        self.base = base

        if spacious is not None:
            self._spacious = spacious

        self.preprocess()
        sections_list = self.orderSubjects()

        self.startDocument()

        firstTime = True
        for header, subjects_list in zip(self.SECTIONS, sections_list):
            if subjects_list:
                self.write(header)
            for subject in subjects_list:
                if self.isDone(subject):
                    continue
                if firstTime:
                    firstTime = False
                if self.statement(subject) and not firstTime:
                    self.write('\n')

        self.endDocument()
        stream.write(u"\n".encode('ascii'))
        stream.write((u"### Serialized using the nifstd custom serializer v1.0.8\n").encode('ascii'))

