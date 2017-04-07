#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

# delete any previous deployments
kubectl delete -f configs/mongo/mongo-deployment.${DEPLOY_TO}.yaml
kubectl delete -f configs/mongo/mongo-service.yaml

FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/mongo  docker/mongo/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/mongo

    gcloud compute disks create --size 200GB mongo-disk --zone $GCLOUD_ZONE
fi

kubectl create -f configs/mongo/mongo-deployment.${DEPLOY_TO}.yaml --record
kubectl create -f configs/mongo/mongo-service.yaml --record
