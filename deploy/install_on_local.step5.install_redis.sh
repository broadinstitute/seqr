#!/usr/bin/env bash

wget http://download.redis.io/redis-stable.tar.gz
tar xvzf redis-stable.tar.gz
cd redis-stable
make
sudo make install

redis-server ${SEQR_DIR}/deploy/docker/redis/redis.conf

cd ..