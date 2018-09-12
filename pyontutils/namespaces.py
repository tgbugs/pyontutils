import yaml
import rdflib
import requests
from pyontutils.config import devconfig

# prefixes

def interlex_namespace(user):
    return 'http://uri.interlex.org/' + user

def nsExact(namespace, slash=True):
    uri = str(namespace)
    if not slash:
        uri = uri[:-1]
    return rdflib.URIRef(uri)

def _loadPrefixes():
    try:
        with open(devconfig.curies, 'rt') as f:
            curie_map = yaml.load(f)
    except FileNotFoundError:
        master_blob = 'https://github.com/tgbugs/pyontutils/blob/master/'
        raw_path = 'scigraph/nifstd_curie_map.yaml?raw=true'
        curie_map = requests.get(master_blob + raw_path)
        curie_map = yaml.load(curie_map.text)

    # holding place for values that are not in the curie map
    full = {
        # interlex predicates  PROVISIONAL
        'ilx.federatesElement':'http://uri.interlex.org/base/ilx_0381445',
        'ilx.isMeasureOf':'http://uri.interlex.org/base/ilx_0381389',
        'ilx.hasMeasurementType':'http://uri.interlex.org/base/ilx_0381388',
        'ilx.hasUnit':'http://uri.interlex.org/base/ilx_0381384',
        'ilx.isAbout':'http://uri.interlex.org/base/ilx_0381385',  # should probalby map to iao
        'ilx.hasLaterality':'http://uri.interlex.org/base/ilx_0381387',  # FIXME being treated data property

        #'':None,  # safety (now managed directly in the curies file)
        #'EHDAA2':'http://purl.obolibrary.org/obo/EHDAA2_',  # FIXME needs to go in curie map?

        # RO predicates
        'hasRole':'http://purl.obolibrary.org/obo/RO_0000087',
        'inheresIn':'http://purl.obolibrary.org/obo/RO_0000052',
        'bearerOf':'http://purl.obolibrary.org/obo/RO_0000053',
        'participatesIn':'http://purl.obolibrary.org/obo/RO_0000056',
        'hasParticipant':'http://purl.obolibrary.org/obo/RO_0000057',
        'hasInput':'http://purl.obolibrary.org/obo/RO_0002233',
        'hasOutput':'http://purl.obolibrary.org/obo/RO_0002234',
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

        # realizes the proper way to connect a process to a continuant
        'realizedIn':'http://purl.obolibrary.org/obo/BFO_0000054',
        'realizes':'http://purl.obolibrary.org/obo/BFO_0000055',

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
        'TEMP': interlex_namespace('temp/uris/'),
        'FIXME':'http://FIXME.org/',
        'NIFRAW':'https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/',
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
        'foaf':'http://xmlns.com/foaf/0.1/',
        'prov':'http://www.w3.org/ns/prov#',

        # defined by chebi.owl, confusingly chebi#2 -> chebi1 maybe an error?
        # better to keep it consistent in case someone tries to copy and paste
        'chebi1':'http://purl.obolibrary.org/obo/chebi#2',
        'chebi2':'http://purl.obolibrary.org/obo/chebi#',
        'chebi3':'http://purl.obolibrary.org/obo/chebi#3',
        'JAX':'http://jaxmice.jax.org/strain/',
    }
    #extras = {**{k:rdflib.URIRef(v) for k, v in full.items()}, **normal}
    extras = {**full, **normal}
    curie_map.update(extras)
    return curie_map

PREFIXES = _loadPrefixes()

def makePrefixes(*prefixes):
    return {k:PREFIXES[k] for k in prefixes}

def makeNamespaces(*prefixes):
    return tuple(rdflib.Namespace(PREFIXES[prefix]) for prefix in prefixes)

def makeURIs(*prefixes):
    return tuple(rdflib.URIRef(PREFIXES[prefix]) for prefix in prefixes)

# namespaces

(HBA, MBA, NCBITaxon, NIFSTD, NIFRID, NIFTTL, UBERON, BFO, ilxtr,
 ilxb, TEMP, ILX) = makeNamespaces('HBA', 'MBA', 'NCBITaxon', 'NIFSTD', 'NIFRID',
                    'NIFTTL', 'UBERON', 'BFO', 'ilxtr', 'ilx', 'TEMP', 'ILX')

# note that these will cause problems in SciGraph because I've run out of hacks still no https
DHBA = rdflib.Namespace('http://api.brain-map.org/api/v2/data/Structure/')
DMBA = rdflib.Namespace('http://api.brain-map.org/api/v2/data/Structure/')

# interlex namespaces
ilx = rdflib.Namespace(interlex_namespace(''))  # XXX NOTE NOT /base/
AIBS = rdflib.Namespace(interlex_namespace('aibs/uris/'))
ilxHBA = rdflib.Namespace(interlex_namespace('aibs/uris/human/labels/'))
ilxMBA = rdflib.Namespace(interlex_namespace('aibs/uris/mouse/labels/'))
ilxDHBA = rdflib.Namespace(interlex_namespace('aibs/uris/human/devel/labels/'))
ilxDMBA = rdflib.Namespace(interlex_namespace('aibs/uris/mouse/devel/labels/'))
FSLATS = rdflib.Namespace(interlex_namespace('fsl/uris/atlases/'))
HCPMMP = rdflib.Namespace(interlex_namespace('hcp/uris/mmp/labels/'))
DKT = rdflib.Namespace(interlex_namespace('mindboggle/uris/dkt/'))
DKTr = rdflib.Namespace(interlex_namespace('mindboggle/uris/dkt/region/labels/'))
DKTs = rdflib.Namespace(interlex_namespace('mindboggle/uris/dkt/sulcus/labels/'))
FSCL = rdflib.Namespace(interlex_namespace('freesurfer/uris/FreeSurferColorLUT/labels/'))
MNDBGL = rdflib.Namespace(interlex_namespace('mindboggle/uris/mndbgl/labels/'))
PAXMUS = rdflib.Namespace(interlex_namespace('paxinos/uris/mouse/labels/'))
paxmusver = rdflib.Namespace(interlex_namespace('paxinos/uris/mouse/versions/'))
PAXRAT = rdflib.Namespace(interlex_namespace('paxinos/uris/rat/labels/'))
paxratver = rdflib.Namespace(interlex_namespace('paxinos/uris/rat/versions/'))
WHSSD = rdflib.Namespace(interlex_namespace('waxholm/uris/sd/labels/'))

# retired namespaces kept as a record in the even that we need them for some reason
_OLD_HCPMMP = rdflib.Namespace(interlex_namespace('hcpmmp/uris/labels/'))

(replacedBy, definition, hasPart, hasRole, hasParticipant, hasInput, hasOutput,
 realizes, partOf, participatesIn, locatedIn,
) = makeURIs('replacedBy', 'definition', 'hasPart', 'hasRole', 'hasParticipant',
             'hasInput', 'hasOutput', 'realizes', 'partOf', 'participatesIn',
             'locatedIn',
            )

