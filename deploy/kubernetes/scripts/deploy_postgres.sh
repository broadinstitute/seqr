#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

echo USE_EXTERNAL_POSTGRES_DB: $USE_EXTERNAL_POSTGRES_DB

CACHE_ARG=
if [ "$BUILD" ]; then
    CACHE_ARG=--no-cache
fi

if [ "$USE_EXTERNAL_POSTGRES_DB" = true ]; then
    echo Deploying external postgres service

    kubectl delete -f configs/postgres/external/postgres-service.yaml
    kubectl create -f configs/postgres/external/postgres-service.yaml --record
else
    echo Deploying postgres

    if [ "$DELETE_BEFORE_DEPLOY" ]; then
        # delete any previous deployments
        kubectl delete -f configs/postgres/postgres.${DEPLOY_TO_PREFIX}.yaml
        wait_until_pod_terminates postgres
    fi

    docker build $CACHE_ARG -t ${DOCKER_IMAGE_PREFIX}/postgres  docker/postgres/
    docker tag ${DOCKER_IMAGE_PREFIX}/postgres ${DOCKER_IMAGE_PREFIX}/postgres:${TIMESTAMP}
    if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
        gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/postgres:${TIMESTAMP}
    fi

    # if the deployment doesn't exist yet, then create it, otherwise just update the image
    kubectl apply -f configs/postgres/postgres.${DEPLOY_TO_PREFIX}.yaml
    wait_until_pod_is_running postgres
fi

