#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

echo ===============================

# delete any previous deployments
kubectl delete -f configs/seqr/seqr-deployment.${DEPLOY_TO}.yaml
kubectl delete -f configs/seqr/seqr-service.yaml

echo ===============================

# docker build
FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
fi

if [ "$DEPLOY_TO" = 'gcloud' ]; then
    docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/seqr  docker/seqr/gcloud/
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/seqr
else
    docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/seqr  docker/seqr/local/
fi

echo ===============================

if [ "$RESET_PHENOTIPSDB" = true ] || [ "$RESET_SEQRDB" = true ] || [ "$RESET_MONGODB" = true ]; then
    sleep 20
fi


# create a clean postgres database
POSTGRES_POD_NAME=$( kubectl get pods -o=name | grep 'postgres-' | cut -f 2 -d / | tail -n 1)
if [ "$RESET_PHENOTIPSDB" = true ]; then
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database xwiki'
fi
kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'create database xwiki'

POSTGRES_POD_NAME=$( kubectl get pods -o=name | grep 'postgres-' | cut -f 2 -d / | tail -n 1)
if [ "$RESET_SEQRDB" = true ]; then
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database seqrdb'
fi
kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'create database seqrdb'


# create a clean mongo database
if [ "$RESET_MONGODB" = true ]; then
    MONGO_POD_NAME=$( kubectl get pods -o=name | grep 'mongo-' | cut -f 2 -d / | tail -n 1)

    kubectl exec $MONGO_POD_NAME -- mongo datastore --eval 'db.dropDatabase()'
fi

echo ===============================

# create new deployment
kubectl create -f configs/seqr/seqr-deployment.${DEPLOY_TO}.yaml --record
kubectl create -f configs/seqr/seqr-service.yaml --record

sleep 5

# migrate the database if needed
SEQR_POD_NAME=$( kubectl get pods -o=name | grep 'seqr-' | cut -f 2 -d / | tail -n 1)
kubectl exec $SEQR_POD_NAME -- python -u manage.py migrate
