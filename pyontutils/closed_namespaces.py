#!/usr/bin/env python3

from rdflib import Graph, URIRef
from rdflib.plugin import PluginException
from rdflib.namespace import ClosedNamespace

__all__ = [
    'dc',
    'dcterms',
    'oboInOwl',
    'owl',
    'skos',
]

###

dc = ClosedNamespace(
    uri=URIRef('http://purl.org/dc/elements/1.1/'),
    terms=['contributor',
           'coverage',
           'creator',
           'date',
           'description',
           'format',
           'identifier',
           'language',
           'publisher',
           'relation',
           'rights',
           'source',
           'subject',
           'title',
           'type']
)

dcterms = ClosedNamespace(
    uri=URIRef('http://purl.org/dc/terms/'),
    terms=['Agent',
           'AgentClass',
           'BibliographicResource',
           'Box',
           'DCMIType',
           'DDC',
           'FileFormat',
           'Frequency',
           'IMT',
           'ISO3166',
           'ISO639-2',
           'ISO639-3',
           'Jurisdiction',
           'LCC',
           'LCSH',
           'LicenseDocument',
           'LinguisticSystem',
           'Location',
           'LocationPeriodOrJurisdiction',
           'MESH',
           'MediaType',
           'MediaTypeOrExtent',
           'MethodOfAccrual',
           'MethodOfInstruction',
           'NLM',
           'Period',
           'PeriodOfTime',
           'PhysicalMedium',
           'PhysicalResource',
           'Point',
           'Policy',
           'ProvenanceStatement',
           'RFC1766',
           'RFC3066',
           'RFC4646',
           'RFC5646',
           'RightsStatement',
           'SizeOrDuration',
           'Standard',
           'TGN',
           'UDC',
           'URI',
           'W3CDTF',
           'abstract',
           'accessRights',
           'accrualMethod',
           'accrualPeriodicity',
           'accrualPolicy',
           'alternative',
           'audience',
           'available',
           'bibliographicCitation',
           'conformsTo',
           'contributor',
           'coverage',
           'created',
           'creator',
           'date',
           'dateAccepted',
           'dateCopyrighted',
           'dateSubmitted',
           'description',
           'educationLevel',
           'extent',
           'format',
           'hasFormat',
           'hasPart',
           'hasVersion',
           'identifier',
           'instructionalMethod',
           'isFormatOf',
           'isPartOf',
           'isReferencedBy',
           'isReplacedBy',
           'isRequiredBy',
           'isVersionOf',
           'issued',
           'language',
           'license',
           'mediator',
           'medium',
           'modified',
           'provenance',
           'publisher',
           'references',
           'relation',
           'replaces',
           'requires',
           'rights',
           'rightsHolder',
           'source',
           'spatial',
           'subject',
           'tableOfContents',
           'temporal',
           'title',
           'type',
           'valid']
)

oboInOwl = ClosedNamespace(
    uri=URIRef('http://www.geneontology.org/formats/oboInOwl#'),
    terms=['DbXref',
           'Definition',
           'ObsoleteClass',
           'ObsoleteProperty',
           'Subset',
           'SubsetProperty',
           'Synonym',
           'SynonymType',
           'SynonymTypeProperty',
           'consider',
           'hasAlternativeId',
           'hasBroadSynonym',
           'hasDate',
           'hasDbXref',
           'hasDefaultNamespace',
           'hasDefinition',
           'hasExactSynonym',
           'hasNarrowSynonym',
           'hasOBONamespace',
           'hasRelatedSynonym',
           'hasSubset',
           'hasSynonym',
           'hasSynonymType',
           'hasURI',
           'hasVersion',
           'inSubset',
           'isCyclic',
           'replacedBy',
           'savedBy']
)

