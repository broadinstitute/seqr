#!/usr/bin/env bash

DEPLOYMENT_TARGET=$1
EXPECTED_CONTEXT=gke_*${DEPLOYMENT_TARGET}

if [[ ${DEPLOYMENT_TARGET} == "prototype" ]]; then
  EXPECTED_CONTEXT=gke_hail-seqr-development*
fi

CONTEXT=$(kubectl config current-context)
if [[ ${CONTEXT} != ${EXPECTED_CONTEXT} ]]; then
  echo "Invalid context for '${DEPLOYMENT_TARGET}': ${CONTEXT}"
  exit 1
fi
