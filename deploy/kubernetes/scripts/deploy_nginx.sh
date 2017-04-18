#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -xe

# delete any previous deployments
kubectl delete -f configs/nginx/nginx-deployment.${DEPLOY_TO}.yaml
kubectl delete -f configs/nginx/nginx-service.yaml

FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/nginx  docker/nginx/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/nginx
fi

kubectl create -f configs/nginx/nginx-deployment.${DEPLOY_TO}.yaml --record
kubectl create -f configs/nginx/nginx-service.yaml --record

# wait for pod to start
set +x
while [ ! "$( kubectl get pods | grep 'nginx-' | grep Running)" ] || [ "$( kubectl get pods | grep 'nginx-' | grep Terminating)" ]; do
    echo $(date) - Waiting for nginx pod to enter "Running" state. Current state is: "$( kubectl get pods | grep 'nginx-' )"
    sleep 5
done
echo $(date) - Success. Current state is: "$( kubectl get pods | grep 'nginx-' )"
set -x
