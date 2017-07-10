#!/usr/bin/env bash

set -x

env

su kibana -c "/usr/local/kibana-${KIBANA_VERSION}-linux-x86_64/bin/kibana \
    --host=0.0.0.0 \
    --port=${KIBANA_PORT} \
    --elasticsearch.url=http://elasticsearch-svc:${ELASTICSEARCH_SVC_SERVICE_PORT}"

echo Kibana started on port ${KIBANA_PORT}!!

# sleep indefinitely to prevent container from terminating
sleep 1000000000000
