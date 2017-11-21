# work for methods/techniques/measures/protocols/datatypes
Any documents related to methodology should go here.

# Use cases
1. Tagging ephys data
2. Tagging fMRI data

# Collected thoughts/working draft
My initial work to provide a consistent view of methodology lives in [methods_isa.graphml](methods_isa.graphml).
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
[ero.owl](https://www.eagle-i.net/ero/latest/ero.owl) see also the [wiki](https://open.med.harvard.edu/wiki/display/eaglei/Ontology)  
[efo.owl](http://www.ebi.ac.uk/efo/efo.owl) see also the [main page](https://www.ebi.ac.uk/efo/)  
[](
)
