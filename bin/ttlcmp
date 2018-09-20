#!/usr/bin/env sh
# run this not on your main copy of the repo in case something goes wrong
GIT=/tmp
ONT=$GIT/NIF-Ontology
TTL=$ONT/ttl
TTLCMP=$ONT/ttlcmp

cd $TTL ;
FILES=$(git ls-files | grep ".ttl")
find -type d -exec mkdir -p $TTLCMP/{} \;
ontload imports NIF-Ontology NIF $FILES -l $GIT &&

for f in $FILES;
do echo -e ${f};
done | xargs -L 1 -P 8 ttl-convert &&

find -name '*.ttl.ttl' -exec bash -c 'mv $1 ../ttlcmp/$1' _ {} \;
ttlfmt $ONT/ttlcmp/{*,*/*,*/*/*}.ttl &&
echo '# comparing current serialization to files serialized from full imports' > /tmp/ttlcmp.patch ;
find $TTLCMP -name '*.ttl.ttl' -exec bash -c 'echo "# "$0 >> /tmp/ttlcmp.patch ; diff -u <(head -n -1 $(echo $0 | rev | cut -d"." -f2- | rev | sed "s/cmp\//\//" | tee -a /tmp/ttlcmp.log)) <(head -n -1 $0) >> /tmp/ttlcmp.patch' {} \;
git checkout $FILES
