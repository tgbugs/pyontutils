import rdflib
from ontquery.terms import OntCuries
from pyontutils.closed_namespaces import *  # EVIL but simplifies downstream imports
from pyontutils.curies import PREFIXES, _loadPrefixes, interlex_namespace, getCuries


# note that these will cause problems in SciGraph because I've run out of hacks still no https
DHBA = rdflib.Namespace('http://api.brain-map.org/api/v2/data/Structure/')
DMBA = rdflib.Namespace('http://api.brain-map.org/api/v2/data/Structure/')
AIBSSPEC = rdflib.Namespace('http://api.brain-map.org/api/v2/data/Specimen/')

# interlex namespaces
ilx = rdflib.Namespace(interlex_namespace(''))  # XXX NOTE NOT /base/
lex = rdflib.Namespace(interlex_namespace('base/lexical/'))
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
#PAXMUS = rdflib.Namespace(interlex_namespace('paxinos/uris/mouse/labels/'))
paxmusver = rdflib.Namespace(interlex_namespace('paxinos/uris/mouse/versions/'))
#PAXRAT = rdflib.Namespace(interlex_namespace('paxinos/uris/rat/labels/'))
paxratver = rdflib.Namespace(interlex_namespace('paxinos/uris/rat/versions/'))
WHSSD = rdflib.Namespace(interlex_namespace('waxholm/uris/sd/labels/'))
BERCAT = rdflib.Namespace(interlex_namespace('berman/uris/cat/labels/'))
npokb = rdflib.Namespace(interlex_namespace('npo/uris/neurons/'))

OntCuries({'BERCAT': str(BERCAT),
           'xsd': str(rdflib.XSD),})

# prefixes

def nsExact(namespace, slash=True):
    uri = str(namespace)
    if not slash:
        uri = uri[:-1]
    return rdflib.URIRef(uri)


OntCuries(PREFIXES)  # anything importing this file should see these bindings


def makePrefixes(*prefixes):
    return {k:PREFIXES[k] for k in prefixes}


def makeNamespaces(*prefixes):
    return tuple(rdflib.Namespace(PREFIXES[prefix]) for prefix in prefixes)


def makeURIs(*prefixes):
    return tuple(rdflib.URIRef(PREFIXES[prefix]) for prefix in prefixes)

# namespaces

(HBA, MBA, NCBITaxon, NIFSTD, NIFRID, NIFTTL,
 UBERON, BFO, SO, CL,
 ilxtr, TEMP, TEMPRAW, ILX, PAXRAT, PAXMUS,
 tech,  ilxti, ilxtib, ilxtio,
 apinatomy, elements,
) = makeNamespaces(
    'HBA', 'MBA', 'NCBITaxon', 'NIFSTD', 'NIFRID', 'NIFTTL',
    'UBERON', 'BFO', 'SO', 'CL',
    'ilxtr', 'TEMP', 'TEMPRAW', 'ILX', 'PAXRAT', 'PAXMUS',
    'tech', 'ilxti', 'ilxtib', 'ilxtio',
    'apinatomy', 'elements',
)

ilxb = interlex_namespace('base/')

# development namespaces
prot = rdflib.Namespace(ilxtr[''] + 'protocol/')
proc = rdflib.Namespace(ilxtr[''] + 'process/')  # even though techniques are sco I don't force the tree
asp = rdflib.Namespace(ilxtr[''] + 'aspect/')
dim = rdflib.Namespace(asp[''] + 'dimension/')
unit = rdflib.Namespace(asp[''] + 'unit/')
sparc = rdflib.Namespace(ilxtr[''] + 'sparc/')
build = rdflib.Namespace(ilxtr[''] + 'build/')
buildid = rdflib.Namespace(build[''] + 'id/')

# retired namespaces kept as a record in the even that we need them for some reason
_OLD_HCPMMP = rdflib.Namespace(interlex_namespace('hcpmmp/uris/labels/'))

(replacedBy, definition, hasPart, hasRole, hasParticipant, hasInput, hasOutput,
 realizes, partOf, participatesIn, locatedIn, isAbout, editorNote,
 ilx_includesTerm, ilx_includesTermSet, ilx_partOf,
) = makeURIs('replacedBy', 'definition', 'hasPart', 'hasRole', 'hasParticipant',
             'hasInput', 'hasOutput', 'realizes', 'partOf', 'participatesIn',
             'locatedIn', 'isAbout', 'editorNote',
             'ilx.includesTerm', 'ilx.includesTermSet', 'ilx.partOf',
            )
