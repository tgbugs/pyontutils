from collections import defaultdict
import rdflib
from rdflib import RDF, OWL, RDFS, BNode
from IPython import embed
from sys import exit

class RDFGraph:
    raw_namespaces = {
        # full
        'hasRole': 'http://purl.obolibrary.org/obo/RO_0000087',
        'inheresIn': 'http://purl.obolibrary.org/obo/RO_0000052',
        'bearerOf': 'http://purl.obolibrary.org/obo/RO_0000053',
        'participatesIn': 'http://purl.obolibrary.org/obo/RO_0000056',
        'hasParticipant': 'http://purl.obolibrary.org/obo/RO_0000057',
        'hasInput': 'http://purl.obolibrary.org/obo/RO_0002233',
        'hasOutput': 'http://purl.obolibrary.org/obo/RO_0002234',
        'adjacentTo': 'http://purl.obolibrary.org/obo/RO_0002220',
        'derivesFrom': 'http://purl.obolibrary.org/obo/RO_0001000',
        'derivesInto': 'http://purl.obolibrary.org/obo/RO_0001001',
        'agentIn': 'http://purl.obolibrary.org/obo/RO_0002217',
        'hasAgent': 'http://purl.obolibrary.org/obo/RO_0002218',
        'containedIn': 'http://purl.obolibrary.org/obo/RO_0001018',
        'contains': 'http://purl.obolibrary.org/obo/RO_0001019',
        'locatedIn': 'http://purl.obolibrary.org/obo/RO_0001025',
        'locationOf': 'http://purl.obolibrary.org/obo/RO_0001015',
        'toward': 'http://purl.obolibrary.org/obo/RO_0002503',
        'replacedBy': 'http://purl.obolibrary.org/obo/IAO_0100001',
        'hasCurStatus': 'http://purl.obolibrary.org/obo/IAO_0000114',
        'definition': 'http://purl.obolibrary.org/obo/IAO_0000115',
        'editorNote': 'http://purl.obolibrary.org/obo/IAO_0000116',
        'termEditor': 'http://purl.obolibrary.org/obo/IAO_0000117',
        'altTerm': 'http://purl.obolibrary.org/obo/IAO_0000118',
        'defSource': 'http://purl.obolibrary.org/obo/IAO_0000119',
        'termsMerged': 'http://purl.obolibrary.org/obo/IAO_0000227',
        'obsReason': 'http://purl.obolibrary.org/obo/IAO_0000231',
        'curatorNote': 'http://purl.obolibrary.org/obo/IAO_0000232',
        'importedFrom': 'http://purl.obolibrary.org/obo/IAO_0000412',
        'realizedIn': 'http://purl.obolibrary.org/obo/BFO_0000054',
        'realizes': 'http://purl.obolibrary.org/obo/BFO_0000055',
        'partOf': 'http://purl.obolibrary.org/obo/BFO_0000050',
        'hasPart': 'http://purl.obolibrary.org/obo/BFO_0000051',
        # normal
        'ILX': 'http://uri.interlex.org/base/ilx_',
        'ilx': 'http://uri.interlex.org/base/',
        'ilxr': 'http://uri.interlex.org/base/readable/',
        'ilxtr': 'http://uri.interlex.org/tgbugs/uris/readable/',
        'fobo': 'http://uri.interlex.org/fakeobo/uris/obo/',
        'PROTEGE': 'http://protege.stanford.edu/plugins/owl/protege#',
        'ILXREPLACE': 'http://ILXREPLACE.org/',
        'FIXME': 'http://FIXME.org/',
        'NIFTTL': 'http://ontology.neuinfo.org/NIF/ttl/',
        'NIFRET': 'http://ontology.neuinfo.org/NIF/Retired/NIF-Retired.owl#',
        'NLXWIKI': 'http://neurolex.org/wiki/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
        'dctypes': 'http://purl.org/dc/dcmitype/',
        'nsu': 'http://www.FIXME.org/nsupper#',
        'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'ro': 'http://www.obofoundry.org/ro/ro.owl#',
        'skos': 'http://www.w3.org/2004/02/skos/core#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'prov': 'http://www.w3.org/ns/prov#',
        'chebi1': 'http://purl.obolibrary.org/obo/chebi#2',
        'chebi2': 'http://purl.obolibrary.org/obo/chebi#',
        'chebi3': 'http://purl.obolibrary.org/obo/chebi#3',
        # Standard Misc
        'PMID': 'https://www.ncbi.nlm.nih.gov/pubmed/',
        'PMCID': 'https://www.ncbi.nlm.nih.gov/pmc/articles/',
        'UBERON': 'http://purl.obolibrary.org/obo/',
        'NIFSTD': 'http://uri.neuinfo.org/nif/nifstd/',
    }

    def __init__(self):
        self.g = rdflib.Graph()
        self.subject_hash = {}
        self.namespaces = {}
        self.rqname = {}
        self.triple2annotation_bnode = {}
        # self.add_standard_namespaces() # deprecated

    def add_standard_namespaces(self):
        for std_ns in ['skos', 'owl', 'rdf', 'rdfs', 'ILX', 'ilx', 'ilxtr']:
            self.process_namespace(std_ns)

    def qname(self, uri):
        '''Returns qname of uri in rdflib graph while also saving it'''
        prefix, namespace, name = self.g.compute_qname(uri)
        qname = prefix + ':' + name
        self.rqname[qname] = uri
        return qname

    def add_namespace(self, prefix, iri):
        if not self.namespaces.get(prefix):
            ns = rdflib.Namespace(iri)
            self.namespaces[prefix] = ns
            self.g.bind(prefix, iri)
        return rdflib.Namespace(iri)

    def find_prefix(self, uri):
        max_iri_len = 0
        max_prefix = None
        for prefix, iri in self.raw_namespaces.items():
            if iri in uri and max_iri_len < len(iri):
                max_prefix = prefix
                max_iri_len = len(iri)
        if max_prefix:
            return max_prefix
        return None

    def add_class(self, subj, *kwargs):
        if 'http' in subj:
            prefix = self.find_prefix(subj)
            if prefix:
                self.process_namespace(prefix)
            else:
                exit(str(subj)+' has a iri not in namespaces; try using add_namespace')
            _subj = rdflib.URIRef(subj)
            self.g.add((_subj, 'rdf:type', 'owl:Class'))
        else:
            # I want to check if I have prefix and if so add it to my prefixes used
            prefix, info = subj.split(':')
            namespace = self.process_namespace(prefix)
            self.subject_hash[str(namespace)+info] = True # deprecated
            _subj = namespace[info]
            self.add_triple(_subj, 'rdf:type', 'owl:Class')
            return namespace[info] # deprecated


    def add_annotation(self, subj, pred, obj, a_p, a_o):
        bnode = self.triple2annotation_bnode.get((subj, pred, obj))
        if not bnode:
            a_s = rdflib.BNode()
            self.triple2annotation_bnode[(subj, pred, obj)] = a_s
            self.g.add((a_s, rdflib.RDF.type, rdflib.OWL.Axiom))
            self.g.add((a_s, rdflib.OWL.annotatedSource, self.process_object(subj)))
            self.g.add((a_s, rdflib.OWL.annotatedProperty,self.process_object(pred)))
            self.g.add((a_s, rdflib.OWL.annotatedTarget, self.process_object(obj)))
        else:
            a_s = bnode
        self.g.add((a_s, self.process_object(a_p), self.process_object(a_o)))
        return a_s #in case you had more tiples to add

    def add_triple(self, subj, pred, obj):
        if None in [subj, pred, obj]:
            pass
        else:
            _subj = self.process_subject(subj)
            _pred = self.process_predicate(pred)
            _obj = self.process_object(obj)  # in case of type change
            self.g.add((_subj, _pred, _obj))

    def process_namespace(self, prefix):
        if self.namespaces.get(prefix):
            return self.namespaces[prefix]
        iri = self.raw_namespaces.get(prefix)
        if iri:
            return self.add_namespace(prefix, iri)
        else:
            exit('Prefix:'+prefix+' does not exist in raw_namespaces')

    # FIXME: if the iri is full it breaks everything; plus you dont know if you want a Class
    def process_subject(self, subject):
        ''' Default is create a new Class. Might be bad practice, but great for me '''
        if 'http' in subject:
            return rdflib.URIRef(subject)
        if not self.subject_hash.get(subject):
            return self.add_class(subject)
        else:
            exit(str(subj) + 'needs to be a uri or an existing namespace')

    def process_predicate(self, predicate):
        if 'http' in predicate: # might break if random iri; useful for annotations
            prefix = self.find_prefix(predicate)
            if prefix:
                self.process_namespace(predicate)
            else:
                exit(str(predicate)+' has a iri not in namespaces; try using add_namespace')
            return rdflib.URIRef(predicate)
        prefix, info = predicate.split(':')
        namespace = self.process_namespace(prefix)
        if not namespace:
            exit(prefix+':'+info+' not yet in namespaces.')
        return namespace[info]

    def process_object(self, object):
        if 'http' in object: # might break if random iri; useful for annotations
            prefix = self.find_prefix(object)
            if prefix:
                self.process_namespace(prefix)
            else:
                exit(str(object)+' has a iri not in namespaces; try using add_namespace')
            return rdflib.URIRef(object)
        if ':' in object:
            split_obj = object.split(':')
            if 2 < len(split_obj) > 2: # if not prefix:info
                pass
            else:
                prefix, info = split_obj
                namespace = self.process_namespace(prefix)
                if namespace:
                    return namespace[info]
        return rdflib.Literal(object)

    def save_graph(self, output):
        self.g.serialize(destination=output, format='turtle')

    def print_graph(self):
        print(self.g.serialize(format='turtle').decode('utf-8'))

def main():
    g = RDFGraph()
    g.add_class('ILX:12345')
    g.add_annotation('ILX:12345', rdflib.RDF.type, rdflib.OWL.Class,
                     a_p='ilxtr:literatureCitation', a_o='PMID:12345')
    g.print_graph()

if __name__ == '__main__':
    main()
