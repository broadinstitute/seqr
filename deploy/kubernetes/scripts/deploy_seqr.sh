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

docker build $BUILD_ARG -t ${DOCKER_IMAGE_PREFIX}/seqr -f docker/seqr/${DEPLOY_TO_PREFIX}/Dockerfile docker/seqr/
if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
    # gcloud beta container images delete gcr.io/seqr-project/seqr  --resolve-tag-to-digest --force-delete-tags
    docker tag ${DOCKER_IMAGE_PREFIX}/seqr ${DOCKER_IMAGE_PREFIX}/seqr:${TIMESTAMP}
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/seqr:${TIMESTAMP}
fi

# reset the db if needed
if [ "$DELETE_BEFORE_DEPLOY" ] || [ "$RESET_DB" ] || [ "$RESTORE_SEQR_DB_FROM_BACKUP" ]; then
    kubectl delete -f configs/seqr/seqr.${DEPLOY_TO_PREFIX}.yaml
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

kubectl apply -f configs/seqr/seqr.${DEPLOY_TO_PREFIX}.yaml --record
wait_until_pod_is_running seqr

# SEQR_POD_NAME=$( kubectl get pods -o=name | grep 'seqr-' | cut -f 2 -d / | tail -n 1)
# kubectl exec $SEQR_POD_NAME -- git pull
