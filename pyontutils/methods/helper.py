from rdflib import Literal
from pyontutils.core import OntCuries, OntId, OntTerm
from pyontutils.core import simpleOnt
from pyontutils.namespaces import partOf
from pyontutils.namespaces import NIFRID, ilxtr, ilx, BFO
from pyontutils.namespaces import definition, hasPart
from pyontutils.combinators import unionOf, intersectionOf
from pyontutils.combinators import Restriction
from pyontutils.combinators import oc, oc_, oop, odp, olit, oec
from pyontutils.combinators import disjointUnionOf
from pyontutils.combinators import restrictions, restriction
from pyontutils.methods.core import methods_core, asp, tech, prot, prov, restN, oECN, branch
from pyontutils.closed_namespaces import owl, rdf, rdfs

###
#   methods helper (subset of the larger ontology to speed up development)
###

restHasValue = Restriction(None, owl.hasValue)

filename = 'methods-helper'
prefixes = ('BFO', 'ilxtr', 'NIFRID', 'RO', 'IAO', 'definition', 'hasParticipant', 'TEMP')
prefixes += ('TEMP', 'ilxtr', 'NIFRID', 'definition', 'realizes', 'hasRole',
            'hasParticipant', 'hasPart', 'hasInput', 'hasOutput', 'BFO',
            'CHEBI', 'GO', 'SO', 'NCBITaxon', 'UBERON', 'SAO', 'BIRNLEX',
            'NLX',
)
OntCuries['HBP_MEM'] = 'http://www.hbp.FIXME.org/hbp_measurement_methods/'
#OntCuries['HBP_MEM'] = 'http://www.hbp.FIXME.org/hbp_measurement_methods/'
#imports = NIFTTL['nif_backend.ttl'],
imports = methods_core.iri,
comment = 'helper for methods development'
_repo = True
debug = True

triples = (
    (tech.injection, owl.equivalentClass, OntTerm('BIRNLEX:2135')),
          )

triples += ( # protocols
            oc(prot.CLARITY, ilxtr.protocol),
            oc(prot.deepSequencing, ilxtr.protocol),
            oc(prot.sangerSequencing, ilxtr.protocol),
            oc(prot.shotgunSequencing, ilxtr.protocol),
            oc(prot.fMRI, ilxtr.protocol),
            oc(prot.dwMRI, ilxtr.protocol),
            oc(prot.DTI, ilxtr.protocol),
           )

triples += ( # information entity

    # information entities
    oc(ilxtr.informationEntity),
    olit(ilxtr.informationEntity, rdfs.label, 'information entity'),
    olit(ilxtr.informationEntity, definition, 'Any physically encoded information.'),

    oc(ilxtr.informationArtifact, ilxtr.informationEntity),
    oc(ilxtr.informationArtifact, BFO['0000031']),
    olit(ilxtr.informationArtifact, rdfs.label, 'information artifact'),
    olit(ilxtr.informationArtifact, definition,
         ('An information entity that has an explicit symbolic encoding '
          'which is distinct from the existence or being that it encodes.')),
    (ilxtr.informationArtifact, owl.equivalentClass, OntTerm('IAO:0000030', label='information content entity')),

    oc(ilxtr.protocol, ilxtr.informationEntity),
    olit(ilxtr.protocol, rdfs.label, 'protocol'),
    olit(ilxtr.protocol, NIFRID.synonym, 'technique specification'),

    oc(ilxtr.protocolArtifact, ilxtr.informationArtifact),
    (ilxtr.protocolArtifact, rdfs.subClassOf, ilxtr.protocol),
    olit(ilxtr.protocolArtifact, rdfs.label, 'protocol artifact'),

    oc(ilxtr.stereotaxiCoordinateSystem, ilxtr.informationEntity),

    # information artifacts
    oc(ilxtr.informationArtifact),  # FIXME entity vs artifact, i think clearly artifact by my def
    oc(ilxtr.image, ilxtr.informationArtifact),
    olit(ilxtr.image, rdfs.label, 'image (ilxtr)'),  # bloody iao
    olit(ilxtr.image,
         definition,
         ('A symbolic representation of some spatial or spatial-temporal '
          'aspect of a participant. Often takes the form of a 2d or 3d matrix '
          'that has some mapping to sensor space and may also be collected at '
          'multiple timepoints. Regardless of the ultimate format has some '
          'part that can be reduced to a two dimensional matrix.'  # TODO
         )),

    oc(ilxtr.photograph, ilxtr.image),
    oc(ilxtr.spatialFrequencyImageStack, ilxtr.image),

    oc(ilxtr.timeSeries, ilxtr.informationArtifact),
    olit(ilxtr.timeSeries, definition,
         'a series of numbers with a total order defined by sequential collection in time'),

    # TODO have parcellation-artifacts import methods-core?
    oc(ilxtr.parcellationArtifact, ilxtr.informationArtifact),
    oc(ilxtr.parcellationCoordinateSystem, ilxtr.parcellationArtifact),
    oc(ilxtr.parcellationCoordinateSystem, ilxtr.parcellationArtifact),
    oc(ilxtr.commonCoordinateFramework, ilxtr.parcellationCoordinateSystem),
    olit(ilxtr.commonCoordinateFramework, rdfs.label, 'common coordinate framework'),
    olit(ilxtr.commonCoordinateFramework, NIFRID.synonym, 'CCF', 'atlas coordinate framework'),
    oc(ilxtr.parcellationAtlas, ilxtr.informationArtifact),

    oc(ilxtr.axiom, ilxtr.informationEntity),
    oc(ilxtr.algorithem, ilxtr.informationEntity),
    oc(ilxtr.spikeSortingAlgorithem, ilxtr.informationEntity),
    oc(ilxtr.superResolutionAlgorithem, ilxtr.algorithem),
    oc(ilxtr.statisticalAlgorithem, ilxtr.algorithem),  # the old what counts as statistics question
    oc(ilxtr.inverseProblemAlgorithem, ilxtr.algorithem),
    oc(ilxtr.radonTransform, ilxtr.inverseProblemAlgorithem),

    oc(ilxtr.classificationCriteria, ilxtr.informationEntity),
    oc(ilxtr.identificationCriteria, ilxtr.informationEntity),

    oc(ilxtr.categoryNames, ilxtr.informationEntity),
    oc(ilxtr.categoryAssignments, ilxtr.informationEntity),
    oc(ilxtr.nameIdentityMapping, ilxtr.informationEntity),

)

