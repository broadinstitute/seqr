#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
source ${SCRIPT_DIR}/check_env.sh

set -x

if [ "$FORCE" = true ]; then
    FORCE_ARG=--no-cache
else
    FORCE_ARG=
fi

docker build $FORCE_ARG -t ${DOCKER_IMAGE_PREFIX}/seqr  docker/seqr/

if [ "$DEPLOY_TO_GOOGLE_CLOUD" = true ]; then
    gcloud docker -- push ${DOCKER_IMAGE_PREFIX}/seqr
fi

kubectl delete -f configs/seqr/seqr-deployment.yaml
kubectl create -f configs/seqr/seqr-deployment.yaml --record

kubectl delete -f configs/seqr/seqr-service.yaml
kubectl create -f configs/seqr/seqr-service.yaml --record

sleep 5

SEQR_POD_NAME=$( kubectl get pods -o=name | grep '\-seqr' | cut -f 2 -d / )
kubectl exec $SEQR_POD_NAME -- python -u manage.py migrate
