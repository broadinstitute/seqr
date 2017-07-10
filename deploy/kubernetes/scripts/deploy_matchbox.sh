#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

if [ "$DELETE_BEFORE_DEPLOY" ]; then
    kubectl delete -f configs/matchbox/matchbox.yaml
fi

CACHE_ARG=
if [ "$BUILD" ]; then
    CACHE_ARG=--no-cache
fi

docker build $CACHE_ARG -t ${DOCKER_IMAGE_PREFIX}/matchbox docker/matchbox/
if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
    docker tag ${DOCKER_IMAGE_PREFIX}/matchbox ${DOCKER_IMAGE_PREFIX}/matchbox:${TIMESTAMP}
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/matchbox:${TIMESTAMP}
fi

kubectl apply -f configs/matchbox/matchbox.yaml
wait_until_pod_is_running matchbox