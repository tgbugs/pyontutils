# work for methods/techniques/measures/protocols/datatypes
Any documents related to methodology should go here.

# Files

## Python
* [Core](https://github.com/tgbugs/pyontutils/blob/master/nifstd/nifstd_tools/methods/core.py)
* [Helper](https://github.com/tgbugs/pyontutils/blob/master/nifstd/nifstd_tools/methods/helper.py)
* [Full](https://github.com/tgbugs/pyontutils/blob/master/nifstd/nifstd_tools/methods/__init__.py)

## turtle
* [Core](https://github.com/SciCrunch/NIF-Ontology/blob/methods/ttl/methods-core.ttl)
* [Helper](https://github.com/SciCrunch/NIF-Ontology/blob/methods/ttl/methods-helper.ttl)
* [Full](https://github.com/SciCrunch/NIF-Ontology/blob/methods/ttl/methods.ttl)

# protio
`protio` is a helper language that simplifies the object property madness for atomic techniques.
It can be found [here](https://github.com/tgbugs/protc/tree/master/protc-tools-lib/protio)
in the [protc](https://github.com/tgbugs/protc) repository.  
Some examples are in [test.rkt](https://github.com/tgbugs/protc/blob/master/protc-tools-lib/protio/test.rkt)  
A full list can be generated using [gen.rkt](https://github.com/tgbugs/protc/blob/master/protc-tools-lib/protio/gen.rkt).

# Use cases
1. Tagging ephys data
2. Tagging fMRI data

# Collected thoughts/working draft
My initial work to provide a consistent view of methodology lives in [methods_isa.graphml](./methods_isa.graphml).
The initial version has a collection of thoughts which need to be refined.
Some parts of it were developed working directly with curators.
To obtain a ttl version of the file and generate hierarchies run `graphml_to_ttl methods_isa.graphml`. 
(`graphml_to_ttl` is installed by pyontutils).

## Tractable high level categories
1. techniques/methods (turns out pretty much every source I can find does not distinguish between these words)  
   Could map these to 4. with `employedInParadigm` or something...
   Alternately, could give up on 4 altogether and make 'microscopy' a synonym for 'microscopy technique' to
   make life easier for users and curators.

   One issue to consider here is how to deal with classes that are techniques vs classes that are collections
   of many different techniques which are 'used in'/'used by'/'employed by' that technique, but are not actually 'subClassOf'.

   I think that this distinction between methods that 'employ'/'employs' (continuant has part?) techniques
   (but are not really techniques themselves), and the techniques themselves may be what I was trying to
   get at with the distinction that I was making between methods and techniques in the past where methods
   were 'named' by their output (turns out that is incorrect).

   If we classify techniques (skills?) based on what the executor has to do/know/learn what do we get?
   Seems like the intersection between a set of tools and what they are employed on.
   Machine interaction -> twiddling, screwing, button pushing, cranking, aligning, focusing, viewing, using x, etc.
   Surgery -> cutting, snipping, clamping, stitching, monitoring, etc.
   Lab -> mixing, shaking, measuring, recording, listing, arranging, etc.  (heating, and weighing dont fit here)
   Construction -> assembling, connecting, grinding, using x, etc. (soldering, grinding, gluing, are all 'using x')
   This does not get us what we want for data annotation, it may for protocols.

2. measures
3. protocols -> is split more cleanly into protocol artifacts and protcol execution
4. experimental paradigms/methdological paradigm/research approach
   The general way, collection of techniques, data, and interpretational practices that are employed
   in a certain set of experimentes (research project, etc.).
   These are the high level categories like histology, anatomy, electrophysiology, microscopy, etc.
   There is no common axis that these can be classified under, and in fact trying to categorize
   these high level approaches by something like they tool they employ can quickly lead to electrophysiology
   being classified as a type of microscopy without a bunch of accompanying restrictions that make ones head hurt.

# Existing sources and sources of interest
## NIFSTD
[NIF-Investigation.ttl](https://github.com/SciCrunch/NIF-Ontology/blob/master/ttl/NIF-Investigation.ttl)  
[NIF-Scientific-Discipline.ttl](https://github.com/SciCrunch/NIF-Ontology/blob/master/ttl/NIF-Scientific-Discipline.ttl)  
[cogat_v0.3.owl](https://github.com/SciCrunch/NIF-Ontology/blob/master/ttl/external/cogat_v0.3.owl)  
[CogPO](https://github.com/SciCrunch/NIF-Ontology/blob/master/ttl/external/CogPO.ttl)

## BBP
[hbp_measurement_methods_ontology.ttl](https://github.com/OpenKnowledgeSpace/methodsOntology/blob/master/ttl/hbp_measurement_methods_ontology.ttl)
corresponds closely to initial work from 2015.  
[hbp_data_modality_ontology.ttl](https://github.com/OpenKnowledgeSpace/methodsOntology/blob/master/ttl/hbp_data_modality_ontology.ttl)  
[hbp_ephys_stimuli.ttl](https://github.com/OpenKnowledgeSpace/methodsOntology/blob/master/ttl/hbp_ephys_stimuli.ttl)  
[hbp_activity_ontology.ttl](https://github.com/OpenKnowledgeSpace/methodsOntology/blob/master/ttl/hbp_activity_ontology.ttl)  
[hbp_data_type_ontology.ttl](https://github.com/OpenKnowledgeSpace/methodsOntology/blob/master/ttl/hbp_data_type_ontology.ttl)  
[hbp_storage_ontology.ttl](https://github.com/OpenKnowledgeSpace/methodsOntology/blob/master/ttl/hbp_storage_ontology.ttl)  
[hbp_role_ontology.ttl](https://github.com/OpenKnowledgeSpace/methodsOntology/blob/master/ttl/hbp_role_ontology.ttl)
This could be expanded into the human executor 'role/skillset/responsibility' ontology.  

## tgbugs/methodsOntology
[tgbugs/methodsOntology](https://github.com/tgbugs/methodsOntology) contains the original work that was done back in 2015.  
[ns_methods.obo](https://github.com/tgbugs/methodsOntology/blob/master/source-material/ns_methods.obo)  
[ns_entities.obo](https://github.com/tgbugs/methodsOntology/blob/master/source-material/ns_entities.obo)  

## Other
[OEN](https://github.com/G-Node/OEN)  
[CNO](https://github.com/INCF/Computational-Neurosciences-Ontology--C.N.O.-)  
[nat](https://github.com/BlueBrain/nat/blob/master/nat/data/modelingDictionary.csv)  
[odml](https://github.com/G-Node/odml-terminologies) see also the [main page](http://www.g-node.org/projects/odml/terminologies)  
[ero.owl](https://www.eagle-i.net/ero/latest/ero.owl) see also the [wiki](https://open.med.harvard.edu/wiki/display/eaglei/Ontology)  
[efo.owl](http://www.ebi.ac.uk/efo/efo.owl) see also the [main page](https://www.ebi.ac.uk/efo/)  
[CHMO](https://github.com/rsc-ontologies/rsc-cmo) (note the cc-by license)

## Related github issues
https://github.com/SciCrunch/NIF-Ontology/issues/100  

## Thoughts

### Tiers for tagging
1. High level experimental approach (sometimes may directly imply a set of techniques as well)
2. More specific techniques that are still high level (e.g. whole cell patch clamp, calcium imaging)
3. Free text term addition if data providers want/need more granularity

### Technique vs Method
The common usage of technique and method are completely overlapping and it will be unproductive
to try to force a distinction between the two. If we want a meaningful higher level above technique/method
we should probably follow the scientific discipline approach or something similar. This higher level
would allow for inclusion of analysis methods that tend to be used with certain types of data produced
by common measurement techniques in a field.

### An alternative: tools + targets
An electrophysiological method is equivalent to some process that uses some ephys amplifier and measures
some electrical property of some part of a living organism.
An ephys technique is any (sub)process that is _required_ as part of a ephys method in order to
produce the measurement or the thing measured. The boundary where it makes sense to draw a line is
at the direct named inputs. For example pipette pulling is not an electrophysiological technique
because 6 MOhm pipettes are a named input for whole cell patch clamp. Incubation of slices could
be an ephys technique because only brain slices and cut buffer are named inputs -- the temperature
for incluation and the process required would thus be part of electrophysiology. A dissenting view
would say that those are slice preparation techniques and that the ephys techniques with regard to
slices start with transferring incubated slices to the recording chamber. All of these processes are
intertwined when it comes to naming. Another way out would be to define the boundary per protocol artifact,
but then there will be no consistent view. Tools + techniques to use them? How about techniques that require
the orchestrated use of multiple tools at the same time? The list of things that someone hired as an
electrophysiologists would be expected to be capable of doing? This pushes us into modelling these as
experimenter roles and capabilities. Perhaps modelling fields as collections of tools that are
routinely used by their practicioners? Better yet, the minimal set of tools needed to match, plus
a larger set of tools that are often expected/accompany the minimal core set. In fact, if we look at
the history of electrophysiology, many PhDs were granted for creating new and better amplifiers.
"A process that uses a (usually low noise) amplifier in order to record electrical signals from some
biological source or physiological process." Or really just "Any process that records electrical signals
from some biological source." For comparison, microscopy "Any process that records data (information, numbers)
and whose black box (process phenomena?) requires a microscope as a necissary component to produce said data.
(Has a microscope as part of the critical path.)" Symbolizes aspect A of target T using U.

A process that symbolizes aspect A of black-box B using U. U should be the tool in the critical path. This
gives us three of the major axes by which techniques are named. The fourth asis by which techniques are
named is by some subprocess or phenomena that they employ (e.g. electroporation), or simply by some
accidental naming of the whole process (e.g. golgi method) which is usually a completely opaque name.
Nevertheless it should still be possible to model those techniques using the the aspect, black-box, or
tool critical path naming criteria. A fifth, and more useful axis is whether the process symbolizes or
just produces/modifies/combines/creates or sustains/maintains (these are included already, just noting again).
subClassOf should probably have its first level divide the processes by whether their _primary_ (defining?)
output is symbol or being, and then within being based on whether it creates or maintains. In theory these
could all be modelled as process -> technique and use `ilxtr:processProducesClass` to allow mixing
(needed for handling destructive measurement methods if we don't want to have multiparent classes).
Technically all non-destructive measurement techniques are also maintaining techniques.
A process that creates a new black-box B' using inputs I.
A process that maintains an existing black-box B using inputs I.
A process that symbolizes an aspect A of a black-box B using inputs I.
(that (we assume makes minimal changes to and thus) maintains B)
(that creates a new black-box B')

