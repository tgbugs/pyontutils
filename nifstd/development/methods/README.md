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
https://github.com/SciCrunch/NIF-Ontology/issues/128  
