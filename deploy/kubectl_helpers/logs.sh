#!/usr/bin/env bash

DIR=$(dirname "$BASH_SOURCE")

set -x -e

POD_NAME=$("${DIR}"/utils/get_pod_name.sh "$@")

COMPONENT=$2
case ${COMPONENT} in
  hail-search) CONTAINER="-c seqr-hail-search-pod" ;;
  *) CONTAINER="--all-containers" ;;
esac

kubectl logs -f "${POD_NAME}" "${CONTAINER}"
