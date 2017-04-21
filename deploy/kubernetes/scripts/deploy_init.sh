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
    --project $GCLOUD_PROJECT \
    --zone $GCLOUD_ZONE \
    --machine-type $CLUSTER_MACHINE_TYPE \
    --num-nodes $CLUSTER_NUM_NODES



    gcloud container clusters get-credentials $CLUSTER_NAME \
    --zone=$GCLOUD_ZONE

else
    mkdir -p ${POSTGRES_DBPATH}
    mkdir -p ${MONGO_DBPATH}
fi

echo Cluster Info:
kubectl cluster-info

# secrets
kubectl delete secret postgres-secrets
kubectl delete secret nginx-secrets
kubectl delete secret matchbox-secrets

kubectl create secret generic postgres-secrets \
    --from-file secrets/${DEPLOY_TO}/postgres/postgres.username \
    --from-file secrets/${DEPLOY_TO}/postgres/postgres.password

kubectl create secret generic nginx-secrets \
    --from-file secrets/${DEPLOY_TO}/nginx/tls.key \
    --from-file secrets/${DEPLOY_TO}/nginx/tls.crt

kubectl create secret generic matchbox-secrets \
    --from-file secrets/${DEPLOY_TO}/matchbox/application.properties \
    --from-file secrets/${DEPLOY_TO}/matchbox/config.xml
