#!/usr/bin/env bash


SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

# delete any previous deployments
kubectl delete -f configs/matchbox/matchbox-deployment.${DEPLOY_TO}.yaml
kubectl delete -f configs/matchbox/matchbox-service.yaml

FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/matchbox docker/matchbox/
if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/matchbox
fi

kubectl create -f configs/matchbox/matchbox-deployment.${DEPLOY_TO}.yaml --record
kubectl create -f configs/matchbox/matchbox-service.yaml --record

# wait for pod to start
set +x
while [ ! "$( kubectl get pods | grep 'matchbox-' | grep Running)" ] || [ "$( kubectl get pods | grep 'matchbox-' | grep Terminating)" ]; do
    echo $(date) - Waiting for matchbox pod to enter "Running" state. Current state is: "$( kubectl get pods | grep 'matchbox-' )"
    sleep 5
done
echo $(date) - Success. Current state is: "$( kubectl get pods | grep 'matchbox-' )"
set -x
