#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

echo USE_EXTERNAL_POSTGRES_DB: $USE_EXTERNAL_POSTGRES_DB

FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
fi


if [ "$USE_EXTERNAL_POSTGRES_DB" = true ]; then
    echo Deploying external postgres service
    kubectl delete -f configs/postgres/external/postgres-service.yaml
    kubectl create -f configs/postgres/external/postgres-service.yaml --record
else
    echo Deploying postgres

    docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/postgres  docker/postgres/
    if [ "$DEPLOY_TO" = 'gcloud' ]; then
        gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/postgres

        gcloud compute disks create --size 200GB postgres-disk --zone $GCLOUD_ZONE
    fi

    # delete any previous deployments
    kubectl delete -f configs/postgres/postgres-deployment.${DEPLOY_TO}.yaml
    kubectl delete -f configs/postgres/postgres-service.yaml

    kubectl create -f configs/postgres/postgres-deployment.${DEPLOY_TO}.yaml --record
    kubectl create -f configs/postgres/postgres-service.yaml --record
fi
