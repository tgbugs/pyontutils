#!/usr/bin/env bash
BASE=~/git/NIF-Ontology
BASESC=$(echo ${BASE} | sed 's/\//\\\//g')
PATHTARGET=${BASE}/ttl/

#cd ${BASE}/ttl/
#find . -type l -exec unlink {} \;
#find ../ -name '*owl.ttl' -exec sh -c 'ln -sT $1 $(echo $1 | sed "s/\.owl//" | sed "s/^.\+\///")' _ {} \;
#find ../ -name '*owl.ttl' -exec sh -c 'echo $1 $(echo $1 | sed "s/\.owl//" | sed "s/^.\+\///")' _ {} \;

OWLFILES=$(find ${BASE} -name '*.owl')
#echo $OWLFILES
GOOD=$(cat ${BASE}/convert.txt ${BASE}/bridge.txt | sed "s/^/${BASESC}\//")
EXTERNAL=$(cat ${BASE}/external.txt | sed "s/^/${BASESC}\//")
for OWLFILE in ${OWLFILES}; do
    TARGET=$(basename $OWLFILE | sed 's/\.owl/.ttl/')
    if [[ $GOOD =~ $OWLFILE ]]; then
        echo 'mv' ${OWLFILE}.ttl $PATHTARGET$TARGET
        mv ${OWLFILE}.ttl $PATHTARGET$TARGET
    elif [[ $EXTERNAL =~ $OWLFILE ]]; then
        echo 'cp -a' $OWLFILE ${BASE}/external/
        cp -a $OWLFILE ${BASE}/external/
        echo 'rm' $OWLFILE.ttl 
        rm $OWLFILE.ttl 
    # TODO put Views and Retired in utility?
    else
        echo 'DEAD mv' $OWLFILE.ttl ${PATHTARGET}unused/${TARGET}
        mv $OWLFILE.ttl ${PATHTARGET}unused/${TARGET}
    fi
done

#FILENAME=~/git/NIF-Ontology/ttl/nif.ttl
#FN2=~/git/NIF-Ontology/ttl/NIF-Cell.ttl
#FILENAMES=~/git/NIF-Ontology/ttl/NIF-Function.ttl

cd $PATHTARGET
#FILENAMES=$(find . -type l -name '*.ttl')
FILENAMES=$(find . -type f -name '*.ttl')
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

# not the right place to do this, though it does seem to work
#GITHUB="https:\/\/raw.githubusercontent.com\/SciCrunch\/NIF-Ontology\/ttl\/"
#sed --follow-symlinks -i "s/\(<http:\/\/ontology\.neuinfo\.org\/NIF\/\)\(.\+\)\(\/[_0-9A-Za-z\-]\+\)\(\.owl>\)/<${GITHUB}ttl\3.ttl>/" $FILENAMES
