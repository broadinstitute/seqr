#!/usr/bin/env bash

VERSION=6.4.0

echo "==== Install and start kibana ====="
set -x


wget -nv https://artifacts.elastic.co/downloads/kibana/kibana-${VERSION}-linux-x86_64.tar.gz
tar xzf kibana-${VERSION}-linux-x86_64.tar.gz
rm kibana-${VERSION}-linux-x86_64.tar.gz

cd kibana-${VERSION}

echo '
cd '$(pwd)'
LOG_FILE=$(pwd)/kibana.log
(nohup ./bin/kibana >& ${LOG_FILE}) &
echo "Kibana started in background. See ${LOG_FILE}"
' | tee start_kibana.sh
chmod 777 ./start_kibana.sh

set +x

./start_kibana.sh

cd  ..
