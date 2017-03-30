#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

echo USE_EXTERNAL_POSTGRES_DB: $USE_EXTERNAL_POSTGRES_DB

if [ "$USE_EXTERNAL_POSTGRES_DB" = true ]; then
    echo Deploying external postgres service
    kubectl delete -f configs/postgres/external/postgres-service.yaml
    kubectl create -f configs/postgres/external/postgres-service.yaml --record
else
    echo Deploying postgres

    docker build --no-cache -t ${DOCKER_IMAGE_PREFIX}/postgres  docker/postgres/
    if [ "DEPLOY_TO_GOOGLE_CLOUD" = true ]; then
        gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/postgres
    fi

    kubectl delete -f configs/postgres/postgres-deployment.yaml
    kubectl create -f configs/postgres/postgres-deployment.yaml --record

    kubectl delete -f configs/postgres/postgres-service.yaml
    kubectl create -f configs/postgres/postgres-service.yaml --record
fi
