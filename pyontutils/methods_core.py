import rdflib
from pyontutils.core import OntId, OntCuries
from pyontutils.core import simpleOnt, oc, oc_, odp, oop, olit, oec, olist
from pyontutils.core import restrictions
from pyontutils.core import NIFTTL, NIFRID, ilxtr, BFO
from pyontutils.core import definition, hasRole, hasParticipant, hasPart, hasInput, hasOutput
from pyontutils.core import owl, rdf, rdfs

prot = rdflib.Namespace(ilxtr[''] + 'protocol/')
tech = rdflib.Namespace(ilxtr[''] + 'technique/')
asp = rdflib.Namespace(ilxtr[''] + 'aspect/')

filename = 'methods-core'
prefixes = ('BFO', 'ilxtr', 'NIFRID', 'RO', 'IAO', 'definition', 'hasParticipant')
OntCuries['HBP_MEM'] = 'http://www.hbp.FIXME.org/hbp_measurement_methods/'
imports = NIFTTL['nif_backend.ttl'],
comment = 'The core components for modelling techniques and methods.'
_repo = True
debug = True

triples = (
    # object properties
    oop(ilxtr.hasOperationDefinition),
    oop(ilxtr.hasDefiningProtocol, ilxtr.hasOperationDefinition),

    oop(ilxtr.hasExecutor, hasParticipant),
    olit(ilxtr.hasExecutor, rdfs.label, 'has executor'),
    olit(ilxtr.hasExecutor, NIFRID.synonym, 'has executing agent'),
    olit(ilxtr.hasExecutor, definition,
         'The relationship between a technique and a thing that executes it.'),
    olit(ilxtr.hasExecutor, rdfs.comment,
         ('For example, a scientific protocol hasExecutor some graduateStudent.'
          'A case like some parallelProcess hasExecutor personA, personB suggests'
          'that the technique is a composite technique and should be broken down.'
          'We may ultimately add a cardinality restriction to enforce this and require'
          'composite techniques to be modelled using hasPart or hasInputFromPart,'
          'but this is too complex to model in owl directly.')),

    oop(ilxtr.wasDiscoveredBy),
    olit(ilxtr.wasDiscoveredBy, rdfs.label, 'was discovered by'),
    olit(ilxtr.wasDiscoveredBy, NIFRID.synonym, 'was invented by'),
    olit(ilxtr.wasDiscoveredBy, definition,
         'The relationship between a process and the person who discovered it.'),

    oop(ilxtr.hasInformationParticipant),
    olit(ilxtr.hasInformationParticipant, rdfs.label, 'has information participant'),
    olit(ilxtr.hasInformationParticipant, NIFRID.synonym,
         'has symbolic participant'),
    olit(ilxtr.hasInformationParticipant, definition,
         ('The relationship between a process and some information that participates in it. '
          'When this this points to a real thing it is interpreted to mean the information'
          'content of the artifact, not the artifact itself.')),
    olit(ilxtr.hasInformationParticipant, rdfs.comment,
         ('This is distinct from RO:0000057 in that we are using RO:0000057 explicitly for '
          'real things in the world. Information must be symbolized by something in the world '
          'but it is not the scratches on the paper that constrain a process, it is their implication.')),

    oop(ilxtr.hasInformationInput, ilxtr.hasInformationParticipant),
    (ilxtr.hasInformationInput, owl.disjointWith, ilxtr.isConstrainedBy),
    olit(ilxtr.hasInformationInput, rdfs.label, 'has information input'),
    olit(ilxtr.hasInformationInput, NIFRID.synonym,
         'has non-constraining information input',
         'has execution time information input',
         'has symbolic input'),
    olit(ilxtr.hasInformationInput, definition,
         'The relationship between a process and information that is an input to the process.'),
    olit(ilxtr.hasInformationInput, rdfs.comment,
         ('This can be though of as the known variables of a process, or the runtime information '
          'that cannot be known prior to process execution.')),

    oop(ilxtr.isConstrainedBy, ilxtr.hasInformationParticipant),
    olit(ilxtr.isConstrainedBy, rdfs.label, 'is constrained by'),
    olit(ilxtr.isConstrainedBy, NIFRID.synonym,
         'has information constraint',
         'has symbolic constraint'),
    olit(ilxtr.isConstrainedBy, definition,
         ('The relationship between a process and prior information that constrains it. '
          'For example the code that is compiled to create a piece of analysis software.')),
    olit(ilxtr.isConstrainedBy, rdfs.comment,
         ('These look like free variables inside a process.\n'
          '(define (my-process free-variables)\n'
          '  (define (execute-process inputs)\n'
          '    (combine free-varibles inputs))\n'
          '  execute-process)')),

    #oop(ilxtr.usedInField),  # FIXME molecular techniques...

    oop(ilxtr.hasInformationOutput, ilxtr.hasInformationParticipant),
    olit(ilxtr.hasInformationOutput, rdfs.label, 'has information output'),
    olit(ilxtr.hasInformationOutput, NIFRID.synonym, 'has symbolic output'),

    ## participants
    oop(hasParticipant),
    olit(hasParticipant, rdfs.label, 'has participant'),
    olit(hasParticipant, NIFRID.synonym, 'has physical participant'),
    oop(hasInput),  # XXX
    olit(hasInput, rdfs.label, 'has input'),  # XXX
    oop(hasOutput),  # XXX
    olit(hasOutput, rdfs.label, 'has output'),  # XXX

    # FIXME need a domain restriction to prevent accidental use with aspects!
    # very easy to confuse photons and NMR as both being 'phenomena'
    # NMR is something we can measure about a real system, but it is not the system
    # in the same way that photons are
    oop(ilxtr.detects, hasParticipant),
    olit(ilxtr.detects, rdfs.label, 'detects'),
    olit(ilxtr.detects, NIFRID.synonym, 'has detected phenomena'),
    olit(ilxtr.detects, definition,
         'The relationship between a technique and the phenomena that it detects.'),

    oop(ilxtr.hasProbe, hasParticipant),
    olit(ilxtr.hasProbe, rdfs.label, 'has probing phenomena'),
    olit(ilxtr.hasProbe, NIFRID.synonym, 'has probe'),
    olit(ilxtr.hasProbe, definition,
         ('The relationship between a technique and the phenomena that it uses to probe other participants. '
          'Useful for cases where the probing phenomena is different than the detected phenomena.')),

    oop(ilxtr.hasPrimaryParticipant, hasParticipant),
    olit(ilxtr.hasPrimaryParticipant, rdfs.label, 'has primary participant'),
    olit(ilxtr.hasPrimaryParticipant, definition, 'The relationship between a process and its primary participant.'),
    olit(ilxtr.hasPrimaryParticipant, rdfs.comment,
         'This property should be used to mark the key input and/or output of a process if its type is not generic.'),

    oop(ilxtr.primaryParticipantIn),
    olit(ilxtr.primaryParticipantIn, rdfs.label, 'primary participant in'),
    (ilxtr.primaryParticipantIn, owl.inverseOf, ilxtr.hasPrimaryParticipant),


    ## intentions
    oop(ilxtr.hasIntention),  # not really sco realizes:? it also includes intended changes in qualities?
    olit(ilxtr.hasIntention, rdfs.label, 'has intention'),
    olit(ilxtr.hasIntention, definition, 'The relationship between a process and an intended outcome.'),
    olit(ilxtr.hasIntention, rdfs.comment, 'Should rarely be used directly.'),

    # while these exist in principle there is no meaningful way to bind them to a specific
    #  participant without a qualifier, therefore we are leaving them out
    # oop(ilxtr.hasParticipantIntentionAspect, ilxtr.intention),
    # oop(ilxtr.hasPrimaryParticipantIntentionAspect, ilxtr.hasParticipantIntentionAspect),
    # oop(ilxtr.hasPrimaryParticipantIntentionPrimaryAspect, ilxtr.hasPrimaryParticipantIntentionAspect),

    oop(ilxtr.hasConstrainingAspect, ilxtr.TODO),  # TODO
    olit(ilxtr.hasConstrainingAspect, rdfs.label, 'has constraining aspect'),
    olit(ilxtr.hasConstrainingAspect, NIFRID.synonym,
         'has constraining primary participant aspect',
         'constrained by aspect'),
    olit(ilxtr.constrainedByAspect, definition,
         # these are definitional to the technique so they are not intentions
         # they must be achieved prior in time to the execution of the technique
         # FIXME is this true? what if you mess up the measurement?
         ('The relationship between a technique and an aspect of the primary '
          'participant that is constrained as part of a technique.')),

    oop(ilxtr.hasPrimaryAspect, ilxtr.hasIntention),
    olit(ilxtr.hasPrimaryAspect, rdfs.label, 'has intended primary aspect'),
    olit(ilxtr.hasPrimaryAspect, NIFRID.synonym,
         'has intention primary aspect',
         'has primary aspect',
         'has intention to effect the primary aspect of the primary participant',
         'hasPrimaryParticipantIntentionPrimaryAspect',),
    olit(ilxtr.hasPrimaryAspect, definition,
         ('The reltionship between a technique and the primary aspect of the '
          'primary participant intended to be effected by the technique.')),
    olit(ilxtr.hasPrimaryAspect, rdfs.comment,
         ('This property is very useful for classifying techniques. '
          'For example a flattening technique is intended to effect the flatness '
          'aspect of any primary participant, though it may effect other aspects as well.')),

    oop(ilxtr.hasPrimaryAspect_dAdS, ilxtr.hasIntention),
    olit(ilxtr.hasPrimaryAspect_dAdS, rdfs.label,
         # FIXME dAdSdt ?? also include the aspect at different points in time?
         #'has intended change in primary aspect as a function of sub parts of the primary participant'
         #'has intended change in primary aspect with respect to subset of the primary participant.'
         #'has intended change in primary aspect as a function of the subset of the primary participant.'
         'has expected difference in the primary aspect with respect to the subset of the primary participant'
),
    olit(ilxtr.hasPrimaryAspect_dAdS, NIFRID.synonym,
         'has intended dA/dS',
         'has intended dAspect/dSubset'
    ),
    olit(ilxtr.hasPrimaryAspect_dAdS, rdfs.comment,
         ('Full specification requires a rule to determine those subsets. '
          'Subsets may be spatial, temporal, or spatio-temporal as long as the temporal '
          'component occurs within the temporal confines of the execution of the technique. '
          'Subsets are defined by hasPrimaryParticipantSubsetRule.'
         )),

    oop(ilxtr.hasPrimaryParticipantSubsetRule, ilxtr.hasIntention),
    olit(ilxtr.hasPrimaryParticipantSubsetRule, rdfs.label, 'has intended primary participant subset rule'),
    olit(ilxtr.hasPrimaryParticipantSubsetRule, NIFRID.synonym,
         'has primary participant subset rule',
         'has subset rule'),
    olit(ilxtr.hasPrimaryParticipantSubsetRule, definition,
         ('The rule by which subsets of the primary participant are intended to be distingushed by '
          'a technique. The dS in dAdS, change in aspect with respect to change in subset of primary '
          'participant.')),

    oop(ilxtr.hasPrimaryAspect_dAdT, ilxtr.hasIntention),
    olit(ilxtr.hasPrimaryAspect_dAdT, rdfs.label,
         'has intended change in primary aspect'),
    olit(ilxtr.hasPrimaryAspect_dAdT, NIFRID.synonym,
         'hasPrimaryParticipantIntentionPrimaryAspect_dAdT'),
    olit(ilxtr.hasPrimaryAspect_dAdT, definition,
         'The intended change in primary aspect of primary participant before and after technique'),

    odp(ilxtr.hasConstrainingAspect_value, ilxtr.isConstrainedBy),  # data type properties spo object property
    olit(ilxtr.hasConstrainingAspect_value, rdfs.label,
         'has constraining aspect value'),
    olit(ilxtr.hasConstrainingAspect_value, definition,
         ('In some cases a protocol is classified based on the value '
          'that a constraining aspect has, not just that it is constrained on that aspect. ')),

    olit(ilxtr.hasConstrainingAspect_value, rdfs.comment,
         ('For example, dead and alive are 0 and 1 on livingness respectively. '
          'we can also define dead and alive, as disjoint, but that does not effectively '
          'model that they are two sides of the same coin for any binary definition. '
          'Note that this implies that these are not just qualities, they must have an '
          'explicit value outcome defined.'
         )
        ),

    #oop(ilxtr.),
    #oop(ilxtr.),
    #oop(ilxtr.),

    # classes
    oc(ilxtr.executor),
    olit(ilxtr.executor, rdfs.label, 'executor'),
    olit(ilxtr.executor, NIFRID.synonym, 'executing agent'),
    olit(ilxtr.executor, definition,
         'An executor is the primary agentous being that participates in a '
         'technique and is usually the vehicle by which prior information '
         'constrains a technique. Human beings usually play this role, but '
         'computers and robots can be considered to be executors when the prior '
         'information has been encoded directly into them and their behavior.'),

    oc(BFO['0000019']),  # XXX  # vs PATO:0000001 quality:
    olit(BFO['0000019'], rdfs.label, 'quality'),  # XXX

    oc(ilxtr.aspect, BFO['0000019']),  # FIXME aspect/
    olit(ilxtr.aspect, rdfs.label, 'aspect'),
    olit(ilxtr.aspect, rdfs.comment,
         'PATO has good coverage of many of these aspects though their naming is not alway consistent.'),

    oc(asp['is'], ilxtr.aspect),
    olit(asp['is'], rdfs.label, 'is'),
    olit(asp['is'], NIFRID.synonym,
         'isness',
         'being aspect',
         'beingness',),
    olit(asp['is'], definition,
         ('The aspect of beingness. Should be true or false, value in {0,1}.'
          "Not to be confused with the 'is a' reltionship which deals with categories/types/classes."
          "For now should not be used for 'partial' beingness, so a partially completed building is not"
          'a building for the purposes of this aspect. This is open to discussion, and if there are'
          'good examples where partial beingness is a useful concept, use as a [0,1] aspect would be encouraged.')),
    olit(asp['is'], rdfs.comment,
         ('There are cases where the value could be ? depending on how one '
          'operationalizes certain concepts from quantum physics. Note also that '
          'isness will be directly affected by the choice of the operational defintion. '
          'Because of the scope of this ontology, there are implicit decisions about the nature '
          'of certain operational definitions, such as livingness, which imply that our '
          'operational definition for isness is invariant to dead.'
         )),

    oc(asp.isClassifiedAs, asp['is']),  # FIXME not quite right
    olit(asp.isClassifiedAs, rdfs.label, 'is classified as'),
    olit(asp.isClassifiedAs, NIFRID.synonym,
         'is named as', 'has operational definition with inclusion criteria that names thing as'),

    oc(asp.flatness, ilxtr.aspect),
    olit(asp.flatness, rdfs.label, 'flatness'),
    olit(asp.flatness, NIFRID.synonym, 'flatness aspect'),
    olit(asp.flatness, definition,
         ('How flat a thing is. There are a huge variety of operational '
          'definitions depending on the type of thing in question.')),

    oc(asp.weight, ilxtr.aspect),  # TODO 'PATO:0000128'
    olit(asp.weight, rdfs.label, 'weight'),
    olit(asp.weight, NIFRID.synonym, 'weight aspect'),

    oc(asp.livingness, ilxtr.aspect),
    oc(asp.aliveness, ilxtr.aspect),  # PATO:0001421
    oc(asp.deadness, ilxtr.aspect),  # PATO:0001422
    (asp.aliveness, owl.disjointWith, asp.deadness),  # this holds for any single operational definition

    oc(ilxtr.informationEntity),
    olit(ilxtr.informationEntity, rdfs.label, 'information entity'),
    olit(ilxtr.informationEntity, definition, 'Any physically encoded information.'),

    oc(ilxtr.informationArtifact, ilxtr.informationEntity),
    olit(ilxtr.informationArtifact, rdfs.label, 'information artifact'),
    olit(ilxtr.informationArtifact, definition,
         ('An information entity that has an explicit symbolic encoding '
          'which is distinct from the existence or being that it encodes.')),

    oc(ilxtr.protocol, ilxtr.informationEntity),
    olit(ilxtr.protocol, rdfs.label, 'protocol'),
    olit(ilxtr.protocol, NIFRID.synonym, 'technique specification'),

    oc(ilxtr.protocolArtifact, ilxtr.informationArtifact),
    (ilxtr.protocolArtifact, rdfs.subClassOf, ilxtr.protocol),
    olit(ilxtr.protocolArtifact, rdfs.label, 'protocol artifact'),

    oc_(ilxtr.protocolExecution,
       oec(ilxtr.technique,
           *restrictions((ilxtr.isConstrainedBy, ilxtr.protocol),)),),
    olit(ilxtr.protocolExecution, rdfs.label, 'protocol execution'),

    ## techniques
    oc(BFO['0000015']),
    olit(BFO['0000015'], rdfs.label, 'process'),

    oc(ilxtr.technique, BFO['0000015']),  # FIXME technique/
    olit(ilxtr.technique, rdfs.label, 'technique'),
    olit(ilxtr.technique, NIFRID.synonym, 'method'),
    olit(ilxtr.technique, definition,
         'A repeatable process that is constrained by some prior information.'),
    (ilxtr.technique, ilxtr.hasTempId, OntId('HBP_MEM:0000000')),

)

# TODO aspects.ttl?
methods_core = simpleOnt(filename=filename,
                         prefixes=prefixes,
                         imports=imports,
                         triples=triples,
                         comment=comment,
                         _repo=_repo)

methods_core._graph.add_namespace('asp', str(asp))
methods_core._graph.add_namespace('ilxtr', str(ilxtr))  # FIXME why is this now showing up...
#methods_core._graph.add_namespace('tech', str(tech))
methods_core._graph.add_namespace('HBP_MEM', OntCuries['HBP_MEM'])
methods_core._graph.write()
