#!/usr/bin/env bash

DEPLOYMENT_TARGET=$1
CONTEXT=$(kubectl config current-context)
if [[ ${CONTEXT} != gke_*${DEPLOYMENT_TARGET} ]]; then
  echo "Invalid context for '${DEPLOYMENT_TARGET}': ${CONTEXT}"
  exit 1
fi
