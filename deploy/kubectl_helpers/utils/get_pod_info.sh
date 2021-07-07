#!/usr/bin/env bash

set -u

DEPLOYMENT_TARGET=$1
COMPONENT=$2
JSON_PATH=$3


kubectl get pod -l "name=${COMPONENT},deployment=gcloud-${DEPLOYMENT_TARGET}" -o "jsonpath=${JSON_PATH}"
