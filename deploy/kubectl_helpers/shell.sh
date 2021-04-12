#!/usr/bin/env bash

set -x

DEPLOYMENT_TARGET=$1
COMPONENT=$2
DIR=$(dirname $BASH_SOURCE)

POD_NAME=$(${DIR}/utils/get_resource_name.sh pod ${DEPLOYMENT_TARGET} ${COMPONENT})

kubectl exec -it ${POD_NAME} -- /bin/bash
