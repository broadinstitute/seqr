#!/usr/bin/env bash

echo "==== Installing redis ===="
set -x

wget http://download.redis.io/redis-stable.tar.gz
tar xvzf redis-stable.tar.gz
cd redis-stable
make
sudo make install

echo 'cd '$(pwd)'
LOG_FILE=$(pwd)/redis.log
(nohup redis-server ${SEQR_DIR}/deploy/docker/redis/redis.conf >& ${LOG_FILE}) &
echo "redis started in background on port 8080. See ${LOG_FILE}"
' | tee start_redis.sh
chmod 777 ./start_redis.sh

set +x

./start_redis.sh

cd ..
