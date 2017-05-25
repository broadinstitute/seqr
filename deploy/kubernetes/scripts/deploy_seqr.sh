#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

# docker build
BUILD_ARG=
if [ "$BUILD" ]; then
    BUILD_ARG=--no-cache
#else
#    BUILD_ARG="--build-arg DISABLE_CACHE=$(date +%s)"
fi

docker build $BUILD_ARG -t ${DOCKER_IMAGE_PREFIX}/seqr -f docker/seqr/${DEPLOY_TO}/Dockerfile docker/seqr/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    # gcloud beta container images delete gcr.io/seqr-project/seqr  --resolve-tag-to-digest --force-delete-tags
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/seqr
fi

# reset the db if needed
if [ "$RESET_DB" ] || [ "$RESTORE_SEQR_DB_FROM_BACKUP" != "none" ]; then
    kubectl delete -f configs/seqr/seqr-deployment.${DEPLOY_TO}.yaml
    kubectl delete -f configs/seqr/seqr-service.yaml

    wait_until_pod_terminates seqr
fi

POSTGRES_POD_NAME=$( kubectl get pods -o=name | grep 'postgres-' | cut -f 2 -d / | tail -n 1 )
if [ "$RESET_DB" ]; then
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database seqrdb'
fi

if [ "$RESTORE_SEQR_DB_FROM_BACKUP" ]; then
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database seqrdb'
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'create database seqrdb'
    kubectl cp $RESTORE_SEQR_DB_FROM_BACKUP ${POSTGRES_POD_NAME}:/root/$(basename $RESTORE_SEQR_DB_FROM_BACKUP)
    kubectl exec $POSTGRES_POD_NAME -- /root/restore_database_backup.sh postgres seqrdb /root/$(basename $RESTORE_SEQR_DB_FROM_BACKUP)
    kubectl exec $POSTGRES_POD_NAME -- rm /root/$(basename $RESTORE_SEQR_DB_FROM_BACKUP)
else
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'create database seqrdb'
fi

# if the deployment doesn't exist yet, then create it, otherwise just update the image
SEQR_POD_NAME=$( kubectl get pods -o=name | grep 'seqr-' | cut -f 2 -d / | tail -n 1 )
if [ "$SEQR_POD_NAME" ]; then
    kubectl set image -f configs/seqr/seqr-deployment.${DEPLOY_TO}.yaml --record
    #kubectl edit -f configs/seqr/seqr-service.yaml --record
else
    kubectl create -f configs/seqr/seqr-deployment.${DEPLOY_TO}.yaml --record
    kubectl create -f configs/seqr/seqr-service.yaml --record
fi

# wait for pod to start
wait_until_pod_is_running seqr

# SEQR_POD_NAME=$( kubectl get pods -o=name | grep 'seqr-' | cut -f 2 -d / | tail -n 1)
# kubectl exec $SEQR_POD_NAME -- git pull
