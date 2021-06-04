#!/usr/bin/env bash

DIR=$(dirname $BASH_SOURCE)

set -x

DEPLOYMENT_TARGET=$1

POD_NAME=$(${DIR}/utils/get_resource_name.sh pod ${DEPLOYMENT_TARGET} seqr)

kubectl exec ${POD_NAME} -- git pull
kubectl exec ${POD_NAME} -- ./manage.py migrate
kubectl exec ${POD_NAME} -- restart_server.sh
