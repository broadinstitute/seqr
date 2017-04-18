#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

# delete any previous deployments
kubectl delete -f configs/mongo/mongo-deployment.${DEPLOY_TO}.yaml
kubectl delete -f configs/mongo/mongo-service.yaml

FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/mongo  docker/mongo/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/mongo
fi

kubectl create -f configs/mongo/mongo-deployment.${DEPLOY_TO}.yaml --record
kubectl create -f configs/mongo/mongo-service.yaml --record

# wait for pod to start
set +x
while [ ! "$( kubectl get pods | grep 'mongo-' | grep Running)" ] || [ "$( kubectl get pods | grep 'mongo-' | grep Terminating)" ]; do
    echo $(date) - Waiting for mongo pod to enter "Running" state. Current state is: "$( kubectl get pods | grep 'mongo-' )"
    sleep 5
done
echo $(date) - Success. Current state is: "$( kubectl get pods | grep 'mongo-' )"
set -x
