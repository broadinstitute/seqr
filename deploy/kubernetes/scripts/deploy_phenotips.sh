#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/init_env.sh
set -x

function kill_phenotips {
    # delete any previous deployments
    kubectl delete -f configs/phenotips/phenotips.${DEPLOY_TO_PREFIX}.yaml
}

function deploy_phenotips {
    kubectl apply -f configs/phenotips/phenotips.${DEPLOY_TO_PREFIX}.yaml
}

set -x

# reset the db if needed
POSTGRES_POD_NAME=$( kubectl get pods -o=name | grep 'postgres-' | cut -f 2 -d / | tail -n 1 )
if [ "$RESET_DB" ] || [ "$RESTORE_PHENOTIPS_DB_FROM_BACKUP" ]; then
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
CACHE_ARG=
if [ "$BUILD" ]; then
    CACHE_ARG=--no-cache
fi

docker build $CACHE_ARG --build-arg PHENOTIPS_PORT=$PHENOTIPS_PORT -t ${DOCKER_IMAGE_PREFIX}/phenotips docker/phenotips/
docker tag ${DOCKER_IMAGE_PREFIX}/phenotips ${DOCKER_IMAGE_PREFIX}/phenotips:${TIMESTAMP}
if [ "$DEPLOY_TO_PREFIX" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/phenotips:${TIMESTAMP}
fi

# if the deployment doesn't exist yet, then create it, otherwise just update the image
deploy_phenotips
wait_until_pod_is_running phenotips


# when the PhenoTips website is opened for the 1st time, it triggers a final set of initialization
# steps, so do wget's to trigger this
PHENOTIPS_POD_NAME=$( kubectl get pods -o=name | grep 'phenotips-' | cut -f 2 -d / | tail -n 1)
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:${PHENOTIPS_PORT} -O test.html
sleep 15
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:${PHENOTIPS_PORT} -O test.html
sleep 15
kubectl exec $PHENOTIPS_POD_NAME -- wget http://localhost:${PHENOTIPS_PORT} -O test.html


if [ "$RESTORE_PHENOTIPS_DB_FROM_BACKUP" ]; then
    kill_phenotips
    wait_until_pod_terminates phenotips

    kubectl cp $RESTORE_PHENOTIPS_DB_FROM_BACKUP ${POSTGRES_POD_NAME}:/root/$(basename $RESTORE_PHENOTIPS_DB_FROM_BACKUP)
    kubectl exec $POSTGRES_POD_NAME -- /root/restore_database_backup.sh  xwiki  xwiki  /root/$(basename $RESTORE_PHENOTIPS_DB_FROM_BACKUP)
    kubectl exec $POSTGRES_POD_NAME -- rm /root/$(basename $RESTORE_DB_FROM_BACKUP)

    deploy_phenotips
    wait_until_pod_is_running phenotips
fi

