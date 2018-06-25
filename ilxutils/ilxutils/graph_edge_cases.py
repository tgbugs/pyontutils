from pyontutils.utils import *
from pyontutils.core import *
from pyontutils.closed_namespaces import *

edge_cases = {
    #Definitions
    'definition:': 'definition:',
    'skos:definition': 'definition:',
    'definition': 'definition:',
    'NIFRID:birnlexDefinition': 'definition:',
    'NIFRID:externallySourcedDefinition': 'definition:',
    #ExistingIds
    'ilxtr:existingIds': 'ilxtr:existingIds',
    #LABELS
    'rdfs:label': 'rdfs:label',
    'skos:prefLabel': 'rdfs:label',
    #SUPERCLASSES
    'rdfs:subClassOf': 'rdfs:subClassOf',
    #SYNONYMS
    'oboInOwl:hasExactSynonym': 'NIFRID:synonym',
    #'oboInOwl:hasNarrowSynonym' : 'NIFRID:synonym',
    #'oboInOwl:hasBroadSynonym' : 'NIFRID:synonym',
    'oboInOwl:hasRelatedSynonym': 'NIFRID:synonym',
    'go:systematic_synonym': 'NIFRID:synonym',
    'NIFRID:synonym': 'NIFRID:synonym',
    #TYPE
    'rdf:type': 'rdf:type',
}

full = {
    #'':None,  # safety (now managed directly in the curies file)
    #'EHDAA2':'http://purl.obolibrary.org/obo/EHDAA2_',  # FIXME needs to go in curie map?
    'hasRole': 'http://purl.obolibrary.org/obo/RO_0000087',
    'inheresIn': 'http://purl.obolibrary.org/obo/RO_0000052',
    'bearerOf': 'http://purl.obolibrary.org/obo/RO_0000053',
    'participatesIn': 'http://purl.obolibrary.org/obo/RO_0000056',
    'hasParticipant': 'http://purl.obolibrary.org/obo/RO_0000057',
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
    'partOf': 'http://purl.obolibrary.org/obo/BFO_0000050',
    'hasPart': 'http://purl.obolibrary.org/obo/BFO_0000051',
}

normal = {
    'ILX': 'http://uri.interlex.org/base/ilx_',
    'ilx': 'http://uri.interlex.org/base/',
    'ilxr': 'http://uri.interlex.org/base/readable/',
    'ilxtr': 'http://uri.interlex.org/tgbugs/uris/readable/',
    # for obo files with 'fake' namespaces, http://uri.interlex.org/fakeobo/uris/ eqiv to purl.obolibrary.org/
    'fobo': 'http://uri.interlex.org/fakeobo/uris/obo/',
    'PROTEGE': 'http://protege.stanford.edu/plugins/owl/protege#',
    'ILXREPLACE': 'http://ILXREPLACE.org/',
    'TEMP': interlex_namespace('temp/uris'),
    'FIXME': 'http://FIXME.org/',
    'NIFTTL': 'http://ontology.neuinfo.org/NIF/ttl/',
    'NIFRET': 'http://ontology.neuinfo.org/NIF/Retired/NIF-Retired.owl#',
    'NLXWIKI': 'http://neurolex.org/wiki/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'dctypes':
    'http://purl.org/dc/dcmitype/',  # FIXME there is no agreement on qnames
    # FIXME a thought: was # intentionally used to increase user privacy? or is this just happenstance?
    'nsu': 'http://www.FIXME.org/nsupper#',
    'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'ro': 'http://www.obofoundry.org/ro/ro.owl#',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'prov': 'http://www.w3.org/ns/prov#',
}

expo = {
    'ilxtr:existingId': 'ilxtr:identifier',
    'oboInOwl:hasAlternativeId': 'ilxtr:identifier',
    'NIFRID:isReplacedByClass': 'replacedBy:',
    'skos:editorialNote': 'editorNote:',
    'ncbitaxon:has_rank': 'NIFRID:hasTaxonRank',
}
