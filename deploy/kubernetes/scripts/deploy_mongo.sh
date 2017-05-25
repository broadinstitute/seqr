#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

# delete any previous deployments
#kubectl delete -f configs/mongo/mongo-deployment.${DEPLOY_TO}.yaml
#kubectl delete -f configs/mongo/mongo-service.yaml

BUILD_ARG=
if [ "$BUILD" = true ]; then
    BUILD_ARG=--no-cache
fi

docker build $BUILD_ARG -t ${DOCKER_IMAGE_PREFIX}/mongo  docker/mongo/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/mongo
fi


# if the deployment doesn't exist yet, then create it, otherwise just update the image
MONGO_POD_NAME=$( kubectl get pods -o=name | grep 'mongo-' | cut -f 2 -d / | tail -n 1 )
if [ "$MONGO_POD_NAME" ] ; then
    kubectl set image -f configs/mongo/mongo-deployment.${DEPLOY_TO}.yaml --record
    #kubectl edit -f configs/mongo/mongo-service.yaml --record
else
    kubectl create -f configs/mongo/mongo-deployment.${DEPLOY_TO}.yaml --record
    kubectl create -f configs/mongo/mongo-service.yaml --record
fi

wait_until_pod_is_running mongo