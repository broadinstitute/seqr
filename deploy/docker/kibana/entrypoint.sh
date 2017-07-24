#!/usr/bin/env bash

set -x

env

su kibana -c "/usr/local/kibana-${KIBANA_VERSION}-linux-x86_64/bin/kibana \
    --host=0.0.0.0 \
    --port=${KIBANA_SERVICE_PORT} \
    --elasticsearch.url=http://${ELASTICSEARCH_SERVICE_HOST}:${ELASTICSEARCH_SERVICE_PORT}" &

echo Kibana started on port ${KIBANA_SERVICE_PORT}!!

# sleep indefinitely to prevent container from terminating
sleep 1000000000000
