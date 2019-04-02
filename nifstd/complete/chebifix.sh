#!/usr/bin/env sh
# run at NIF-Ontology commit: 4594e88e4127886a850353d138bf8ec24f20804a

WD=~/git/NIF-Ontology/ttl/
FILES="NIF-Molecule-Role-Inferred.ttl
NIF-Molecule.ttl
NIF-Chemical.ttl
NIF-Molecule-Role-Bridge.ttl"

old_chebi="@prefix chebi: <http:\/\/purl.obolibrary.org\/obo\/chebi.owl#> ."
new_chebi="@prefix CHEBI: <http:\/\/purl.obolibrary.org\/obo\/CHEBI_> ."
old_pat="chebi:CHEBI_"
new_pat="CHEBI:"

cd $WD

fix_chebi () {
    sed -i "s/${old_chebi}/${new_chebi}/g" $1 
    sed -i "s/${old_pat}/${new_pat}/g" $1
}


for FILE in $FILES; do
    echo $FILE
    git checkout $FILE  # reset each time so we can do a read sed -i
    fix_chebi $FILE
done

# individual fixes
old_obo="@prefix obo: <http:\/\/purl.obolibrary.org\/obo\/> ."
new_obo="@prefix PR: <http:\/\/purl.obolibrary.org\/obo\/PR_> ."
old_pr="obo:PR_"
new_pr="PR:"
sed -i "s/${old_pr}/${new_pr}/g" NIF-Molecule-Role-Inferred.ttl
sed -i "s/${old_obo}/${new_obo}/g" NIF-Molecule-Role-Inferred.ttl

old_pro="@prefix PRO: <http:\/\/purl.obolibrary.org\/obo\/> ."
old_pr="PRO:PR_"
new_pr="PR:"
sed -i "s/${old_pr}/${new_pr}/g" NIF-Molecule-Role-Bridge.ttl
sed -i "s/${old_pro}/${new_obo}/g" NIF-Molecule-Role-Bridge.ttl

# reserialize (run separately for 2nd commit)
#java -cp ~/git/ttl-convert/target/ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar scicrunch.App $FILES

#for FILE in $FILES; do
    #mv $FILE.ttl $FILE
#done

