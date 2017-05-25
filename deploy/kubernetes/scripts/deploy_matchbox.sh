#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

if [ "$DELETE_BEFORE_DEPLOY" ]; then
    # delete any previous deployments
    kubectl delete -f configs/matchbox/matchbox-deployment.yaml
    kubectl delete -f configs/matchbox/matchbox-service.yaml
fi

BUILD_ARG=
if [ "$BUILD" ]; then
    BUILD_ARG=--no-cache
fi

docker build $BUILD_ARG -t ${DOCKER_IMAGE_PREFIX}/matchbox docker/matchbox/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/matchbox
fi

MATCHBOX_POD_NAME=$( kubectl get pods -o=name | grep 'matchbox-' | cut -f 2 -d / | tail -n 1 )
if [ "$MATCHBOX_POD_NAME" ] ; then
    kubectl set image -f configs/matchbox/matchbox-deployment.${DEPLOY_TO}.yaml --record
    #kubectl edit -f configs/matchbox/matchbox-service.yaml --record
else
    kubectl create -f configs/matchbox/matchbox-deployment.yaml --record
    kubectl create -f configs/matchbox/matchbox-service.yaml --record
fi

wait_until_pod_is_running matchbox