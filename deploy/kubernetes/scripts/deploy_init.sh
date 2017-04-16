#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

echo Current Directory: `pwd`

set -x

echo DEPLOY_TO_GOOGLE_CLOUD: $DEPLOY_TO_GOOGLE_CLOUD
echo FORCE: $FORCE

if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud config set project $GCLOUD_PROJECT

    # create persistent disks  (200Gb is the minimum recommended by Google)
    gcloud compute disks create --size 200GB postgres-disk --zone $GCLOUD_ZONE
    gcloud compute disks create --size 200GB mongo-disk --zone $GCLOUD_ZONE

    # create cluster
    gcloud container clusters create $CLUSTER_NAME \
    --machine-type $CLUSTER_MACHINE_TYPE \
    --num-nodes $CLUSTER_NUM_NODES \
    --project $GCLOUD_PROJECT \
    --zone $GCLOUD_ZONE

    gcloud container clusters get-credentials $CLUSTER_NAME \
    --zone=$GCLOUD_ZONE

else
    mkdir -p ${POSTGRES_DBPATH}
    mkdir -p ${MONGO_DBPATH}
fi

echo Cluster Info:
kubectl cluster-info

kubectl create -f configs/cockpit/kubernetes-cockpit.json

# secrets
kubectl delete -f configs/postgres-secrets.yaml
kubectl create -f configs/postgres-secrets.yaml

kubectl delete -f configs/matchbox-secrets.yaml
kubectl create -f configs/matchbox-secrets.yaml

kubectl delete -f configs/nginx-secrets.yaml
kubectl create -f configs/nginx-secrets.yaml
