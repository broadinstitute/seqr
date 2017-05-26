#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

if [ "$DELETE_BEFORE_DEPLOY" ]; then
    kubectl delete -f configs/mongo/mongo.${DEPLOY_TO}.yaml
fi

BUILD_ARG=
if [ "$BUILD" = true ]; then
    BUILD_ARG=--no-cache
fi

docker build $BUILD_ARG -t ${DOCKER_IMAGE_PREFIX}/mongo  docker/mongo/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/mongo
fi

# if the deployment doesn't exist yet, then create it, otherwise just update the image
kubectl apply -f configs/mongo/mongo.${DEPLOY_TO}.yaml --record
wait_until_pod_is_running mongo