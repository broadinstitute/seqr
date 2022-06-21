#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e -u

DEPLOYMENT_TARGET=$1
COMPONENT=$2
FILE=$3
TO_POD=$4 # boolean indicating whether to copy a file to the pod or from the pod

POD_NAME=$("${DIR}"/get_pod_name.sh "${DEPLOYMENT_TARGET}" "${COMPONENT}")
if ${TO_POD}; then
    SRC="${FILE}"
    DST="${POD_NAME}:."
else
    SRC="${POD_NAME}:${FILE}"
    DST="."
fi

kubectl cp "${SRC}" "${DST}"