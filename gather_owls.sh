#!/usr/bin/env sh
BASE=~/git/NIF-Ontology
find "${BASE}"/Backend -name '*.owl' > /tmp/back_files
find "${BASE}"/BiomaterialEntities/ -name '*.owl' > /tmp/be_files
find "${BASE}"/DigitalEntities/ -name '*.owl' > /tmp/de_files
find "${BASE}"/Dysfunction/ -name '*.owl' > /tmp/dys_files
find "${BASE}"/Function/ -name '*.owl' > /tmp/fun_files
#find "${BASE}" -name 'nif.owl' > /tmp/base_files

#find "${BASE}"/*/ -name '*.owl.ttl' -exec rm {} \;

java -cp ~/git/ttl-convert/target/ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar scicrunch.App /tmp/*_files
./convert_imports.sh

# gonna need to fix/improve how convert_imports works to deal with curified stuff

#dupes
#diff $(find . | grep BIRNLex-OBI-proxy.owl)  # OK check iri refs

#gvim $(find . | grep quality.owl)
#gvim $(find . | grep NIF-Resource.owl)
#gvim $(find . | grep quality_bfo_bridge.owl)
#gvim $(find . | grep NIF-Dysfunction-DOID-Bridge.owl)
#gvim $(find . | grep NIF-Quality.owl)

# external imports (do not ttl them!)
#CogPO.owl  # megawtf here
#so.owl #aka sequence.owl  # seriously wtf moving this to external import
#uberon.owl
#ero.owl
#pr.owl  # FXIME
#go.owl
#
