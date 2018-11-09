import rdflib
from pyontutils import combinators as cmb


class AnnotationMixin:
    @property
    def __graph(self):
        if hasattr(self, 'out_graph'):
            return self.out_graph
        elif hasattr(self, 'graph'):
            return self.graph
        else:
            raise AttributeError('no graph or out_graph')

    def getPredicate(self, object):
        """ override this if you get predicates in a special way """

    def getObject(self, predicate):
        """ override this if you get objects in a special way """

    def annotate(self, predicate, object, annotations):
        t = self.identifier, predicate, object
        print(t)
        # FIXME obviously it is quite a trick to annotat a bnode without
        # so we annotate the lowered version (or is it the lifted version?)
        [self.__graph.add(t) for t in cmb.annotation(t, *annotations)()]

    def annotateByPredicate(self, predicate, annotations):
        # TODO more sane conversion of predicate in the event it is a curie
        print(predicate, annotations)
        predicate = rdflib.URIRef(predicate)
        object = self.getObject(predicate)
        self.annotate(predicate, object, annotations)

    def annotateByObject(self, object, annotations):
        # TODO more sane conversion of object in the event it is a curie
        print(object, annotations)
        object = rdflib.URIRef(object)
        predicate = self.getPredicate(object)
        self.annotate(predicate, object, annotations)

    def batchAnnotate(self, thing_annotations, function=None):
        if function is None:
            for (predicate, object), annotations in thing_annotations.items():
                self.annotate(predicate, object, annotations)
        else:
            for thing, annotations in thing_annotations.items():
                function(thing, annotations)

    def batchAnnotateByPredicate(self, predicate_annotations):
        self.batchAnnotate(predicate_annotations, self.annotateByPredicate)

    def batchAnnotateByObject(self, object_annotations):
        self.batchAnnotate(object_annotations, self.annotateByObject)
