#!/usr/bin/env bash

set -x

env

# init GCS Fuse directory
if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]
then
    mkdir -p /mounted-bucket/exomiser/exomiser-cli-8.0.0/data/phenix
fi

cd /matchbox_deployment/config/
wget https://storage.googleapis.com/matchbox-mounted-bucket/gene_symbol_to_ensembl_id_map.txt

cd /matchbox_deployment

java -jar \
    -Dallow.no-gene-in-common.matches=$ALLOW_NO_GENE_IN_COMMON_MATCHES \
    -Dexomiser.data-directory=$EXOMISER_DATA_DIR \
    -Dspring.data.mongodb.host=$MONGO_SERVICE_HOSTNAME \
    -Dspring.data.mongodb.port=$MONGO_SERVICE_PORT \
    -Dspring.data.mongodb.database=$MONGODB_DATABASE \
    matchbox-0.1.0.jar &

sleep 10000000000
