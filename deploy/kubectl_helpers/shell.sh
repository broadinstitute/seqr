#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

COMPONENT=$2

POD_NAME=$("${DIR}"/utils/get_pod_name.sh "$@")

case ${COMPONENT} in
  seqr) CONTAINER=seqr-pod ;;
  *) CONTAINER=${COMPONENT} ;;
esac

kubectl exec -it "${POD_NAME}" -c "${CONTAINER}" -- /bin/bash
