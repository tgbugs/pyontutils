#!/usr/bin/env python3.5
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib import RDF, BNode

class CustomTurtleSerializer(TurtleSerializer):
    """ NIFSTD custom ttl serliziation """

    def orderSubjects(self):
        seen = {}
        subjects = []

        for classURI in self.topClasses:
            members = list(self.store.subjects(RDF.type, classURI))
            members.sort()

            for member in members:
                subjects.append(member)
                self._topLevels[member] = True
                seen[member] = True

        recursable = [
            (isinstance(subject, BNode),
             self._references[subject], subject)
            for subject in self._subjects if subject not in seen]

        recursable.sort()
        subjects.extend([subject for (isbnode, refs, subject) in recursable])

        return subjects

    def serialize(self, stream, base=None, encoding=None,
                  spacious=None, **args):
        super(CustomTurtleSerializer, self).serialize(stream, base, encoding, spacious, **args)
        stream.write(u"# serialized using the nifstd custom serializer\n".encode('ascii'))

