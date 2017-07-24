#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

if [ "$DELETE_BEFORE_DEPLOY" ]; then
    kubectl delete -f kubernetes/configs/elasticsearch/elasticsearch.${DEPLOY_TO_PREFIX}.yaml
    wait_until_pod_terminates elasticsearch
fi

CACHE_ARG=
if [ "$BUILD" ]; then
    CACHE_ARG=--no-cache
fi

docker build $CACHE_ARG --build-arg ELASTICSEARCH_SERVICE_PORT=$ELASTICSEARCH_SERVICE_PORT -t ${DOCKER_IMAGE_PREFIX}/elasticsearch docker/elasticsearch/
docker tag ${DOCKER_IMAGE_PREFIX}/elasticsearch ${DOCKER_IMAGE_PREFIX}/elasticsearch:${TIMESTAMP}
if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/elasticsearch:${TIMESTAMP}
fi

# if the deployment doesn't exist yet, then create it, otherwise just update the image
kubectl apply -f kubernetes/configs/elasticsearch/elasticsearch.${DEPLOY_TO_PREFIX}.yaml --record
wait_until_pod_is_running elasticsearch
