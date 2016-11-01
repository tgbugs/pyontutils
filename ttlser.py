#!/usr/bin/env python3.5
import re
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib import RDF, RDFS, OWL, BNode
from rdflib.namespace import SKOS, DC, Namespace

OBOANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#')
BIRNANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#')

def natsort(s, pat=re.compile(r'([0-9]+)')):
    return [int(t) if t.isdigit() else t.lower() for t in pat.split(s)]


# desired behavior
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

class CustomTurtleSerializer(TurtleSerializer):
    """ NIFSTD custom ttl serliziation """

    topClasses = [RDFS.Class,
                  OWL.Ontology,
                  OWL.ObjectProperty,
                  OWL.AnnotationProperty,
                  OWL.Class,
                 ]

    predicateOrder = [RDF.type,
                      OWL.onProperty,
                      OWL.allValuesFrom,
                      OWL.someValuesFrom,
                      OWL.imports,
                      OWL.deprecated,
                      OWL.equivalentClass,
                      RDFS.label,
                      SKOS.prefLabel,
                      OBOANN.synonym,
                      OBOANN.abbrev,
                      DC.title,
                      SKOS.definition,
                      DC.description,
                      RDFS.subClassOf,
                      OWL.intersectionOf
                      OWL.unionOf
                      OWL.disjointWith,
                      OWL.disjointUnionOf,
                      OBOANN.createdDate,
                      OBOANN.modifiedDate,
                      RDFS.comment,
                      SKOS.note,
                      SKOS.editorialNote,
                      SKOS.changeNote,
                      OWL.versionInfo,
                     ]

    def __init__(self, store):
        super(CustomTurtleSerializer, self).__init__(store)
        self._local_order = []  # for tracking non BNode sort values

    def startDocument(self):
        self._started = True
        ns_list = sorted(self.namespaces.items(), key=lambda kv: natsort(kv[0]))
        for prefix, uri in ns_list:
            self.write(self.indent() + '@prefix %s: <%s> .\n' % (prefix, uri))
        if ns_list and self._spacious:
            self.write('\n')

    def orderSubjects(self):  # copied over to enable natural sort of subjects
        seen = {}
        subjects = []

        for classURI in self.topClasses:
            members = list(self.store.subjects(RDF.type, classURI))
            members.sort(key=natsort)

            for member in members:
                subjects.append(member)
                self._topLevels[member] = True
                seen[member] = True

        recursable = [
            (isinstance(subject, BNode),
             self._references[subject], subject)
            for subject in self._subjects if subject not in seen]

        #recursable.sort(key=lambda r: natsort(r[-1]))
        subjects.extend([subject for (isbnode, refs, subject) in recursable])

        return subjects

    def _predicateList(self, subject, newline=False):
        properties = self.buildPredicateHash(subject)
        propList = self.sortProperties(properties)
        if len(propList) == 0:
            return
        self.verb(propList[0], newline=newline)
        self.objectList(properties[propList[0]])
        for predicate in propList[1:]:
            self.write(' ;\n' + self.indent(1))
            self.verb(predicate, newline=True)
            self.objectList(sorted(properties[predicate], key=natsort))

    def _sortProperties(self, properties):
        """Take a hash from predicate uris to lists of values.
           Sort the lists of values.  Return a sorted list of properties."""
        # Sort object lists
        for prop, objects in properties.items():
            objects.sort(key=natsort)

        # Make sorted list of properties
        propList = []
        seen = {}
        for prop in self.predicateOrder:
            if (prop in properties) and (prop not in seen):
                propList.append(prop)
                seen[prop] = True
        props = list(properties.keys())
        props.sort(key=natsort)
        for prop in props:
            if prop not in seen:
                propList.append(prop)
                seen[prop] = True
        return propList

    def _buildPredicateHash(self, subject):
        """
        Build a hash key by predicate to a list of objects for the given
        subject
        """
        properties = {}
        for s, p, o in self.store.triples((subject, None, None)):
            oList = properties.get(p, [])
            oList.append(o)
            properties[p] = oList

        for k in properties:
            properties[k].sort(key=natsort)

        return properties

    def p_default(self, node, position, newline=False):
        if position != SUBJECT and not newline:
            self.write(' ')
        self.write(self.label(node, position))
        return True

    def p_squared(self, node, position, newline=False):
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

    def s_default(self, subject):  # XXX ordering issues start here
        self.write('\n' + self.indent())
        self.path(subject, SUBJECT)
        self.predicateList(subject)
        self.write(' .')
        return True

    def s_squared(self, subject):  # XXX ordering issues start here
        if (self._references[subject] > 0) or not isinstance(subject, BNode):
            return False
        self.write('\n' + self.indent() + '[]')
        self.predicateList(subject)
        self.write(' .')
        return True

    def serialize(self, stream, base=None, encoding=None,
                  spacious=None, **args):
        super(CustomTurtleSerializer, self).serialize(stream, base, encoding, spacious, **args)
        stream.write(u"# serialized using the nifstd custom serializer\n".encode('ascii'))

