#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

DEPLOYMENT_TARGET=$1

POD_NAME=$("${DIR}"/utils/get_pod_name.sh "${DEPLOYMENT_TARGET}" seqr)

kubectl exec "${POD_NAME}" -- git pull
kubectl exec "${POD_NAME}" -- pip install -r requirements.txt
kubectl exec "${POD_NAME}" -- ./manage.py migrate
kubectl exec "${POD_NAME}" -- restart_server.sh
