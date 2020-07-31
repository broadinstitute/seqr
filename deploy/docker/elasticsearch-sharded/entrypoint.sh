#!/usr/bin/env bash

env

set -x


mkdir -p /logs
chown elasticsearch /elasticsearch-data /logs


export ES_JAVA_OPTS="-Xms3900m -Xmx3900m"

su elasticsearch -c "/usr/local/elasticsearch-${ELASTICSEARCH_VERSION}/bin/elasticsearch \
    -E cluster.routing.allocation.disk.threshold_enabled=false \
    -E network.host=0.0.0.0 \
    -E http.port=${ELASTICSEARCH_SERVICE_PORT} \
    -E path.data=/elasticsearch-data \
    -E path.logs=/logs"
