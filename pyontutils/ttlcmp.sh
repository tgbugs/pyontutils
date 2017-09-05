#!/usr/bin/env sh
GIT=${HOME}/git
ONT=${HOME}/git/NIF-Ontology
TTL=$ONT/ttl
TTLCMP=$ONT/ttlcmp

cd $TTL ;
ontload imports NIF-Ontology NIF *.ttl */*.ttl */*/*.ttl -l $GIT &&
java -cp $GIT/ttl-convert/target/ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar scicrunch.App $TTL/*.ttl $TTL/*/*.ttl $TTL/*/*/*.ttl &&
find -type d -exec mkdir -p ../ttlcmp/{} \;
find -name '*.ttl.ttl' -exec bash -c 'mv $1 ../ttlcmp/$1' _ {} \;
ttlfmt $ONT/ttlcmp/*.ttl &&
ttlfmt $ONT/ttlcmp/*/*.ttl &&
ttlfmt $ONT/ttlcmp/*/*/*.ttl &&
find -name '*.ttl' -exec bash -c 'diff -u $1 ../ttlcmp/$1.ttl >> /tmp/ttlcmp.patch' _ {} \;
git checkout *.ttl */*.ttl */*/*.ttl
