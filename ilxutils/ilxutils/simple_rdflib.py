from collections import defaultdict
from IPython import embed
from rdflib import Graph, RDF, OWL, RDFS, BNode, Literal, URIRef, Namespace
from sys import exit
from typing import Dict, Tuple, List, Union
from ilxutils.rdfdata import common_namespaces
# TODO: integrate ### entity type commentss

class SimpleGraph:
    """ rdflib shortcuts | rdflib made simple

    Although rdflib is a good toolbox, it has no blueprints on how the structure of RDF files
    should be built. As a result is is lacking autocompletes and gives a lot of room for shortcuts.

    If something is lacking here that exists in rdflib, simply just pull the "g" attribute out
    becuase that is the rdflib Graph being used.

    Attributes:
        g: rdflib Graph
        namespaces: rdflib Graph namespaces saved to be and checked. rdflib has a bug where
            duplicates can be made.
            I.E. if "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .", exists
            and you want to add "@predix rdf: <http://made_up_uri#> .", it won't skip. It
            will literally make "@predix rdf1: <http://made_up_uri#> .". Appending an
            iteration to the prefix.
        rqname: reverse qualified name.
            rdflib can make a qname/property ( prefix_of_uri : property_name ) from
            a uri if a prefix namespace is already given, but it cannot make a uri from the
            qname sadly.
        triple2annotation_bnode: Once a BNode is created to anchor an annotation of the triple,
             the BNode address is lost unless saved. Therefore if you want to add to the triples
             annotation you need the same BNode address.
    """

    def __init__(self):
        self.g = Graph() # rdflib.Graph
        self.namespaces = {} # Dict[Namespace]
        self.rqname = {} # Dict[str]
        self.triple2annotation_bnode = {} # Dict[Bnode]

    def add_namespaces(self, namespaces: Dict[str, str]) -> None:
        """ Adds a prefix to uri mapping (namespace) in bulk

        Adds a namespace to replace any uris in iris with shortened prefixes
        in order to make the file more readable. Not techniqually necessary.

        Args: namespaces: prefix to uri mappings

        Example:
            add_namespaces(
                namespaces = {
                    'my_prefix': 'http://myurl.org/',
                    'memo': 'http://memolibrary.org/memo#',
                }
            )
        """
        for prefix, uri in namespaces.items():
            self.add_namespace(prefix=prefix, uri=uri)

    def qname(self, iri: str) -> str:
        """ Get qualified name of uri in rdflib graph while also saving it

        Args: iri: The iri that you want to replace the uri with a known prefix with

        Returns: qualified name of the iri to be used as the new predicate
        """
        prefix, namespace, name = self.g.compute_qname(uri)
        qname = prefix + ':' + name
        self.rqname[qname] = iri
        return qname

    def add_namespace(self, prefix: str, uri: str) -> Namespace:
        """ Adds a prefix to uri mapping (namespace)

        Adds a namespace to replace any uris in iris with shortened prefixes
        in order to make the file more readable. Not techniqually necessary.

        Args:
            prefix: prefix that will substitute the uri in the iri
            uri: the uri in the iri to be substituted by the prefix

        Returns:
            A namespace of the uri

        Example:
            add_namespace(
                prefix = "rdfs",
                uri = 'http://www.w3.org/2000/01/rdf-schema#',
            )
            makes
            "http://www.w3.org/2000/01/rdf-schema#label 'neuron'@en ;",
            become
            "rdfs:label 'neuron'@en ;"
        """
        ns = Namespace(uri)
        if not self.namespaces.get(prefix):
            self.namespaces[prefix] = ns
            self.g.bind(prefix, uri)
        return ns

    def find_prefix(self, iri: Union[URIRef, Literal, str]) -> Union[None, str]:
        """ Finds if uri is in common_namespaces

        Auto adds prefix if incoming iri has a uri in common_namespaces. If its not in the local
        library, then it will just be spit out as the iri and not saved/condensed into qualified
        names.

        The reason for the maxes is find the longest string match. This is to avoid accidently
        matching iris with small uris when really is a more complete uri that is the match.

        Args: iri: iri to be searched to find a known uri in it.

        Eample:
            In  [1]: print(find_prefix("http://www.w3.org/2000/01/rdf-schema#label"))
            Out [1]: "http://www.w3.org/2000/01/rdf-schema#"
            In  [2]: print(find_prefix("http://made_up_uri/label"))
            Out [2]: None
        """
        iri = str(iri)
        max_iri_len = 0
        max_prefix = None
        for prefix, uri in common_namespaces.items():
            if uri in iri and max_iri_len < len(uri): # if matched uri is larger; replace as king
                max_prefix = prefix
                max_iri_len = len(uri)
        return max_prefix

    def add_annotation(
            self,
            subj: URIRef,
            pred: URIRef,
            obj: Union[Literal, URIRef],
            a_p: URIRef ,
            a_o: Union[Literal, URIRef],
        ) -> BNode:
        """ Adds annotation to rdflib graph.

        The annotation axiom will filled in if this is a new annotation for the triple.

        Args:
            subj: Entity subject to be annotated
            pref: Entities Predicate Anchor to be annotated
            obj: Entities Object Anchor to be annotated
            a_p: Annotation predicate
            a_o: Annotation object

        Returns:
            A BNode which is an address to the location in the RDF graph that is storing the
            annotation information.
        """
        bnode: BNode = self.triple2annotation_bnode.get( (subj, pred, obj) )
        if not bnode:
            a_s: BNode = BNode()
            self.triple2annotation_bnode[(subj, pred, obj)]: BNode = a_s
            self.g.add((a_s, RDF.type, OWL.Axiom))
            self.g.add((a_s, OWL.annotatedSource, self.process_subj_or_pred(subj)))
            self.g.add((a_s, OWL.annotatedProperty,self.process_subj_or_pred(pred)))
            self.g.add((a_s, OWL.annotatedTarget, self.process_obj(obj)))
        else:
            a_s: BNode = bnode
        self.g.add((a_s, self.process_subj_or_pred(a_p), self.process_obj(a_o)))
        return bnode # In case you have more triples to add

    def add_triple(
            self,
            subj: Union[URIRef, str],
            pred: Union[URIRef, str],
            obj: Union[URIRef, Literal, str]
        ) -> None:
        """ Adds triple to rdflib Graph

        Triple can be of any subject, predicate, and object of the entity without a need for order.

        Args:
            subj: Entity subject
            pred: Entity predicate
            obj: Entity object

        Example:
            In  [1]: add_triple(
                ...:    'http://uri.interlex.org/base/ilx_0101431',
                ...:    RDF.type,
                ...:    'http://www.w3.org/2002/07/owl#Class')
                ...: )
        """
        if obj in [None, "", " "]: return # Empty objects are bad practice
        _subj = self.process_subj_or_pred(subj)
        _pred = self.process_subj_or_pred(pred)
        _obj = self.process_obj(obj)
        self.g.add( (_subj, _pred, _obj) )

    def process_prefix(self, prefix: str) -> Union[Namespace, None]:
        """ Add namespace to graph if it has a local match

        This allows qnames to be used without adding their respected namespaces if they are in
        the common_namespaces local dict. This is is to save a butt-ton of time trying to see what
        the ontology has as far as uris go.

        Args: prefix: prefix of the uri in the rdflib namespace to be checked if it exists in
            the local dict of common_namespaces.

        Returns: Namespace of uri if add or already exists; else None
        """
        if self.namespaces.get(prefix):
            return self.namespaces[prefix]
        iri: str = common_namespaces.get(prefix)
        if iri:
            return self.add_namespace(prefix, iri)

    def process_subj_or_pred(self, component: Union[URIRef, str]) -> URIRef:
        """ Adds viable uri from iri or expands viable qname to iri to be triple ready

        Need to have a viable qualified name (qname) in order to use a qname. You can make it
        viable by either add the namespace beforehand with add_namespace(s) or if its already
        in the local common_namespaces preloaded.

        Args:
            component: entity subject or predicate to be expanded or have its uri saved.

        Returns:
            rdflib URIRef ready subject or predicate to be put into a triple.

        Raises:
            SystemExit: When expecting a qname to be expanded, but is not valid or if
                component is not a qualified name or a iri.
        """
        if 'http' in component:
            prefix = self.find_prefix(component) # Find uri in iri based on common_namespaces
            if prefix: self.process_prefix(prefix) # if match, will add to Graph namespaces
            return URIRef(component)
        elif ':' in component:
            presumed_prefix, info = component.split(':', 1)
            namespace: Union[Namespace, None] = self.process_prefix(presumed_prefix)
            if not namespace: exit(component + ': qname namespace does\'t exist yet.')
            return namespace[info]
        exit(component + ': is not a valid subject or predicate')

    def process_obj(self, obj: Union[URIRef, Literal, str]) -> Union[URIRef, Literal]:
        """ Gives component the proper node type

        Args:
            obj: Entity object to be converted to its appropriate node type

        Returns:
            URIRef or Literal type of the object provided.

        Raises:
            SystemExit: If object is a dict or list it becomes str with broken data. Needs to
                come in one object at a time.
        """
        if isinstance(obj, dict) or isinstance(obj, list):
            exit(str(obj) + ': should be str or intended to be a URIRef or Literal.')

        if isinstance(obj, Literal) or isinstance(obj, URIRef):
            prefix = self.find_prefix(obj)
            if prefix: self.process_prefix(prefix)
            return obj

        if len(obj) > 8:
            if 'http' == obj[:4] and '://' in obj and ' ' not in obj:
                prefix = self.find_prefix(obj)
                if prefix: self.process_prefix(prefix)
                return URIRef(obj)

        if ':' in str(obj):
            presumed_prefix, info = obj.split(':', 1)
            namespace: Union[Namespace, None] = self.process_prefix(presumed_prefix)
            if namespace: return namespace[info]

        return Literal(obj)

    def serialize(self, **kwargs) -> str:
        """ rdflib.Graph().serialize wrapper

        Original serialize cannot handle PosixPath from pathlib. You should ignore everything, but
        destination and format. format is a must, but if you don't include a destination, it will
        just return the formated graph as an str output.

        Args:
            destination: Output file path,
            format: format for for the triple to be put together as: 'xml', 'n3', 'turtle', 'nt',
                'pretty-xml', 'trix', 'trig' and 'nquads' are built in. json-ld in rdflib_jsonld
            base: none
            encoding: None
            **args: None
        """
        kwargs = {key: str(value) for key, value in kwargs.items()}
        return self.g.serialize(**kwargs).encode('utf-8') # FIXME: might ruin it when conv to utf-8

    def remove_triple(
            self,
            subj: URIRef,
            pred: URIRef,
            obj: Union[URIRef, Literal]
        ) -> None:
        """ Removes triple from rdflib Graph

        You must input the triple in its URIRef or Literal form for each node exactly the way it
        was inputed or it will not delete the triple.

        Args:
            subj: Entity subject to be removed it its the only node with this subject; else this is
                just going to delete a desciption I.E. predicate_object of this entity.
            pred: Entity predicate to be removed
            obj: Entity object to be removed
        """
        self.g.remove( (subj, pred, obj) )

    def print_graph(self, format: str = 'turtle') -> str:
        """ prints serialized formated rdflib Graph """
        print(self.g.serialize(format=format).decode('utf-8'))


def main():
    g = RDFGraph()
    g.add_class('ILX:12345')
    g.add_annotation('ILX:12345', rdflib.RDF.type, rdflib.OWL.Class,
                     a_p='ilxtr:literatureCitation', a_o='PMID:12345')
    g.print_graph()

if __name__ == '__main__':
    main()