triples += (
    # results
    oc(ilxtr.result),
    olit(ilxtr.result, definition,
         ('The result of a measurement.')),
    oop(ilxtr.resultAspect),
    (ilxtr.resultAspect, rdfs.domain, ilxtr.result),
    (ilxtr.resultAspect, rdfs.range, ilxtr.aspect),  # these are preferably units?
    odp(ilxtr.resultValue),

    oop(ilxtr.hasResult),  # or hadResult ...
    (ilxtr.hasResult, rdfs.subClassOf, prov.generated),
    (ilxtr.hasResult, rdfs.domain, ilxtr.protocolExecution),
    # FIXME this domain restriction may not work quite like we want it to
    # ideally we would like to take an instance of a material entity + an aspect
    # and bind the result to that pair, with some additional sematics outside owl
    # you could use [ a protc:Result; protc:onAspect asp:myAspect; protc:resultValue 100; protc:impl <some impl id>; protc:prov <id>]
    # we could then and lift that to [ a owl:Restriction; owl:onProperty asp:myAspect; owl:hasValue 100]
    # or we could create a new iri from the intersection of the aspect and the implementation or better yet the execution prov id ...
    (ilxtr.hasResult, rdfs.range, ilxtr.result),

    oc_(ilxtr.protocolExecution,
       oec(ilxtr.technique,
           *restrictions((ilxtr.isConstrainedBy, ilxtr.protocol),)),),
    (ilxtr.protocolExecution, rdfs.subClassOf, prov.Activity),
    olit(ilxtr.protocolExecution, rdfs.label, 'protocol execution'),
)

