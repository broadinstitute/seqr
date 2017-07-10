#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh



echo Current Directory: `pwd`

set -x

if [ "$BUILD_AND_RESET_DB" ]; then
    export BUILD=1
    export RESET_DB=1
fi

'--metadata startup-script=#!/bin/bash
# set VM settings required for elasticsearch
sudo /sbin/sysctl -w vm.max_map_count=262144
'
if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
    gcloud config set project $GCLOUD_PROJECT

    # create cluster
    gcloud container clusters create $CLUSTER_NAME \
    --project $GCLOUD_PROJECT \
    --zone $GCLOUD_ZONE \
    --machine-type $CLUSTER_MACHINE_TYPE \
    --num-nodes $CLUSTER_NUM_NODES

    gcloud container clusters get-credentials $CLUSTER_NAME \
    --zone=$GCLOUD_ZONE

    # create persistent disks  (200Gb is the minimum recommended by Google)
    gcloud compute disks create --size 200GB ${DEPLOY_TO}-postgres-disk --zone $GCLOUD_ZONE
    gcloud compute disks create --size 200GB ${DEPLOY_TO}-mongo-disk --zone $GCLOUD_ZONE
    gcloud compute disks create --size 200GB ${DEPLOY_TO}-elasticsearch-disk --zone $GCLOUD_ZONE

    if [ "$DEPLOY_TO" = 'gcloud-dev' ]; then
        gcloud compute disks create --size 200GB ${DEPLOY_TO}-solr-disk --zone $GCLOUD_ZONE
        gcloud compute disks create --size 200GB ${DEPLOY_TO}-cassandra-disk --zone $GCLOUD_ZONE
    fi

else
    mkdir -p ${POSTGRES_DBPATH}
    mkdir -p ${MONGO_DBPATH}

    mkdir -p ${SOLR_DBPATH}
    mkdir -p ${CASSANDRA_DBPATH}
    mkdir -p ${ELASTICSEARCH_DBPATH}
fi

echo Cluster Info:
kubectl cluster-info

# secrets
if [ "$UPDATE_SECRETS" ]; then
    kubectl delete secret seqr-secrets
    kubectl delete secret postgres-secrets
    kubectl delete secret nginx-secrets
    kubectl delete secret matchbox-secrets

    kubectl create secret generic seqr-secrets \
        --from-file secrets/${DEPLOY_TO}/seqr/omim_key

    kubectl create secret generic postgres-secrets \
        --from-file secrets/${DEPLOY_TO}/postgres/postgres.username \
        --from-file secrets/${DEPLOY_TO}/postgres/postgres.password

    kubectl create secret generic nginx-secrets \
        --from-file secrets/${DEPLOY_TO}/nginx/tls.key \
        --from-file secrets/${DEPLOY_TO}/nginx/tls.crt

    kubectl create secret generic matchbox-secrets \
        --from-file secrets/${DEPLOY_TO}/matchbox/application.properties \
        --from-file secrets/${DEPLOY_TO}/matchbox/config.xml
fi
