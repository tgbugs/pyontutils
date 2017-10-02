#!/usr/bin/env sh
GIT=${HOME}/git
ONT=${HOME}/git/NIF-Ontology
TTL=$ONT/ttl
TTLCMP=$ONT/ttlcmp

cd $TTL ;
find -type d -exec mkdir -p $TTLCMP/{} \;
ontload imports NIF-Ontology NIF {*,*/*,*/*/*}.ttl -l $GIT &&
java -cp $GIT/ttl-convert/target/ttl-convert-1.0-SNAPSHOT-jar-with-dependencies.jar scicrunch.App $TTL/{*,*/*,*/*/*}.ttl ;
find -name '*.ttl.ttl' -exec bash -c 'mv $1 ../ttlcmp/$1' _ {} \;
ttlfmt $ONT/ttlcmp/{*,*/*,*/*/*}.ttl &&
echo '# comparing current serialization to files serialized from full imports' > /tmp/ttlcmp.patch ;
find $TTLCMP -name '*.ttl.ttl' -exec bash -c 'echo "# "$0 >> /tmp/ttlcmp.patch ; diff -u <(head -n -1 $(echo $0 | rev | cut -d"." -f2- | rev | sed "s/cmp\//\//" | tee -a /tmp/ttlcmp.log)) <(head -n -1 $0) >> /tmp/ttlcmp.patch' {} \;
git checkout {*,*/*,*/*/*}.ttl
