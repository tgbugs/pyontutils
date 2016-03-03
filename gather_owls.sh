#!/usr/bin/env sh
BASE=~/git/NIF-Ontology
BASESC=$(echo ${BASE} | sed 's/\//\\\//g')
echo $BASESC
CONVFILE=/tmp/owl_to_convert.txt

find "${BASE}"/Backend -name '*.owl' > /tmp/back_files
find "${BASE}"/BiomaterialEntities/ -name '*.owl' > /tmp/be_files
find "${BASE}"/DigitalEntities/ -name '*.owl' > /tmp/de_files
find "${BASE}"/Dysfunction/ -name '*.owl' > /tmp/dys_files
find "${BASE}"/Function/ -name '*.owl' > /tmp/fun_files
find "${BASE}"/Views/ -name '*.owl' > /tmp/view_files
find "${BASE}"/Retired/ -name '*.owl' > /tmp/re_files
find "${BASE}" -name 'nif.owl' > /tmp/base_files

find "${BASE}"/*/ -name '*.owl.ttl' -exec rm {} \;  # XXX this is EXTREMELY dangerous to copy and paste

java -cp ~/git/ttl-convert/target/ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar scicrunch.App /tmp/*_files


#sed "s/^/${BASESC}\//" ${BASE}/convert.txt > ${CONVFILE}
#sed "s/^/${BASESC}\//" ${BASE}/bridge.txt >> ${CONVFILE}
#java -cp ~/git/ttl-convert/target/ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar scicrunch.App ${CONVFILE}

#./convert_imports.sh

# gonna need to fix/improve how convert_imports works to deal with curified stuff

#dupes
#diff $(find . | grep BIRNLex-OBI-proxy.owl)  # OK check iri refs

#gvim $(find . | grep quality.owl)  # both deleted (replaced by pato)
#gvim $(find . | grep quality_bfo_bridge.owl)  # deleted BE and ./ versions
#gvim $(find . | grep NIF-Dysfunction-DOID-Bridge.owl)  # both deleted

#crazytown below :/ one will go in the main and one in the unused and we can sort it out after that
#gvim $(find . | grep NIF-Quality.owl)  # identical, the issue is that the BE version iri is used in the bridge
#gvim $(find . | grep NIF-Resource.owl)  # complete an utter madness between BE and DE

# external imports (do not ttl them!)
#CogPO.owl  # megawtf here
#so.owl #aka sequence.owl  # seriously wtf moving this to external import
#uberon.owl
#ero.owl
#pr.owl  # FXIME
#go.owl
#
