#!/usr/bin/env python3.6
import re
from datetime import datetime
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib import RDF, RDFS, OWL, BNode, URIRef, Literal
from rdflib.namespace import SKOS, DC, Namespace
from IPython import embed

NIFRID = Namespace('http://uri.neuinfo.org/nif/nifstd/readable/')
OBOANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#')
BIRNANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#')
oboInOwl = Namespace('http://www.geneontology.org/formats/oboInOwl#')
#IAO = Namespace('http://purl.obolibrary.org/obo/IAO_')  # won't work because numbers ...

DEBUG = True

def natsort(s, pat=re.compile(r'([0-9]+)')):
    return [int(t) if t.isdigit() else t.lower() for t in pat.split(s)]

def litsort(l):
    dt = l.datatype if l.datatype is not None else ''
    lang = l.language if l.language is not None else ''
    return (natsort(l), dt, lang)

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
        pr = sorted(sorted(set(self.store.predicates(None, None))), key=natsort)
        self.npreds = len(pr)
        self.predicateOrder = [p for p in self.predicateOrder if p in pr]  # drop unused
        max_pred = len(self.predicateOrder) + 1
        self.object_rank = {o:i  # global rank for all URIRef that appear as objects
                            for i, o in
                            list(
                            enumerate(
                                sorted(set((_ for _ in self.store.predicates(None, None))),
                                       key=lambda _: self.predicateOrder.index(_) if _ in self.predicateOrder else max_pred + pr.index(_) # needed for owl:Restrictions
                                      ) +
                                sorted(  # doublesort needed for stability wrt case for literals
                                    sorted((_ for _ in self.store.objects(None, None)
                                            if isinstance(_, Literal))),
                                       key=litsort) +
                                sorted(
                                    sorted(set(
                                        [_ for _ in self.store.objects(None, None)
                                         if isinstance(_, URIRef)] +
                                        [_ for _ in self.store.subjects(None, None)
                                         if isinstance(_, URIRef)]), key=self.store.qname),
                                    # we add to dict in reverse so that the rank of any nodes
                                    # that appear more than once is their lowest rank
                                    key=lambda _: natsort(self.store.qname(_)))))[::-1]}

        max_or = max(self.object_rank.values()) + 1
        node_rank = {}
        need_rank = {}
        #mempreds = {}
        #anons = set()
        #level_preds = [{RDF.type},
                       #{OWL.onProperty, OWL.annotatedSource},
                       #{OWL.annotatedProperty},  # slot 2 is for predicate ranking generally
                       #{OWL.annotatedTarget}]
        def recurse(rank, node, pred, depth=0, start=tuple()):
            #print(rank, node, pred, depth, start)
            if isinstance(node, BNode):
                if node not in node_rank:
                    node_rank[node] = [0] * (self.npreds + 2)
                if pred is None:
                    pindex = -2
                else:
                    orp = self.object_rank[pred]
                    pindex = self.npreds - orp - 1
                    #print(self.npreds, orp, pindex)
                node_rank[node][pindex] += rank
            pd = 0
            for s, p in self.store.subject_predicates(node):  # there should be only one of these usually
                if not start:
                    start = {node}
                elif node not in start:
                    start.add(node)
                if s not in start:
                    parent, d = recurse(rank, s, p, depth + 1, start)  # XXX recursion is here
                    if isinstance(node, BNode) and d > pd:
                        pd = d
                        if isinstance(parent, BNode):
                            out = BNode(parent)  # XXX rdflib bug
                        else:
                            out = URIRef(parent)  # rdflib.term.URIRef and URIRef hash to different values :/ XXX rdflib bug
                        if out in self.object_rank:
                            #print(hash(out))
                            #print('\n'.join(sorted(f'{k} {hash(k)}' for k in self.object_rank)))
                            node_rank[node][-1] = self.object_rank[out]  # tie breaker
                        else:
                            need_rank[node] = out
            try:
                return out, pd
            except NameError:
                return node, depth  # no more parents

        def _old_recurse():
            #if node not in mempreds:
                #ranked_preds = sorted(set(self.store.predicates(node, None)), key=self._globalSortKey)
                #mempreds[node] = ranked_preds
            #else:
                #ranked_preds = mempreds[node]

            for s, p in self.store.subject_predicates(node):  # subject_predicate for predicate ranking, walk backward up the tree?
                if isinstance(s, BNode):
                    if s not in self.node_rank:
                        self.node_rank[s] = [0] * (self.npreds + 1)

                    prank = self.object_rank[p]
                    #if prank == pred_rank:
                        #self.node_rank[s][pred_rank] += rank
                    #else:
                    self.node_rank[s][prank] += rank
                    recurse(rank, s, p)
                    continue

                    isanon = False
                    if s not in anons:
                        has_type_triple = set(self.store.objects(s, RDF.type))
                        if has_type_triple:
                            anons.add(s)
                            isanon = True
                    else:
                        isanon = True

                    # TODO instead of using level_preds, sort the predicates by their predicate rank and _then_ file
                    if isanon:
                        for level, preds in enumerate(level_preds):
                            if p in preds:
                                self.node_rank[s][level] += rank

                            if level == 2:
                                self.node_rank[s][level] += self.object_rank[p]
                            elif level == 3:
                                self.node_rank[s][level] += rank

                    else:
                        self.node_rank[s][-1] += rank

                    recurse(s, rank)  # in theory the recurse gets smaller since we go up...
                else:
                    pass  # we have hit a top level

        for o, r in self.object_rank.items():
            recurse(r, o, None)

        nr = {k:v + max_or for v, k in enumerate(k for k, v in sorted(node_rank.items(), key=lambda t:t[-1]))}
        for node, parent in need_rank.items():
            before = node_rank[node][-1]
            node_rank[node][-1] = nr[need_rank[node]]
            after = node_rank[node][-1]
            #print(before, after)

        old_nr = [(k,tuple(v)) for k, v in node_rank.items()]
        nr = {k:v + max_or for v, k in enumerate(k for k, v in sorted(nr.items(), key=lambda t:t[-1]))}
        #or_ = 
        #self.node_rank = {k:tuple(v) for k, v in node_rank.items()}
        self.node_rank = nr
        #self.object_rank = {k:((0,) * self.npreds) + (v,) for k, v in self.object_rank.items()}
        self.recurse = recurse

    def _globalSortKey(self, bnode):
        if isinstance(bnode, BNode):
            try:
                return self.node_rank[bnode]
            except KeyError as e : 
                # This is what we have to contend with here :/
                # ro:proper_part_of oboInOwl:hasDefinition [ oboInOwl:hasDbXref [ ] ] .
                print('WARNING: some node that is an object isnt really an object?')
                print(e)
                #embed()
                #return (-1, -1, -1, -1)
                #return (-1,) * (self.npreds + 1)
                return -2
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
        propList = []
        seen = {}
        for prop in self.predicateOrder:
            if (prop in properties) and (prop not in seen):
                propList.append(prop)
                seen[prop] = True
        props = sorted(properties.keys())
        props.sort(key=natsort)
        for prop in props:
            if prop not in seen:
                propList.append(prop)
                seen[prop] = True
        return propList

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
            if DEBUG:
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
            if DEBUG:
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

            if DEBUG:
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
            if DEBUG:
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
        if DEBUG:
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

