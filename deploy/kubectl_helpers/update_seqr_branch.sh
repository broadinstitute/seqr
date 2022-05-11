#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

DEPLOYMENT_TARGET=prototype

POD_NAME=$("${DIR}"/utils/get_pod_name.sh "${DEPLOYMENT_TARGET}" seqr)

kubectl exec "${POD_NAME}" -- git pull origin hail-backend
kubectl exec "${POD_NAME}" -- restart_server.sh
