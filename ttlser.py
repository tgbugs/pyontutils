#!/usr/bin/env python3.5
import re
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib import RDF, RDFS, OWL, BNode
from rdflib.namespace import SKOS, DC, Namespace

OBOANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#')
BIRNANN = Namespace('http://ontology.neuinfo.org/NIF/Backend/BIRNLex_annotation_properties.owl#')

def natsort(s, pat=re.compile(r'([0-9]+)')):
    return [int(t) if t.isdigit() else t for t in pat.split(s)]

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

        recursable.sort(key=lambda r: natsort(r[-1]))
        subjects.extend([subject for (isbnode, refs, subject) in recursable])

        return subjects

    def predicateList(self, subject, newline=False):
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

    def serialize(self, stream, base=None, encoding=None,
                  spacious=None, **args):
        super(CustomTurtleSerializer, self).serialize(stream, base, encoding, spacious, **args)
        stream.write(u"# serialized using the nifstd custom serializer\n".encode('ascii'))

