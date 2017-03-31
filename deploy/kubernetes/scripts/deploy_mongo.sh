#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
else
    FORCE_ARG=
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/mongo  docker/mongo/
if [ "DEPLOY_TO_GOOGLE_CLOUD" = true ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/mongo
fi

kubectl delete -f configs/mongo/mongo-deployment.yaml
kubectl create -f configs/mongo/mongo-deployment.yaml --record

kubectl delete -f configs/mongo/mongo-service.yaml
kubectl create -f configs/mongo/mongo-service.yaml --record
