#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

DEPLOYMENT_TARGET=$1
COMPONENT=$2
FILE=$3
TO_POD=$4

POD_NAME=$("${DIR}"/get_pod_name.sh "${DEPLOYMENT_TARGET}" "${COMPONENT}")
if ${TO_POD}; then
    COMMAND="${FILE} ${POD_NAME}:."
else
    COMMAND="${POD_NAME}:${FILE} ."
fi

kubectl cp "${COMMAND}"