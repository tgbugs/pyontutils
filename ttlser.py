#!/usr/bin/env python3.5
import re
from datetime import datetime
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib import RDF, RDFS, OWL, BNode, URIRef
from rdflib.namespace import SKOS, DC, Namespace
from IPython import embed

OBOANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#')
BIRNANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#')
oboInOwl = Namespace('http://www.geneontology.org/formats/oboInOwl#')
#IAO = Namespace('http://purl.obolibrary.org/obo/IAO_')  # won't work because numbers ...

def natsort(s, pat=re.compile(r'([0-9]+)')):
    return [int(t) if t.isdigit() else t.lower() for t in pat.split(s)]

# XXX WARNING prefixes are not 100% deterministic if there is more than one prefix for namespace
#     the implementation of IOMemory.bind in rdflib means that the last prefix defined in the list
#     will likely be the one that is called when NamespaceManager.compute_qname calls self.store.prefix

# desired behavior (XXX does not match the implementation!
# 1) if there is more than one entry at a level URIRef goes first natsorted then lists then predicate lists then subject lists
# 2) sorting for nested structures in a list determined by
#     a) rank of object attached to the highest ranked predicate (could just be alpha)
#     b) rank of object attached to the second highest ranked predicate
#     c) where there are multiple of the same predicate their own rank is determined by the ranks of their objects
#     d) predicate lists are ranked -2 and subject (proper?) lists are ranked -1 as predicates
#     e) sorting proper lists... get the predicate rank and then the rank of the value
# object type ranks:
#  1 URIRef
#  2 predicate list []
#  3 proper list ()
# object value ranks:
#  1 URIRef -> alphabetical
#  2 lists -> object type ranks of their nth elements
#
# a nice example is NIF-Cell:nlx_cell_091210 in NIF-Neuron-BrainRegion-Bridge.ttl

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
    """ NIFSTD custom ttl serliziation """

    topClasses = [RDFS.Class,
                  OWL.Ontology,
                  OWL.ObjectProperty,
                  RDFS.Datatype,  # FIXME order in this list matters, so we need to skip BNode cases
                  OWL.AnnotationProperty,
                  OWL.DatatypeProperty,
                  OWL.Class,
                  OWL.NamedIndividual,
                  OWL.AllDifferent,
                 ]

    SECTIONS = ('',
                '',
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
                      OWL.imports,
                      OWL.deprecated,
                      URIRef('http://purl.obolibrary.org/obo/IAO_0100001'),  # replacedBy:
                      oboInOwl.hasDbXref,
                      OWL.equivalentClass,
                      RDFS.label,
                      SKOS.prefLabel,
                      OBOANN.synonym,
                      OBOANN.abbrev,
                      DC.title,
                      SKOS.definition,
                      DC.description,
                      RDFS.subClassOf,
                      OWL.intersectionOf,
                      OWL.unionOf,
                      OWL.disjointWith,
                      OWL.disjointUnionOf,
                      RDFS.comment,
                      SKOS.note,
                      SKOS.editorialNote,
                      SKOS.changeNote,
                      OWL.versionInfo,
                      OBOANN.createdDate,
                      OBOANN.modifiedDate,
                     ]

    def __init__(self, store):
        setattr(store.__class__, 'qname', qname_mp)  # monkey patch to fix generate=True
        store.namespace_manager.reset()  # ensure that the namespace_manager cache doesn't lead to non deterministic ser
        super(CustomTurtleSerializer, self).__init__(store)
        max_pred = len(self.predicateOrder) + 1
        self.object_rank = {o:i  # global rank for all URIRef that appear as objects
                            for i, o in
                            enumerate(
                                #sorted(set((_ for _ in self.store.predicates(None, None))),
                                       #key=lambda _: self.predicateOrder.index(_) if _ in self.predicateOrder else max_pred # needed for owl:onProperty cases
                                      #) +
                                sorted(
                                    sorted(set(
                                        [_ for _ in self.store.objects(None, None)
                                         if not isinstance(_, BNode)] +  # URIRef + Literal
                                        [_ for _ in self.store.subjects(None, None)
                                         if isinstance(_, URIRef)])),
                                    key=lambda _: natsort(self.store.qname(_))))}

        self.node_rank = {}
        def recurse(node, rank):
            for s, p in self.store.subject_predicates(node):  # subject_predicate for predicate ranking, walk backward up the tree?
                if isinstance(s, BNode):
                    if s not in self.node_rank:
                        self.node_rank[s] = [0, 0]
                    if p == OWL.someValuesFrom or p == OWL.allValuesFrom:  # second level sort
                        self.node_rank[s][1] += rank
                    else:
                        self.node_rank[s][0] += rank
                    recurse(s, rank)
                else:
                    pass  # we have hit a top level

        for o, r in self.object_rank.items():
            recurse(o, r)

        self.node_rank = {k:tuple(v) for k, v in self.node_rank.items()}
        self.object_rank = {k:(0, v) for k, v in self.object_rank.items()}

    def _globalSortKey(self, bnode):
        if isinstance(bnode, BNode):
            try:
                return self.node_rank[bnode]
            except KeyError as e : 
                # This is what we have to contend with here :/
                # ro:proper_part_of oboInOwl:hasDefinition [ oboInOwl:hasDbXref [ ] ] .
                print('WARNING: some node that is an object isnt really an object?')
                print(e)
                return (-1, -1)
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

        def key(m):
            if not isinstance(m, BNode):
                m = self.store.qname(m)
            return natsort(m)

        for i, classURI in enumerate(self.topClasses):  # SECTIONS
            members = sorted(self.store.subjects(RDF.type, classURI))
            members.sort(key=key)

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

        sections[-1].extend([subject for (isbnode, refs, subject) in recursable if isbnode])  # group bnodes with classes
        sections.append([subject for (isbnode, refs, subject) in recursable if not isbnode])  # annotation targets

        return sections

    def _predicateList(self, subject, newline=False):  # XXX unmodified
        properties = self.buildPredicateHash(subject)
        propList = self.sortProperties(properties)
        if len(propList) == 0:
            return
        self.verb(propList[0], newline=newline)
        self.objectList(properties[propList[0]])
        for predicate in propList[1:]:
            self.write(' ;\n' + self.indent(1))
            self.verb(predicate, newline=True)
            self.objectList(properties[predicate])

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
            #if header == self.SECTIONS[-2]:  # Axioms can be BNodes as it turns out...
                #if any([not isinstance(s, BNode) for s in subjects_list]):
                    #print('GOT ONE')
                #self.write(header)
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
        stream.write((u"### Serialized using the nifstd custom serializer v1.0.4\n").encode('ascii'))

