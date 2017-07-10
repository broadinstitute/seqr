#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

if [ "$DELETE_BEFORE_DEPLOY" ]; then
    kubectl delete -f configs/seqr/seqr.pipeline-runner.yaml
    wait_until_pod_terminates pipeline-runner
fi

CACHE_ARG=
if [ "$BUILD" ]; then
    CACHE_ARG=--no-cache
fi

docker build $CACHE_ARG -t ${DOCKER_IMAGE_PREFIX}/pipeline-runner -f docker/seqr/pipeline-runner/Dockerfile docker/seqr/
if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
    docker tag ${DOCKER_IMAGE_PREFIX}/pipeline-runner ${DOCKER_IMAGE_PREFIX}/pipeline-runner:${TIMESTAMP}
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/pipeline-runner:${TIMESTAMP}
fi


kubectl apply -f configs/seqr/seqr.pipeline-runner.yaml --record
wait_until_pod_is_running pipeline-runner
