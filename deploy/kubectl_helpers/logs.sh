#!/usr/bin/env bash

DIR=$(dirname $BASH_SOURCE)

set -x

DEPLOYMENT_TARGET=$1
COMPONENT=$2

POD_NAME=$(${DIR}/utils/get_resource_name.sh pod ${DEPLOYMENT_TARGET} ${COMPONENT})

kubectl logs -f ${POD_NAME} --all-containers