triples += (  # material entities

    ## material entity
    (ilxtr.materialEntity, owl.equivalentClass, BFO['0000040']),
    oc_(ilxtr.materialEntity,
        restriction(ilxtr.hasAspect, asp.livingness),
        restriction(ilxtr.hasAspect, asp['is'])),

    oc(ilxtr.compositeMaterialEntity, ilxtr.materialEntity),

    # more real than real
    oc(ilxtr.theObservableUniverse, ilxtr.compositeMaterialEntity),  # or is it a process...
    oc_(ilxtr.theObservableUniverse,
        restriction(ilxtr.hasExpAspect, asp.speedOfLight),
        restriction(ilxtr.hasExpAspect, asp.PlankAspect),
        restriction(ilxtr.hasExpAspect, asp.elementaryCharge),
        restriction(ilxtr.hasExpAspect, asp.JosephsonAspect),
        restriction(ilxtr.hasExpAspect, asp.vonKlitzingAspect),
        restriction(ilxtr.hasExpAspect, asp.GravitationalAspect),
        restriction(ilxtr.hasExpAspect, asp.BoltzmannAspect),
        restriction(ilxtr.hasExpAspect, asp.electronRestMass),
        restriction(ilxtr.hasExpAspect, asp.gravitationalCouplingAspect),
        restriction(ilxtr.hasExpAspect, asp.fineStructureAspect),
        restriction(ilxtr.hasExpAspect, asp.permittivityOfFreeSpace),
        restriction(ilxtr.hasExpAspect, asp.permeabilityOfFreeSpace),
        restriction(ilxtr.hasExpAspect, asp.impedanceOfFreeSpace),
        restriction(ilxtr.hasExpAspect, asp.fineStructureAspect),
        restriction(ilxtr.hasExpAspect, asp.CoulombsAspect),
        # more... FIXME some of these probably shouldn't count?
        # since they are/can be derived?
        # https://en.wikipedia.org/wiki/Physical_constant
       ),

    oc(ilxtr.physicalForce, ilxtr.materialEntity),
    oc(ilxtr.mechanicalForce, ilxtr.physicalForce),
    oc(ilxtr.electricalField, ilxtr.physicalForce),
    oc(ilxtr.magneticField, ilxtr.physicalForce),

    #oc_(OntTerm('NCBITaxon:1', label='ncbitaxon'), restriction(ilxtr.hasAspect, asp.livingness)),
    # this is technically correct, but misleading, because rocks also have asp.livingness
    # which evaluates to false, aspects are qualities, but they are not in and of themselves meaningful
    # because I can measure the livingness of a star, or define it, basically all material entities
    # have all aspects

    # FIXME a molecule of nucleic acid vs a sequence of molecules
    #  thingWithSequence VS thingThatCanFormPolymers

    oc(ilxtr.thingWithSequence, OntTerm('CHEBI:25367', term='molecule')),
    olit(ilxtr.thingWithSequence, rdfs.label, 'thing with molecular sequence'),

    oc(OntTerm('CHEBI:33696', label='nucleic acid'), ilxtr.thingWithSequence),  # FIXME should not have to put oc here, but byto[ito] becomes unhappy
    oc(ilxtr.nucleicAcid, ilxtr.molecule),
    (ilxtr.nucleicAcid, owl.equivalentClass, OntTerm('CHEBI:33696', label='nucleic acid')),
    oc(ilxtr.methylatedDNA, OntTerm('CHEBI:16991', term='DNA')),
    (ilxtr.DNA, owl.equivalentClass, OntTerm('CHEBI:16991', term='DNA')),
    oc(ilxtr.DNA, ilxtr.nucleicAcid),

    oc(ilxtr.molecule, ilxtr.materialEntity),

    oc(OntTerm('CHEBI:25367', label='molecule'), OntTerm('CHEBI:24431', label='chemical entity')),
    (ilxtr.molecule, owl.equivalentClass, OntTerm('CHEBI:25367', label='molecule')),
    oc(ilxtr.plasmidDNA, ilxtr.molecule),  # FIXME how do we model the physical manifestation of a sequence? 'SO:0000155'
    oc(ilxtr.primaryHeritableGeneticMaterial, ilxtr.molecule),
    oc(ilxtr.hybridizationProbe, ilxtr.molecule),
    oc(ilxtr.nucleicAcidLibrary, ilxtr.materialEntity),  # TODO

    # FIXME should probably be to a higher level go?
    # FIXME redundant when we import all of go
    (OntTerm('GO:0005615'), rdfs.subClassOf, OntTerm('GO:0005575', label='cellular_component')),
    (OntTerm('GO:0005622'), rdfs.subClassOf, OntTerm('GO:0005575', label='cellular_component')),
    oc(OntTerm('SAO:1813327414', label='Cell'), ilxtr.materialEntity),
    (ilxtr.cell, owl.equivalentClass, OntTerm('SAO:1813327414', label='Cell')),
    oc_(OntTerm('SAO:1813327414', label='Cell'),
        restriction(hasPart, OntTerm('GO:0005575', label='cellular_component'))),  # inputs also need to input all their parts
    oc(ilxtr.cellSoma, OntTerm('GO:0005575')),
    oc(ilxtr.synapse, OntTerm('GO:0005575')),
    oc(OntTerm('GO:0044464'), OntTerm('GO:0005575')),
    oc(OntId('CHEBI:33697'), OntTerm('CHEBI:33696', label='nucleic acid')),
    (ilxtr.RNA, owl.equivalentClass, OntId('CHEBI:33697')),
    (ilxtr.RNA, rdfs.subClassOf, ilxtr.nucleicAcid),
    #oc(ilxtr.mRNA, OntTerm('CHEBI:33697', label='RNA')),
    oc(OntTerm('SO:0000234', label='mRNA'), OntId('CHEBI:33697')),
    (ilxtr.mRNA, owl.equivalentClass, OntTerm('SO:0000234', label='mRNA')),  # FIXME role?

    (OntTerm('GO:0005575', label='cellular_component'), rdfs.subClassOf, ilxtr.physiologicalSystem),
    # FIXME owl:sameAs is NOT for generic iris >_<
    #oc(ilxtr.physiologicalSystem, ilxtr.materialEntity),
    # FIXME what about things that were synthesized entirely?
    # how about... constrainedBy _information_ derived from some organism?
    # a protein is indeed constrained by that information regardless of
    # whether it was synthesized or not...
    #oc(OntTerm('NCBITaxon:1'), ilxtr.materialEntity),  # needed to accomodate deadness?
    oc(ilxtr.physiologicalSystem, ilxtr.materialEntity),
    oc_(ilxtr.physiologicalSystem,
        unionOf(OntTerm('NCBITaxon:1'),
                restN(partOf, OntTerm('NCBITaxon:1')))),
        #oec(ilxtr.materialEntity,  # FIXME in vitro...
            #restN(partOf, OntTerm('NCBITaxon:1'))
           #)),
    oc(OntTerm('NCBITaxon:1'), ilxtr.physiologicalSystem),  # needed to accomodate deadness?

    #oc_(ilxtr.physiologicalSystemDisjointWithOrganism,
        #oec(ilxtr.physiologicalSystem)
       #),
    #(ilxtr.physiologicalSystemDisjointWithOrganism, owl.disjointWith, OntTerm('NCBITaxon:1')),
    oc(ilxtr.viralParticle, ilxtr.physiologicalSystem),
    oc(ilxtr.AAVretro, ilxtr.viralParticle),

    oc(OntTerm('UBERON:0000465'), ilxtr.materialEntity),
    oc(OntTerm('UBERON:0000955'), OntTerm('UBERON:0000465')),
    oc(OntTerm('UBERON:0007798'), OntTerm('UBERON:0000465')),
    oc(OntTerm('UBERON:0001049', label='neural tube'), OntTerm('UBERON:0000465')),
    oc(OntTerm('UBERON:0000479', label='tissue'), OntTerm('UBERON:0000465')),

    oc_(ilxtr.partOfSomePrimaryInput,
        oECN(intersectionOf(
            ilxtr.materialEntity,
            restN(partOf,
                  restN(ilxtr.primaryInputIn,
                        ilxtr.technique))))),  # it would be nice to say the technique in question...

    oc(ilxtr.section, ilxtr.materialEntity),
    oc_(ilxtr.section,
        intersectionOf(ilxtr.partOfSomePrimaryInput,
                       restN(partOf, ilxtr.primaryInputOfThisInstanceOfTechnique), # FIXME
                       restN(ilxtr.hasAspect, asp.flatness),  # FIXME has aspect needs more love
                      )),
    oc(ilxtr.thinSection, ilxtr.section),
    oc_(ilxtr.thinSection,
        # has value 'small'
        restriction(ilxtr.hasAspect, asp.thickness)),
    oc(ilxtr.veryThinSection, ilxtr.section),
    oc(ilxtr.brainSlice, ilxtr.section),
    oc(ilxtr.acuteBrainSlice, ilxtr.physiologicalSystem),
    oc(ilxtr.food_and_water, ilxtr.materialEntity),
    oc(ilxtr.food, ilxtr.food_and_water),  # TODO edible organic matter with variable nutritional value depending on the organism
    oc(ilxtr.highFatDiet, ilxtr.food),
    oc(ilxtr.DIODiet, ilxtr.highFatDiet),
    oc(ilx['researchdiets/uris/productnumber/D12492'], ilxtr.DIODiet),

    oc(ilxtr.water, ilxtr.materialEntity),
    olit(ilxtr.water, rdfs.label, 'water (bulk)'),
    olit(ilxtr.water, definition,
         'A bulk volume of water, as opposed to molecular water.'),
    oc_(ilxtr.water,
        intersectionOf(restN(hasPart, OntTerm('CHEBI:15377', label='water')),
                       restN(hasPart, ilxtr.electrolytes),  # FIXME and other impurities...
                       restN(ilxtr.hasAspect, asp.volume),
                       restN(ilxtr.hasAspectValue, ilxtr.notBottom))),
    oc(ilxtr.electricalGround, ilxtr.materialEntity),
    oc(ilxtr.microscope, ilxtr.materialEntity),
    oc(ilxtr.lightMicroscope, ilxtr.microscope),
    (ilxtr.lightMicroscope, owl.equivalentClass, OntTerm('BIRNLEX:2112', label='Optical microscope')),
    oc(OntTerm('BIRNLEX:2041', label='Electron microscope', synonyms=[]), ilxtr.microscope),
    (OntTerm('BIRNLEX:2029', label='Confocal microscope'), rdfs.subClassOf, ilxtr.lightMicroscope),
    oc(ilxtr.DICmicroscope, ilxtr.lightMicroscope),
    oc(ilxtr.microtome, ilxtr.materialEntity),
    oc(ilxtr.serialBlockfaceMicrotome, ilxtr.microtome),
    oc(ilxtr.ultramicrotome, ilxtr.microtome),
    oc(ilxtr.serialBlockfaceUltraMicrotome, ilxtr.ultramicrotome),
    oc(ilxtr.stereotax, ilxtr.materialEntity),
    oc(ilxtr.centrifuge, ilxtr.materialEntity),
    oc(ilxtr.ultracentrifuge, ilxtr.centrifuge),
    oc(ilxtr.cuttingTool, ilxtr.materialEntity),
    oc(ilxtr.IRCamera, ilxtr.materialEntity),
    oc(ilxtr.recordingElectrode, ilxtr.materialEntity),
    oc(ilxtr.singleElectrode, ilxtr.recordingElectrode),
    oc(ilxtr.multiElectrode, ilxtr.recordingElectrode),
    oc(ilxtr.laminarProbe, ilxtr.multiElectrode),
    oc(ilxtr.multiElectrodeArray, ilxtr.multiElectrode),
    oc(ilxtr.ephysRig, ilxtr.materialEntity),
    oc(ilxtr.inVitroEphysRig, ilxtr.ephysRig),

    oc(ilxtr.microPipette, ilxtr.materialEntity),
    oc(ilxtr.patchPipette, ilxtr.microPipette),

    oc(ilxtr.patchElectrode, ilxtr.recordingElectrode),
    oc_(ilxtr.patchElectrode,
        intersectionOf(restN(hasPart, ilxtr.singleElectrode),
                       restN(hasPart, ilxtr.patchPipette))),

    oc(ilxtr.sharpMicroPipette, ilxtr.microPipette),
    oc(ilxtr.sharpElectrode, ilxtr.recordingElectrode),
    oc_(ilxtr.sharpElectrode,
        intersectionOf(restN(hasPart, ilxtr.singleElectrode),
                       restN(hasPart, ilxtr.sharpMicroPipette))),

    oc(ilxtr.contrastAgen, ilxtr.materialEntity),

    oc(ilxtr.inductionFactor, ilxtr.materialEntity),

    oc(ilxtr.bathSolution, ilxtr.materialEntity),

    oc(ilxtr.photons, ilxtr.materialEntity),
    oc_(ilxtr.photons,
        disjointUnionOf(ilxtr.radiowaves,
                        ilxtr.microwaves,
                        ilxtr.infaredLight,
                        ilxtr.visibleLight,
                        ilxtr.ultravioletLight,
                        ilxtr.xrays,
                        ilxtr.gammarays)
       ),
    oc(ilxtr.radiowaves, ilxtr.photons),
    oc(ilxtr.microwaves, ilxtr.photons),
    oc(ilxtr.infaredLight, ilxtr.photons),
    oc(ilxtr.visibleLight, ilxtr.photons),
    oc(ilxtr.ultravioletLight, ilxtr.photons),
    oc(ilxtr.xrays, ilxtr.photons),
    oc(ilxtr.gammarays, ilxtr.photons),
    #oc(ilxtr.infaredLight, ilxtr.photons),
    #oc(ilxtr.visibleLight, ilxtr.photons),
    #oc(ilxtr.xrays, ilxtr.photons),
    (ilxtr.positron, owl.equivalentClass, OntTerm('CHEBI:30225')),

    oc(ilxtr.tissue, ilxtr.materialEntity),
    oc(ilxtr.axon, ilxtr.materialEntity),
    oc(ilxtr.cellMembrane, ilxtr.materialEntity),
    oc(ilxtr.building, ilxtr.materialEntity),
    oc(ilxtr.electrolytes, ilxtr.materialEntity),

    oc(ilxtr.contrastAgent, ilxtr.materialEntity),  # FIXME this should be a role?
    oc_(ilxtr.contrastAgent, restriction(ilxtr.hasAspect, asp.contrast)),
    oc(ilxtr.detectedPhenomena, ilxtr.materialEntity),  # ie a phenomena that we know how to detect
    oc(ilxtr.fluorescentMolecule, ilxtr.materialEntity),

    oc(ilxtr.cultureMedia, ilxtr.materialEntity),

)

