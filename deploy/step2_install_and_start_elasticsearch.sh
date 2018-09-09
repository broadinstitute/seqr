#!/usr/bin/env bash

echo ==== Install and start elasticsearch =====
set -x

ELASTICSEARCH_VERSION=elasticsearch-6.4.0

curl -L http://artifacts.elastic.co/downloads/elasticsearch/${ELASTICSEARCH_VERSION}.tar.gz -o ${ELASTICSEARCH_VERSION}.tar.gz
tar xzf ${ELASTICSEARCH_VERSION}.tar.gz

echo "ES_JAVA_OPTS='-Xms5000m -Xmx5000m' ./${ELASTICSEARCH_VERSION}/bin/elasticsearch -E network.host=0.0.0.0" | tee start_elasticsearch.sh
chmod 777 ./start_elasticsearch.sh

set +x

./start_elasticsearch.sh
