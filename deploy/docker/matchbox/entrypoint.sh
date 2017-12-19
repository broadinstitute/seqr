#!/usr/bin/env bash

set -x

env

cd /matchbox_deployment

java -jar \
    -Dallow.no-gene-in-common.matches=$ALLOW_NO_GENE_IN_COMMON_MATCHES \
    -Dexomiser.data-directory=$EXOMISER_DATA_DIR \
    -Dspring.data.mongodb.host=$MONGO_SERVICE_HOSTNAME \
    -Dspring.data.mongodb.port=$MONGO_SERVICE_PORT \
    -Dspring.data.mongodb.database=$MONGODB_DATABASE \
    -Dmatchbox.gene-symbol-to-id-mappings=$EXOMISER_DATA_DIR/gene_symbol_to_ensembl_id_map.txt \
    matchbox-0.1.0.jar &

sleep 10000000000