triples += (  # changes
    oc(ilxtr.positive, ilxtr.changeType),
    oc(ilxtr.negative, ilxtr.changeType),
    (ilxtr.negative, owl.disjointWith, ilxtr.positive),

    oc(ilxtr.positiveNonZero, ilxtr.nonZero),
    oc(ilxtr.positiveNonZero, ilxtr.positive),
    #oc_(ilxtr.positiveNonZero,
        #intersectionOf(ilxtr.positive,
                       #ilxtr.nonZero),
        #blankc(owl.disjointWith, ilxtr.zero)),

    oc(ilxtr.negativeNonZero, ilxtr.nonZero),
    oc(ilxtr.negativeNonZero, ilxtr.negative),
    #oc_(ilxtr.negativeNonZero,
        #intersectionOf(ilxtr.negative,
                       #ilxtr.nonZero),
        #blankc(owl.disjointWith, ilxtr.zero)),

    oc(ilxtr.nonZero, ilxtr.changeType),
    oc_(ilxtr.nonZero, disjointUnionOf(ilxtr.negativeNonZero, ilxtr.positiveNonZero)),
    oc(ilxtr.zero, ilxtr.changeType),
    (ilxtr.zero, owl.disjointWith, ilxtr.nonZero),
)

triples += (  # aspects

    # local _to this universe_
    oc(asp.speedOfLight, asp.Local),  # in a vacuum, as far as we know this is invariant in all universes
    oc(asp.PlankAspect, ilxtr.aspect),
    oc(asp.elementaryCharge, ilxtr.aspect),
    oc(asp.JosephsonAspect, ilxtr.aspect),
    oc(asp.vonKlitzingAspect, ilxtr.aspect),
    oc(asp.GravitationalAspect, ilxtr.aspect),
    oc(asp.BoltzmannAspect, ilxtr.aspect),
    oc(asp.electronRestMass, ilxtr.aspect),
    oc(asp.gravitationalCouplingAspect, ilxtr.aspect),
    oc(asp.fineStructureAspect, ilxtr.aspect),
    oc(asp.permittivityOfFreeSpace, ilxtr.aspect),
    oc(asp.permeabilityOfFreeSpace, ilxtr.aspect),
    oc(asp.impedanceOfFreeSpace, ilxtr.aspect),
    oc(asp.fineStructureAspect, ilxtr.aspect),
    oc(asp.CoulombsAspect, ilxtr.aspect),

    # aspect value

    oc(ilxtr.aspectBottom),  # TODO disjointness etc.
    olit(ilxtr.aspectBottom, rdfs.label, 'aspect bottom'),
    olit(ilxtr.aspectBottom, definition,
         ('The result of attempting to measurement or actualize '
          'an aspect bound to a being for which the operational '
          'definition of the aspect makes it impossible to evaluate '
          '(as in function evaluation). For examples '
          '(*: angles-on-head-of-pin count) -> aspectBottom '
          'or even (: angels-on-head-of-pin count) -> aspectBottom '
          'since one cannot even bind the notion of numbers to the '
          'non-being much less actually attempt to make such a measurement.')),

    # isness
    oc(asp['is'], asp.Local),
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
          'good examples where partial beingness is a useful concept, use as a [0,1] aspect would be '
          'encouraged.')),
    olit(asp['is'], rdfs.comment,
         ('There are cases where the value could be ? depending on how one '
          'operationalizes certain concepts from quantum physics. Note also that '
          'isness will be directly affected by the choice of the operational defintion. '
          'Because of the scope of this ontology, there are implicit decisions about the nature '
          'of certain operational definitions, such as livingness, which imply that our '
          'operational definition for isness is invariant to dead.'
         )),

    oc(asp.amount, asp['is']),  # this implies that asp.mass is asp.is
    oc(asp['count'], asp.amount),
    # instantaneous vs over a time interval
    # interestingly if you ignore time then the idea of
    # 'counting' similar events is entirely consistent
    # so hasPrimaryAspect_dAdT xsd.NonNegativeInteger
    # is valid

    # location/allocation
    # NOTE allocation is an aspect, location is NOT an aspect
    # allocation is an aspect of a composite being where the
    # location of each of its parts can be considered to be
    # something directly measurable about the composite being
    # for example a pile of sand or a set of grains of sand
    # can have an allocation based only by counting the members
    oc(asp.spatial, asp.nonLocal),
    oc(asp.location, asp.spatial),
    # you cannot measure the location of something
    # you can only measure the location of something relative to something else
    # our model assumes that there is no privilidged reference frame in this universe
    oc(asp.direction, asp.spatial),
    oc(asp.locationInAtlas, asp.location),
    oc_(asp.locationInAtlas, restriction(ilxtr.hasContext, ilxtr.atlasLandmarks)),  # morphology matching atlas?

    oc(asp.time, asp.nonLocal),  # requires some periodic phenomena to create the ordinals
    oc_(asp.time,
        restriction(ilxtr.hasMaterialContext, ilxtr.periodicPhenomena),
        restriction(ilxtr.hasAspectContext, asp.startTime)),  # FIXME how to deal with this as a zero
    oc(asp.startTime, asp.time),  # point in time aspects are all defined
    oc(asp.endTime, asp.time),
    oc(asp.timeInterval, asp.nonLocal),
    oc_(asp.timeInterval,  # invervals only need on anchor
        restriction(ilxtr.hasMaterialContext, ilxtr.periodicPhenomena),
        restriction(ilxtr.hasAspectContext, asp.startTime),
        restriction(ilxtr.hasAspectContext, asp.endTime)),
    olit(asp.timeInterval, NIFRID.symomym, 'duration'),

    # no teleportation allowed unless you are a photon in its own reference frame
    oc(asp.startLocation, asp.location),
    oc_(asp.startLocation,
        restriction(ilxtr.hasAspectContext,
                    asp.startTime)),

    oc(asp.endLocation, asp.location),
    oc_(asp.endLocation,
        restriction(ilxtr.hasAspectContext,
                    asp.endTime)),

    oc(asp.name, asp.nonLocal),
    oc(asp.identity, asp.Local),
    oc_(asp.name,
        restriction(ilxtr.isQualifiedFormOf, asp.identity),
        restriction(ilxtr.hasInformationContext, ilxtr.nameIdentityMapping)),

    oc(asp.category, asp.Local),
    oc(asp.categoryAssigned, asp.nonLocal),
    # FIXME categories are conceptual space... how to cope...
    oc_(asp.categoryAssigned,
        restriction(ilxtr.isQualifiedFormOf, asp.category),
        intersectionOf(restN(ilxtr.hasInformationContext, ilxtr.categoryNames),
                       restN(ilxtr.hasInformationContext, ilxtr.categoryAssignments))),

    oc(asp.allocation, asp.location),  # FIXME not clear whether this is local or nonlocal
    # seems non-local to me...
    olit(asp.allocation, definition,
         ('Allocation is the amount of something in a given place '
          'rather than the total universal amount of a thing. '
          'For example if I move 100 grains of salt from a container '
          'to a scale, I have changed the allocation of the salt (solid). '
          'If I dissolve the salt in water then I have negatively impacted '
          'the amount of total salt (solid) in the universe since that salt '
          'is now ionized in solution.')),

    oc(asp.proportion, asp.allocation),

    oc(asp.homogenaity, asp.allocation),
    oc(asp.heterogenity, asp.allocation),
    (asp.homogenaity, owl.inverseOf, asp.heterogenity),

    #oc(asp.isClassifiedAs, asp['is']),  # FIXME not quite right, renaming is different then identity
    # this is only an isness in the case where there are a finite and fixed number of types
    #olit(asp.isClassifiedAs, rdfs.label, 'is classified as'),
    #olit(asp.isClassifiedAs, NIFRID.synonym,
         #'is named as', 'has operational definition with inclusion criteria that names thing as'),

    oc(asp.flatness, asp.Local),
    olit(asp.flatness, rdfs.label, 'flatness'),  # bind domain is some surface? (ie nonbottom)
    olit(asp.flatness, NIFRID.synonym, 'flatness aspect'),
    olit(asp.flatness, definition,
         ('How flat a thing is. There are a huge variety of operational '
          'definitions depending on the type of thing in question.')),

    oc(asp.weight, asp.Local),  # TODO 'PATO:0000128'
    olit(asp.weight, rdfs.label, 'weight'),
    olit(asp.weight, NIFRID.synonym,
         'weight on earth',
         'weight aspect',
         'weight aspect on earth'),
    # ICK this is nasty
    oc_(asp.weight, intersectionOf(restN(ilxtr.hasQualifiedForm,
                                         asp.weightUnqualified),
                                   restN(ilxtr.qualifyingValue,
                                         intersectionOf(asp.acceleration,
                                                        restHasValue(ilxtr.hasMeasuredValue,
                                                                     Literal('9.8 m/s^2')))))),

    oc(asp.weightQualified, asp.nonLocal),
    oc_(asp.weightQualified, restriction(ilxtr.hasAspectContext, asp.acceleration)),
    olit(asp.weightQualified, rdfs.label, 'weight qualified'),

    oc_(asp.weightOnJupiter, intersectionOf(restN(ilxtr.hasQualifiedForm,
                                                  asp.weightUnqualified),
                                            restN(ilxtr.qualifyingValue,
                                                  intersectionOf(asp.acceleration,
                                                                 restHasValue(ilxtr.hasMeasuredValue,
                                                                              Literal('24.5 m/s^2')))))),

    oc(asp.livingness, asp.Local),
    oc(asp.aliveness, asp.Local),  # PATO:0001421
    oc(asp.deadness, asp.Local),  # PATO:0001422
    (asp.aliveness, owl.disjointWith, asp.deadness),  # this holds for any single operational definition
    #((hasAspect some livingness) and (hasAspectValue value true)) DisjointWith: ((hasAspect some livingness) and (hasAspectValue value false))

    # functional/stateful (the conflation here is amusing)
    oc(asp.boundFunctionalAspect, asp.nonLocal),
    olit(asp.boundFunctionalAspect, rdfs.label, 'bound functional aspect'),
    # TODO
    # the 'functionality' of the aspect is going to be qualified by the
    # subject to which it is bound...
    # this is equivalentClass intersectionOf material entity
    # restriction
    # onProperty isFunctional
    # has qualified role?
    #
    oc(asp.behavioral, asp.nonLocal),
    # depends on a spatial structure over time so is nonLocal
    # also cannot be measured directly
    # FIXME how is behavior nonLocal while elsticity is Local?
    #  answer: elasticity depends on space not time
    # both depend on some measurement made over time but are in theory
    # time invariant properties of the named thing in question?
    # ie they are dispositions since they are literally our experimental phenotypes
    # then again we just assume (based on lots of evidence) that the mass of a brick
    # doesn't magically change when we are not measuring it...
    # consider a reaction time test, it is a temporal test that is beahvioral
    # only in so far as the timepoints that it marks signify some interaction(s)
    # between a thing and the measurement/timing system

    oc(asp.physiological, asp.Local),  # FIXME vs ilxtr.physiologicalSystem? pretty sure is nonLocal?

    oc(asp.sequence, asp.Local),
    #(OntTerm('SO:0000001', label='region', synonyms=['sequence']), rdfs.subClassOf, asp.sequence), this very much does not work...
    oc(asp.methylationSequence, asp.sequence),
    oc_(asp.methylationSequence,
        restriction(ilxtr.knownUnderlyingProcess,  # TODO namedUnderlyingProcess??
                    OntTerm('GO:0010424', label='DNA methylation on cytosine within a CG sequence'))),

    oc(asp.sensory, asp.Local),
    oc(asp.vision, asp.sensory),  # FIXME asp.canSee

    oc(asp.anySpatioTemporalMeasure, ilxtr.aspect),  # FIXME
    oc(asp.electromagnetic, ilxtr.aspect),
    oc(asp.electrical, asp.electromagnetic),
    oc(asp.voltage, asp.electrical),
    oc(asp.voltage, asp.nonLocal),
    oc_(asp.voltage, restriction(ilxtr.hasMaterialContext, ilxtr.electricalGround)),
    oc(asp.junctionPotential, asp.voltage),
    oc(asp.current, asp.electrical),
    oc(asp.current, asp.nonLocal),
    oc(asp.charge, asp.electrical),
    oc(asp.resistance, asp.electrical),
    oc(asp.resistance, asp.Local),
    oc(asp.magnetic, asp.electromagnetic),
    olit(asp.magnetic, rdfs.label, 'magnetic (ilxtr)'),

    oc(asp.mass, asp.Local),
    olit(asp.mass, rdfs.label, 'mass'),
    olit(asp.mass, NIFRID.synonym, 'rest mass'),
    oc(asp.massRelativistic, asp.nonLocal),
    oc(asp.energy, asp.nonLocal),
    oc(asp.velocity, asp.nonLocal),
    oc(asp.momentum, asp.nonLocal),
    oc(asp.acceleration, asp.nonLocal),  # frame of reference issues
    oc(asp.force, asp.nonLocal),

    oc(asp.informationEntropy, asp.Local),
    oc(asp.elasticity, asp.Local),
    oc(asp.stiffness, asp.Local),
    olit(asp.stiffness, rdfs.label, 'stiffness'),
    olit(asp.stiffness, NIFRID.synonym, 'mechanical rigidity'),
    oc(asp.spectrum, asp.Local),
    oc(asp.spontaneousChangeInStructure, asp.Local),
    oc(asp.connectivity, asp.Local),
    oc(asp.physicalOrderedness, asp.Local),
    oc(asp.latticePeriodicity, asp.physicalOrderedness),  # physical order

    #oc(asp.functional, ilxtr.aspect),  # asp.functional is not the right way to model this
    #olit(ilxtr.functionalAspectRole, definition,
         #('A functional aspect is any aspect that can be used to define ')),
    oc(asp.biologicalActivity, asp.Local),  # TODO very broad from enyme activity to calories burned
    #oc(asp.circadianPhase, asp.biologicalActivity),
    oc(asp.circadianPhase, asp.Local),  # FIXME hrm... time as a proxy for biological state?

    oc(asp.sensitivity, asp.nonLocal),
    # FIXME issue with sensitivity and the 'towards' relation

    #oc(asp.functionalDefinition, asp['is']),  # TODO not quite right?
    oc(asp.functionalDefinition, asp.nonLocal),
    oc(asp.permeability, asp.functionalDefinition),  # changes some functional property so is thus an isness?

    oc(asp.transparency, asp.nonLocal),  # also not direct...
    oc_(asp.transparency,
        restriction(ilxtr.hasMaterialContext, ilxtr.interactingPhenomena),
        restriction(ilxtr.hasComplementAspect, asp.opacity)),
    oc(asp.opacity, asp.nonLocal),
    oc_(asp.opacity,
        restriction(ilxtr.hasMaterialContext, ilxtr.interactingPhenomena),
        restriction(ilxtr.hasComplementAspect, asp.transparency)),

    oc(asp.dynamicRange, asp.nonLocal),  # dynamic range to what?
    oc(asp.contrast, asp.nonLocal),  # TODO what is this more specifically? this is derived ...
    # contrast is always qualified by some detecting phenomena
    oc_(asp.contrast,
        restriction(ilxtr.hasMaterialContext, ilxtr.interactingPhenomena),
        restriction(ilxtr.hasAspectContext, asp.dynamicRange)),

    oc(asp.density, asp.Local),  # local but not directly measurable

    oc(asp.direct, asp.Local),  # FIXME don't think we are going to use this...
    olit(asp.direct, definition,
         'An aspect that can be measured directly in a single instant in time. '
         'Note that these are in principle direct, the operational definition '
         'may mean that in reality they were not measured directly.'
         'Anything with time units is not direct. '
         'In theory a count/amount of a complex entity can be direct. Whether it '
         'is possible in reality to actually accomplish such a thing is another '
         'question altogether.'),

    # FIXME need a better way to model the 'in principle direct'
    # or more accurately 'can never be measured directly'
    #oc(asp.mass, asp.direct),
    oc(asp['count'], asp.Local),  # this is the universal count on name binding
    oc(asp.volume, asp.Local),  # NOTE these are all _rest_ values ignoring relativity
    oc(asp.length, asp.Local),  # distance is the non-direct version because the start or end point must be known as well
    olit(asp.length, rdfs.comment, 'This is rest-length.'),
    # NOTE all unitifications are nonLocal because they depend on the measurement tool barring demonstration of some invariant
    oc(asp.size, asp.Local),
    oc(asp.radius, asp.Local),
    oc(asp.diametere, asp.Local),
    oc(asp.boundingRadius, asp.Local),

    oc(asp.lengthRelativistic, asp.nonLocal),
    oc(asp.volumeRelativistic, asp.nonLocal),

    oc(asp.orientation, asp.spatial),
    oc_(asp.orientation,
        restriction(ilxtr.hasMaterialContext,
                    ilxtr.measurableReferenceFrame)),

    oc(asp.thickness, asp.nonLocal),
    oc_(asp.thickness,
        restriction(ilxtr.hasAspectContext, asp.orientation)),

    oc(asp.distance, asp.nonLocal),
    oc(asp.distanceFromSoma, asp.distance),
    oc_(asp.distanceFromSoma, restriction(ilxtr.hasMaterialContext, ilxtr.cellSoma)),

    # all of these are questionable because they depend on some
    # measurement process which has a tau
    oc(asp.temperature, asp.Local),

    oc(asp.boilingPoint, asp.nonLocal),  # tripple point!
    oc_(asp.boilingPoint, restriction(ilxtr.hasAspectContext, asp.pressure)),
    #oc_(asp.boilingPoint, restN(ilxtr.hasContext, asp.pressure)) FIXME

    oc(asp.epitopePresent, asp.Local),  # true predicates are always local by definition
    oc(asp.complementSequencePresent, asp.Local),
    oc(asp.condensationPoint, asp.nonLocal),

    oc(asp.lumenance, asp.Local),

    oc(asp.shape, asp.Local),
    # TODO also need the constants...

    oc(asp.nuclearMagneticResonance, asp.nonLocal),
    oc_(asp.nuclearMagneticResonance,
        # TODO hasMaterialAspectContext binding the frequency and the strenght respectively
        restriction(ilxtr.hasMaterialContext, ilxtr.magneticField),
        restriction(ilxtr.hasMaterialContext, ilxtr.radiowaves)),

    oc(asp.concentration, asp.nonLocal),
    oc_(asp.concentration,
        restriction(ilxtr.hasMaterialContext, ilxtr.solvent)),
)

