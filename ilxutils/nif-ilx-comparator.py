import json
import pickle
import pandas as pd
import numpy as np
from pyontutils.utils import *
from pyontutils.core import *
import rdflib
from collections import defaultdict
import subprocess as sb

'''Saved Ram'''
iri_to_family_iris = json.load(open('/Users/tmsincomb/Desktop/interlexutils/ontology-interlex/dump/iri-to-family.json','r'))
iri_to_ilx = json.load(open('/Users/tmsincomb/Desktop/interlexutils/ontology-interlex/dump/iri-to-ilx.json','r'))

g_ilx = makeGraph('', graph=rdflib.Graph().parse('../Interlex.ttl', format='turtle'))
g_qnames_purpose_only = makeGraph('', graph=rdflib.Graph().parse('../Interlex_qnames.ttl', format='turtle'))
g_nif = makeGraph('', graph=pickle.load(open('../NIF-ALL.pickle', 'rb')))

qilx = g_ilx.qname
qnif = g_nif.qname
qall = g_qnames_purpose_only.qname

edge_cases = {
    #Definitions
    'definition:' : 'definition:',
    'skos:definitions' : 'definition:',
    'definition' : 'definition:',

    #ExistingIds
    'ilxtr:existingIds' : 'ilxtr:existingIds',
    #LABELS
    'rdfs:label' : 'rdfs:label',
    #SUPERCLASSES
    'rdfs:subClassOf' : 'rdfs:subClassOf',
    #SYNONYMS
    'oboInOwl:hasExactSynonym' : 'NIFRID:synonym',
    'oboInOwl:hasNarrowSynonym' : 'NIFRID:synonym',
    'oboInOwl:hasBroadSynonym' : 'NIFRID:synonym',
    'oboInOwl:hasRelatedSynonym' : 'NIFRID:synonym',
    'go:systematic_synonym' : 'NIFRID:synonym',
    'NIFRID:synonym' : 'NIFRID:synonym',
    #TYPE
    'rdf:type':'rdf:type',
}

full = {
    #'':None,  # safety (now managed directly in the curies file)
    #'EHDAA2':'http://purl.obolibrary.org/obo/EHDAA2_',  # FIXME needs to go in curie map?

    'hasRole':'http://purl.obolibrary.org/obo/RO_0000087',
    'inheresIn':'http://purl.obolibrary.org/obo/RO_0000052',
    'bearerOf':'http://purl.obolibrary.org/obo/RO_0000053',
    'participatesIn':'http://purl.obolibrary.org/obo/RO_0000056',
    'hasParticipant':'http://purl.obolibrary.org/obo/RO_0000057',
    'adjacentTo':'http://purl.obolibrary.org/obo/RO_0002220',
    'derivesFrom':'http://purl.obolibrary.org/obo/RO_0001000',
    'derivesInto':'http://purl.obolibrary.org/obo/RO_0001001',
    'agentIn':'http://purl.obolibrary.org/obo/RO_0002217',
    'hasAgent':'http://purl.obolibrary.org/obo/RO_0002218',
    'containedIn':'http://purl.obolibrary.org/obo/RO_0001018',
    'contains':'http://purl.obolibrary.org/obo/RO_0001019',
    'locatedIn':'http://purl.obolibrary.org/obo/RO_0001025',
    'locationOf':'http://purl.obolibrary.org/obo/RO_0001015',
    'toward':'http://purl.obolibrary.org/obo/RO_0002503',

    'replacedBy':'http://purl.obolibrary.org/obo/IAO_0100001',
    'hasCurStatus':'http://purl.obolibrary.org/obo/IAO_0000114',
    'definition':'http://purl.obolibrary.org/obo/IAO_0000115',
    'editorNote':'http://purl.obolibrary.org/obo/IAO_0000116',
    'termEditor':'http://purl.obolibrary.org/obo/IAO_0000117',
    'altTerm':'http://purl.obolibrary.org/obo/IAO_0000118',
    'defSource':'http://purl.obolibrary.org/obo/IAO_0000119',
    'termsMerged':'http://purl.obolibrary.org/obo/IAO_0000227',
    'obsReason':'http://purl.obolibrary.org/obo/IAO_0000231',
    'curatorNote':'http://purl.obolibrary.org/obo/IAO_0000232',
    'importedFrom':'http://purl.obolibrary.org/obo/IAO_0000412',

    'partOf':'http://purl.obolibrary.org/obo/BFO_0000050',
    'hasPart':'http://purl.obolibrary.org/obo/BFO_0000051',
}

normal = {
    'ILX':'http://uri.interlex.org/base/ilx_',
    'ilx':'http://uri.interlex.org/base/',
    'ilxr':'http://uri.interlex.org/base/readable/',
    'ilxtr':'http://uri.interlex.org/tgbugs/uris/readable/',
    # for obo files with 'fake' namespaces, http://uri.interlex.org/fakeobo/uris/ eqiv to purl.obolibrary.org/
    'fobo':'http://uri.interlex.org/fakeobo/uris/obo/',

    'PROTEGE':'http://protege.stanford.edu/plugins/owl/protege#',
    'ILXREPLACE':'http://ILXREPLACE.org/',
    'TEMP': interlex_namespace('temp/uris'),
    'FIXME':'http://FIXME.org/',
    'NIFTTL':'http://ontology.neuinfo.org/NIF/ttl/',
    'NIFRET':'http://ontology.neuinfo.org/NIF/Retired/NIF-Retired.owl#',
    'NLXWIKI':'http://neurolex.org/wiki/',
    'dc':'http://purl.org/dc/elements/1.1/',
    'dcterms':'http://purl.org/dc/terms/',
    'dctypes':'http://purl.org/dc/dcmitype/',  # FIXME there is no agreement on qnames
    # FIXME a thought: was # intentionally used to increase user privacy? or is this just happenstance?
    'nsu':'http://www.FIXME.org/nsupper#',
    'oboInOwl':'http://www.geneontology.org/formats/oboInOwl#',
    'owl':'http://www.w3.org/2002/07/owl#',
    'ro':'http://www.obofoundry.org/ro/ro.owl#',
    'skos':'http://www.w3.org/2004/02/skos/core#',
    'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
    'prov':'http://www.w3.org/ns/prov#',
}

