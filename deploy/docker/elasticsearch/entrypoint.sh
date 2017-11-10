#!/usr/bin/env bash

env

set -x

# must run sudo /sbin/sysctl -w vm.max_map_count=262144  on the VM

mkdir -p /logs
chown elasticsearch /elasticsearch-data /logs

su elasticsearch -c "/usr/local/elasticsearch-${ELASTICSEARCH_VERSION}/bin/elasticsearch \
    -E network.host=0.0.0.0 \
    -E http.port=${ELASTICSEARCH_SERVICE_PORT} \
    -E path.data=/elasticsearch-data \
    -E path.logs=/logs" &

# sleep indefinitely to prevent container from terminating
sleep 1000000000000
