#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

# docker build
CACHE_ARG=
if [ "$BUILD" ]; then
    CACHE_ARG=--no-cache
#else
#    CACHE_ARG="--build-arg DISABLE_CACHE=$(date +%s)"
fi

docker build $CACHE_ARG \
    --build-arg SEQR_SERVICE_PORT=$SEQR_SERVICE_PORT \
    --build-arg SEQR_UI_DEV_PORT=$SEQR_UI_DEV_PORT \
    -t ${DOCKER_IMAGE_PREFIX}/seqr \
    -f docker/seqr/${DEPLOY_TO_PREFIX}/Dockerfile docker/seqr

docker tag ${DOCKER_IMAGE_PREFIX}/seqr ${DOCKER_IMAGE_PREFIX}/seqr:${TIMESTAMP}
if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
    # gcloud beta container images delete gcr.io/seqr-project/seqr  --resolve-tag-to-digest --force-delete-tags
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/seqr:${TIMESTAMP}
fi

POSTGRES_POD_NAME=$( kubectl get pods -l name=postgres -o jsonpath='{.items[0].metadata.name}' )

# reset the db if needed
if [ "$DELETE_BEFORE_DEPLOY" ]; then
    kubectl delete -f kubernetes/configs/seqr/seqr.${DEPLOY_TO_PREFIX}.yaml
    wait_until_pod_terminates seqr
elif [ "$RESET_DB" ] || [ "$RESTORE_SEQR_DB_FROM_BACKUP" ]; then
    SEQR_POD_NAME=$( kubectl get pods -o=name | grep 'seqr-' | cut -f 2 -d / | tail -n 1 )
    kubectl exec $SEQR_POD_NAME -- /usr/local/bin/stop_server.sh
fi

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

kubectl apply -f kubernetes/configs/seqr/seqr.${DEPLOY_TO_PREFIX}.yaml --record
wait_until_pod_is_running seqr

# SEQR_POD_NAME=$( kubectl get pods -o=name | grep 'seqr-' | cut -f 2 -d / | tail -n 1)
# kubectl exec $SEQR_POD_NAME -- git pull