triples += (
    # tracing
    oop(ilxtr.hasTracingDirection),
    oop(ilxtr.hasTracingTransportType),
    oop(ilxtr.hasTracingUptakeStructure),
    #oop(ilxtr.hasTracingStartLocation),  # genetic is both since there is no 'uptake', UptakeStructure was old name
    # FIXME this isnt' StartLocation, it really is uptake structures
    # cell soma, axons, boutons, dendrites

    oop(ilxtr.hasDeliveryVector),  # FIXME similar terms already exist maybe? DNA delivery via ...
    # iuep, virus, germ line

    # the proper model requires the use of negative axioms for maximum power
    # we have to state that rabies in this prep _does not go_ anterograde (for example)
    oc(ilxtr.anterograde, ilxtr.aspect),
    oc(ilxtr.retrograde, ilxtr.aspect),

    oc(ilxtr.movesViaActiveTransport, ilxtr.aspect),  # implies in vivo
    oc(ilxtr.movesViaPassiveTransport, ilxtr.aspect),
    # FIXME djw may not be accurate, some things passively transported could also be actively transported...
    # the asymmetirc version which is 'requiresActiveTransport' might be an alternative
    (ilxtr.movesViaActiveTransport, owl.disjointWith, ilxtr.movesViaPassiveTransport),

    # FIXME cellLabel conflates contrast with movement/uptake logic
    oc(ilxtr.cellLabel, ilxtr.contrastAgent),
    olit(ilxtr.cellLabel, NIFRID.synonym, 'tracer'),  # FIXME why does this fail?
    #(ilxtr.cellLabel, NIFRID.synonym, Literal('tracer')),
    oc(ilxtr.inertLabel, ilxtr.cellLabel),
    oc(ilxtr.activeLabel, ilxtr.cellLabel),  # aka geneticLabel, but there could be other active labels
    oc(ilxtr.functionalLabel, ilxtr.activeLabel),  # implies in vivo
    oc(ilxtr.modifierLabel, ilxtr.activeLabel),  # aka control label
    oc(ilxtr.expressionModifierLabel, ilxtr.modifierLabel),
    oc(ilxtr.spreadModifierLabel, ilxtr.modifierLabel),

    (ilxtr.cellLabel, ilxtr.hasTracingTransportType, ilxtr.movesVia_Transport),  # FIXME need a unionOf here probably
    (ilxtr.cellLabel, ilxtr.hasTracingDirection, ilxtr.someDirection),  # FIXME need a unionOf here probably
    (ilxtr.cellLabel, ilxtr.hasTracingStartLocation, ilxtr.nervousSystemRegion),  # FIXME find correct UBERON id
    (ilxtr.activeLabel, ilxtr.hasDeliveryVector, ilxtr.someVector),

    (ilxtr.interLabel, owl.disjointWith, ilxtr.activeLabel),
)

