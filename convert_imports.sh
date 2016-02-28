#!/usr/bin/env bash

cd ~/git/NIF-Ontology/ttl/
find . -type l -exec unlink {} \;
find ../ -name '*owl.ttl' -exec sh -c 'ln -sT $1 $(echo $1 | sed "s/\.owl//" | sed "s/^.\+\///")' _ {} \;
#find ../ -name '*owl.ttl' -exec sh -c 'echo $1 $(echo $1 | sed "s/\.owl//" | sed "s/^.\+\///")' _ {} \;

#FILENAME=~/git/NIF-Ontology/ttl/nif.ttl
#FN2=~/git/NIF-Ontology/ttl/NIF-Cell.ttl
#FILENAMES=~/git/NIF-Ontology/ttl/NIF-Function.ttl

FILENAMES=$(find . -type l -name '*.ttl')
# fails when encounter owl:imports
#sed --follow-symlinks -i "s/\(^\s\+<http:\/\/ontology\.neuinfo\.org\/NIF\/\)\(.\+\)\(\/[_0-9A-Za-z\-]\+\)\(\.owl>\)/\1ttl\3.ttl>/" $FILENAME $FN2

declare -A subs
subs[Backend]="<http:\/\/ontology.neuinfo.org\/NIF\/Backend\/"
subs[p15]="<http:\/\/ontology.neuinfo.org\/NIF\/Backend\/"
subs[nif_back]="<http:\/\/ontology.neuinfo.org\/NIF\/Backend\/"
subs[p16]="<http:\/\/ontology.neuinfo.org\/NIF\/BiomaterialEntities\/"

for FIND in "${!subs[@]}"; do
    sed --follow-symlinks -i "/@prefix\ ${FIND}/d" $FILENAMES
    sed --follow-symlinks -i "s/${FIND}:\(.\+\)\ /${subs[$FIND]}\1> /" $FILENAMES
done

sed --follow-symlinks -i "s/\(<http:\/\/ontology\.neuinfo\.org\/NIF\/\)\(.\+\)\(\/[_0-9A-Za-z\-]\+\)\(\.owl>\)/\1ttl\3.ttl>/" $FILENAMES
