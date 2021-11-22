#!/usr/bin/env bash

set -u

DEPLOYMENT_TARGET=$1
COMPONENT=$2
JSON_PATH=$3

case ${DEPLOYMENT_TARGET} in
  dev)
    DEPLOYMENT_TARGET=gcloud-${DEPLOYMENT_TARGET}
    ;;
  prod)
    DEPLOYMENT_TARGET=gcloud-${DEPLOYMENT_TARGET}
    ;;
esac


kubectl get pod -l "name=${COMPONENT},deployment=${DEPLOYMENT_TARGET}" -o "jsonpath=${JSON_PATH}"