owl = ClosedNamespace(
    uri=URIRef('http://www.w3.org/2002/07/owl#'),
    terms=['AllDifferent',
           'AllDisjointClasses',
           'AllDisjointProperties',
           'Annotation',
           'AnnotationProperty',
           'AsymmetricProperty',
           'Axiom',
           'Class',
           'DataRange',
           'DatatypeProperty',
           'DeprecatedClass',
           'DeprecatedProperty',
           'FunctionalProperty',
           'InverseFunctionalProperty',
           'IrreflexiveProperty',
           'NamedIndividual',
           'NegativePropertyAssertion',
           'Nothing',
           'ObjectProperty',
           'Ontology',
           'OntologyProperty',
           'ReflexiveProperty',
           'Restriction',
           'SymmetricProperty',
           'Thing',
           'TransitiveProperty',
           'allValuesFrom',
           'annotatedProperty',
           'annotatedSource',
           'annotatedTarget',
           'assertionProperty',
           'backwardCompatibleWith',
           'bottomDataProperty',
           'bottomObjectProperty',
           'cardinality',
           'complementOf',
           'datatypeComplementOf',
           'deprecated',
           'differentFrom',
           'disjointUnionOf',
           'disjointWith',
           'distinctMembers',
           'equivalentClass',
           'equivalentProperty',
           'hasKey',
           'hasSelf',
           'hasValue',
           'imports',
           'incompatibleWith',
           'intersectionOf',
           'inverseOf',
           'maxCardinality',
           'maxQualifiedCardinality',
           'members',
           'minCardinality',
           'minQualifiedCardinality',
           'onClass',
           'onDataRange',
           'onDatatype',
           'onProperties',
           'onProperty',
           'oneOf',
           'priorVersion',
           'propertyChainAxiom',
           'propertyDisjointWith',
           'qualifiedCardinality',
           'sameAs',
           'someValuesFrom',
           'sourceIndividual',
           'targetIndividual',
           'targetValue',
           'topDataProperty',
           'topObjectProperty',
           'unionOf',
           'versionIRI',
           'versionInfo',
           'withRestrictions']
)

skos = ClosedNamespace(
    uri=URIRef('http://www.w3.org/2004/02/skos/core#'),
    terms=['Collection',
           'Concept',
           'ConceptScheme',
           'OrderedCollection',
           'altLabel',
           'broadMatch',
           'broader',
           'broaderTransitive',
           'changeNote',
           'closeMatch',
           'definition',
           'editorialNote',
           'exactMatch',
           'example',
           'hasTopConcept',
           'hiddenLabel',
           'historyNote',
           'inScheme',
           'mappingRelation',
           'member',
           'memberList',
           'narrowMatch',
           'narrower',
           'narrowerTransitive',
           'notation',
           'note',
           'prefLabel',
           'related',
           'relatedMatch',
           'scopeNote',
           'semanticRelation',
           'topConceptOf']
)

###

def main():
    # use to populate terms
    uris = {
        'oboInOwl':'http://www.geneontology.org/formats/oboInOwl#',
        'owl':'http://www.w3.org/2002/07/owl#',
        'skos':'http://www.w3.org/2004/02/skos/core#',
        'dc':'http://purl.org/dc/elements/1.1/',
        'dcterms':'http://purl.org/dc/terms/',
    }
    tw = 4
    tab = ' ' * tw
    ind = ' ' * (tw + len('terms=['))
    functions = ''
    for name, uri in sorted(uris.items()):
        try:
            g = Graph().parse(uri.rstrip('#'))
        except PluginException:
            g = Graph().parse(uri.rstrip('#') + '.owl')
        sep = uri[-1]
        globals().update(locals())
        terms = sorted(set(s.rsplit(sep, 1)[-1]
                           for s in g.subjects()
                           if uri in s and uri != s.toPython() and sep in s))
        block = ('\n'
                 '{name} = ClosedNamespace(\n'
                 "{tab}uri=URIRef('{uri}'),\n"
                 '{tab}' + "terms=['{t}',\n".format(t=terms[0]) + ''
                 '{ind}' + ',\n{ind}'.join("'{t}'".format(t=t)  # watch out for order of operations issues
                                           for t in terms[1:]) + ']\n'
                 ')\n')
        function = block.format(name=name,
                                uri=uri,
                                tab=tab,
                                ind=ind)
        functions += function

    functions += '\n'

    with open(__file__, 'rt') as f:
        text = f.read()

    sep = '###\n'
    start, mid, end = text.split(sep)
    code = sep.join((start, functions, end))
    with open(__file__, 'wt') as f:
        f.write(code)

if __name__ == '__main__':
    main()
