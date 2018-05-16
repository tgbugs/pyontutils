docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
  --input=https://search-interlex-jnsyal3bwjqhaledmfvvwytzy4.us-west-2.es.amazonaws.com/scicrunch \
  --output=/elastic_testing/interlex_settings.json \
  --type=settings \
  --limit=1000

docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
  --input=https://search-interlex-jnsyal3bwjqhaledmfvvwytzy4.us-west-2.es.amazonaws.com/scicrunch \
  --output=/elastic_testing/interlex_analyzer.json \
  --type=analyzer \
  --limit=1000

docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
  --input=https://search-interlex-jnsyal3bwjqhaledmfvvwytzy4.us-west-2.es.amazonaws.com/scicrunch \
  --output=/elastic_testing/interlex_mapping.json \
  --type=mapping \
  --limit=1000

docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
  --input=https://search-interlex-jnsyal3bwjqhaledmfvvwytzy4.us-west-2.es.amazonaws.com/scicrunch \
  --output=/elastic_testing/interlex_data.json \
  --type=data \
  --limit=1000

Put:

docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
  --input=/elastic_testing/interlex_settings.json \
  --output=https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/beta2_interlex \
  --type=settings \
  --httpAuthFile=/elastic_testing/auth.ini \
  --limit=1000

docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
  --input=/elastic_testing/interlex_analyzer.json \
  --output=https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/beta2_interlex \
  --type=analyzer \
  --httpAuthFile=/elastic_testing/auth.ini \
  --limit=1000

docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
  --input=/elastic_testing/interlex_mapping.json \
  --output=https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/beta2_interlex \
  --type=mapping \
  --httpAuthFile=/elastic_testing/auth.ini \
  --limit=1000

time docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
  --input=/elastic_testing/interlex_data.json \
  --output=https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/beta2_interlex \
  --type=data \
  --httpAuthFile=/elastic_testing/auth.ini \
  --limit=1000








#old production elastic
http://interlex.scicrunch.io/

#to see if upload worked
docker run --rm -ti -v  /home/troy/elastic_testing:/elastic_testing taskrabbit/elasticsearch-dump \
    --input=https://5f86098ac2b28a982cebf64e82db4ea2.us-west-2.aws.found.io:9243/beta2_interlex \
    --output=/elastic_testing/beta2_mapping.json \
    --httpAuthFile=/elastic_testing/auth.ini \
    --type=mapping \
    --limit=1000
