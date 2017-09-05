#!/usr/bin/env bash

set -x

env

cd /matchbox_deployment

java -jar \
    -Dallow.no-gene-in-common.matches=$ALLOW_NO_GENE_IN_COMMON_MATCHES \
    -Dexomiser.data-directory=$EXOMISER_DATA_DIR \
    -Dspring.data.mongodb.host=$MONGO_SERVICE_HOST \
    -Dspring.data.mongodb.port=$MONGO_SERVICE_PORT \
    -Dspring.data.mongodb.database=$MONGODB_DATABASE \
    matchbox-0.1.0.jar &

sleep 10000000000
