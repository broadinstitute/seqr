#!/usr/bin/env bash

DIR=$(dirname $BASH_SOURCE)

set -x  -e

DEPLOYMENT_TARGET=$1
COMPONENT=$2

POD_NAME=$(${DIR}/utils/get_pod_name.sh ${DEPLOYMENT_TARGET} ${COMPONENT})

kubectl exec -it ${POD_NAME} -- /bin/bash
