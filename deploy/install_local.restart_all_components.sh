#!/usr/bin/env bash

# this script restarts all server components needed for seqr

sudo systemctl start postgresql-9.6    # though postgres should start up automatically after reboot
sudo service mongod start

cd ${SEQR_DIR}/..
./elasticsearch-6.4.0/start_elasticsearch.sh
./kibana-6.4.0-linux-x86_64/start_kibana.sh
./redis/start_redis.sh
./seqr/start_server.sh
./phenotips-standalone-1.2.6/start_phenotips.sh