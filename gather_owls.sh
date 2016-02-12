#!/usr/bin/env sh
BASE=~/git/NIF-Ontology/
find "${BASE}"/Backend -name '*.owl' > /tmp/back_files
find "${BASE}"/BiomaterialEntities/ -name '*.owl' > /tmp/be_files
find "${BASE}"/DigitalEntities/ -name '*.owl' > /tmp/de_files
find "${BASE}"/Dysfunction/ -name '*.owl' > /tmp/dys_files
find "${BASE}"/Function/ -name '*.owl' > /tmp/fun_files
find "${BASE}" -name 'nif.owl' > /tmp/base_files
java -cp ~/git/ttl-convert/target/ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar scicrunch.App /tmp/*_files
./convert_imports.sh
# gonna need to fix/improve how convert_imports works to deal with curified stuff
