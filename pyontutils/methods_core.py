from IPython import embed
import rdflib
from pyontutils.core import OntId, OntCuries
from pyontutils.core import simpleOnt, oc, oc_, odp, oop, olit, oec, olist
from pyontutils.core import POCombinator, _POCombinator, ObjectCombinator, propertyChainAxiom, Combinator
from pyontutils.core import restriction, restrictions
from pyontutils.core import NIFTTL, NIFRID, ilxtr, BFO
from pyontutils.core import definition, hasRole, hasParticipant, hasPart, hasInput, hasOutput, makeNamespaces
from pyontutils.core import owl, rdf, rdfs

restG = POCombinator(rdf.type, owl.Restriction).full_combinator
axiom = POCombinator(rdf.type, owl.Axiom)
blankc = POCombinator
equivalentClassC = POCombinator(owl.equivalentClass, ObjectCombinator).full_combinator
owlClass = oc_
owlClassC = oc_.full_combinator
subClassOf = POCombinator(rdfs.subClassOf, ObjectCombinator).full_combinator
oop_ = POCombinator(rdf.type, owl.ObjectProperty)

def _t(subject, label, *rests, def_=None, synonyms=tuple(), equivalentClass=oec):
    members = tuple()
    _rests = tuple()
    for rest in rests:
        if isinstance(rest, tuple):
            if len(rest) == 2:
                _rests += rest,
            else:
                raise ValueError(f'length of {rest} is not 2!')
        elif isinstance(rest, Combinator):
            members += rest,
        else:
            members += rest,

    rests = _rests
    if not members:
        members = ilxtr.technique,

    yield from oc(subject)
    yield from equivalentClass.serialize(subject, *members, *restrictions(*rests))
    yield from olit(subject, rdfs.label, label)
    if def_:
        yield from olit(subject, definition, def_)

    if synonyms:
        if not isinstance(synonyms, tuple):
            # this is why python sucks and racket is awesome if this was racket
            # the error would show up on the line where the problem was :/
            raise TypeError(f'Type of {synonyms!r} should not be {type(synonyms)}!')
        yield from olit(subject, NIFRID.synonyms, *synonyms)

prot = rdflib.Namespace(ilxtr[''] + 'protocol/')
tech = rdflib.Namespace(ilxtr[''] + 'technique/')
asp = rdflib.Namespace(ilxtr[''] + 'aspect/')

