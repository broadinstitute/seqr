#!/usr/bin/env bash

DIR=$(dirname $BASH_SOURCE)

DEPLOYMENT_TARGET=$1
CONTEXT=$(kubectl config current-context)
if [[ ${CONTEXT} != gke_*${DEPLOYMENT_TARGET} ]]; then
  echo "Invalid context for '${DEPLOYMENT_TARGET}': ${CONTEXT}"
  exit 1
fi

STATUS=$(${DIR}/get_pod_info.sh "$@" "{.items[0].status.phase}")
if [ ${STATUS} != "Running" ]; then
    echo "Invalid pod status: ${STATUS}"
    exit 1
fi

${DIR}/get_pod_info.sh "$@" "{.items[0].metadata.name}"