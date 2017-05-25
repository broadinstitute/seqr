#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

function kill_phenotips {
    # delete any previous deployments
    kubectl delete -f configs/phenotips/phenotips-deployment.${DEPLOY_TO}.yaml
    kubectl delete -f configs/phenotips/phenotips-service.yaml
}

function deploy_phenotips {
    kubectl create -f configs/phenotips/phenotips-deployment.${DEPLOY_TO}.yaml --record
    kubectl create -f configs/phenotips/phenotips-service.yaml --record
}

set -x

# reset the db if needed
POSTGRES_POD_NAME=$( kubectl get pods -o=name | grep 'postgres-' | cut -f 2 -d / | tail -n 1 )
if [ "$RESET_DB" ] || [ "$RESTORE_PHENOTIPS_DB_FROM_BACKUP" != "none" ]; then
    kill_phenotips
    wait_until_pod_terminates phenotips

    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c "create role xwiki with CREATEDB LOGIN PASSWORD 'xwiki'"
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database xwiki'
    kubectl exec $POSTGRES_POD_NAME -- psql -U xwiki postgres -c 'create database xwiki'
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'grant all privileges on database xwiki to xwiki'

elif [ "$DELETE_BEFORE_DEPLOY" ]; then
    kill_phenotips
    wait_until_pod_terminates phenotips
fi


# build docker image
BUILD_ARG=
if [ "$BUILD" ]; then
    BUILD_ARG=--no-cache
fi

docker build $BUILD_ARG -t ${DOCKER_IMAGE_PREFIX}/phenotips  docker/phenotips/

if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/phenotips
fi

# if the deployment doesn't exist yet, then create it, otherwise just update the image
PHENOTIPS_POD_NAME=$( kubectl get pods -o=name | grep 'phenotips-' | cut -f 2 -d / | tail -n 1 )
if [ "$PHENOTIPS_POD_NAME" ]; then
    kubectl set image -f configs/phenotips/phenotips-deployment.${DEPLOY_TO}.yaml --record
    #kubectl edit -f configs/phenotips/phenotips-service.yaml --record
else
    deploy_phenotips
    wait_until_pod_is_running phenotips
fi

# when the PhenoTips website is opened for the 1st time, it triggers a final set of initialization
# steps, so do wget's to trigger this
PHENOTIPS_POD_NAME=$( kubectl get pods -o=name | grep 'phenotips-' | cut -f 2 -d / | tail -n 1)
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:8080 -O test.html
sleep 15
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:8080 -O test.html
sleep 15
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:8080 -O test.html


if [ "$RESTORE_PHENOTIPS_DB_FROM_BACKUP" != "none" ]; then
    kill_phenotips
    wait_until_pod_terminates phenotips

    kubectl cp $RESTORE_PHENOTIPS_DB_FROM_BACKUP ${POSTGRES_POD_NAME}:/root/$(basename $RESTORE_PHENOTIPS_DB_FROM_BACKUP)
    kubectl exec $POSTGRES_POD_NAME -- /root/restore_database_backup.sh  xwiki  xwiki  /root/$(basename $RESTORE_PHENOTIPS_DB_FROM_BACKUP)
    kubectl exec $POSTGRES_POD_NAME -- rm /root/$(basename $RESTORE_DB_FROM_BACKUP)

    deploy_phenotips
fi

wait_until_pod_is_running phenotips