# FIXME cellLabel is tracer/logic + contrast/color??!
def cellLabel(id, label, transportType, directions=tuple(), uptakeStructures=tuple(), synonyms=tuple()):
    yield id, rdf.type, owl.Class
    yield id, rdfs.subClassOf, ilxtr.cellLabel
    yield id, rdfs.label, rdflib.Literal(label)
    yield id, ilxtr.hasTracingTransportType, transportType
    yield from ((id, ilxtr.hasTracingDirection, d) for d in directions)
    yield from ((id, ilxtr.hasUptakeStructure, u) for u in updateStructures)
    yield from ((id, NIFRID.synonym, s) for s in synonyms)

triples += tuple()
(
    # cell labels
    # 'PR:000021959' is this really ctb?

    'ctb'
    'fg' 'NLXMOL:1012018'

    'AAV8-hSyn-FLEX-TVA-P2A-GFP-2A-oG'
    'AAVretro-EF1a-Cre'
    'EnvA G-deleted rabies RVdG-4mCherry'
    'EnvA G-deleted rabies dsRedXpress'
    'aav-gfp'
    'aav-rfp'
    'aav-tdTomato'
    'ctb-488' 'CHEBI:52661'
    'ctb-488+smRabies-HA'
    'ctb-555' 'CHEBI:52673'
    'ctb-555+smRabies'
    'ctb-647' 'CHEBI:137394'
    'ctb-647+smRabies-OLLAS'
    'phal-647' 'CHEBI:137394'
    # amusment regarding dashes... PHA-L -> PHAL
    'https://www.ncbi.nlm.nih.gov/pubmed/2391562'
)

methods_helper = simpleOnt(filename=filename,
                           prefixes=prefixes,
                           imports=imports,
                           triples=triples,
                           comment=comment,
                           branch=branch,
                           _repo=_repo)


def main():
    methods_helper._graph.add_namespace('asp', str(asp))
    methods_helper._graph.add_namespace('ilxtr', str(ilxtr))  # FIXME why is this now showing up...
    methods_helper._graph.add_namespace('prot', str(prot))
    methods_helper._graph.add_namespace('tech', str(tech))
    methods_helper._graph.add_namespace('HBP_MEM', OntCuries['HBP_MEM'])
    methods_helper._graph.write()  # note to self, simpleOnt calls write as well
