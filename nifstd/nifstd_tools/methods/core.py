import rdflib
from pyontutils import combinators as cmb
from pyontutils.core import simpleOnt, OntId, OntGraph
from pyontutils.namespaces import OntCuries, makeNamespaces
from pyontutils.namespaces import NIFTTL, NIFRID, ilxtr, BFO
from pyontutils.namespaces import partOf, definition, editorNote, replacedBy
from pyontutils.namespaces import hasParticipant, hasPart, hasInput, hasOutput
from pyontutils.namespaces import prot, proc, tech, asp, dim, unit
from pyontutils.namespaces import owl, rdf, rdfs
from pyontutils.combinators import oc, oc_, odp, oop, olit, oec
from pyontutils.combinators import POCombinator, ObjectCombinator
from pyontutils.combinators import propertyChainAxiom, Combinator, Restriction2, EquivalentClass
from pyontutils.combinators import restriction, restrictions, intersectionOf


collector = OntGraph(path='property-chains.ttl')


def _propertyChainAxiom(*args):
    class Derp(Combinator):
        def __init__(self):
            pass
        def __call__(self, *argsi):
            [collector.add(_) for _ in propertyChainAxiom(*args)(*argsi)]
            yield ilxtr.a, ilxtr.b, ilxtr.c
    return Derp()

restN = Restriction2(None, owl.onProperty, owl.someValuesFrom)
restG = POCombinator(rdf.type, owl.Restriction).full_combinator
axiom = POCombinator(rdf.type, owl.Axiom)
blankc = POCombinator
equivalentClassC = POCombinator(owl.equivalentClass, ObjectCombinator).full_combinator
oECN = EquivalentClass(None)
owlClass = oc_
owlClassC = oc_.full_combinator
subClassOf = POCombinator(rdfs.subClassOf, ObjectCombinator).full_combinator
oop_ = POCombinator(rdf.type, owl.ObjectProperty)

def _t(subject, label, *rests, def_=None, synonyms=tuple(), comment=None,
       equivalentClass=oec):
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
        yield from olit(subject, NIFRID.synonym, *synonyms)

    if comment:
        yield from olit(subject, rdfs.comment, comment)

obo, RO, prov, *_ = makeNamespaces('obo', 'RO', 'prov')
filename = 'methods-core'
prefixes = None
OntCuries['HBP_MEM'] = 'http://www.hbp.FIXME.org/hbp_measurement_methods/'
imports = NIFTTL['nif_backend.ttl'],
#imports = obo['bfo.owl'], obo['ro.owl']
#imports = tuple()
comment = 'The core components for modelling techniques and methods.'
branch = 'methods'
_repo = True
debug = True

