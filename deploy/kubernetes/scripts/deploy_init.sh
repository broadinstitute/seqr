#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

echo Current Directory: `pwd`

set -x

echo DEPLOY_TO_GOOGLE_CLOUD: $DEPLOY_TO_GOOGLE_CLOUD
echo FORCE: $FORCE

if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud config set project $GCLOUD_PROJECT

    gcloud container clusters create $CLUSTER_NAME \
    --machine-type $CLUSTER_MACHINE_TYPE \
    --num-nodes $CLUSTER_NUM_NODES \
    --project $GCLOUD_PROJECT \
    --zone $GCLOUD_ZONE

    gcloud container clusters get-credentials $CLUSTER_NAME \
    --zone=$GCLOUD_ZONE
fi

echo Cluster Info:
kubectl cluster-info

kubectl create -f configs/cockpit/kubernetes-cockpit.json