obo, RO, *_ = makeNamespaces('obo', 'RO')
filename = 'methods-core'
prefixes = ('BFO', 'ilxtr', 'NIFRID', 'RO', 'IAO', 'definition', 'hasParticipant')
OntCuries['HBP_MEM'] = 'http://www.hbp.FIXME.org/hbp_measurement_methods/'
#imports = NIFTTL['nif_backend.ttl'],
imports = obo['bfo.owl'], obo['ro.owl']
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
    oop_(ilxtr.hasInformationInput,
         propertyChainAxiom(hasPart, ilxtr.hasInformationInput)),
    (ilxtr.hasInformationInput, owl.propertyDisjointWith, ilxtr.isConstrainedBy),
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
    (ilxtr.hasInformationInput, rdfs.domain, ilxtr.technique),
    (ilxtr.hasInformationInput, rdfs.range, ilxtr.informationEntity),

    oop(ilxtr.isConstrainedBy, ilxtr.hasInformationParticipant),
    oop_(ilxtr.isConstrainedBy,
         propertyChainAxiom(hasPart, ilxtr.isConstrainedBy)),
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
    oop(ilxtr.hasInformationOutput, ilxtr.hasIntention),
    oop_(ilxtr.hasInformationOutput,
         propertyChainAxiom(hasPart, ilxtr.hasInformationOutput)),
    olit(ilxtr.hasInformationOutput, rdfs.label, 'has information output'),
    olit(ilxtr.hasInformationOutput, NIFRID.synonym, 'has symbolic output'),
    (ilxtr.hasInformationOutput, rdfs.domain, ilxtr.technique),
    (ilxtr.hasInformationOutput, rdfs.range, ilxtr.informationEntity),

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
    (ilxtr.hasProbe, rdfs.domain, ilxtr.technique),
    (ilxtr.hasProbe, rdfs.range, ilxtr.materialEntity),

    oop(ilxtr.hasPrimaryParticipant, hasParticipant),
    olit(ilxtr.hasPrimaryParticipant, rdfs.label, 'has primary participant'),
    olit(ilxtr.hasPrimaryParticipant, definition, 'The relationship between a process and its primary participant.'),
    olit(ilxtr.hasPrimaryParticipant, rdfs.comment,
         'This property should be used to mark the key input and/or output of a process if its type is not generic.'),
    (ilxtr.hasPrimaryParticipant, rdfs.domain, ilxtr.technique),
    (ilxtr.hasPrimaryParticipant, rdfs.range, ilxtr.materialEntity),

    oop(ilxtr.primaryParticipantIn),
    olit(ilxtr.primaryParticipantIn, rdfs.label, 'primary participant in'),
    (ilxtr.primaryParticipantIn, owl.inverseOf, ilxtr.hasPrimaryParticipant),

    oop(ilxtr.hasPrimaryInput, ilxtr.hasPrimaryParticipant),
    oop(ilxtr.hasPrimaryInput, hasInput),
    oop(ilxtr.hasPrimaryOutput, ilxtr.hasPrimaryParticipant),
    oop(ilxtr.hasPrimaryOutput, ilxtr.hasIntention),
    oop(ilxtr.hasPrimaryOutput, hasOutput),

    # posterior or knowledge based participants that define techniques
    # often they would be part of the actual primary input
    # FIXME aspect vs participant ...
    # FIXME vs constrainedByAspect
    oop(ilxtr.knownDetectedPhenomena, hasParticipant),
    oop(ilxtr.knownProbedPhenomena, hasParticipant),
    oop(ilxtr.knownDifferentiatingPhenomena, ilxtr.hasAspect),

    ## naming (naming is distinct from intentions because it always succeeds)
    oop(ilxtr.names),
    oop(ilxtr.assigns, ilxtr.names),
    oop(ilxtr.asserts, ilxtr.names),
    # this operate on aspects in cases where the aspect is 'extrinsic'
    # i.e. where if given only the named thing in question the binding
    # of the aspect to the thing cannot be determined making measurements
    # on only the thing itself (or that it was not determined in that way)
    # these are cases where information from the surrounding environment is
    # needed. for example the part of a brain a cell was collected from cannot
    # (currently) be determined with 100% certainty by making measurements on
    # the cell alone, additional information is required, therefore the 'measurement'
    # of the aspect is not a measurement, it is an assertion

    ## intentions
    oop(ilxtr.hasIntention),  # not really sco realizes:? it also includes intended changes in qualities?
    olit(ilxtr.hasIntention, rdfs.label, 'has intention'),
    olit(ilxtr.hasIntention, definition, 'The relationship between a process and an intended outcome.'),
    olit(ilxtr.hasIntention, rdfs.comment, 'Should rarely be used directly.'),
    # TODO implies has expected outcome?

    # while these exist in principle there is no meaningful way to bind them to a specific
    #  participant without a qualifier, therefore we are leaving them out
    # oop(ilxtr.hasParticipantIntentionAspect, ilxtr.intention),
    # oop(ilxtr.hasPrimaryParticipantIntentionAspect, ilxtr.hasParticipantIntentionAspect),
    # oop(ilxtr.hasPrimaryParticipantIntentionPrimaryAspect, ilxtr.hasPrimaryParticipantIntentionAspect),

    oop(ilxtr.techniqueHasAspect),
    oop_(ilxtr.techniqueHasAspect,
         propertyChainAxiom(hasPart, ilxtr.techniqueHasAspect),
         propertyChainAxiom(ilxtr.hasConstrainingAspect),
         propertyChainAxiom(ilxtr.hasPrimaryAspect),
        ),
    (ilxtr.techniqueHasAspect, rdfs.domain, ilxtr.technique),
    (ilxtr.techniqueHasAspect, rdfs.range, ilxtr.aspect),

    oop(ilxtr.hasConstrainingAspect, ilxtr.techniqueHasAspect),  # TODO
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
    (ilxtr.hasPrimaryAspect, rdfs.subPropertyOf, ilxtr.techniqueHasAspect),
    olit(ilxtr.hasPrimaryAspect, rdfs.label, 'has primary aspect'),
    olit(ilxtr.hasPrimaryAspect, NIFRID.synonym,
         'has intended primary aspect',
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
    # TODO property chain or general axiom? implies that primary participant of has aspect
    # axiom(None, POC(ilxtr.hasPrimarAspec))

    oop(ilxtr.hasPrimaryAspectActualized, ilxtr.hasPrimaryAspect),
    olit(ilxtr.hasPrimaryAspectActualized, rdfs.label, 'has primary aspect actualized'),
    olit(ilxtr.hasPrimaryAspectActualized, NIFRID.synonym,
         'has intended primary aspect actualized',),

    #oop(ilxtr.hasPrimaryAspectMeasured, ilxtr.hasPrimaryAspect),
    # redundant with hasPrimaryAspect, cannot be disjoint with actualized
    # because all actualization techniques are also measurement techniques


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

    odp(ilxtr.hasAspectValue),
    odp(ilxtr.hasConstrainingAspect_value, ilxtr.isConstrainedBy),  # data type properties spo object property
    (ilxtr.hasConstrainingAspect_value, rdfs.subPropertyOf, ilxtr.hasAspectValue),
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

    oop(ilxtr.hasAspect, RO['0000086']),
    # FIXME make it clear that this is between material entities (it is subclassof quality)
    # for hasAspect
    #oop_(ilxtr.hasAspect,
         #propertyChainAxiom(ilxtr.hasAspect),
         #propertyChainAxiom(hasPart, ilxtr.hasAspect),
        #),
    oop(ilxtr.aspectOf, RO['0000080']),
    (ilxtr.aspectOf, owl.inverseOf, ilxtr.hasAspect),

    #oop(ilxtr.),
    #oop(ilxtr.),
    #oop(ilxtr.),

    # classes

    ## executor
    oc(ilxtr.executor, ilxtr.materialEntity),  # probably equivalent to agent in ero
    olit(ilxtr.executor, rdfs.label, 'executor'),
    olit(ilxtr.executor, NIFRID.synonym, 'executing agent'),
    olit(ilxtr.executor, definition,
         'An executor is the primary agentous being that participates in a '
         'technique and is usually the vehicle by which prior information '
         'constrains a technique. Human beings usually play this role, but '
         'computers and robots can be considered to be executors when the prior '
         'information has been encoded directly into them and their behavior.'),

    ## aspect
    oc(BFO['0000019']),  # XXX  # vs PATO:0000001 quality:
    olit(BFO['0000019'], rdfs.label, 'quality'),  # XXX

    oc(ilxtr.aspect, BFO['0000019']),  # FIXME aspect/
    olit(ilxtr.aspect, rdfs.label, 'aspect'),
    olit(ilxtr.aspect, rdfs.comment,
         'PATO has good coverage of many of these aspects though their naming is not alway consistent.'),
    olit(ilxtr.aspect, NIFRID.synonym,
         'measureable',
         'measureable aspect'),
    # hasValue, hasRealizedValue
    # hasActualizedValue
    # hasMeasuredValue
    #ilxtr.aspect hasOutputValue 
    #ilxtr.aspect hasMeasurementProtocol
    # should aspects not be bound to symbolic entities?
    # for example a word count for a document?
    # I guess all implementations of symbolic systems are physical
    # and ultimately the distinction between symbolic and physical
    # isn't actually useful for aspects
    # we do however need a notation of bottom for aspects which
    # says that for certain inputs the aspect cannot return a
    # meaningful (correctly typed non null) value

    ## technique
    oc(BFO['0000015']),
    olit(BFO['0000015'], rdfs.label, 'process'),

    oc(ilxtr.technique, BFO['0000015']),  # FIXME technique/
    olit(ilxtr.technique, rdfs.label, 'technique'),
    olit(ilxtr.technique, NIFRID.synonym, 'method'),
    olit(ilxtr.technique, definition,
         'A repeatable process that is constrained by some prior information.'),
    (ilxtr.technique, ilxtr.hasTempId, OntId('HBP_MEM:0000000')),
    # NOTE: not all techniques have primary participants, especially in the case of composite techniques

    oc_(ilxtr.technique, restriction(ilxtr.hasExecutor, ilxtr.executor)),
    #_t(tech.test, 'test test test',
       #(ilxtr.hasPrimaryParticipant, ilxtr.thingA),
       #(ilxtr.hasPrimaryParticipant, ilxtr.thingB)),

    #(ilxtr.thingA, rdfs.subClassOf, ilxtr.materialEntity),
    #(ilxtr.thingB, rdfs.subClassOf, ilxtr.materialEntity),
    #(ilxtr.thingA, owl.disjointWith, ilxtr.thingB),
) 

