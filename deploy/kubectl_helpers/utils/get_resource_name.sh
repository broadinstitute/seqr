#!/usr/bin/env bash

RESOURCE_TYPE=$1
DEPLOYMENT_TARGET=$2
COMPONENT=$3

kubectl get ${RESOURCE_TYPE} -l name=${COMPONENT},deployment=gcloud-${DEPLOYMENT_TARGET} -o jsonpath="{.items[0].metadata.name}"