expo = {
    'ilxtr:existingId' : 'ilxtr:identifier',
    'oboInOwl:hasAlternativeId':'ilxtr:identifier',
    'NIFRID:isReplacedByClass':'replacedBy:',
    'skos:editorialNote' : 'editorNote:',
    'ncbitaxon:has_rank' : 'NIFRID:hasTaxonRank',
}
#Maybe a 5th category which is "labels/synonyms with parens in them"
#would be a way to see whether that is a good filter would help too.

extras = {**full, **normal}
edge_cases = {**{qall(v)+':':k for k,v in extras.items()}, **edge_cases, **expo}

def modify_namespaces():
    """ Delete all Defaults """
    ns_to_del = []
    for namespace in g_nif.namespaces:
        if 'default' in namespace.split(':')[0]:
            ns_to_del.append(namespace)
    for ns in ns_to_del:
        g_nif.del_namespace(ns)

    """ Create new namespaces; old are messed up """
    for s, ns in g_nif.namespaces.items():
        g_nif.del_namespace(s)
        g_nif.add_namespace(s, rdflib.Namespace(str(ns)))

    """ Reset blasted cache """
    for _ in range(10):
        g_nif.g.namespace_manager.reset()

    """ Fill ilx qname to fix the existing ids """
    for s, ns in g_nif.namespaces.items():
        if not g_qnames_purpose_only.namespaces.get(s):
            g_qnames_purpose_only.add_namespace(s, rdflib.Namespace(str(ns)))

def main():

    modify_namespaces()

    interlex_with_mods = defaultdict(set)
    nif_with_mods = defaultdict(set)
    data = defaultdict(dict)

    for subj in g_ilx.g.subjects(rdflib.RDF.type, rdflib.OWL.Class):

        #if qilx(subj) != 'ILX:0105215': continue

        shared_iris = set()
        ilx_mod_conversion = {}
        nif_mod_conversion = {}

        for pred, obj in g_ilx.g.predicate_objects(subject=subj):

            '''Needs traversal convert superclass ilx to its respected exisiting ids'''
            if qilx(pred) == 'rdfs:subClassOf':
                superclasses_iris = iri_to_family_iris[str(obj)]
                for superclasses_iri in superclasses_iris:
                    tup = (qilx(pred), ' '.join(superclasses_iri.lower().strip().split()))
                    ilx_mod_conversion[tup] = (qilx(pred), superclasses_iri)
                    interlex_with_mods[qilx(subj)].add(tup)
            else:
                tup = (qilx(pred), ' '.join(str(obj).lower().strip().split()))
                ilx_mod_conversion[tup] = (qilx(pred), str(obj))
                interlex_with_mods[qilx(subj)].add(tup)

            '''Build nif when ilx exisiting id found in nif'''
            if qilx(pred) == 'ilxtr:existingIds':
                for p, o in g_nif.g.predicate_objects(subject=obj):
                    shared_iris.add(obj)
                    tup = (qnif(p), ' '.join(str(o).lower().strip().split()))
                    if edge_cases.get(qnif(p)):
                        nif_with_mods[qnif(obj)].add((edge_cases[tup[0]], tup[1]))
                        nif_mod_conversion[(edge_cases[tup[0]], tup[1])] = (qnif(p), str(o))
                    else:
                        nif_with_mods[qnif(obj)].add(tup)
                        nif_mod_conversion[tup] = (qnif(p), str(o))

        '''Comparator btw current ilx term and each nif term sharing ilx existing id'''
        for shared_iri in shared_iris:
            #print(shared_iris)
            nif = nif_with_mods[qnif(shared_iri)]
            ilx = interlex_with_mods[qilx(subj)]

            i = ilx - nif
            n = nif - ilx
            b = nif & ilx

            def formatter(current_set, mod_conversion):
                return sorted([(p,qall(o)) for p,o in [mod_conversion[po] for po in current_set]])

            data[qall(subj)].update({
                qall(shared_iri): {
                    'ilx_only'     : formatter(i, ilx_mod_conversion),
                    'nif_only'     : formatter(n, nif_mod_conversion),
                    'both_contain' : formatter(b, nif_mod_conversion),
                }
            })

            #if debug:
            #    pass

    outf = '/Users/tmsincomb/Desktop/interlexutils/ontology-interlex/dump/moderate-nif-ilx-comparator-extras.json'
    with open(outf, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    #ex for short hand vi -e
    #-s so it doesnt print file details
    #-cwq is command-save-quit
    #use $ to specify variable
    #!ex -s +'g/\[[\ \n]\+"/j4' -cwq $outf
    sb.call("ex -s +'g/\[[\ \n]\+\"/j4' -cwq "+outf, shell=True) #FIXME

if __name__ == '__main__':
    main()