def derp():
    b0 = rdflib.BNode()
    yield ilxtr.technique, owl.equivalentClass, b0

    yield b0, rdf.type, owl.Class
    a, b, c = (rdflib.BNode() for _ in range(3))
    yield b0, owl.intersectionOf, a
    b1 = rdflib.BNode()
    yield a, rdf.first, b1
    r1 = restG(
    blankc(owl.onProperty, ilxtr.hasPrimaryParticipant),
    blankc(owl.maxQualifiedCardinality, rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
    blankc(owl.onClass, BFO['0000004']))(b1)
    yield from r1

    b2 = rdflib.BNode()
    yield b, rdf.first, b2
    r2 = restG(
    blankc(owl.onProperty, ilxtr.hasPrimaryAspect),
    blankc(owl.maxQualifiedCardinality, rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
    blankc(owl.onClass, ilxtr.aspect))(b2)
    yield from r2

    b3 = rdflib.BNode()
    yield c, rdf.first, b3
    r3 = restG(
    blankc(owl.onProperty, ilxtr.hasPrimaryAspect_dAdT),
    blankc(owl.maxQualifiedCardinality, rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
    blankc(owl.onClass, ilxtr.changeType))(b3)
    yield from r3

    for _1, _2 in ((a, b), (b, c), (c, rdf.nil)):
        yield _1, rdf.rest, _2

triples += tuple(derp())


"""
asdf = tuple(
    owlClass(ilxtr.technique,
             equivalentClassC(None,
                 owlClassC(
                     subClassOf(
                         restG(blankC(owl.onProperty, ilxtr.hasPrimaryParticipant),
                               blankC(owl.maxQualifiedCardinality,
                                      rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
                               blankC(owl.onClass,
                                      # FIXME maybe more specific?
                                      BFO['0000004'])),
                         restG(blankC(owl.onProperty, ilxtr.hasPrimaryAspect),
                               blankC(owl.maxQualifiedCardinality,
                                      rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
                               blankC(owl.onClass, ilxtr.aspect)),
                         restG(blankC(owl.onProperty, ilxtr.hasPrimaryAspect_dAdT),
                               blankC(owl.maxQualifiedCardinality,
                                      rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
                               blankC(owl.onClass, ilxtr.changeType))))))
         )

embed()
"""

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
