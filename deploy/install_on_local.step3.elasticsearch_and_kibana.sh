#!/usr/bin/env bash

VERSION=6.4.0

echo ==== Install and start elasticsearch =====
set -x

wget -nv http://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${VERSION}.tar.gz
tar xzf elasticsearch-${VERSION}.tar.gz
rm elasticsearch-${VERSION}.tar.gz

cd elasticsearch-${VERSION}

echo '
cd '$(pwd)'/'elasticsearch-${VERSION}'
(ES_JAVA_OPTS="-Xms3900m -Xmx3900m" nohup ./bin/elasticsearch -E network.host=0.0.0.0 | tee elasticsearch.log) &
' | tee start_elasticsearch.sh
chmod 777 ./start_elasticsearch.sh

set +x

./start_elasticsearch.sh

cd  ..

echo ==== Install and start kibana =====
set -x


wget -nv https://artifacts.elastic.co/downloads/kibana/kibana-${VERSION}-linux-x86_64.tar.gz
tar xzf kibana-${VERSION}-linux-x86_64.tar.gz
rm kibana-${VERSION}-linux-x86_64.tar.gz

cd kibana-${VERSION}

echo '
cd '$(pwd)'/'elasticsearch-${VERSION}'
(ES_JAVA_OPTS="-Xms3900m -Xmx3900m" nohup ./bin/elasticsearch -E network.host=0.0.0.0 | tee elasticsearch.log) &
' | tee start_elasticsearch.sh
chmod 777 ./start_elasticsearch.sh

set +x

./start_kibana.sh

cd  ..