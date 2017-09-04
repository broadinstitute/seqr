#!/usr/bin/env bash

set -x

env

cd /matchbox_deployment

java -jar -Dallow.no-gene-in-common.matches=$ALLOW_NO_GENE_IN_COMMON_MATCHES -Dexomiser.data-directory=$EXOMISER_DATA_DIR  -Dspring.data.mongodb.host=$MONGODB_HOSTNAME  -Dspring.data.mongodb.port=$MONGODB_PORT -Dspring.data.mongodb.database=$MONGODB_DATABASE matchbox-0.1.0.jar &

sleep 10000000000