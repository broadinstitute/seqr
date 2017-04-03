#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x


# delete any previous deployments
kubectl delete -f configs/seqr/seqr-deployment.yaml
kubectl delete -f configs/seqr/seqr-service.yaml

FORCE_ARG=
if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/seqr  docker/seqr/

if [ "$DEPLOY_TO" = 'gcloud' ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/seqr
fi

kubectl create -f configs/seqr/seqr-deployment.yaml --record
kubectl create -f configs/seqr/seqr-service.yaml --record

sleep 5

SEQR_POD_NAME=$( kubectl get pods -o=name | grep 'seqr-' | cut -f 2 -d / )
kubectl exec $SEQR_POD_NAME -- python -u manage.py migrate