triples = (
    # data properties

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

    oop(ilxtr.hasDualTechnique),
    (ilxtr.hasDualTechnique, rdf.type, owl.SymmetricProperty),
    olit(ilxtr.hasDualTechnique, rdfs.label, 'has dual technique'),
    olit(ilxtr.hasDualTechnique, definition,
         ('The relationship between techniques that are duals of each other. '
          'An example usage is in cases where the matter constituting the primary '
          'input in one technique is transformed (read: renamed) and becomes the '
          'primary output of another technique. Bearing this relation implies that '
          'both techniques are part of a same enclosing technique.')),
    (ilxtr.hasDualTechnique, rdfs.domain, ilxtr.technique),
    (ilxtr.hasDualTechnique, rdfs.range, ilxtr.technique),

    oop(ilxtr.hasDualInputTechnique, ilxtr.hasDualTechnique),
    olit(ilxtr.hasDualInputTechnique, rdfs.label, 'has dual input technique'),
    olit(ilxtr.hasDualInputTechnique, definition,
         ('The relationship between a technique that has a primary output '
          'and a dual technique that has a primary input that is destroyed.')),
    oop(ilxtr.hasDualOutputTechnique, ilxtr.hasDualTechnique),
    olit(ilxtr.hasDualOutputTechnique, rdfs.label, 'has dual output technique'),
    olit(ilxtr.hasDualOutputTechnique, definition,
         ('The relationship between a technique that has a primary input that is '
          'destroyed and a dual technique that has the corresponding primary output.')),
    (ilxtr.hasDualInputTechnique, owl.inverseOf, ilxtr.hasDualOutputTechnique),

    oop(ilxtr.hasInformationParticipant),
    oop_(ilxtr.hasInformationParticipant,
         propertyChainAxiom(hasPart, ilxtr.hasInformationParticipant),
         propertyChainAxiom(hasPart, ilxtr.hasDirectInformationParticipant)),
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
         propertyChainAxiom(hasPart, ilxtr.hasInformationInput),
         propertyChainAxiom(hasPart, ilxtr.hasDirectInformationInput)),
    #(ilxtr.hasInformationInput, owl.propertyDisjointWith, ilxtr.isConstrainedBy),  # XXX fact++ issues?
    # hermit says cannot use disjointness on non simple properties
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
         propertyChainAxiom(hasPart, ilxtr.hasInformationOutput),
         propertyChainAxiom(hasPart, ilxtr.hasDirectInformationOutput)),
    olit(ilxtr.hasInformationOutput, rdfs.label, 'has information output'),
    olit(ilxtr.hasInformationOutput, NIFRID.synonym, 'has symbolic output'),
    (ilxtr.hasInformationOutput, rdfs.domain, ilxtr.technique),
    (ilxtr.hasInformationOutput, rdfs.range, ilxtr.informationEntity),

    oop(ilxtr.hasDirectInformationParticipant, ilxtr.hasInformationParticipant),
    # implies that there is a time in the full technique prior to which
    # the information input did not exist
    # FIXME also parent to hasInformationInput/Output??
    oop(ilxtr.hasDirectInformationInput, ilxtr.hasDirectInformationParticipant),
    oop(ilxtr.hasDirectInformationInput, ilxtr.hasInformationInput),
    olit(ilxtr.hasDirectInformationInput, rdfs.label, 'has direct information input'),
    oop(ilxtr.hasDirectInformationOutput, ilxtr.hasDirectInformationParticipant),
    oop(ilxtr.hasDirectInformationOutput, ilxtr.hasInformationOutput),
    oop(ilxtr.hasDirectInformationOutput, ilxtr.hasIntention),
    olit(ilxtr.hasDirectInformationOutput, rdfs.label, 'has direct information output'),

    ## participants
    oop(hasParticipant),
    olit(hasParticipant, rdfs.label, 'has participant'),
    olit(hasParticipant, NIFRID.synonym, 'has physical participant'),

    oop(ilxtr.hasInputOutput, hasParticipant),
    oop(hasInput, ilxtr.hasInputOutput),  # XXX
    oop_(hasInput, propertyChainAxiom(hasPart, hasInput)),
    olit(hasInput, rdfs.label, 'has input'),  # XXX
    oop(hasOutput, ilxtr.hasInputOutput),  # XXX
    oop_(hasOutput, propertyChainAxiom(hasPart, hasOutput)),
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

    #oop(ilxtr.hasEnergyProbe, ilxtr.hasProbe),
    # photon
    # electron
    # neutron
    # atomic nucleus
    # usually they leave
    # non addative probe, may modify, but unlikely to add
    #oop(ilxtr.hasMaterialProbe, ilxtr.hasProbe),

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

    oop(ilxtr.primaryInputIn, ilxtr.primaryParticipantIn),
    oop(ilxtr.primaryOutputIn, ilxtr.primaryParticipantIn),
    (ilxtr.primaryInputIn, owl.inverseOf, ilxtr.hasPrimaryInput),
    (ilxtr.primaryOutputIn, owl.inverseOf, ilxtr.hasPrimaryOutput),

    oop(ilxtr.hasPrimaryInputOutput, ilxtr.hasPrimaryParticipant),
    oop(ilxtr.hasPrimaryInputOutput, ilxtr.hasInputOutput),
    oop(ilxtr.hasPrimaryInput, ilxtr.hasPrimaryParticipant),
    oop(ilxtr.hasPrimaryInput, hasInput),
    oop(ilxtr.hasPrimaryOutput, ilxtr.hasPrimaryParticipant),
    oop(ilxtr.hasPrimaryOutput, ilxtr.hasIntention),
    oop(ilxtr.hasPrimaryOutput, hasOutput),

    oop(ilxtr.hasPrimaryInputUnbinding, ilxtr.hasPrimaryInput),  # aka NoOutput
    (ilxtr.hasPrimaryInputUnbinding, owl.propertyDisjointWith, ilxtr.hasPrimaryOutput),
    oop(ilxtr.hasPrimaryParticipantUnbinding, ilxtr.hasPrimaryParticipant),  # aka NoOutput
    (ilxtr.hasPrimaryParticipantUnbinding, owl.propertyDisjointWith, ilxtr.hasPrimaryOutput),
    oop(ilxtr.modifiesPrimaryInputOutput, ilxtr.hasPrimaryInput),
    oop(ilxtr.modifiesPrimaryInputOutput, ilxtr.hasPrimaryOutput),

    oop(ilxtr.hasPrimaryOutputNoInput, ilxtr.hasPrimaryOutput),
    (ilxtr.hasPrimaryOutputNoInput, owl.propertyDisjointWith, ilxtr.hasPrimaryInput),
    oop(ilxtr.hasPrimaryParticipantNoInput, ilxtr.hasPrimaryParticipant),
    (ilxtr.hasPrimaryParticipantNoInput, owl.propertyDisjointWith, ilxtr.hasPrimaryInput),
    oop(ilxtr.hasPrimaryParticipantNoInputNoOutput, ilxtr.hasPrimaryParticipant),
    (ilxtr.hasPrimaryParticipantNoInputNoOutput, owl.propertyDisjointWith, ilxtr.hasPrimaryInput),
    (ilxtr.hasPrimaryParticipantNoInputNoOutput, owl.propertyDisjointWith, ilxtr.hasPrimaryOutput),

    # posterior or knowledge based participants that define techniques
    # often they would be part of the actual primary input
    # FIXME aspect vs participant ...
    # FIXME vs hasConstrainingAspect
    oop(ilxtr.knownDetectedPhenomena, ilxtr.hasPrimaryInput),  # FIXME confusing naming...
    oop(ilxtr.knownProbedPhenomena, ilxtr.hasPrimaryParticipant),
    oop(ilxtr.knownDifferentiatingPhenomena, ilxtr.hasAspect),

    ## naming (naming is distinct from intentions because it always succeeds)
    oop(ilxtr.names),
    oop(ilxtr.assigns, ilxtr.names),
    oop(ilxtr.asserts, ilxtr.names),
    #oop_(ilxtr.asserts, propertyChainAxiom(ilxtr.hasPrimaryAspect (asp.nonLocal)))
    # assertion occurs when the accompanying information is not present
    # this operate on aspects in cases where the aspect is 'extrinsic'
    # i.e. where if given only the named thing in question the binding
    # of the aspect to the thing cannot be determined making measurements
    # on only the thing itself (or that it was not determined in that way)
    # these are cases where information from the surrounding environment is
    # needed. for example the part of a brain a cell was collected from cannot
    # (currently) be determined with 100% certainty by making measurements on
    # the cell alone, additional information is required, therefore the 'measurement'
    # of the aspect is not a measurement, it is an assertion

    ## list
    # on primary participant
    # hasPrimaryAspect (hasPrimaryParticipant, hasAspect)
    # hasPrimaryAspectActualized
    # hasPrimaryQualifiedAspect (hasPrimaryParticipant, hasQualifiedAspect)
    # hasPrimaryQualifiedAspectActualized
    #
    # hasConstrainingAspect
    # hasConstrainingQualifiedAspect
    # cannot actualize constraining aspects? but they are defact actualized by thier constraint
    #
    # but then there are parts of the pp
    # hasPrimaryParticipantPartConstrainingAspect
    #
    # hasInput
    # hasPrimaryInput
    #


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

    oop(ilxtr.processHasAspect),
    olit(ilxtr.processHasAspect, rdfs.label, 'process has aspect'),
    (ilxtr.processHasAspect, rdfs.domain, BFO['0000015']),
    (ilxtr.processHasAspect, rdfs.range, ilxtr.aspect),
    oop(ilxtr.processMeasuresAspect, ilxtr.processHasAspect),
    olit(ilxtr.processMeasuresAspect, rdfs.label, 'measures aspect'),
    oop(ilxtr.processActualizesAspect, ilxtr.processHasAspect), # there is a tau...
    olit(ilxtr.processActualizesAspect, rdfs.label, 'actualizes aspect'),
    oop(ilxtr.processIncludesOnAspect, ilxtr.processHasAspect),
    oop(ilxtr.processExcludesOnAspect, ilxtr.processHasAspect),
    oop(ilxtr.processHasPrimaryAspect, ilxtr.processHasAspect),

    #oop(ilxtr.techniqueHasAspect, ilxtr.processHasAspect),
    oop_(ilxtr.processHasAspect,
         propertyChainAxiom(hasPart, ilxtr.processHasAspect),
         propertyChainAxiom(ilxtr.hasConstrainingAspect),
         propertyChainAxiom(ilxtr.hasPrimaryAspect),
        ),
    #(ilxtr.techniqueHasAspect, rdfs.domain, ilxtr.technique),
    #(ilxtr.techniqueHasAspect, rdfs.range, ilxtr.aspect),

    oop(ilxtr.hasConstrainingAspect, ilxtr.processHasAspect),  # TODO
    oop_(ilxtr.hasConstrainingAspect,
         # TODO isConstrainedBy some value on that particular aspect
         propertyChainAxiom(ilxtr.hasPrimaryParticipant, ilxtr.hasExpAspect),
         #propertyChainAxiom(hasPart, ilxtr.processHasAspect),  # XXX fact++ encounters a circularity error
         # hermit informs that this is circular

         # IF the primary participant is the same
         #propertyChainAxiom(hasPart, ilxtr.hasPrimaryAspectActualized),
         # sanity check says that if you havePart dnaDeliveryTechnique
         # then any parent process will be constrained by some location
         # on its primary participant, which is incorrect... at least for
         # nonLocal aspects
        ),
    #oc_(None,
        # sigh
        #intersectionOf(
            #restN(ilxtr.hasConstrainingAspect, ilxtr.aspect)),
        #intersectionOf(restN(ilxtr.hasPrimaryParticipant,
                             #ilxtr.theSameThing),
                       #restN(hasPart,
                             #restN(ilxtr.hasPrimaryParticipant,
                                   #ilxtr.theSameThing))),
        #oECN())
    olit(ilxtr.hasConstrainingAspect, rdfs.label, 'has constraining aspect'),
    olit(ilxtr.hasConstrainingAspect, NIFRID.synonym,
         'has constraining primary participant aspect',
         'constrained by aspect'),
    olit(ilxtr.hasConstrainingAspect, definition,
         # these are definitional to the technique so they are not intentions
         # they must be achieved prior in time to the execution of the technique
         # FIXME is this true? what if you mess up the measurement?
         ('The relationship between a technique and an aspect of the primary '
          'participant that is constrained as part of a technique.')),

    oop(ilxtr.hasPriParticipantPartAspect),
    oop(ilxtr.hasPriParticipantPartPriAspect),
    oop(ilxtr.hasPartPriAspect, ilxtr.processHasAspect),
    oop_(ilxtr.hasPartPriAspect,
         propertyChainAxiom(hasPart, ilxtr.hasPrimaryAspect)),
    oop(ilxtr.hasPriParticipantPartAspect, ilxtr.processHasAspect),

    oop(ilxtr.hasParticipantPartConstrainingAspect, ilxtr.processHasAspect),
    oop_(ilxtr.hasParticipantPartConstrainingAspect,
         propertyChainAxiom(ilxtr.hasPrimaryParticipant, hasPart, ilxtr.hasExpAspect),
         # subprocesses have no executor
         propertyChainAxiom(ilxtr.hasSubProcess, ilxtr.hasConstrainingAspect)),

    oop(ilxtr.hasPrimaryAspect, ilxtr.hasIntention),
    oop(ilxtr.hasPrimaryAspect, ilxtr.processHasPrimaryAspect),
    #oop_(ilxtr.hasPrimaryAspect,  # this does not help us and breaks reasoners
         #propertyChainAxiom(ilxtr.hasPrimaryParticipant, ilxtr.hasMainAspect)),
    (ilxtr.hasPrimaryAspect, rdfs.subPropertyOf, ilxtr.processHasAspect),
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
    oop(ilxtr.hasPrimaryAspectActualized, ilxtr.processActualizesAspect),
    olit(ilxtr.hasPrimaryAspectActualized, rdfs.label, 'has primary aspect actualized'),
    olit(ilxtr.hasPrimaryAspectActualized, NIFRID.synonym,
         'has intended primary aspect actualized',),

    oop(ilxtr.hasPrimaryAspectMeasured, ilxtr.hasPrimaryAspect),
    # cannot be disjoint with actualized
    # because all actualization techniques are also measurement techniques

    oop(ilxtr.hasParentPrimaryAspect, ilxtr.processHasAspect),
    # note that this is distinctly not spo hasPrimaryAspect
    oop_(ilxtr.hasParentPrimaryAspect,
         propertyChainAxiom(partOf, ilxtr.hasPrimaryParticipant, ilxtr.hasExpAspect)),

    oop(ilxtr.hasParticipantPartPrimaryAspect, ilxtr.processHasAspect),
    # note that this is distinctly not spo hasPrimaryAspect
    oop_(ilxtr.hasParticipantPartPrimaryAspect,
         propertyChainAxiom(ilxtr.hasPrimaryParticipant, hasPart, ilxtr.hasExpAspect)),

    oop(ilxtr.hasParticipantPartPrimaryAspectActualized, ilxtr.hasParticipantPartPrimaryAspect),
    oop(ilxtr.hasParticipantPartPrimaryAspectActualized, ilxtr.processActualizesAspect),
    # note that this is distinctly not spo hasPrimaryAspect
    oop_(ilxtr.hasParticipantPartPrimaryAspect,
         propertyChainAxiom(ilxtr.hasPrimaryParticipant, hasPart, ilxtr.hasExpAspect),
         # subprocesses have no executor
         propertyChainAxiom(ilxtr.hasSubProcess, ilxtr.hasPrimaryAspect)),

    oop(ilxtr.hasSubProcess, hasPart),  # TODO see if we really need this
    #_t(None, None,
       #(ilxtr.hasPrimaryParticipant, restN(hasPart, ilxtr.sameThing)),
      #),
    oop(ilxtr.hasPartPart, hasPart),
    oop_(ilxtr.hasPartPriParticipant,
         # invariance to whether the primary participant or
         # the technique itself is the first down the partonomy
         # FIXME hermit informs that these cause circular dependency issues
         propertyChainAxiom(ilxtr.hasPrimaryParticipant, hasPart),#, partOf),  # self
         propertyChainAxiom(hasPart, ilxtr.hasPrimaryParticipant),
                            #partOf, ilxtr.primaryParticipantIn)  # self
        ),
    (ilxtr.hasPartPart, rdfs.domain, BFO['0000015']),
    (ilxtr.hasPartPart, rdfs.range, BFO['0000015']),
    oop(ilxtr.hasPartNotPart, hasPart),
    #oop_(ilxtr.hasPartNotPart,  # XXX fact ++ error
         # hermit informs that there is a circular dependency
         #propertyChainAxiom(hasPart, ilxtr.hasPrimaryParticipant, ilxtr.primaryParticipantIn)),
    (ilxtr.hasPartPart, owl.propertyDisjointWith, ilxtr.hasPartNotPart),
    (ilxtr.hasPartNotPart, rdfs.domain, BFO['0000015']),
    (ilxtr.hasPartNotPart, rdfs.range, BFO['0000015']),

    oop(ilxtr.hasPartAspectInvariant, ilxtr.processHasAspect),
    oop_(ilxtr.hasPartAspectInvariant,
         propertyChainAxiom(ilxtr.hasPrimaryParticipant, ilxtr.hasExpAspect),
         # FIXME need a notion of union of the aspects of the parts...
         # so that the output value when measuring the aspect includes
         # that aspect as bound to all the parts
         propertyChainAxiom(hasPart, ilxtr.hasConstrainingAspect)),

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

    oop(ilxtr.hasConstrainingAspect_dAdT, ilxtr.hasIntention),
    olit(ilxtr.hasConstrainingAspect_dAdT, rdfs.label,
         'has intended change in constraining aspect'),

    oop(ilxtr.hasAspect, RO['0000086']),
    # FIXME make it clear that this is between material entities (it is subclassof quality)
    # for hasAspect
    #oop_(ilxtr.hasAspect,
         #propertyChainAxiom(ilxtr.hasAspect),
         #propertyChainAxiom(hasPart, ilxtr.hasAspect),
        #),
    oop(ilxtr.aspectOf, RO['0000080']),
    (ilxtr.aspectOf, owl.inverseOf, ilxtr.hasAspect),
    (ilxtr.hasAspect, rdfs.domain, ilxtr.materialEntity),
    (ilxtr.hasAspect, rdfs.range, ilxtr.aspect),

    oop(ilxtr.hasExpAspect, ilxtr.hasAspect),  # has experimental aspect or has operational aspect
    #oop(ilxtr.hasMainAspect, ilxtr.hasExpAspect), # this does not help us
    # FIXME ilxtr.hasMainAspectInSomeTechnique

    ## aspect to aspect relationships
    oop(ilxtr.hasQualifiedForm),
    olit(ilxtr.hasQualifiedForm, rdfs.label, 'has qualified form'),
    (ilxtr.hasQualifiedForm, rdfs.domain, asp.Local),
    (ilxtr.hasQualifiedForm, rdfs.range, asp.nonLocal),

    oop(ilxtr.isQualifiedFormOf),
    olit(ilxtr.isQualifiedFormOf, rdfs.label, 'is qualified form of'),
    (ilxtr.hasQualifiedForm, owl.inverseOf, ilxtr.isQualifiedFormOf),

    oop(ilxtr.hasUnqualifiedEquivalent),

    oop(ilxtr.hasComplementAspect),  # implies inverse, should be in the symbolic operational definitions

    ## aspect to value relationships

    # FIXME has vs yields vs yielded
    oop(ilxtr.aspectHasValue),
    oop(ilxtr.hasDefinedValue, ilxtr.aspectHasValue),
    oop(ilxtr.hasMeasuredValue, ilxtr.aspectHasValue),
    oop(ilxtr.hasActualizedValue, ilxtr.aspectHasValue),
    oop(ilxtr.hasDefinedActualizedValue, ilxtr.hasActualizedValue),
    oop(ilxtr.hasDefinedActualizedValue, ilxtr.hasDefinedValue),
    oop(ilxtr.hasMeasuredActualizedValue, ilxtr.hasActualizedValue),
    oop(ilxtr.hasMeasuredActualizedValue, ilxtr.hasMeasuredValue),

    ## contexts
    oop(ilxtr.hasContext),
    (ilxtr.hasContext, rdfs.domain, ilxtr.aspect),

    oop(ilxtr.hasInformationContext, ilxtr.hasContext),
    oop(ilxtr.hasTechniqueContext, ilxtr.hasContext),
    oop(ilxtr.hasMaterialContext, ilxtr.hasContext),
    oop(ilxtr.hasAspectContext, ilxtr.hasContext),

    (ilxtr.hasInformationContext, rdfs.range, ilxtr.informationEntity),
    (ilxtr.hasTechniqueContext, rdfs.range, ilxtr.technique),  # aka some other step that has some constraint
    (ilxtr.hasMaterialContext, rdfs.range, ilxtr.materialEntity),  # TODO (hasMatCont (hasPart some matEnt))???
    (ilxtr.hasAspectContext, rdfs.range, ilxtr.aspect),  # TODO aspectOf some thing partOf ??
    #oop(ilxtr.hasMaterialAspectContext, ilxtr.hasContext)

    oop(ilxtr.processHasContext),
    (ilxtr.processHasContext, rdfs.domain, BFO['0000015']),

    # aspects for processes
    # these are not modelled with a notion of intention because
    # they are processes which _must_ occur in order to be classified as such

    # FIXME TODO naming, Required?
    oop(ilxtr.hasActualPrimaryAspect),
    oop(ilxtr.hasActualPrimaryAspect_dAdT),

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
    olit(ilxtr.aspect, definition,
         'An aspect is a measurable quantity or quality of a thing. '
         'Aspects must be able to act as a function that is dependent '
         'only on a measurement device and the thing to which the aspect '
         'is bound. This is to say that aspects require a notion of locality. '),
    olit(ilxtr.aspect, rdfs.comment,
         'To illustrate with an example. The location of a thing cannot be an '
         'aspect of that thing because location requires knowing the spatial '
         'realtionship between that thing any measurement device. Said in yet '
         'another way, (measure thing location) -> here for all values of thing. '
         'Aspects all assume an inertial reference frame centered on their named inputs. '
         'Location thus can only ever be computed on some part of a larger named system.'
         'Therefore, in order to accomodate measurements on composite beings such as '
         'the number of geese in a flock or the location of a missing set of keys possibly '
         'in the house, we split aspects into signular and composite. The composite are '
         'indeed aspects of a single nameable thing, but they make measurements on or '
         'between parts of that thing. The simplest version is nearly always named thing '
         'plus implied complement of that thing. Note also that the number of geese in a '
         'flock is different from the number of things in existence that are geese by the '
         'isness aspect. The asp/isness/count can be determined entirely locally because '
         'the definition of what a goose is is independent of time and place (where and when). '
         'Time dependent or place dependent definitions of geese (such as in the game of '
         'duck duck goose) require additional information and thus are not what/singular aspects.'
        ),
    olit(ilxtr.aspect, rdfs.comment,
         'PATO has good coverage of many of these aspects though their naming is '
         'not alway consistent. And their definition is perhaps overly broad.'),
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

    (asp.Local, owl.disjointWith, asp.nonLocal),
    oc(asp.Local, ilxtr.aspect),  # aka unqualified or does not need qualification
    olit(asp.Local, rdfs.label, 'aspect unqualified'),
    olit(asp.Local, definition,
         'aspect of thing that is invariant to context'),
    oc(asp.nonLocal, ilxtr.aspect),  # qualified
    olit(asp.nonLocal, rdfs.label, 'aspect qualified'),
    oc_(asp.nonLocal, restriction(ilxtr.hasContext, BFO['0000002'])),
    # FIXME context isn't just the material entity it is the aspects thereof
    # the context probably also needs to be a technique that binds all
    # intersectionOf for multiple aspects? hrm
    # the additional aspects?
    # context dealt with below
    # binding a nonLocal aspect to a single entity will
    # lead to construction of a context
    olit(asp.nonLocal, definition,
         'aspect of thing that varies depending on context'),

    oop_(hasParticipant,
         propertyChainAxiom(ilxtr.processHasAspect, ilxtr.hasContext)),

    restG(blankc(owl.onProperty, ilxtr.hasPrimaryAspect_dAdT),
          blankc(owl.someValuesFrom, ilxtr.nonZero),
          blankc(rdfs.subClassOf,
                 restN(ilxtr.hasPrimaryAspectActualized,
                       ilxtr.aspect)))(rdflib.BNode()),

    ## modalitiy
    cmb.Class(
        ilxtr.ExperimentalModality,
        cmb.Pair(owl.deprecated, rdflib.Literal(True)),
        cmb.Pair(replacedBy, ilxtr.ExperimentalApproach),
        cmb.Pair(editorNote, rdflib.Literal(
            'For clarity switch to use ilxtr:ExperimentalApproach since we are '
            'changing the preferred terminology. Hopefully keeping the id '
            'aligned will prevent confusion down the line. Follow replacedBy: '
            'to find the new id.')),
    ),
    cmb.Class(
        ilxtr.ExperimentalApproach,
        cmb.Pair(rdfs.label, rdflib.Literal('experimental approach')),
        cmb.Pair(NIFRID.synonym, rdflib.Literal('experimental modality')),
        cmb.Pair(definition, rdflib.Literal(
            'The general experimental approach used to answer a '
            'scientific question. Approaches often define whole '
            'research disciplines.')),
    ),
    cmb.Class(ilxtr.ExperimentalPreparation,
              cmb.Pair(rdfs.label, rdflib.Literal('experimental preparation')),
              ),  # in vivo in vitro

    ## behavior
    cmb.Class(ilxtr.BehavioralTask,
              cmb.Pair(rdfs.label, rdflib.Literal('behavioral task')),
              ),  # tasks that have protocols
    cmb.Class(ilxtr.BehavioralParadigm,
              cmb.Pair(rdfs.label, rdflib.Literal('behavioral paradigm')),
              ),  # more abstract behaviors e.g. forced choice detection
    cmb.Class(ilxtr.BehavioralReadout,
              cmb.Pair(rdfs.label, rdflib.Literal('behavioral readout')),
              ),  # e.g. delayed saccad
    # behaviorl task structure
    # reward type
    # structure in the sensory environment that they need to process
    # working memory is more like a study target

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
    oc_(ilxtr.technique,
        restriction(ilxtr.hasExecutor, ilxtr.executor)),

    oc_(rdflib.BNode(),
        oECN(intersectionOf(BFO['0000015'],
                            restN(hasParticipant,
                                  restN(ilxtr.hasAspect, asp.nonLocal))),  # vs hasExpAspect
             intersectionOf(BFO['0000015'],
                            restN(ilxtr.processHasAspect,
                                  restN(ilxtr.hasContext, BFO['0000002'])))),
        # FIXME still doesn't get the binding right
        intersectionOf(BFO['0000015'],
                       # FIXME nonLocal in time requires some time keeping device
                       # id some periodic phenomenon
                       restN(ilxtr.processHasContext, BFO['0000002'])),
       ),

    #oc_(rdflib.BNode(),
        #restN(ilxtr.hasAspect, asp.nonLocal),
        #restN(ilxtr.hasContext, ilxtr.materialEntity),
        # TODO that nonLocal's context should be the same...
       #),

    oc_(rdflib.BNode(),
        oECN(intersectionOf(ilxtr.materialEntity,
                            restN(ilxtr.hasAspect, asp.nonLocal))),
        #restN(ilxtr.hasContext, ),
        # this works because immaterial entities have to be anchored to some
        # internal frame which requires something with inertia which requires
        # a meterial entity...
        intersectionOf(ilxtr.materialEntity,
                       restN(partOf, ilxtr.compositeMaterialEntity)),
       ),
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
        blankc(owl.maxQualifiedCardinality,
               rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
        blankc(owl.onClass, BFO['0000004']))(b1)
    yield from r1

    b2 = rdflib.BNode()
    yield b, rdf.first, b2
    r2 = restG(
        blankc(owl.onProperty, ilxtr.hasPrimaryAspect),
        blankc(owl.maxQualifiedCardinality,
               rdflib.Literal(1, datatype=rdflib.XSD.nonNegativeInteger)),
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

methods_core = simpleOnt(filename=filename,
                         prefixes=prefixes,
                         imports=imports,
                         triples=triples,
                         comment=comment,
                         branch=branch,
                         _repo=_repo,
                         calling__file__=__file__,)

methods_core._graph.add_namespace('asp', str(asp))
methods_core._graph.add_namespace('ilxtr', str(ilxtr))  # FIXME why is this now showing up...
#methods_core._graph.add_namespace('tech', str(tech))
methods_core._graph.add_namespace('HBP_MEM', OntCuries['HBP_MEM'])


def main():
    # TODO aspects.ttl?
    collector.write()
    methods_core._graph.write()


if __name__ == '__main__':
    main()
