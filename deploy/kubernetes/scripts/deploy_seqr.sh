#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

# delete any previous deployments
kubectl delete -f configs/seqr/seqr-deployment.${DEPLOY_TO}.yaml
kubectl delete -f configs/seqr/seqr-service.yaml

# docker build
FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
else
    FORCE_ARG="--build-arg DISABLE_CACHE=$(date +%s)"
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/seqr docker/seqr/${DEPLOY_TO}/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    # gcloud beta container images delete gcr.io/seqr-project/seqr  --resolve-tag-to-digest --force-delete-tags
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/seqr
fi

# reset the db if needed
POSTGRES_POD_NAME=$( kubectl get pods -o=name | grep 'postgres-' | cut -f 2 -d / | tail -n 1 )
if [ "$RESET_PHENOTIPS_DB" = true ]; then
    kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'drop database seqrdb'
fi
kubectl exec $POSTGRES_POD_NAME -- psql -U postgres postgres -c 'create database seqrdb'


# create new deployment
kubectl create -f configs/seqr/seqr-deployment.${DEPLOY_TO}.yaml --record
kubectl create -f configs/seqr/seqr-service.yaml --record

# wait for pod to start
set +x
while [ ! "$( kubectl get pods | grep 'seqr-' | grep Running)" ] || [ "$( kubectl get pods | grep 'seqr-' | grep Terminating)" ]; do
    echo $(date) - Waiting for seqr pod to enter "Running" state. Current state is: "$( kubectl get pods | grep 'seqr-' )"
    sleep 5
done
echo $(date) - Success. Current state is: "$( kubectl get pods | grep 'seqr-' )"
set -x

# migrate the database if needed
SEQR_POD_NAME=$( kubectl get pods -o=name | grep 'seqr-' | cut -f 2 -d / | tail -n 1)
kubectl exec $SEQR_POD_NAME -- python -u manage.py migrate

kubectl exec $SEQR_POD_NAME -- python -u manage.py check
